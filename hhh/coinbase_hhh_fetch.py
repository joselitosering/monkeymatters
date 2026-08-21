#!/usr/bin/env python3
"""
SHADOW MONKEY // COINBASE ON-CHAIN WALLET FETCHER — HHH sourcing leg 2a
------------------------------------------------------------------------
Reads on-chain token balances (Base network) for your self-custody
wallet(s) via the Coinbase Developer Platform (CDP) Data API, prices them
via Financial Modeling Prep, and writes/updates the "Crypto" account entry
inside manual_accounts.json's `append` list — which schwab_hhh_fetch.py
already knows how to merge into the final dashboard.

Run this BEFORE schwab_hhh_fetch.py so the Crypto sleeve is fresh when the
template gets built:
    python3 coinbase_hhh_fetch.py
    python3 schwab_hhh_fetch.py --template HHH_APEX_Template.html --out HHH_Latest.html

WHAT THIS COVERS (leg 2a): your self-custody Base wallet(s) — regular ERC-20
/ native ETH balances, PLUS the cbwsETH soulbound token that represents your
ETH staked via the Base app (staking is on-chain/non-custodial there; the
receipt token lives in your own wallet, not a separate staking address).

WHAT THIS DOES NOT COVER (leg 2b, not yet built): your actual Coinbase.com
EXCHANGE account balances. That's a *different* Coinbase product (Advanced
Trade / Coinbase App API) which requires an ES256 (ECDSA) key — the
Ed25519 CDP Data API key below (COINBASE_API_KEY / COINBASE_PRIVATE_KEY)
is NOT valid for it. Create a second key under that product in the CDP
portal when you're ready and this script can grow a second leg.

Reads from the repo-root .env:
  COINBASE_API_KEY      CDP Secret API Key ID (Ed25519 / Data API product)
  COINBASE_PRIVATE_KEY  CDP Secret API Key secret — base64, 64 raw bytes
                         (32-byte Ed25519 seed + 32-byte pubkey; only the
                         seed half is used to sign)
  FMP_API_KEY            Financial Modeling Prep key, for USD pricing
                         (optional — positions still write with qty-only
                         if missing, just no mktVal/price)

Reads wallet addresses from hhh_config.json:
  "crypto_wallets": [
    {"address": "0x...", "label": "Base app (self-custody)"}
  ],
  "crypto_network": "base"     // default "base"; also valid: "base-sepolia", "ethereum"

Requires one extra dependency beyond stdlib (Ed25519 signing isn't in the
Python standard library):
    pip install cryptography        (or: py -m pip install cryptography)

Cost basis: self-custody wallets don't carry brokerage-style lot data, so
costBasis/unrlPL/unrlPct are left blank (the template treats missing as 0
and simply excludes the position from the account's weighted unrealized%
— it does NOT invent a fake break-even price). Add real entry prices later
via a manual overlay if you want true unrealized P/L tracked for crypto.
"""

import argparse
import base64
import gzip
import io
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CDP_HOST = "api.cdp.coinbase.com"
STABLES = {"USDC", "USDT", "DAI", "USDBC"}

# Tracking scope (Joe-confirmed, 2026-08-19): spot BTC, spot ETH, spot XRP,
# and SXT only — nothing else. This on-chain leg only ever sees Base-network
# tokens, so in practice that means ETH (incl. wrapped/staked receipt tokens)
# and any bridged BTC/SXT that happen to live in this wallet; XRP isn't a
# Base-network asset and won't appear here, but is included for completeness/
# future-proofing. Everything else — every airdrop, "claim your $X" spam
# token, meme coin, etc. that lands in this wallet uninvited — is dropped
# entirely rather than shown as a $0 row. Diagnosed 2026-08-20: an earlier,
# unfiltered version of this script found 9 such spam/airdrop tokens (incl.
# ones with phishing URLs baked into their names) and wrote them into
# manual_accounts.json, overwriting real hand-verified holdings with ~$0 of
# garbage — twice. Do not remove this filter without addressing that.
SYMBOL_ALIASES = {
    "ETH": "ETH", "WETH": "ETH", "CBETH": "ETH", "CBWSETH": "ETH",
    "BTC": "BTC", "WBTC": "BTC", "CBBTC": "BTC",
    "XRP": "XRP",
    "SXT": "SXT",
}

SCRIPT_DIR = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Shared helpers (mirrors schwab_hhh_fetch.py / schwab_auth.py conventions)
# ---------------------------------------------------------------------------

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
    env = {}
    for line in read_text_any(path).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def find_dotenv(config_path):
    for d in (Path(config_path).resolve().parent, SCRIPT_DIR, SCRIPT_DIR.parent, Path.cwd()):
        cand = d / ".env"
        if cand.exists():
            return cand
    return None


def read_error_body(e):
    """HTTPError bodies are sometimes gzip-compressed regardless of what we
    asked for — decompress if needed so the real error text (not a
    UnicodeDecodeError on raw gzip bytes) reaches the user."""
    raw = e.read()
    if raw[:2] == b"\x1f\x8b":
        try:
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        except OSError:
            pass
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace")


def http_json(req):
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config(path):
    cfg = {}
    p = Path(path)
    if p.exists():
        cfg = json.loads(read_text_any(p))

    dotenv_path = find_dotenv(path)
    dotenv = parse_dotenv(dotenv_path) if dotenv_path else {}

    def pick(*names):
        for n in names:
            if os.environ.get(n):
                return os.environ[n]
        for n in names:
            if dotenv.get(n):
                return dotenv[n]
        return None

    cfg["coinbase_key_id"] = pick("COINBASE_API_KEY")
    cfg["coinbase_priv_key"] = pick("COINBASE_PRIVATE_KEY")
    cfg["fmp_api_key"] = pick("FMP_API_KEY")
    cfg["_cfg_dir"] = str(Path(path).resolve().parent)
    cfg.setdefault("crypto_wallets", [])
    cfg.setdefault("crypto_network", "base")
    return cfg


def resolve_side_file(cfg, key, default):
    raw = cfg.get(key, default)
    if not raw:
        return None
    p = Path(raw).expanduser()
    return p if p.is_absolute() else Path(cfg["_cfg_dir"]) / p


# ---------------------------------------------------------------------------
# CDP auth (EdDSA / Ed25519 bearer JWT — Data API product only; NOT valid
# for Advanced Trade / Coinbase App endpoints, which require an ES256 key)
# ---------------------------------------------------------------------------

def b64url(raw_bytes):
    return base64.urlsafe_b64encode(raw_bytes).rstrip(b"=").decode()


def build_cdp_jwt(key_id, priv_key_b64, method, host, path):
    """CDP REST bearer token: EdDSA-signed JWT, 120s validity, single-use
    nonce. `uri` claim is METHOD + host + path (no query string)."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    raw = base64.b64decode(priv_key_b64)
    if len(raw) < 32:
        sys.exit("[FATAL] COINBASE_PRIVATE_KEY doesn't decode to a usable Ed25519 key "
                  "(expected 64 raw bytes, base64-encoded). Re-copy it from the CDP portal.")
    seed = raw[:32]  # CDP secret keys are 64 bytes: 32-byte seed + 32-byte pubkey
    priv = Ed25519PrivateKey.from_private_bytes(seed)

    now = int(time.time())
    header = {"alg": "EdDSA", "typ": "JWT", "kid": key_id, "nonce": secrets.token_hex(8)}
    payload = {"sub": key_id, "iss": "cdp", "aud": ["cdp_service"],
               "nbf": now, "exp": now + 120, "uri": f"{method} {host}{path}"}
    signing_input = (
        b64url(json.dumps(header, separators=(",", ":")).encode()) + "." +
        b64url(json.dumps(payload, separators=(",", ":")).encode())
    )
    sig = priv.sign(signing_input.encode())
    return f"{signing_input}.{b64url(sig)}"


def fetch_wallet_balances(cfg, address):
    """Paginated GET /platform/v2/evm/token-balances/{network}/{address}."""
    network = cfg["crypto_network"]
    path = f"/platform/v2/evm/token-balances/{network}/{address}"
    balances, page_token = [], None
    while True:
        url = f"https://{CDP_HOST}{path}"
        if page_token:
            url += f"?pageToken={urllib.parse.quote(page_token)}"
        jwt = build_cdp_jwt(cfg["coinbase_key_id"], cfg["coinbase_priv_key"], "GET", CDP_HOST, path)
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {jwt}",
            "Accept": "application/json",
        })
        try:
            data = http_json(req)
        except urllib.error.HTTPError as e:
            body = read_error_body(e)
            hint = ""
            if e.code in (401, 403):
                hint = ("\n     Check COINBASE_API_KEY/COINBASE_PRIVATE_KEY are the Ed25519 "
                        "'Data API' / 'Platform APIs' key — an Advanced Trade (ES256) key "
                        "will fail here with the same error.")
            sys.exit(f"[FATAL] CDP token-balances call failed ({e.code}) for {address}: "
                      f"{body[:400]}{hint}")
        balances.extend(data.get("balances", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return balances


# ---------------------------------------------------------------------------
# Pricing (Financial Modeling Prep — same key other pipelines in this repo
# already use; avoids adding yet another unauthenticated third-party call)
# ---------------------------------------------------------------------------

def fmp_price(fmp_key, symbol_usd):
    """Returns (price, day_change_pct) or (None, None) if unavailable."""
    if not fmp_key:
        return None, None
    url = (f"https://financialmodelingprep.com/stable/quote-short"
           f"?symbol={urllib.parse.quote(symbol_usd)}&apikey={urllib.parse.quote(fmp_key)}")
    try:
        data = http_json(urllib.request.Request(url))
    except Exception:
        return None, None
    if not data:
        return None, None
    row = data[0] if isinstance(data, list) else data
    price = row.get("price")
    day_pct = row.get("changesPercentage", row.get("changePercentage", row.get("change")))
    return price, day_pct


def cached_price(cache, key, fetcher):
    if key not in cache:
        cache[key] = fetcher()
    return cache[key]


# ---------------------------------------------------------------------------
# Build the Crypto account object
# ---------------------------------------------------------------------------

def build_positions(cfg, address, label, price_cache):
    positions = []
    for b in fetch_wallet_balances(cfg, address):
        tok = b.get("token", {})
        symbol = tok.get("symbol") or "?"
        amt = b.get("amount", {})
        decimals = amt.get("decimals", 18)
        try:
            raw_amt = int(amt.get("amount", "0"))
        except (TypeError, ValueError):
            raw_amt = 0
        qty = raw_amt / (10 ** decimals)
        if qty == 0:
            continue
        if symbol.upper() not in SYMBOL_ALIASES:
            continue  # out-of-scope token (spam/airdrop/unrelated) — never tracked, never written

        note = None
        if symbol == "cbwsETH":
            price, day_pct = cached_price(price_cache, "ETHUSD",
                                           lambda: fmp_price(cfg.get("fmp_api_key"), "ETHUSD"))
            note = ("Base app staked-ETH receipt (soulbound, non-transferable, ~2% APY) — "
                    "valued 1:1 to ETH; no independent market price exists for this token.")
        elif symbol.upper() in STABLES:
            price, day_pct = 1.0, 0.0
        else:
            key = f"{symbol.upper()}USD"
            price, day_pct = cached_price(price_cache, key,
                                           lambda k=key: fmp_price(cfg.get("fmp_api_key"), k))
            if price is None:
                note = "Price unavailable from FMP — shown at qty only until a source is added."

        mkt_val = round(qty * price, 2) if price is not None else None
        day_pct_num = day_pct if isinstance(day_pct, (int, float)) else None
        day_chg = round(mkt_val * (day_pct_num / 100), 2) if (mkt_val and day_pct_num) else 0.0

        pos = {
            "symbol": symbol,
            "desc": f'{tok.get("name") or symbol} · {label}',
            "qty": round(qty, 8),
            "price": round(price, 6) if price is not None else None,
            "mktVal": mkt_val,
            "dayChg": day_chg,
            "dayPct": round(day_pct_num, 2) if day_pct_num is not None else 0.0,
            "costBasis": None,
            "unrlPL": None,
            "unrlPct": None,
        }
        if note:
            pos["note"] = note
        positions.append(pos)
    return positions


def build_crypto_account(cfg):
    price_cache = {}
    positions = []
    for w in cfg["crypto_wallets"]:
        positions.extend(build_positions(cfg, w["address"], w.get("label", w["address"]), price_cache))
    return {
        "name": "Crypto",
        "kind": "crypto",
        "positions": positions,
    }


def merge_into_manual_accounts(manual_path, crypto_account):
    """Replace the 'Crypto' entry in append[] with the freshly-fetched one —
    UNLESS that would blindly destroy real data. This on-chain leg only ever
    sees Base-network tokens (see SYMBOL_ALIASES above); it cannot see
    Coinbase.com exchange balances (BTC/XRP/SXT today) or supply cost basis
    for anything. So if the existing entry already carries real value
    (mktVal or costBasis on any position) and this run's filtered result is
    empty or trivial, that's almost certainly this leg being blind to real
    holdings, not those holdings actually going to zero — refuse the
    overwrite and tell the operator why, rather than repeat the 2026-08-19/20
    incident where this silently replaced hand-verified BTC/ETH/XRP/SXT data
    with ~$0 of unrelated spam tokens, twice."""
    manual = {}
    if manual_path.exists():
        manual = json.loads(read_text_any(manual_path))
    manual.setdefault("append", [])
    existing = next((a for a in manual["append"] if a.get("name") == "Crypto"), None)
    existing_val = sum((p.get("mktVal") or 0) for p in existing["positions"]) if existing else 0
    existing_has_basis = bool(existing) and any(p.get("costBasis") for p in existing["positions"])
    new_val = sum((p.get("mktVal") or 0) for p in crypto_account["positions"])

    if existing and (existing_val > 1 or existing_has_basis) and new_val <= 1:
        print(f"[WARN] Refusing to overwrite the existing Crypto entry (~${existing_val:,.2f}, "
              f"cost-basis data present={existing_has_basis}) with this run's near-empty result "
              f"(~${new_val:,.2f}, {len(crypto_account['positions'])} position(s)). This on-chain "
              f"leg can't see Coinbase.com exchange balances or cost basis — an empty/near-zero "
              f"result here almost always means it's blind to your real holdings, not that they "
              f"went to zero. manual_accounts.json left UNCHANGED.")
        return False

    manual["append"] = [a for a in manual["append"] if a.get("name") != "Crypto"]
    manual["append"].append(crypto_account)
    manual_path.write_text(json.dumps(manual, indent=2), encoding="utf-8")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="hhh_config.json")
    ap.add_argument("--dry-run", action="store_true", help="print the Crypto account JSON, write nothing")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if not cfg["coinbase_key_id"] or not cfg["coinbase_priv_key"]:
        sys.exit("[FATAL] COINBASE_API_KEY / COINBASE_PRIVATE_KEY not found in .env.")
    if not cfg["crypto_wallets"]:
        sys.exit('[FATAL] No wallets configured. Add to hhh_config.json:\n'
                  '  "crypto_wallets": [{"address": "0x...", "label": "Base app (self-custody)"}]')
    if not cfg.get("fmp_api_key"):
        print("[WARN] FMP_API_KEY not found — positions will write with qty only, no price/mktVal.")

    crypto_account = build_crypto_account(cfg)
    total = sum(p["mktVal"] for p in crypto_account["positions"] if p["mktVal"])
    print(f"[OK] {len(crypto_account['positions'])} position(s) across "
          f"{len(cfg['crypto_wallets'])} wallet(s), ~${total:,.2f}")

    if args.dry_run:
        json.dump(crypto_account, sys.stdout, indent=2)
        print()
        return

    manual_path = resolve_side_file(cfg, "manual_accounts_path", "manual_accounts.json")
    wrote = merge_into_manual_accounts(manual_path, crypto_account)
    if wrote:
        print(f"[OK] Wrote Crypto account into {manual_path}")
    else:
        print(f"[OK] Crypto account left as-is (see WARN above) — not an error, exiting 0.")


if __name__ == "__main__":
    main()
