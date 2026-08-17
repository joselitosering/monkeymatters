#!/usr/bin/env python3
"""
Shadow Monkey — One-time Google OAuth2 Setup
Run this script ONCE to authorise mmm_sync.py to access Google Drive.

Requirements (install first):
  pip install google-auth-oauthlib google-api-python-client

Steps:
  1. Download credentials.json from Google Cloud Console
     → https://console.cloud.google.com/apis/credentials
     → Create project → Enable Google Drive API
     → Create credentials → OAuth 2.0 Client ID → Desktop app
     → Download JSON → save as  scripts/credentials.json

  2. Run this script:
     python scripts/setup_google_auth.py

  3. A browser window opens → sign in as joselitovsering@gmail.com → click Allow

  4. token.json is saved in scripts/ — mmm_sync.py is now authorised.
     You never need to run this again unless you revoke access.
"""

from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES      = ["https://www.googleapis.com/auth/drive"]
SCRIPTS_DIR = Path(__file__).parent
CREDS_FILE  = SCRIPTS_DIR / "credentials.json"
TOKEN_FILE  = SCRIPTS_DIR / "token.json"


def main():
    if not CREDS_FILE.exists():
        print(f"\n❌  credentials.json not found at:\n    {CREDS_FILE}")
        print("\nTo fix:")
        print("  1. Visit https://console.cloud.google.com/apis/credentials")
        print("  2. Create a project and enable Google Drive API")
        print("  3. Create OAuth2 credentials (Desktop app type)")
        print("  4. Download JSON and save it as  scripts/credentials.json")
        print("  5. Re-run this script.\n")
        return

    print("\nOpening browser for Google authorisation...")
    flow  = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
    creds = flow.run_local_server(port=0)

    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    print(f"\n✓  token.json saved to:\n   {TOKEN_FILE}")
    print("\n  mmm_sync.py is now authorised to access Google Drive.")
    print("  You do not need to run this script again.\n")


if __name__ == "__main__":
    main()
