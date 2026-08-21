#!/usr/bin/env python3
"""
fetch_mmm_data.py — Shadow Monkey Morning Market Monitor, DATA-ONLY pass.

Hybrid design (Joe, 2026-08-18): split hard numbers from qualitative
analysis so the numbers can run on a pure cron with NO LLM call and NO
Anthropic API key — Joe is on a Max plan and does not want separate API
billing. This script does ONLY what's deterministic:
  - real date/day-of-week (kills the recurring "wrong weekday" bug)
  - real KPI-bar numbers from FMP's direct REST API (confirmed working
    endpoints on Joe's current plan: index-quote, cryptocurrency-quote-
    short, commodities-quote-short — NOT the batch "quote" endpoint,
    which the FMP MCP tool showed is plan-gated)
  - fills ONLY the tokens it can ground in a real number
  - leaves every qualitative field (advisory, CA_* analysis blocks,
    catalyst alerts, econ calendar, earnings watch, gainers/decliners,
    sector rotation, spotlight, options ideas, money flow, unusual
    options, and the 20-row trade table) as an explicit PENDING marker
    UNLESS a same-day insert file already supplies them (see
    data/daily/YYYY-MM-DD.insert.json, written by the on-demand pass —
    a live Claude session, run whenever Joe asks, using chat usage
    already covered by his subscription, not a separate API call).

True CME futures premarket levels (/ES, /NQ) are not reliably available
without a paid futures feed at this tier — this script honestly labels
the KPI tiles as cash-index-derived rather than silently mislabeling
them as futures.
"""
from __future__ import annotations
import os, re, sys, json, subprocess, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import urllib.request
import urllib.parse

ROOT = Path(__file__).resolve().parent.parent
# Repo layout as of 2026-08-18 (Joe): shadowmonkey/ is THE public folder --
# index.html, mmm-daily/, mmm-weekly/ all live inside it, separate from
# repo internals (hhh/, turtleshell/, scripts/, data/, template/ source).
# Pages publishes shadowmonkey/ only (see pages-deploy.yml).
TEMPLATE_PATH = ROOT / "template" / "mmm_template.html"
OUT_DIR = ROOT / "shadowmonkey" / "mmm-daily"
DATA_DIR = ROOT / "data" / "daily"
INDEX_PATH = ROOT / "shadowmonkey" / "index.html"
PT = ZoneInfo("America/Los_Angeles")

TARGET_HOUR, TARGET_MIN, WINDOW_MIN = 6, 10, 20  # trigger target; deadline is 6:25 (see mmm-daily.yml)
# Verified directly against FMP's raw REST API 2026-08-18 -- the per-asset-
# class endpoint names used by the FMP MCP tool (index-quote,
# cryptocurrency-quote-short, commodities-quote-short) are an internal MCP
# abstraction, not real URL paths; hitting them directly 404s. The single
# generic /stable/quote?symbol=X endpoint covers indices, crypto, and
# commodities alike -- confirmed with a live call per asset class before
# committing to this design, not assumed from docs.
FMP_QUOTE_URL = "https://financialmodelingprep.com/stable/quote"

# symbol -> (fmp symbol, decimals)
SOURCES = {
    "VIX":  ("^VIX",   1),
    "SPX":  ("^GSPC",  2),
    "GOLD": ("GCUSD",  2),
    "BTC":  ("BTCUSD", 2),
    "ETH":  ("ETHUSD", 2),
}

SCHWAB_TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"
SCHWAB_QUOTES_URL = "https://api.schwabapi.com/marketdata/v1/quotes"


def fetch_schwab_futures() -> dict:
    """Real /ES /NQ futures via Schwab's Market Data scope -- confirmed
    working 2026-08-18 (Joe completed OAuth; the earlier blocker was an
    unregistered SCHWAB_CALLBACK_URL, not credentials, and separately the
    accounts endpoint needs a different app scope than market data does --
    this only touches market data). NEVER hard-fails the pipeline: any
    problem here (env vars missing, refresh token expired, network) returns
    an empty dict and the caller falls back to the FMP cash-index proxy.

    Maintenance reality, not hidden: Schwab refresh tokens die every ~7
    days and can only be renewed via the browser-based schwab_auth.py flow
    -- there is no way to make this self-heal in an unattended cron. When
    SCHWAB_REFRESH_TOKEN goes stale, this function fails closed (silently
    returns {}) and the KPI bar quietly reverts to the FMP proxy rather
    than breaking the whole report -- but real futures data stops flowing
    until the secret is refreshed by hand.
    """
    client_id = env_or_dotenv("SCHWAB_CLIENT_ID")
    client_secret = env_or_dotenv("SCHWAB_CLIENT_SECRET")
    refresh_token = env_or_dotenv("SCHWAB_REFRESH_TOKEN")
    if not refresh_token:
        # Local-testing convenience: GH Actions gets this from the
        # SCHWAB_REFRESH_TOKEN secret (no token file is ever checked out
        # there); locally, read straight from the token file schwab_auth.py
        # already wrote, same as schwab_hhh_fetch.py does.
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
        return {}
    try:
        body = urllib.parse.urlencode(
            {"grant_type": "refresh_token", "refresh_token": refresh_token}
        ).encode()
        basic = __import__("base64").b64encode(f"{client_id}:{client_secret}".encode()).decode()
        req = urllib.request.Request(
            SCHWAB_TOKEN_URL, data=body,
            headers={"Authorization": f"Basic {basic}",
                     "Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            access_token = json.loads(resp.read().decode())["access_token"]

        url = SCHWAB_QUOTES_URL + "?" + urllib.parse.urlencode({"symbols": "/ES,/NQ"})
        req = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        out = {}
        for key, prefix in (("ES", "/ES"), ("NQ", "/NQ")):
            entry = next((v for k, v in data.items() if k.startswith(prefix)), None)
            if not entry or "quote" not in entry:
                continue
            q = entry["quote"]
            price = q.get("mark") or q.get("lastPrice")
            change = q.get("netChange", 0) or 0
            out[key] = {
                "price": round(price, 2) if price is not None else None,
                "change": round(change, 2),
                "changePercentage": q.get("futurePercentChange"),
                "color": color_for(change),
                "contract": entry.get("symbol"),
            }
        return out
    except Exception as e:
        print(f"WARN: Schwab futures fetch failed, falling back to FMP proxy: {e}", file=sys.stderr)
        return {}


def read_text_any(path: Path) -> str:
    """Windows-proof text read: BOM-aware, matching the pattern already
    used by schwab_auth.py / schwab_hhh_fetch.py in this repo."""
    data = path.read_bytes()
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16")
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def env_or_dotenv(*names: str) -> str:
    """Check real env vars first (the GitHub Actions path, populated from
    secrets.*), then fall back to reading the repo-root .env directly (the
    local-testing path, same convention as this repo's other scripts).
    GH Actions never has a .env file checked out, so this is a no-op there."""
    for n in names:
        if os.environ.get(n):
            return os.environ[n]
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in read_text_any(env_path).splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() in names and v.strip().strip('"').strip("'"):
                return v.strip().strip('"').strip("'")
    return ""


def gate(force: bool) -> datetime.datetime:
    now = datetime.datetime.now(PT)
    if force:
        print(f"FORCE_RUN set — skipping gate. Now: {now.isoformat()}")
        return now
    if now.weekday() >= 5:
        print(f"Weekend ({now.strftime('%A')}) — no-op.")
        sys.exit(0)
    target = now.replace(hour=TARGET_HOUR, minute=TARGET_MIN, second=0, microsecond=0)
    delta_min = abs((now - target).total_seconds()) / 60
    if delta_min > WINDOW_MIN:
        print(f"Outside 6:25 AM PT window (now {now.strftime('%H:%M %Z')}, "
              f"{delta_min:.0f} min off) — DST-mirror cron firing wrong offset. No-op.")
        sys.exit(0)
    print(f"In window: {now.isoformat()} ({delta_min:.0f} min from target)")
    return now


def fmp_fetch(symbol: str, api_key: str) -> dict | None:
    url = FMP_QUOTE_URL + "?" + urllib.parse.urlencode({"symbol": symbol, "apikey": api_key})
    req = urllib.request.Request(url, headers={"User-Agent": "shadowmonkey-mmm/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        if isinstance(data, list) and data:
            return data[0]
        print(f"WARN: unexpected FMP response shape for {symbol}: {data}", file=sys.stderr)
    except Exception as e:
        print(f"WARN: FMP fetch failed for {symbol}: {e}", file=sys.stderr)
    return None


def color_for(change: float) -> str:
    if change > 0:
        return "c-safe"
    if change < 0:
        return "c-bad"
    return "c-sub"


def fetch_all(api_key: str) -> dict:
    out = {}
    for name, (symbol, decimals) in SOURCES.items():
        q = fmp_fetch(symbol, api_key)
        if not q:
            out[name] = None
            continue
        price = q.get("price")
        change = q.get("change", 0) or 0
        out[name] = {
            "price": round(price, decimals) if price is not None else None,
            "change": round(change, decimals),
            "changePercentage": q.get("changePercentage"),
            "color": color_for(change),
        }
    return out


def fmt(v) -> str:
    return f"{v:,.2f}" if isinstance(v, (int, float)) else "N/A"


def fmt_change(d: dict | None) -> str:
    if not d or d.get("change") is None:
        return "N/A"
    sign = "+" if d["change"] >= 0 else ""
    pct = d.get("changePercentage")
    pct_str = f" ({sign}{pct:.2f}%)" if isinstance(pct, (int, float)) else ""
    return f"{sign}{d['change']:,.2f}{pct_str}"


def build_kpi_tokens(quotes: dict, schwab: dict) -> dict:
    """KPI bar + VIX sentiment tile. ES/NQ prefer real Schwab futures when
    available (schwab dict non-empty); otherwise fall back to the FMP
    cash-index proxy, honestly labeled either way in the rendered footnote."""
    t = {}

    if schwab.get("ES"):
        q = schwab["ES"]
        t["ES_PREMARKET"] = fmt(q["price"])
        t["ES_CHANGE"] = fmt_change(q)
        t["ES_COLOR"] = q["color"]
        t["ES_SOURCE"] = f"Schwab {q.get('contract', '/ES')} (real futures)"
    else:
        q = quotes.get("SPX")
        t["ES_PREMARKET"] = fmt(q["price"]) if q else "N/A"
        t["ES_CHANGE"] = fmt_change(q)
        t["ES_COLOR"] = q["color"] if q else "c-sub"
        t["ES_SOURCE"] = "S&P 500 cash index (Schwab futures unavailable)"

    if schwab.get("NQ"):
        q = schwab["NQ"]
        t["NQ_PREMARKET"] = fmt(q["price"])
        t["NQ_CHANGE"] = fmt_change(q)
        t["NQ_COLOR"] = q["color"]
        t["NQ_SOURCE"] = f"Schwab {q.get('contract', '/NQ')} (real futures)"
    else:
        t["NQ_PREMARKET"] = "N/A"
        t["NQ_CHANGE"] = "N/A"
        t["NQ_COLOR"] = "c-sub"
        t["NQ_SOURCE"] = "no source available"

    for token, key in (("GOLD_PRICE", "GOLD"), ("BTC_PRICE", "BTC"),
                       ("SPX_CLOSE", "SPX"), ("ETH_PRICE", "ETH")):
        q = quotes.get(key)
        t[token] = fmt(q["price"]) if q else "N/A"
        t[token.replace("_PRICE", "_CHANGE").replace("_CLOSE", "_CHANGE")] = fmt_change(q)
        t[token.replace("_PRICE", "_COLOR").replace("_CLOSE", "_COLOR")] = q["color"] if q else "c-sub"

    vix = quotes.get("VIX")
    t["VIX_VAL"] = fmt(vix["price"]) if vix else "N/A"
    t["SENT_COLOR"] = vix["color"] if vix else "c-sub"
    return t


PENDING = "PENDING — awaiting analysis pass"


def render(template: str, now: datetime.datetime, kpi: dict, insert: dict | None) -> str:
    date_long = now.strftime("%A, %B ") + str(now.day) + now.strftime(", %Y")
    date_short = now.strftime("%b ") + str(now.day)
    day_of_week = now.strftime("%A")
    prev = now - datetime.timedelta(days=3 if now.weekday() == 0 else 1)
    prev_date_short = prev.strftime("%b ") + str(prev.day)

    values = {
        "DATE_LONG": date_long, "DATE_SHORT": date_short, "DAY_OF_WEEK": day_of_week,
        "PREV_DATE_SHORT": prev_date_short, "SESSION_LABEL": "NY Session (pre-open)",
        "REGIME_LABEL": "PENDING", "PRIMARY_CATALYST": PENDING,
        "ES_PREMARKET": kpi.get("ES_PREMARKET", "N/A"),
        "ES_CHANGE": kpi.get("ES_CHANGE", "N/A"), "ES_COLOR": kpi.get("ES_COLOR", "c-sub"),
        "NQ_PREMARKET": "N/A", "NQ_CHANGE": "N/A", "NQ_COLOR": "c-sub",
        "GOLD_PRICE": kpi.get("GOLD_PRICE", "N/A"),
        "GOLD_CHANGE": kpi.get("GOLD_CHANGE", "N/A"), "GOLD_COLOR": kpi.get("GOLD_COLOR", "c-sub"),
        "BTC_PRICE": kpi.get("BTC_PRICE", "N/A"),
        "BTC_CHANGE": kpi.get("BTC_CHANGE", "N/A"), "BTC_COLOR": kpi.get("BTC_COLOR", "c-sub"),
        "SPX_CLOSE": kpi.get("SPX_CLOSE", "N/A"),
        "SPX_CHANGE": kpi.get("SPX_CHANGE", "N/A"), "SPX_COLOR": kpi.get("SPX_COLOR", "c-sub"),
        "ETH_PRICE": kpi.get("ETH_PRICE", "N/A"),
        "ETH_CHANGE": kpi.get("ETH_CHANGE", "N/A"), "ETH_COLOR": kpi.get("ETH_COLOR", "c-sub"),
        "VIX_VAL": kpi.get("VIX_VAL", "N/A"), "VIX_LABEL": PENDING,
        "SENT_COLOR": kpi.get("SENT_COLOR", "c-sub"),
        "FNG_VAL": "N/A", "FNG_LABEL": PENDING,
        "PUTCALL_VAL": "N/A", "PUTCALL_LABEL": PENDING,
        "BREADTH_VAL": "N/A", "BREADTH_LABEL": PENDING,
        "AAII_VAL": "N/A", "AAII_LABEL": PENDING,
        "SENTIMENT_VAL": "N/A", "SENTIMENT_LABEL": PENDING,
        "ADVISORY_VERDICT": "PENDING", "ADVISORY_BODY": PENDING,
        "SIGNAL_BULL": "—", "SIGNAL_WATCH": "—", "SIGNAL_CAUTION": "—", "SIGNAL_AVOID": "—",
        "OPERATIVE_VERDICT_TEXT": PENDING,
        "BBM_BULL_PCT": "50", "BBM_BEAR_PCT": "50", "BBM_HEADLINE": PENDING,
    }
    if insert:
        values.update(insert)  # on-demand pass can override any of the above

    html = template
    for key, val in values.items():
        html = html.replace("{{" + key + "}}", str(val))

    if insert and "INJECTED_SECTIONS" in insert:
        for marker, content in insert["INJECTED_SECTIONS"].items():
            html = html.replace(marker, content)
    else:
        # Replace every remaining INJECT comment block with an explicit,
        # visible pending notice rather than leaving raw comments or
        # blank tables -- honest about what hasn't run yet.
        html = re.sub(
            r"<!--\s*INJECT:.*?-->",
            f'<tr><td colspan="4" style="color:var(--muted);font-style:italic">{PENDING}</td></tr>',
            html, flags=re.S,
        )
        html = html.replace(
            '<tbody><!-- INJECT UP TO 20 TRADE ROWS. Column order: #, Symbol, Type, Direction, Setup, Entry, Stop, Target, R:R, Notes, Priority -->',
            f'<tbody><tr><td colspan="11" style="color:var(--muted);font-style:italic">{PENDING}</td></tr>'
        )
    return html


def validate(html: str) -> None:
    if not html.startswith("<!DOCTYPE html>"):
        raise RuntimeError("Output does not start with <!DOCTYPE html> — refusing to publish.")
    if "</html>" not in html.lower():
        raise RuntimeError("Output looks truncated — refusing to publish.")
    if len(html) < 15000:
        raise RuntimeError(f"Output suspiciously short ({len(html)} chars) — refusing to publish.")


def rebuild_index() -> None:
    # 2026-08-21: index now covers BOTH products (MMM daily + FFF weekly) so
    # neither workflow clobbers the other's links. Kept in sync with the
    # identical rebuild_index() in template/generate_fff.py.
    files = sorted(OUT_DIR.glob("*.html"), reverse=True)
    rows = "\n".join(
        f'<tr><td>{f.stem}</td><td><a href="mmm-daily/{f.name}">Open</a></td></tr>'
        for f in files
    )
    fff_dir = ROOT / "shadowmonkey" / "fff"
    fff_files = sorted(fff_dir.glob("*.html"), reverse=True) if fff_dir.exists() else []
    fff_rows = "\n".join(
        f'<tr><td>{f.stem}</td><td><a href="fff/{f.name}">Open</a></td></tr>'
        for f in fff_files
    ) or '<tr><td colspan="2" style="color:#666">none yet</td></tr>'
    INDEX_PATH.write_text(f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Shadow Monkey — Monkey Matters LLC</title>
<style>body{{background:#080808;color:#fff;font-family:'Space Mono',monospace;padding:24px}}
a{{color:#c8ff00}} table{{border-collapse:collapse;margin-bottom:28px}}
td{{padding:6px 14px;border-bottom:1px solid #222}} h2{{color:#c8ff00;letter-spacing:2px}}</style>
</head><body><h1>Shadow Monkey — Intelligence Archive</h1>
<h2>FFF — Friday Financial Forecast (weekly)</h2>
<table>{fff_rows}</table>
<h2>MMM — Morning Market Monitor (daily)</h2>
<table>{rows}</table></body></html>""", encoding="utf-8")


def main() -> None:
    force = os.environ.get("FORCE_RUN", "").lower() in ("true", "1")
    now = gate(force)

    if not TEMPLATE_PATH.exists():
        print(f"FATAL: {TEMPLATE_PATH} not found.", file=sys.stderr)
        sys.exit(1)
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    api_key = env_or_dotenv("FMP_API_KEY")
    if not api_key:
        print("FATAL: FMP_API_KEY not set (checked env and .env).", file=sys.stderr)
        sys.exit(1)

    quotes = fetch_all(api_key)
    schwab = fetch_schwab_futures()
    if schwab:
        print(f"Schwab futures live: {[(k, v['price'], v.get('contract')) for k, v in schwab.items()]}")
    kpi = build_kpi_tokens(quotes, schwab)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    date_str = now.strftime("%Y-%m-%d")
    (DATA_DIR / f"{date_str}.json").write_text(
        json.dumps({"fetched_at": now.isoformat(), "quotes": quotes, "schwab_futures": schwab}, indent=2),
        encoding="utf-8"
    )

    insert_path = DATA_DIR / f"{date_str}.insert.json"
    insert = json.loads(insert_path.read_text(encoding="utf-8")) if insert_path.exists() else None
    if insert:
        print(f"Found on-demand insert for {date_str} — merging analysis content.")

    html = render(template, now, kpi, insert)
    validate(html)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{date_str}.html"
    out_path.write_text(html, encoding="utf-8")
    rebuild_index()

    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "sanitize.py"), str(ROOT)],
                             capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        print("SANITIZE FAILED — not committing.", file=sys.stderr)
        sys.exit(1)

    print(f"OK: wrote {out_path} ({len(html)} chars). Quotes: "
          f"{ {k: (v['price'] if v else None) for k, v in quotes.items()} }")


if __name__ == "__main__":
    main()
