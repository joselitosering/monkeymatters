#!/usr/bin/env python3
"""
Shadow Monkey — MMM Drive Sync
Pulls new MMM files from Google Drive queue into the local git repo, pushes to GitHub.
Run via Windows Task Scheduler every 30 min on weekdays (6 AM – 11 AM PT).

SETUP (one-time — run before first scheduled execution):
  1. Go to https://console.cloud.google.com/apis/credentials
  2. Create or select a project → Enable "Google Drive API"
  3. Create OAuth2 credentials → type: "Desktop app"
  4. Download JSON → save as:  scripts/credentials.json
  5. Run once:  python setup_google_auth.py   (browser opens → click Allow)
  6. token.json is created — all future scheduled runs are fully automated.

INSTALL DEPS (run once in cmd):
  pip install google-auth-oauthlib google-api-python-client
"""

import re
import json
import logging
import subprocess
from datetime import date
from io import BytesIO
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# ── CONFIG ───────────────────────────────────────────────────────────────────
SCRIPTS_DIR  = Path(__file__).parent
REPO         = SCRIPTS_DIR.parent
# shadowmonkey/ is THE public folder as of 2026-08-18 (Joe) -- was docs/.
HTML_DIR     = REPO / "shadowmonkey" / "mmm-daily"
JSON_DIR     = REPO / "data" / "daily"
INDEX_HTML   = REPO / "shadowmonkey" / "index.html"
LOG_FILE     = REPO / "data" / "sync.log"
TOKEN_FILE   = SCRIPTS_DIR / "token.json"
CREDS_FILE   = SCRIPTS_DIR / "credentials.json"

# Google Drive folder IDs (do not change)
QUEUE_ID     = "1ZxkhpSMTPlSAisDvRE_N-4AgWKXpvgDs"   # Monkey Matters/queue/
PROCESSED_ID = "1zw4r6jQfXvGAqFL_QKtZaLWmoh9VUODS"   # Monkey Matters/queue/processed/

SCOPES = ["https://www.googleapis.com/auth/drive"]
WEEKDAYS = {0: "MON", 1: "TUE", 2: "WED", 3: "THU", 4: "FRI", 5: "SAT", 6: "SUN"}
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("mmm-sync")


# ── GOOGLE DRIVE ─────────────────────────────────────────────────────────────

def get_drive_service():
    """Load credentials from token.json, refreshing if expired."""
    if not TOKEN_FILE.exists():
        raise RuntimeError(
            f"token.json not found at {TOKEN_FILE}\n"
            "Run setup_google_auth.py first to authorise Google Drive access."
        )
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        else:
            raise RuntimeError("Credentials invalid. Re-run setup_google_auth.py.")
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def list_queue_files(svc) -> list[dict]:
    """List all non-trashed files currently in the queue folder."""
    q = f"'{QUEUE_ID}' in parents and trashed = false"
    resp = svc.files().list(q=q, fields="files(id,name,mimeType)").execute()
    return resp.get("files", [])


def download_file(svc, file_id: str) -> bytes:
    """Download raw bytes for any file (not a Google Workspace doc)."""
    req = svc.files().get_media(fileId=file_id)
    buf = BytesIO()
    dl = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _, done = dl.next_chunk()
    return buf.getvalue()


def move_to_processed(svc, file_id: str) -> None:
    """Move a Drive file from queue/ to queue/processed/."""
    svc.files().update(
        fileId=file_id,
        addParents=PROCESSED_ID,
        removeParents=QUEUE_ID,
        fields="id,parents",
    ).execute()


# ── HTML / INDEX ─────────────────────────────────────────────────────────────

def iso_week(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def build_index_card(date_str: str, data: dict) -> str:
    """Render the HTML card to prepend into the #daily-grid div."""
    d = date.fromisoformat(date_str)
    dow    = WEEKDAYS[d.weekday()]
    week   = iso_week(d)
    regime = data.get("regime", {}).get("label", "MIXED")
    hl     = data.get("advisory", {}).get("headline", "Morning Market Monitor")
    body   = data.get("advisory", {}).get("body", "")
    sub    = (body.split(".")[0].strip() + ".") if body else ""
    return (
        f'<div class="card">\n'
        f'  <a href="mmm-daily/{date_str}.html">\n'
        f'    <div class="card-date">{dow} · {date_str} · {week}</div>\n'
        f'    <div class="card-title">{regime} — {hl}</div>\n'
        f'    <div class="card-sub">{sub}</div>\n'
        f'    <span class="card-badge badge-daily">DAILY MMM</span>\n'
        f'  </a>\n'
        f'</div>'
    )


def prepend_to_index(card_html: str) -> bool:
    """Insert card immediately after the opening <div id="daily-grid"> tag."""
    content = INDEX_HTML.read_text(encoding="utf-8")
    marker = 'id="daily-grid"'
    pos = content.find(marker)
    if pos == -1:
        log.error('Could not find id="daily-grid" in index.html')
        return False
    tag_end = content.index(">", pos) + 1
    updated = content[:tag_end] + "\n" + card_html + "\n" + content[tag_end:]
    INDEX_HTML.write_text(updated, encoding="utf-8")
    return True


# ── GIT ──────────────────────────────────────────────────────────────────────

def git(args: list[str]) -> tuple[int, str, str]:
    r = subprocess.run(
        ["git", "-C", str(REPO)] + args,
        capture_output=True, text=True,
    )
    return r.returncode, r.stdout.strip(), r.stderr.strip()


# ── MAIN SYNC ────────────────────────────────────────────────────────────────

def sync():
    log.info("══════════════════════════════════════════")
    log.info("  MMM Drive Sync — starting")
    log.info("══════════════════════════════════════════")

    svc = get_drive_service()
    all_files = list_queue_files(svc)

    if not all_files:
        log.info("Queue is empty. Nothing to sync. Exiting.")
        return

    # Group files by date stem: expects names like "2026-08-18.html" / ".json"
    date_re = re.compile(r"^(\d{4}-\d{2}-\d{2})\.(html|json)$")
    date_map: dict[str, dict] = {}
    for f in all_files:
        m = date_re.match(f["name"])
        if m:
            ds, ext = m.group(1), m.group(2)
            date_map.setdefault(ds, {})[ext] = f
        else:
            log.warning(f"Unrecognised file in queue, skipping: {f['name']}")

    # Only process dates that have BOTH html and json
    pairs = [
        (ds, fm)
        for ds, fm in sorted(date_map.items())
        if "html" in fm and "json" in fm
    ]

    if not pairs:
        log.info("No complete HTML+JSON pairs in queue yet. Waiting.")
        return

    log.info(f"Found {len(pairs)} complete pair(s): {[p[0] for p in pairs]}")
    staged: list[str] = []

    for date_str, fm in pairs:
        log.info(f"  ── Processing {date_str} ──")

        # Download HTML
        html_bytes = download_file(svc, fm["html"]["id"])
        html_dest  = HTML_DIR / f"{date_str}.html"
        html_dest.write_bytes(html_bytes)
        log.info(f"    ✓ HTML  → {html_dest}  ({len(html_bytes):,} bytes)")

        # Download JSON
        json_bytes = download_file(svc, fm["json"]["id"])
        json_dest  = JSON_DIR / f"{date_str}.json"
        json_dest.write_bytes(json_bytes)
        log.info(f"    ✓ JSON  → {json_dest}  ({len(json_bytes):,} bytes)")

        # Parse JSON for index card metadata
        data = json.loads(json_bytes)
        card = build_index_card(date_str, data)
        ok   = prepend_to_index(card)
        log.info(f"    {'✓' if ok else '✗'} index.html card prepended")

        staged += [
            f"shadowmonkey/mmm-daily/{date_str}.html",
            f"data/daily/{date_str}.json",
            "shadowmonkey/index.html",
        ]

        # Archive Drive files
        move_to_processed(svc, fm["html"]["id"])
        move_to_processed(svc, fm["json"]["id"])
        log.info(f"    ✓ Drive files archived to processed/")

    # git add
    rc, _, err = git(["add"] + staged)
    if rc != 0:
        log.error(f"git add failed: {err}")
        return
    log.info(f"Staged {len(staged)} files")

    # git commit
    labels = ", ".join(p[0] for p in pairs)
    msg = f"daily: {labels} MMM — Drive sync"
    rc, out, err = git(["commit", "-m", msg])
    if rc != 0:
        log.error(f"git commit failed: {err}")
        return
    log.info(f"Committed: {msg}")

    # git push
    rc, out, err = git(["push"])
    if rc == 0:
        log.info("✓ Pushed to GitHub — Pages deploy triggered")
    else:
        log.error(f"Push failed: {err}")

    log.info("══════════════════════════════════════════")
    log.info("  MMM Drive Sync — complete")
    log.info("══════════════════════════════════════════")


if __name__ == "__main__":
    sync()
