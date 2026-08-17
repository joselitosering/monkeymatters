#!/usr/bin/env python3
"""
SHADOW MONKEY // HHH PORTFOLIO FETCHER
--------------------------------------
Pulls accounts + positions from the Schwab Trader API and injects them into
the APEX-themed HHH template (between the PORTFOLIO_DATA_START/END markers).

Runs on papa as the local Schwab leg (same OAuth reality as market-ops:
Schwab refresh tokens live ~7 days and need a browser re-auth, so this
script only *refreshes* the access token — it does not do the initial grant).

Setup (one time):
  1. Create an app at https://developer.schwab.com (Trader API — Individual),
     callback URL e.g. https://127.0.0.1:8182
  2. Do the initial OAuth code grant once (schwab-py's `client_from_login_flow`
     is the easy path, or any manual flow) and save the token JSON to TOKEN_PATH.
     Expected token file shape: {"refresh_token": "...", "access_token": "...", ...}
  3. Export SCHWAB_APP_KEY and SCHWAB_APP_SECRET (or put them in hhh_config.json).
  4. Optional: hhh_config.json maps account hashes to display names/kinds,
     and ratings.json overlays your F/T ratings per symbol.

Usage:
  python3 schwab_hhh_fetch.py --template HHH_APEX_Template.html --out HHH_Latest.html
  python3 schwab_hhh_fetch.py --dry-run          # print mapped JSON, write nothing

hhh_config.json example:
{
  "token_path": "~/.schwab/token.json",
  "app_key": "...",            // optional; env var wins
  "app_secret": "...",         // optional; env var wins
  "accounts": {
    "ABC123HASH": {"name": "Savings",    "kind": "equity"},
    "DEF456HASH": {"name": "Income",     "kind": "options"},
    "GHI789HASH": {"name": "Piggy Bank", "kind": "etf"}
  },
  "crypto_account_names": ["Crypto"],
  "crypto_sleeve_cap_pct": 30,
  "single_position_cap_pct": 25,
  "manual_accounts_path": "manual_accounts.json"   // e.g. Coinbase/crypto sleeve not at Schwab
}

NOTE: Schwab does not hold the crypto sleeve. Keep non-Schwab accounts
(Crypto, futures marks, etc.) in manual_accounts.json using the same account
schema as the template's PORTFOLIO_DATA.accounts entries; they are appended.
"""

import argparse
import base64
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"
ACCOUNTS_URL = "https://api.schwabapi.com/trader/v1/accounts?fields=positions"

START = "/*PORTFOLIO_DATA_START*/"
END = "/*PORTFOLIO_DATA_END*/"

SCRIPT_DIR = Path(__file__).resolve().parent


def read_text_any(path):
    """Windows-proof text read: BOM-aware (UTF-16 from PowerShell, UTF-8-sig
    from Notepad) with sane fallbacks. Never trusts the locale codepage."""
    data = Path(path).read_bytes()
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16")
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def parse_dotenv(path):
    """Minimal .env parser — no dependency."""
    env = {}
    for line in read_text_any(path).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def find_dotenv(config_path):
    """Search: config dir -> script dir -> repo root (script parent) -> cwd."""
    for d in (Path(config_path).resolve().parent, SCRIPT_DIR, SCRIPT_DIR.parent, Path.cwd()):
        cand = d / ".env"
        if cand.exists():
            return cand
    return None


def load_config(path):
    cfg = {}
    p = Path(path)
    if p.exists():
        cfg = json.loads(read_text_any(p))

    dotenv_path = find_dotenv(path)
    dotenv = parse_dotenv(dotenv_path) if dotenv_path else {}
    cfg["_repo_root"] = str(dotenv_path.parent) if dotenv_path else str(SCRIPT_DIR.parent)

    def pick(*names, cfg_key=None):
        for n in names:
            if os.environ.get(n):
                return os.environ[n]
        for n in names:
            if dotenv.get(n):
                return dotenv[n]
        return cfg.get(cfg_key) if cfg_key else None

    # monkeymatters .env convention first; legacy names accepted
    cfg["app_key"] = pick("SCHWAB_CLIENT_ID", "SCHWAB_APP_KEY", cfg_key="app_key")
    cfg["app_secret"] = pick("SCHWAB_CLIENT_SECRET", "SCHWAB_APP_SECRET", cfg_key="app_secret")
    tok = pick("SCHWAB_TOKEN_PATH", cfg_key="token_path") or ".secrets/schwab_token.json"
    tok = Path(tok).expanduser()
    if not tok.is_absolute():
        tok = Path(cfg["_repo_root"]) / tok   # relative paths anchor at repo root (.env location)
    cfg["token_path"] = str(tok)
    cfg["callback_url"] = pick("SCHWAB_CALLBACK_URL", cfg_key="callback_url") or "https://127.0.0.1:8182"
    cfg["_cfg_dir"] = str(Path(path).resolve().parent)
    cfg.setdefault("accounts", {})
    cfg.setdefault("crypto_account_names", ["Crypto"])
    cfg.setdefault("crypto_sleeve_cap_pct", 30)
    cfg.setdefault("single_position_cap_pct", 25)
    return cfg


def resolve_side_file(cfg, key, default):
    """Overlay files (manual/ratings/analysis) resolve relative to the config file."""
    raw = cfg.get(key, default)
    if not raw:
        return None
    p = Path(raw).expanduser()
    return p if p.is_absolute() else Path(cfg["_cfg_dir"]) / p


def http_json(req):
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def refresh_access_token(cfg):
    """Exchange the stored refresh token for a fresh access token; persist both."""
    token_path = Path(cfg["token_path"]).expanduser()
    tok = json.loads(read_text_any(token_path))
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": tok["refresh_token"],
    }).encode()
    basic = base64.b64encode(f'{cfg["app_key"]}:{cfg["app_secret"]}'.encode()).decode()
    req = urllib.request.Request(TOKEN_URL, data=body, headers={
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    try:
        fresh = http_json(req)
    except urllib.error.HTTPError as e:
        sys.exit(f"[FATAL] Token refresh failed ({e.code}). Schwab refresh tokens "
                 f"expire every ~7 days — re-run the browser login flow and save a "
                 f"new token to {token_path}. Body: {e.read().decode()[:300]}")
    tok.update(fresh)
    tok["_refreshed_at"] = datetime.now().isoformat(timespec="seconds")
    token_path.write_text(json.dumps(tok, indent=2), encoding="utf-8")
    return tok["access_token"]


def fetch_accounts(access_token):
    req = urllib.request.Request(ACCOUNTS_URL, headers={
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    })
    try:
        return http_json(req)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            sys.exit(f"[FATAL] Accounts call rejected ({e.code}). Your Schwab app must have "
                     f"'Accounts and Trading Production' access — an app registered only for "
                     f"'Market Data Production' cannot read positions. Check the app's API "
                     f"products at developer.schwab.com. Body: {e.read().decode()[:200]}")
        raise


def map_position(pos, kind):
    """Schwab position object -> template position schema."""
    inst = pos.get("instrument", {})
    asset = inst.get("assetType", "")
    qty = (pos.get("longQuantity", 0) or 0) - (pos.get("shortQuantity", 0) or 0)
    mult = 100 if asset == "OPTION" else 1
    mkt_val = pos.get("marketValue", 0.0) or 0.0
    avg = pos.get("averagePrice", 0.0) or 0.0
    cost = round(avg * qty * mult, 2)
    unrl = round(mkt_val - cost, 2)
    day_chg = pos.get("currentDayProfitLoss", 0.0) or 0.0
    day_pct = pos.get("currentDayProfitLossPercentage", None)
    price = round(mkt_val / (qty * mult), 4) if qty else None
    return {
        "symbol": inst.get("symbol", "?"),
        "desc": inst.get("description", inst.get("symbol", "")),
        "qty": qty,
        "price": price,
        "mktVal": round(mkt_val, 2),
        "dayChg": round(day_chg, 2),
        "dayPct": round(day_pct, 2) if day_pct is not None else (
            round(day_chg / (mkt_val - day_chg) * 100, 2) if (mkt_val - day_chg) else 0.0),
        "costBasis": cost,
        "unrlPL": unrl,
        "unrlPct": round(unrl / cost * 100, 2) if cost > 0 else (100.0 if unrl > 0 else 0.0),
        "rating": None,
    }


def guess_kind(positions):
    types = {p.get("instrument", {}).get("assetType") for p in positions}
    if types <= {"OPTION"}:
        return "options"
    if "COLLECTIVE_INVESTMENT" in types or "MUTUAL_FUND" in types or "ETF" in types:
        return "etf"
    return "equity"


def build_data(cfg, raw):
    accounts_out = []
    for entry in raw:
        acct = entry.get("securitiesAccount", {})
        hash_or_num = entry.get("hashValue") or acct.get("accountNumber", "")
        meta = cfg["accounts"].get(hash_or_num, {})
        positions = acct.get("positions", [])
        kind = meta.get("kind") or guess_kind(positions)
        bal = acct.get("currentBalances", {})
        cash = round((bal.get("cashBalance", 0) or 0) + (bal.get("moneyMarketFund", 0) or 0), 2)
        accounts_out.append({
            "name": meta.get("name") or f"Account …{str(acct.get('accountNumber',''))[-4:]}",
            "kind": kind,
            "cash": cash if cash > 0.005 else None,
            "positions": [map_position(p, kind) for p in positions],
        })

    # Non-Schwab data (crypto exchange, futures marks, credit cards, bank cash)
    # manual_accounts.json may also carry "creditCards" and "cashAccounts" —
    # neither comes from the Schwab Trader API, so they live here and pass through.
    manual = {}
    manual_path = resolve_side_file(cfg, "manual_accounts_path", "manual_accounts.json")
    if manual_path and manual_path.exists():
        manual = json.loads(read_text_any(manual_path))
        accounts_out = manual.get("prepend", []) + accounts_out + manual.get("append", [])

    # Ratings / notes overlay (analyst layer stays yours; rules engine is automatic)
    ratings_path = resolve_side_file(cfg, "ratings_path", "ratings.json")
    if ratings_path and ratings_path.exists():
        overlay = json.loads(read_text_any(ratings_path))
        for a in accounts_out:
            for p in a["positions"]:
                key = p["symbol"].split(" ")[0]
                if key in overlay:
                    p["rating"] = overlay[key].get("rating", p.get("rating"))
                    if overlay[key].get("note"):
                        p["note"] = overlay[key]["note"]

    # Analysis overlay — account-level technical/fundamental/guidance and
    # per-position management strategies (written by Shadow Monkey per refresh).
    # analysis.json shape:
    # {
    #   "accounts": {"Savings": {"technical": "...", "fundamental": "...", "guidance": "..."}},
    #   "strategies": {"Savings|NVDA": "...", "NVDA": "..."}   // account-qualified wins
    # }
    # Auto-managed flags come from hhh_config accounts entries ("autoManaged": true);
    # bucket labels come from cfg["buckets"] = {"FNDA": "US Equity", ...}
    analysis_path = resolve_side_file(cfg, "analysis_path", "analysis.json")
    analysis = json.loads(read_text_any(analysis_path)) if analysis_path and analysis_path.exists() else {}
    buckets = cfg.get("buckets", {})
    auto_names = {m.get("name") for m in cfg["accounts"].values() if m.get("autoManaged")}
    for a in accounts_out:
        if a["name"] in auto_names:
            a["autoManaged"] = True
        if a["name"] in analysis.get("accounts", {}):
            a["analysis"] = analysis["accounts"][a["name"]]
        for p in a["positions"]:
            root = p["symbol"].split(" ")[0]
            strat = (analysis.get("strategies", {}).get(f'{a["name"]}|{p["symbol"]}')
                     or analysis.get("strategies", {}).get(f'{a["name"]}|{root}')
                     or analysis.get("strategies", {}).get(root))
            if strat and not a.get("autoManaged"):
                p["strategy"] = strat
            if root in buckets:
                p["bucket"] = buckets[root]

    for a in accounts_out:
        if a.get("cash") is None:
            a.pop("cash", None)

    return {
        "meta": {
            "generated": datetime.now().strftime("%a, %b %-d, %Y %H:%M %Z").strip(),
            "source": "Schwab Trader API",
            "cryptoAccountNames": cfg["crypto_account_names"],
            "cryptoSleeveCapPct": cfg["crypto_sleeve_cap_pct"],
            "singlePositionCapPct": cfg["single_position_cap_pct"],
        },
        "accounts": accounts_out,
        "creditCards": manual.get("creditCards", []),
        "cashAccounts": manual.get("cashAccounts", []),
        "advisory": (lambda ap: json.loads(read_text_any(ap)) if ap and ap.exists() else None)(
                    resolve_side_file(cfg, "advisory_path", None)),
        "sources": [
            {"text": 'Charles Schwab. "Trader API — Accounts and Positions." '
                     "Charles Schwab Developer Portal, %d" % datetime.now().year,
             "url": "https://developer.schwab.com/"},
        ],
    }


def inject(template_path, out_path, data):
    html = read_text_any(template_path)
    payload = f"{START}\nconst PORTFOLIO_DATA = {json.dumps(data, indent=2)};\n{END}"
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(html):
        sys.exit("[FATAL] PORTFOLIO_DATA markers not found in template.")
    Path(out_path).write_text(pattern.sub(lambda _: payload, html), encoding="utf-8")
    print(f"[OK] Wrote {out_path}")


def main():
    ap = argparse.ArgumentParser(description="Schwab -> APEX HHH portfolio HTML")
    ap.add_argument("--config", default="hhh_config.json")
    ap.add_argument("--template", default="HHH_APEX_Template.html")
    ap.add_argument("--out", default="HHH_Latest.html")
    ap.add_argument("--dry-run", action="store_true", help="print mapped JSON, write nothing")
    ap.add_argument("--list-accounts", action="store_true",
                    help="print account hashes + last-4 + value so you can fill the config mapping")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if not cfg["app_key"] or not cfg["app_secret"]:
        sys.exit("[FATAL] Missing SCHWAB_APP_KEY / SCHWAB_APP_SECRET (env or config).")

    token = refresh_access_token(cfg)
    raw = fetch_accounts(token)

    if args.list_accounts:
        print(f"{'HASH':<44} {'ACCT':>8} {'TYPE':<10} {'POSITIONS':>9} {'VALUE':>14}  MAPPED AS")
        for entry in raw:
            acct = entry.get("securitiesAccount", {})
            h = entry.get("hashValue", "?")
            last4 = str(acct.get("accountNumber", ""))[-4:]
            val = acct.get("currentBalances", {}).get("liquidationValue", 0) or 0
            mapped = cfg["accounts"].get(h, {}).get("name", "— UNMAPPED —")
            print(f"{h:<44} …{last4:>7} {acct.get('type',''):<10} "
                  f"{len(acct.get('positions', [])):>9} {val:>14,.2f}  {mapped}")
        print("\nCopy each HASH into hhh_config.json accounts{} with its sleeve name.")
        return

    data = build_data(cfg, raw)
    unmapped = [e.get("hashValue") for e in raw if e.get("hashValue") not in cfg["accounts"]]
    if unmapped:
        print(f"[WARN] {len(unmapped)} account(s) not in config mapping — "
              f"run --list-accounts and fill hhh_config.json: {', '.join(h[:8]+'…' for h in unmapped)}")

    if args.dry_run:
        json.dump(data, sys.stdout, indent=2)
        print()
        return
    inject(args.template, args.out, data)


if __name__ == "__main__":
    main()
