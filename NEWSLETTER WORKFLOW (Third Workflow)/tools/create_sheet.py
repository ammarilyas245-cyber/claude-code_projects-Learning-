"""Create the newsletter log Google Sheet and save its ID to .env as GOOGLE_SHEETS_ID.

Usage:
    python tools/create_sheet.py [--title "Newsletter Log"]
The first run opens a browser once for Google consent.
"""

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.archive_to_sheets import HEADER
from tools.utils import PROJECT_ROOT, get_google_credentials, load_env


def save_env(sheet_id: str) -> None:
    env = PROJECT_ROOT / ".env"
    text = env.read_text(encoding="utf-8") if env.exists() else ""
    if re.search(r"^GOOGLE_SHEETS_ID=.*$", text, re.M):
        text = re.sub(r"^GOOGLE_SHEETS_ID=.*$", f"GOOGLE_SHEETS_ID={sheet_id}", text, flags=re.M)
    else:
        text += f"\nGOOGLE_SHEETS_ID={sheet_id}\n"
    env.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", default="Newsletter Log")
    parser.add_argument("--force", action="store_true", help="create a new sheet even if GOOGLE_SHEETS_ID is set")
    args = parser.parse_args()

    load_env()
    if os.getenv("GOOGLE_SHEETS_ID") and not args.force:
        sys.exit(f"GOOGLE_SHEETS_ID is already set ({os.getenv('GOOGLE_SHEETS_ID')}). Use --force to create another.")

    from googleapiclient.discovery import build

    sheets = build("sheets", "v4", credentials=get_google_credentials())
    sheet = sheets.spreadsheets().create(body={"properties": {"title": args.title}}, fields="spreadsheetId,spreadsheetUrl").execute()
    sheets.spreadsheets().values().update(
        spreadsheetId=sheet["spreadsheetId"], range="A1", valueInputOption="RAW", body={"values": [HEADER]}
    ).execute()
    save_env(sheet["spreadsheetId"])
    print(f"Created '{args.title}': {sheet['spreadsheetUrl']}\nSaved GOOGLE_SHEETS_ID to .env")
