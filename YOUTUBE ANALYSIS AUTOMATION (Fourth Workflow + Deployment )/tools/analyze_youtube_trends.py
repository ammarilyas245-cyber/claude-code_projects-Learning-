"""Compute breakout scores, engagement, format split and topic signals into .tmp/trend_analysis.json.

Breakout score = video views/day divided by its channel's median views/day (channels with at least 3 videos).

Usage:
    python tools/analyze_youtube_trends.py
    python tools/analyze_youtube_trends.py --topic-pattern "\\b(meta|llama)\\b"

With --topic-pattern, baselines still come from every fetched video (so breakout scores stay
comparable), but the breakout, engagement, format and topic outputs only count videos whose
title matches the pattern. Channel sheet data (videos_analyzed.json) is never filtered.
"""

import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.utils import ensure_tmp_dir, load_config, parse_iso

MIN_AGE_DAYS = 2
MIN_VIEWS_FOR_BREAKOUT = 500
MIN_VIDEOS_FOR_BASELINE = 3
SHORT_MAX_SECONDS = 180
WORD = re.compile(r"[a-z][a-z0-9+\-]{2,}")
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "you",
    "your",
    "how",
    "what",
    "why",
    "are",
    "can",
    "will",
    "its",
    "from",
    "just",
    "new",
    "get",
    "use",
    "using",
    "into",
    "not",
    "all",
    "out",
    "top",
    "best",
    "our",
    "now",
    "here",
    "his",
    "her",
    "more",
    "make",
    "made",
    "video",
    "full",
    "part",
    "you're",
    "it's",
    "don't",
    "they",
    "them",
    "than",
    "about",
    "like",
    "when",
    "who",
    "why",
    "was",
}


def median(values: list) -> float:
    return statistics.median(values) if values else 0.0


def summarize(r: dict) -> dict:
    return {
        "video_id": r["video_id"],
        "title": r["title"],
        "channel_title": r["channel_title"],
        "url": f"https://www.youtube.com/watch?v={r['video_id']}",
        "format": r["format"],
        "age_days": r["age_days"],
        "views": r["views"],
        "views_per_day": round(r["views_per_day"], 1),
        "engagement_rate": round(r["engagement_rate"], 4),
        "breakout_score": r["breakout_score"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--topic-pattern", default="", help="regex on titles to scope the output"
    )
    parser.add_argument(
        "--topic-label", default="", help="readable topic name shown in the deck"
    )
    args = parser.parse_args()
    topic_re = (
        re.compile(args.topic_pattern, re.IGNORECASE) if args.topic_pattern else None
    )

    tmp = ensure_tmp_dir()
    raw = json.loads((tmp / "videos_raw.json").read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    niche_days = load_config("niche_keywords.json")["lookback_days"]

    rows = []
    for v in raw:
        age = (now - parse_iso(v["published_at"])).total_seconds() / 86400
        if age < MIN_AGE_DAYS:
            continue
        views = v["views"]
        rows.append(
            {
                **v,
                "age_days": round(age, 1),
                "views_per_day": views / age,
                "engagement_rate": (
                    (v["likes"] + v["comments"]) / views if views else 0.0
                ),
                "format": (
                    "short" if v["duration_seconds"] <= SHORT_MAX_SECONDS else "long"
                ),
            }
        )

    per_channel = defaultdict(list)
    for r in rows:
        per_channel[r["channel_id"]].append(r["views_per_day"])
    baseline = {
        ch: median(vals)
        for ch, vals in per_channel.items()
        if len(vals) >= MIN_VIDEOS_FOR_BASELINE
    }
    for r in rows:
        base = baseline.get(r["channel_id"])
        r["breakout_score"] = round(r["views_per_day"] / base, 2) if base else None

    # Output scope: all fetched videos, or only the topic-matched ones.
    scoped = [r for r in rows if topic_re is None or topic_re.search(r["title"])]

    breakout_pool = [
        r
        for r in scoped
        if r["breakout_score"] is not None and r["views"] >= MIN_VIEWS_FOR_BREAKOUT
    ]
    breakout_pool.sort(key=lambda r: r["breakout_score"], reverse=True)
    engagement_pool = sorted(scoped, key=lambda r: r["engagement_rate"], reverse=True)

    formats = {}
    for fmt in ("short", "long"):
        subset = [r for r in scoped if r["format"] == fmt]
        formats[fmt] = {
            "videos": len(subset),
            "median_views_per_day": round(
                median([r["views_per_day"] for r in subset]), 1
            ),
            "median_engagement_rate": round(
                median([r["engagement_rate"] for r in subset]), 4
            ),
        }

    topic_counts = Counter()
    for r in scoped:
        topic_counts.update(
            {w for w in WORD.findall(r["title"].lower()) if w not in STOPWORDS}
        )

    analysis = {
        "generated_at": now.isoformat(),
        "scope": {
            "topic_pattern": args.topic_pattern or None,
            "topic_label": args.topic_label or args.topic_pattern or None,
            "matched_videos": len(scoped),
            "niche_videos": len(rows),
        },
        "totals": {
            "videos": len(scoped),
            "channels": len({r["channel_id"] for r in scoped}),
            "median_views_per_day": round(
                median([r["views_per_day"] for r in scoped]), 1
            ),
            "median_engagement_rate": round(
                median([r["engagement_rate"] for r in scoped]), 4
            ),
            "niche_median_views_per_day": round(
                median([r["views_per_day"] for r in rows]), 1
            ),
            "niche_median_engagement_rate": round(
                median([r["engagement_rate"] for r in rows]), 4
            ),
        },
        "top_breakout": [summarize(r) for r in breakout_pool[:10]],
        "top_engagement": [summarize(r) for r in engagement_pool[:10]],
        "formats": formats,
        "topics": topic_counts.most_common(20),
        "most_active_channels": Counter(r["channel_title"] for r in rows).most_common(
            10
        ),
    }
    breakout_by_id = {r["video_id"]: r["breakout_score"] for r in rows}
    all_videos = []
    for v in raw:
        age = max((now - parse_iso(v["published_at"])).total_seconds() / 86400, 0.1)
        views = v["views"]
        all_videos.append(
            {
                "video_id": v["video_id"],
                "channel_id": v["channel_id"],
                "channel_title": v["channel_title"],
                "title": v["title"],
                "url": f"https://www.youtube.com/watch?v={v['video_id']}",
                "format": (
                    "short" if v["duration_seconds"] <= SHORT_MAX_SECONDS else "long"
                ),
                "published_at": v["published_at"],
                "duration_seconds": v["duration_seconds"],
                "age_days": round(age, 1),
                "views": views,
                "likes": v["likes"],
                "comments": v["comments"],
                "views_per_day": round(views / age, 1),
                "engagement_rate": (
                    round((v["likes"] + v["comments"]) / views, 4) if views else 0.0
                ),
                "breakout_score": breakout_by_id.get(v["video_id"]),
            }
        )

    channel_stats = json.loads((tmp / "channel_stats.json").read_text(encoding="utf-8"))
    channel_summary = {}
    for cid, stats in channel_stats.items():
        vids = [e for e in all_videos if e["channel_id"] == cid]
        top = max(vids, key=lambda e: e["views"], default=None)
        channel_summary[cid] = {
            **stats,
            "videos_this_run": len(vids),
            "median_views_per_day": round(
                median([e["views_per_day"] for e in vids]), 1
            ),
            "median_engagement_rate": round(
                median([e["engagement_rate"] for e in vids]), 4
            ),
            "top_video_title": top["title"] if top else "",
            "top_video_url": top["url"] if top else "",
            "top_video_views": top["views"] if top else 0,
            "latest_upload": max((e["published_at"][:10] for e in vids), default=""),
            "uploads_per_week": round(len(vids) / (niche_days / 7), 1),
            "short_share": (
                round(sum(1 for e in vids if e["format"] == "short") / len(vids), 2)
                if vids
                else 0.0
            ),
            "top_keywords": [
                w
                for w, _ in Counter(
                    w
                    for e in vids
                    for w in set(WORD.findall(e["title"].lower()))
                    if w not in STOPWORDS
                ).most_common(5)
            ],
        }
    analysis["channel_summary"] = channel_summary

    (tmp / "videos_analyzed.json").write_text(
        json.dumps(all_videos, indent=2), encoding="utf-8"
    )
    out = tmp / "trend_analysis.json"
    out.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    print(f"Analyzed {len(rows)} videos. Output: {out}")


if __name__ == "__main__":
    main()
