#!/usr/bin/env python3
"""
SHADOW MONKEY // SCHWAB ONE-TIME AUTH
-------------------------------------
Mints the initial token file for the HHH fetcher. Run this on papa whenever
the refresh token dies (Schwab kills them every ~7 days).

Flow (paste-the-URL method — no local https server or certs needed):
  1. Script opens your browser to Schwab's login page.
  2. Log in, approve the app for the accounts you want.
  3. Browser redirects to your callback URL (https://127.0.0.1:...) and shows
     a "can't connect" page — THAT'S EXPECTED. Copy the FULL URL from the
     address bar (it contains ?code=...).
  4. Paste it into this terminal. Script exchanges it and writes the token file.

Reads credentials from the repo-root .env (SCHWAB_CLIENT_ID / SCHWAB_CLIENT_SECRET,
optional SCHWAB_CALLBACK_URL, SCHWAB_TOKEN_PATH). Token defaults to
.secrets/schwab_token.json at the repo root (gitignored).

Usage (from the repo root or hhh/):
  python schwab_auth.py
"""

import argparse
import base64
import json
import os
import sys
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path

AUTH_URL = "https://api.schwabapi.com/v1/oauth/authorize"
TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"

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
    env = {}
    for line in read_text_any(path).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def find_dotenv():
    for d in (SCRIPT_DIR, SCRIPT_DIR.parent, Path.cwd()):
        if (d / ".env").exists():
            return d / ".env"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="hhh_config.json")
    args = ap.parse_args()

    cfg = json.loads(read_text_any(args.config)) if Path(args.config).exists() else {}
    dotenv_path = find_dotenv()
    dotenv = parse_dotenv(dotenv_path) if dotenv_path else {}
    repo_root = dotenv_path.parent if dotenv_path else SCRIPT_DIR.parent

    def pick(*names, cfg_key=None, default=None):
        for n in names:
            if os.environ.get(n):
                return os.environ[n]
        for n in names:
            if dotenv.get(n):
                return dotenv[n]
        return cfg.get(cfg_key, default) if cfg_key else default

    app_key = pick("SCHWAB_CLIENT_ID", "SCHWAB_APP_KEY", cfg_key="app_key")
    app_secret = pick("SCHWAB_CLIENT_SECRET", "SCHWAB_APP_SECRET", cfg_key="app_secret")
    callback = pick("SCHWAB_CALLBACK_URL", cfg_key="callback_url", default="https://127.0.0.1:8182")
    tok = Path(pick("SCHWAB_TOKEN_PATH", cfg_key="token_path",
                    default=".secrets/schwab_token.json")).expanduser()
    token_path = tok if tok.is_absolute() else repo_root / tok

    if not app_key or not app_secret:
        sys.exit("[FATAL] SCHWAB_CLIENT_ID / SCHWAB_CLIENT_SECRET not found — "
                 "fill them in the repo-root .env first.")
    print(f"    .env: {dotenv_path or 'NOT FOUND'}")
    print(f"    token will be written to: {token_path}")

    url = f"{AUTH_URL}?client_id={urllib.parse.quote(app_key)}&redirect_uri={urllib.parse.quote(callback)}"
    print("\n[1] Opening browser to Schwab login…\n    " + url)
    webbrowser.open(url)
    print("\n[2] Log in, approve the app for ALL accounts you want tracked.")
    print("[3] The browser will land on a dead page at your callback URL — expected.")
    pasted = input("\n[4] Paste the FULL redirected URL here:\n> ").strip()

    qs = urllib.parse.parse_qs(urllib.parse.urlparse(pasted).query)
    code = (qs.get("code") or [None])[0]
    if not code:
        sys.exit("[FATAL] No ?code= found in that URL. Paste the entire address bar contents.")

    body = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": callback,
    }).encode()
    basic = base64.b64encode(f"{app_key}:{app_secret}".encode()).decode()
    req = urllib.request.Request(TOKEN_URL, data=body, headers={
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            tok = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"[FATAL] Token exchange failed ({e.code}): {e.read().decode()[:300]}")

    tok["_minted_at"] = datetime.now().isoformat(timespec="seconds")
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(json.dumps(tok, indent=2), encoding="utf-8")
    os.chmod(token_path, 0o600)
    print(f"\n[OK] Token written to {token_path}")
    print("     Access token valid 30 min; refresh token ~7 days.")
    print("     Next: python3 schwab_hhh_fetch.py --list-accounts")


if __name__ == "__main__":
    main()
