"""Fetch recent uploads and stats for every tracked channel into .tmp/videos_raw.json.

Uses channels.list -> uploads playlist -> playlistItems.list -> videos.list (about 1 quota unit per call).
playlistItems returns only each channel's latest 50 uploads.

Usage:
    python tools/youtube_fetch_videos.py
"""

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.utils import (
    chunks,
    ensure_tmp_dir,
    load_config,
    niche_title_pattern,
    parse_iso,
    youtube_get,
)

DURATION = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def duration_seconds(iso: str) -> int:
    match = DURATION.fullmatch(iso or "")
    if not match:
        return 0
    hours, minutes, seconds = (int(g or 0) for g in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def main() -> None:
    niche = load_config("niche_keywords.json")
    channels = load_config("tracked_channels.json")["channels"]
    if not channels:
        sys.exit("No tracked channels. Run tools/youtube_discover_channels.py first.")
    cutoff = datetime.now(timezone.utc) - timedelta(days=niche["lookback_days"])
    title_pattern = niche_title_pattern(niche["title_terms"])
    channel_ids = [c["channel_id"] for c in channels]

    uploads, channel_stats = {}, {}
    for batch in chunks(channel_ids, 50):
        data = youtube_get(
            "channels",
            part="snippet,statistics,contentDetails",
            id=",".join(batch),
            maxResults=50,
        )
        for ch in data.get("items", []):
            uploads[ch["id"]] = ch["contentDetails"]["relatedPlaylists"]["uploads"]
            stats = ch.get("statistics", {})
            channel_stats[ch["id"]] = {
                "title": ch["snippet"]["title"],
                "custom_url": ch["snippet"].get("customUrl", ""),
                "country": ch["snippet"].get("country", ""),
                "created_at": ch["snippet"]["publishedAt"][:10],
                "description": " ".join(ch["snippet"].get("description", "").split())[
                    :300
                ],
                "subscribers": (
                    0
                    if stats.get("hiddenSubscriberCount")
                    else int(stats.get("subscriberCount", 0))
                ),
                "total_views": int(stats.get("viewCount", 0)),
                "video_count": int(stats.get("videoCount", 0)),
            }

    video_channel = {}
    for channel_id, playlist_id in uploads.items():
        data = youtube_get(
            "playlistItems",
            part="contentDetails",
            playlistId=playlist_id,
            maxResults=50,
        )
        for item in data.get("items", []):
            detail = item["contentDetails"]
            published = detail.get("videoPublishedAt")
            if published and parse_iso(published) >= cutoff:
                video_channel[detail["videoId"]] = channel_id

    videos = []
    for batch in chunks(list(video_channel), 50):
        data = youtube_get(
            "videos",
            part="snippet,statistics,contentDetails",
            id=",".join(batch),
            maxResults=50,
        )
        for v in data.get("items", []):
            if not title_pattern.search(v["snippet"]["title"]):
                continue
            stats = v.get("statistics", {})
            videos.append(
                {
                    "video_id": v["id"],
                    "channel_id": video_channel[v["id"]],
                    "channel_title": v["snippet"]["channelTitle"],
                    "title": v["snippet"]["title"],
                    "published_at": v["snippet"]["publishedAt"],
                    "duration_seconds": duration_seconds(
                        v["contentDetails"]["duration"]
                    ),
                    "views": int(stats.get("viewCount", 0)),
                    "likes": int(stats.get("likeCount", 0)),
                    "comments": int(stats.get("commentCount", 0)),
                }
            )

    tmp = ensure_tmp_dir()
    (tmp / "videos_raw.json").write_text(json.dumps(videos, indent=2), encoding="utf-8")
    (tmp / "channel_stats.json").write_text(
        json.dumps(channel_stats, indent=2), encoding="utf-8"
    )
    print(
        f"Fetched {len(videos)} videos from {len(channel_stats)} channels in the last {niche['lookback_days']} days."
    )


if __name__ == "__main__":
    main()
