"""Append one row per presentation to the branded Presentation Tracking Google Sheet.

The first run creates the spreadsheet and saves its ID and the logo's Drive URL to
config/tracking_sheet.json. Older copies with channel tabs are migrated by removing those tabs,
since channel data now lives in the separate channel sheet (tools/update_channel_sheet.py).

Usage:
    python tools/update_tracking_sheet.py --deck-url "<deck url>"
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from googleapiclient.discovery import build

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.sheet_branding import (
    append_rows,
    sheet_ids,
    setup_tabs,
    upload_logo,
)
from tools.utils import (
    PROJECT_ROOT,
    ensure_tmp_dir,
    get_google_credentials,
    load_config,
    save_config,
)

TAB = "Presentation Tracking"
HEADERS = {
    TAB: [
        "Date",
        "Top Breakout Title",
        "Top Breakout URL",
        "Breakout Score",
        "Top Channel",
        "Median Views / Day",
        "Median Engagement",
        "Videos Analyzed",
        "Deck",
    ]
}
TITLE_PREFIX = "Weekly AI YouTube Trends"
SCHEMA_VERSION = 3
STATE_FILE = "tracking_sheet.json"
LEGACY_TABS = ["Weekly Summary", "Channel Details", "Video Data", "Channels"]


def create_spreadsheet(sheets, drive, style: dict) -> dict:
    logo = PROJECT_ROOT / style["logo_path"]
    logo_url = upload_logo(drive, logo) if logo.exists() else None
    body = {
        "properties": {"title": "YouTube AI Presentation Tracker"},
        "sheets": [{"properties": {"title": TAB}}],
    }
    created = sheets.create(body=body, fields="spreadsheetId,spreadsheetUrl").execute()
    sid = created["spreadsheetId"]
    setup_tabs(
        sheets, sid, HEADERS, sheet_ids(sheets, sid), TITLE_PREFIX, logo_url, style
    )
    return {
        "spreadsheet_id": sid,
        "spreadsheet_url": created["spreadsheetUrl"],
        "logo_url": logo_url,
        "schema_version": SCHEMA_VERSION,
    }


def migrate_spreadsheet(sheets, state: dict, style: dict) -> dict:
    sid = state["spreadsheet_id"]
    ids = sheet_ids(sheets, sid)
    requests = [
        {"deleteSheet": {"sheetId": ids[name]}}
        for name in LEGACY_TABS
        if name in ids and name != "Weekly Summary"
    ]
    if "Weekly Summary" in ids:
        requests.append(
            {
                "updateSheetProperties": {
                    "properties": {"sheetId": ids["Weekly Summary"], "title": TAB},
                    "fields": "title",
                }
            }
        )
    elif TAB not in ids:
        requests.append({"addSheet": {"properties": {"title": TAB}}})
    if requests:
        sheets.batchUpdate(spreadsheetId=sid, body={"requests": requests}).execute()
    ids = sheet_ids(sheets, sid)
    setup_tabs(sheets, sid, HEADERS, ids, TITLE_PREFIX, state.get("logo_url"), style)
    return {**state, "schema_version": SCHEMA_VERSION}


def ensure_spreadsheet(sheets, drive, style: dict) -> dict:
    path = PROJECT_ROOT / "config" / STATE_FILE
    if not path.exists():
        state = create_spreadsheet(sheets, drive, style)
        save_config(STATE_FILE, state)
        print(f"Created presentation tracker: {state['spreadsheet_url']}")
        return state
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("schema_version") != SCHEMA_VERSION:
        state = migrate_spreadsheet(sheets, state, style)
        save_config(STATE_FILE, state)
        print(f"Migrated presentation tracker: {state['spreadsheet_url']}")
    return state


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deck-url", required=True)
    args = parser.parse_args()

    analysis = json.loads(
        (ensure_tmp_dir() / "trend_analysis.json").read_text(encoding="utf-8")
    )
    style = load_config("youtube_deck_style.json")

    creds = get_google_credentials()
    sheets = build("sheets", "v4", credentials=creds).spreadsheets()
    drive = build("drive", "v3", credentials=creds)
    state = ensure_spreadsheet(sheets, drive, style)

    top = analysis["top_breakout"][0] if analysis["top_breakout"] else {}
    row = [
        date.today().isoformat(),
        top.get("title", ""),
        top.get("url", ""),
        top.get("breakout_score", ""),
        top.get("channel_title", ""),
        analysis["totals"]["median_views_per_day"],
        analysis["totals"]["median_engagement_rate"],
        analysis["totals"]["videos"],
        args.deck_url,
    ]
    append_rows(sheets, state["spreadsheet_id"], TAB, [row])
    print(f"Logged presentation row. Sheet: {state['spreadsheet_url']}")


if __name__ == "__main__":
    main()
