"""Find the most active AI-niche channels and merge them into config/tracked_channels.json.

Keyword searches are ordered by view count within the lookback window (search.list costs 100 quota units each).

Usage:
    python tools/youtube_discover_channels.py
"""

import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.utils import (
    chunks,
    ensure_tmp_dir,
    load_config,
    niche_title_pattern,
    save_config,
    youtube_get,
)


def main() -> None:
    import json

    niche = load_config("niche_keywords.json")
    tracked = load_config("tracked_channels.json")["channels"]
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=niche["lookback_days"])
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    title_pattern = niche_title_pattern(niche["title_terms"])

    keyword_hits = defaultdict(set)
    for keyword in niche["keywords"]:
        data = youtube_get(
            "search",
            part="snippet",
            q=keyword,
            type="video",
            order="viewCount",
            publishedAfter=cutoff,
            maxResults=50,
            relevanceLanguage="en",
        )
        for item in data.get("items", []):
            if title_pattern.search(item["snippet"]["title"]):
                keyword_hits[item["snippet"]["channelId"]].add(keyword)

    discovered = []
    for batch in chunks(list(keyword_hits), 50):
        data = youtube_get(
            "channels", part="snippet,statistics", id=",".join(batch), maxResults=50
        )
        for ch in data.get("items", []):
            stats = ch.get("statistics", {})
            subs = (
                0
                if stats.get("hiddenSubscriberCount")
                else int(stats.get("subscriberCount", 0))
            )
            if subs < niche["min_subscribers"]:
                continue
            matched = sorted(keyword_hits[ch["id"]])
            if len(matched) < niche["min_keyword_hits"]:
                continue
            discovered.append(
                {
                    "channel_id": ch["id"],
                    "title": ch["snippet"]["title"],
                    "subscribers": subs,
                    "keyword_hits": len(matched),
                    "matched_keywords": matched,
                }
            )

    discovered.sort(key=lambda c: (c["keyword_hits"], c["subscribers"]), reverse=True)
    top = discovered[: niche["discovery_top_n"]]

    known = {c["channel_id"]: c for c in tracked}
    new_count = 0
    for c in top:
        if c["channel_id"] not in known:
            known[c["channel_id"]] = {
                "channel_id": c["channel_id"],
                "title": c["title"],
            }
            new_count += 1
    channels = list(known.values())[: niche["max_tracked_channels"]]
    save_config("tracked_channels.json", {"channels": channels})

    out = ensure_tmp_dir() / "discovered_channels.json"
    out.write_text(
        json.dumps({"top": top, "new_this_run": new_count}, indent=2), encoding="utf-8"
    )
    print(
        f"Discovered {len(discovered)} channels over {niche['min_subscribers']} subs; "
        f"added {new_count} new. Tracking {len(channels)} channels. Output: {out}"
    )


if __name__ == "__main__":
    main()
