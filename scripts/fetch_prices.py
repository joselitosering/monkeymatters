#!/usr/bin/env python3
"""
fetch_prices.py — FFF Stage 2: daily-OHLC price history cache.

Fills data/prices/<KEY>.json with daily bars for (a) the macro trackers the
FFF report renders and (b) every symbol appearing in the week's trade ideas.
Same doctrine as fetch_mmm_data.py: zero LLM calls, never hard-fails the
pipeline — a symbol that can't be fetched is simply absent from the cache
and downstream grading records it as no_data instead of guessing.

Source ladder per symbol (first rung that yields bars wins; each cached bar
records its source so grading evidence stays honest):
  1. cache        data/prices/<KEY>.json (merged; fetched once, kept forever)
  2. FMP stable   /stable/historical-price-eod/full?symbol=X   <-- sibling of
                  the ONE confirmed-live endpoint (/stable/quote). Shape is
                  VERIFIED AT RUNTIME (list of {date,open,high,low,close}),
                  and on any failure we fall back to the legacy
                  /api/v3/historical-price-full/{sym} shape. Whichever shape
                  answered is logged — per WEEKLY_PIPELINE_HANDOFF.md's
                  "verify the real endpoint empirically" rule.
  3. Schwab       marketdata/v1/pricehistory (daily candles) — for /ES, /NQ,
                  $DXY and anything FMP can't serve. Same refresh-token
                  reality as the daily fetch: token dies ~7 days, fails
                  closed to "absent", never breaks the run.
  4. FMP quote    same-day synthetic bar: after the close, /stable/quote's
                  open/dayHigh/dayLow/price ARE today's daily bar. Lets the
                  Friday 2:10 PM PT run grade Friday without waiting for the
                  EOD history endpoint to catch up. Marked src:"quote-synth".

Cache format (data/prices/<KEY>.json):
  [{"date":"YYYY-MM-DD","open":..,"high":..,"low":..,"close":..,
    "volume":..,"src":"fmp-stable|fmp-v3|schwab|quote-synth"}, ...]
KEY: FMP symbol with ^ -> IDX_ ("^GSPC" -> IDX_GSPC), Schwab "/ES" -> FUT_ES,
"$DXY" -> IDX_DXY. See key_for().
"""
from __future__ import annotations
import json, sys, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import urllib.request, urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_mmm_data import env_or_dotenv  # env-then-.env convention, BOM-safe

ROOT = Path(__file__).resolve().parent.parent
PRICES_DIR = ROOT / "data" / "prices"
PT = ZoneInfo("America/Los_Angeles")

FMP_STABLE_EOD = "https://financialmodelingprep.com/stable/historical-price-eod/full"
FMP_V3_EOD = "https://financialmodelingprep.com/api/v3/historical-price-full/{sym}"
FMP_QUOTE = "https://financialmodelingprep.com/stable/quote"
SCHWAB_TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"
SCHWAB_HISTORY_URL = "https://api.schwabapi.com/marketdata/v1/pricehistory"

# Macro trackers the FFF report always wants (label -> fetch symbol).
# Schwab-only symbols (futures, $DXY) route to rung 3 automatically.
TRACKER_SYMBOLS = ["^GSPC", "^IXIC", "GCUSD", "SIUSD", "BTCUSD", "ETHUSD", "BZUSD", "$DXY"]
SCHWAB_ONLY = {"$DXY", "/ES", "/NQ", "/MES", "/MNQ"}


def key_for(symbol: str) -> str:
    s = symbol.strip()
    if s.startswith("/"):
        return "FUT_" + s[1:].upper()
    if s.startswith("$"):
        return "IDX_" + s[1:].upper()
    if s.startswith("^"):
        return "IDX_" + s[1:].upper()
    return s.upper()


def _get_json(url: str, headers: dict | None = None, timeout: int = 20):
    req = urllib.request.Request(url, headers={"User-Agent": "shadowmonkey-fff/1.0", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _norm_bar(row: dict, src: str) -> dict | None:
    try:
        bar = {
            "date": str(row["date"])[:10],
            "open": float(row["open"]), "high": float(row["high"]),
            "low": float(row["low"]), "close": float(row["close"]),
            "volume": row.get("volume"), "src": src,
        }
        if bar["high"] < bar["low"]:
            return None
        return bar
    except (KeyError, TypeError, ValueError):
        return None


def fmp_history(symbol: str, frm: str, to: str, api_key: str) -> list[dict]:
    """Try /stable first, verify shape, fall back to legacy /api/v3."""
    try:
        url = FMP_STABLE_EOD + "?" + urllib.parse.urlencode(
            {"symbol": symbol, "from": frm, "to": to, "apikey": api_key})
        data = _get_json(url)
        rows = data if isinstance(data, list) else data.get("historical", [])
        bars = [b for b in (_norm_bar(r, "fmp-stable") for r in rows) if b]
        if bars:
            print(f"  {symbol}: {len(bars)} bars via fmp-stable")
            return bars
        print(f"  {symbol}: fmp-stable answered but no usable bars ({str(data)[:120]})", file=sys.stderr)
    except Exception as e:
        print(f"  {symbol}: fmp-stable failed ({e}) — trying legacy v3", file=sys.stderr)
    try:
        url = FMP_V3_EOD.format(sym=urllib.parse.quote(symbol)) + "?" + urllib.parse.urlencode(
            {"from": frm, "to": to, "apikey": api_key})
        data = _get_json(url)
        rows = data.get("historical", []) if isinstance(data, dict) else data
        bars = [b for b in (_norm_bar(r, "fmp-v3") for r in rows) if b]
        if bars:
            print(f"  {symbol}: {len(bars)} bars via fmp-v3 (legacy)")
        return bars
    except Exception as e:
        print(f"  {symbol}: fmp-v3 failed too ({e})", file=sys.stderr)
        return []


def fmp_quote_synth_bar(symbol: str, api_key: str, for_date: str) -> dict | None:
    """After the close, today's quote fields ARE today's daily bar."""
    try:
        url = FMP_QUOTE + "?" + urllib.parse.urlencode({"symbol": symbol, "apikey": api_key})
        data = _get_json(url)
        q = data[0] if isinstance(data, list) and data else None
        if not q:
            return None
        bar = _norm_bar({"date": for_date, "open": q.get("open"),
                         "high": q.get("dayHigh"), "low": q.get("dayLow"),
                         "close": q.get("price"), "volume": q.get("volume")}, "quote-synth")
        if bar:
            print(f"  {symbol}: same-day bar synthesized from /stable/quote")
        return bar
    except Exception as e:
        print(f"  {symbol}: quote-synth failed ({e})", file=sys.stderr)
        return None


def schwab_access_token() -> str:
    client_id = env_or_dotenv("SCHWAB_CLIENT_ID")
    client_secret = env_or_dotenv("SCHWAB_CLIENT_SECRET")
    refresh_token = env_or_dotenv("SCHWAB_REFRESH_TOKEN")
    if not refresh_token:
        tok_path_str = env_or_dotenv("SCHWAB_TOKEN_PATH") or ".secrets/schwab_token.json"
        tok_path = Path(tok_path_str)
        if not tok_path.is_absolute():
            tok_path = ROOT / tok_path
        if tok_path.exists():
            try:
                refresh_token = json.loads(tok_path.read_text(encoding="utf-8")).get("refresh_token", "")
            except Exception:
                pass
    if not (client_id and client_secret and refresh_token):
        return ""
    try:
        body = urllib.parse.urlencode(
            {"grant_type": "refresh_token", "refresh_token": refresh_token}).encode()
        basic = __import__("base64").b64encode(f"{client_id}:{client_secret}".encode()).decode()
        req = urllib.request.Request(
            SCHWAB_TOKEN_URL, data=body,
            headers={"Authorization": f"Basic {basic}",
                     "Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode()).get("access_token", "")
    except Exception as e:
        print(f"WARN: Schwab token refresh failed ({e}) — Schwab rung disabled this run", file=sys.stderr)
        return ""


def schwab_history(symbol: str, frm: str, to: str, access_token: str) -> list[dict]:
    if not access_token:
        return []
    try:
        start_ms = int(datetime.datetime.strptime(frm, "%Y-%m-%d")
                       .replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
        end_ms = int((datetime.datetime.strptime(to, "%Y-%m-%d")
                      + datetime.timedelta(days=1))
                     .replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
        url = SCHWAB_HISTORY_URL + "?" + urllib.parse.urlencode({
            "symbol": symbol, "periodType": "month", "frequencyType": "daily",
            "frequency": 1, "startDate": start_ms, "endDate": end_ms,
            "needExtendedHoursData": "false"})
        data = _get_json(url, headers={"Authorization": f"Bearer {access_token}",
                                       "Accept": "application/json"})
        bars = []
        for c in data.get("candles", []):
            d = datetime.datetime.fromtimestamp(c["datetime"] / 1000,
                                                tz=datetime.timezone.utc).strftime("%Y-%m-%d")
            b = _norm_bar({"date": d, **c}, "schwab")
            if b:
                bars.append(b)
        if bars:
            print(f"  {symbol}: {len(bars)} bars via schwab")
        return bars
    except Exception as e:
        print(f"  {symbol}: schwab history failed ({e})", file=sys.stderr)
        return []


def load_cache(key: str) -> list[dict]:
    p = PRICES_DIR / f"{key}.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_cache(key: str, bars: list[dict]) -> None:
    dedup = {}
    for b in sorted(bars, key=lambda x: (x["date"], x.get("src") == "quote-synth")):
        # real EOD bars overwrite quote-synth for the same date, never vice versa
        if b["date"] not in dedup or dedup[b["date"]].get("src") == "quote-synth":
            dedup[b["date"]] = b
    PRICES_DIR.mkdir(parents=True, exist_ok=True)
    (PRICES_DIR / f"{key}.json").write_text(
        json.dumps(sorted(dedup.values(), key=lambda x: x["date"]), indent=1), encoding="utf-8")


def ensure_bars(symbols: list[str], frm: str, to: str) -> dict[str, list[dict]]:
    """Guarantee-best-effort: returns {key: bars-within-range}. Missing
    symbols simply come back absent."""
    api_key = env_or_dotenv("FMP_API_KEY")
    schwab_token = None  # lazy — only mint if a schwab-routed symbol shows up
    today_pt = datetime.datetime.now(PT).strftime("%Y-%m-%d")
    out = {}
    for sym in dict.fromkeys(symbols):          # de-dupe, keep order
        key = key_for(sym)
        cached = load_cache(key)
        have = {b["date"] for b in cached if b.get("src") != "quote-synth"}
        want = _trading_days(frm, to)
        missing = [d for d in want if d not in have]
        if missing:
            fresh = []
            if sym in SCHWAB_ONLY or sym.startswith("/") or sym.startswith("$"):
                if schwab_token is None:
                    schwab_token = schwab_access_token()
                fresh = schwab_history(sym, frm, to, schwab_token)
            elif api_key:
                fresh = fmp_history(sym, frm, to, api_key)
                if not fresh and schwab_token != "":
                    if schwab_token is None:
                        schwab_token = schwab_access_token()
                    fresh = schwab_history(sym, frm, to, schwab_token)
            # same-day synthetic bar if today is in range and still missing
            got_dates = have | {b["date"] for b in fresh}
            if api_key and today_pt in want and today_pt not in got_dates and not sym.startswith(("/", "$")):
                sb = fmp_quote_synth_bar(sym, api_key, today_pt)
                if sb:
                    fresh.append(sb)
            if fresh:
                save_cache(key, cached + fresh)
                cached = load_cache(key)
        out[key] = [b for b in cached if frm <= b["date"] <= to]
        if not out[key]:
            print(f"  {sym}: NO BARS available ({frm}..{to}) — downstream will mark no_data")
    return out


def _trading_days(frm: str, to: str) -> list[str]:
    d = datetime.datetime.strptime(frm, "%Y-%m-%d").date()
    end = datetime.datetime.strptime(to, "%Y-%m-%d").date()
    days = []
    while d <= end:
        if d.weekday() < 5:
            days.append(d.strftime("%Y-%m-%d"))
        d += datetime.timedelta(days=1)
    return days


if __name__ == "__main__":
    # manual test: python scripts/fetch_prices.py 2026-08-10 2026-08-14 [SYM ...]
    frm = sys.argv[1] if len(sys.argv) > 1 else datetime.datetime.now(PT).strftime("%Y-%m-%d")
    to = sys.argv[2] if len(sys.argv) > 2 else frm
    syms = sys.argv[3:] or TRACKER_SYMBOLS
    got = ensure_bars(syms, frm, to)
    for k, v in got.items():
        print(k, f"{len(v)} bars", v[-1] if v else "")
