"""Append each run's channel and video data to the YouTube Channel Intelligence Google Sheet.

Tabs: Channel Details (one row per tracked channel per run) and Video Data (one row per fetched video).
The first run creates the spreadsheet and saves its ID to config/channel_sheet.json.
Both tabs are append-only history.

Usage:
    python tools/update_channel_sheet.py
"""

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

CHANNEL_TAB = "Channel Details"
VIDEO_TAB = "Video Data"
HEADERS = {
    CHANNEL_TAB: [
        "Run Date",
        "Channel",
        "Channel ID",
        "YouTube Link",
        "Custom URL",
        "Country",
        "Channel Created",
        "Subscribers",
        "Total Views",
        "Total Videos",
        "Avg Views per Video",
        "Videos This Run",
        "Uploads per Week",
        "Short Share",
        "Latest Upload",
        "Median Views / Day",
        "Median Engagement",
        "Most Viewed This Run",
        "Most Viewed URL",
        "Most Viewed Views",
        "Top Keywords",
        "Description",
    ],
    VIDEO_TAB: [
        "Run Date",
        "Video ID",
        "Channel",
        "Channel ID",
        "Title",
        "Format",
        "Published",
        "Duration (s)",
        "Age (days)",
        "Views",
        "Likes",
        "Comments",
        "Views / Day",
        "Engagement",
        "Breakout Score",
        "Video URL",
    ],
}
TITLE_PREFIX = "YouTube Channel Intelligence"
SCHEMA_VERSION = 1
STATE_FILE = "channel_sheet.json"


def create_spreadsheet(sheets, drive, style: dict) -> dict:
    tracking = PROJECT_ROOT / "config" / "tracking_sheet.json"
    logo_url = None
    if tracking.exists():
        logo_url = json.loads(tracking.read_text(encoding="utf-8")).get("logo_url")
    if not logo_url:
        logo = PROJECT_ROOT / style["logo_path"]
        logo_url = upload_logo(drive, logo) if logo.exists() else None
    body = {
        "properties": {"title": "YouTube Channel Intelligence"},
        "sheets": [{"properties": {"title": tab}} for tab in HEADERS],
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


def ensure_spreadsheet(sheets, drive, style: dict) -> dict:
    path = PROJECT_ROOT / "config" / STATE_FILE
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    state = create_spreadsheet(sheets, drive, style)
    save_config(STATE_FILE, state)
    print(f"Created channel intelligence sheet: {state['spreadsheet_url']}")
    return state


def channel_row(today: str, cid: str, s: dict) -> list:
    video_count = s["video_count"]
    return [
        today,
        s["title"],
        cid,
        f"https://www.youtube.com/channel/{cid}",
        s.get("custom_url", ""),
        s.get("country", ""),
        s.get("created_at", ""),
        s["subscribers"],
        s["total_views"],
        video_count,
        round(s["total_views"] / video_count) if video_count else 0,
        s["videos_this_run"],
        s["uploads_per_week"],
        s["short_share"],
        s["latest_upload"],
        s["median_views_per_day"],
        s["median_engagement_rate"],
        s["top_video_title"],
        s["top_video_url"],
        s["top_video_views"],
        ", ".join(s["top_keywords"]),
        s.get("description", ""),
    ]


def video_row(today: str, v: dict) -> list:
    return [
        today,
        v["video_id"],
        v["channel_title"],
        v["channel_id"],
        v["title"],
        v["format"],
        v["published_at"][:10],
        v["duration_seconds"],
        v["age_days"],
        v["views"],
        v["likes"],
        v["comments"],
        v["views_per_day"],
        v["engagement_rate"],
        v["breakout_score"] if v["breakout_score"] is not None else "",
        v["url"],
    ]


def main() -> None:
    tmp = ensure_tmp_dir()
    analysis = json.loads((tmp / "trend_analysis.json").read_text(encoding="utf-8"))
    videos = json.loads((tmp / "videos_analyzed.json").read_text(encoding="utf-8"))
    style = load_config("youtube_deck_style.json")
    today = date.today().isoformat()

    creds = get_google_credentials()
    sheets = build("sheets", "v4", credentials=creds).spreadsheets()
    drive = build("drive", "v3", credentials=creds)
    state = ensure_spreadsheet(sheets, drive, style)
    sid = state["spreadsheet_id"]

    channels = [
        channel_row(today, cid, s) for cid, s in analysis["channel_summary"].items()
    ]
    video_rows = [video_row(today, v) for v in videos]
    append_rows(sheets, sid, CHANNEL_TAB, channels)
    append_rows(sheets, sid, VIDEO_TAB, video_rows)
    print(
        f"Logged {len(channels)} channel rows and {len(video_rows)} video rows. "
        f"Sheet: {state['spreadsheet_url']}"
    )


if __name__ == "__main__":
    main()
