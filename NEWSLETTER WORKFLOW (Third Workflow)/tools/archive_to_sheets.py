"""Append one row per newsletter to the Google Sheet in GOOGLE_SHEETS_ID.

Columns: date, topic, headline, subject, recipients, status, html_file, infographic_file, sources

Usage:
    python tools/archive_to_sheets.py --input .tmp/research_<topic>.json --subject "..." \
        --recipients 3 --status sent --html .tmp/newsletter_<topic>.html --infographic .tmp/infographics/<topic>.png
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.utils import get_api_key, get_google_credentials

HEADER = ["date", "topic", "headline", "subject", "recipients", "status", "html_file", "infographic_file", "sources"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--recipients", type=int, default=0)
    parser.add_argument("--status", default="sent", choices=["sent", "test", "draft"])
    parser.add_argument("--html", default="")
    parser.add_argument("--infographic", default="")
    args = parser.parse_args()

    from googleapiclient.discovery import build

    sheet_id = get_api_key("GOOGLE_SHEETS_ID")
    research = json.loads(Path(args.input).read_text(encoding="utf-8"))
    values = build("sheets", "v4", credentials=get_google_credentials()).spreadsheets().values()

    if not values.get(spreadsheetId=sheet_id, range="A1:A1").execute().get("values"):
        values.update(spreadsheetId=sheet_id, range="A1", valueInputOption="RAW", body={"values": [HEADER]}).execute()

    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        research.get("topic", ""),
        research.get("headline", ""),
        args.subject,
        args.recipients,
        args.status,
        args.html,
        args.infographic,
        "; ".join(s["url"] for s in research.get("sources", [])),
    ]
    values.append(
        spreadsheetId=sheet_id, range="A1", valueInputOption="RAW", insertDataOption="INSERT_ROWS", body={"values": [row]}
    ).execute()
    print(f"Archived to sheet {sheet_id}: {args.subject}")


if __name__ == "__main__":
    main()
