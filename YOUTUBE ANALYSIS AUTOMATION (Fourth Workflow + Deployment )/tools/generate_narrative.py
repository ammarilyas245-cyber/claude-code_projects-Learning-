"""Write .tmp/narrative.json from trend_analysis.json using fixed templates (no AI call).

Every sentence is built from a number or title in the analysis JSON, so nothing is invented.
The wording is plainer than a hand-written narrative; the trade-off was chosen to avoid an
Anthropic API key in the unattended run.

Usage:
    python tools/generate_narrative.py --topic-label "Content Creation and Personal Branding"
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.utils import ensure_tmp_dir

MAX_FINDINGS = 5
MAX_OPPORTUNITIES = 5
MAX_LINE = 170  # keeps each line within two lines in the PDF and deck
MIN_SAMPLE = 30  # below this, the headline says the trend is directional only


def short(text: str, limit: int = 70) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def fmt_pct(current: float, baseline: float) -> str:
    if not baseline:
        return "n/a"
    change = (current - baseline) / baseline * 100
    return f"{change:+.0f}%"


def build_narrative(analysis: dict, topic_label: str | None, today: str) -> dict:
    scope = analysis["scope"]
    totals = analysis["totals"]
    formats = analysis["formats"]
    breakouts = analysis.get("top_breakout", [])
    engagement = analysis.get("top_engagement", [])
    active = analysis.get("most_active_channels", [])

    matched = scope["matched_videos"]
    niche = scope["niche_videos"]
    channels = totals["channels"]
    median = totals["median_views_per_day"]
    niche_median = totals["niche_median_views_per_day"]
    eng = totals["median_engagement_rate"]
    niche_eng = totals["niche_median_engagement_rate"]
    label = topic_label or scope.get("topic_label") or "AI and AI-automation"
    scoped = bool(scope.get("topic_pattern"))

    if scoped:
        title = f"{label}: AI YouTube Trends (Week of {today})"
        headline = (
            f"{matched} videos from {channels} channels on {label} reached a median of "
            f"{median:,.0f} views per day ({fmt_pct(median, niche_median)} vs the niche)."
        )
        if matched < MIN_SAMPLE:
            headline += " The sample is small, so treat the trends as directional."
    else:
        title = f"AI and AI-Automation YouTube Trends (Week of {today})"
        headline = (
            f"{matched} videos from {channels} channels reached a median of "
            f"{median:,.0f} views per day this week."
        )

    findings = []
    if scoped:
        findings.append(
            f"Scope: {matched} of {niche} niche videos match this topic. Their median is "
            f"{median:,.0f} views per day, {fmt_pct(median, niche_median)} against the niche median of {niche_median:,.0f}."
        )
    findings.append(
        f"Median engagement is {eng:.2%} against {niche_eng:.2%} for the niche."
    )
    long_f = formats.get("long", {})
    short_f = formats.get("short", {})
    if long_f.get("videos") and short_f.get("videos"):
        findings.append(
            f"Long-form median {long_f['median_views_per_day']:,.0f} views per day "
            f"({long_f['videos']} videos) vs Shorts {short_f['median_views_per_day']:,.0f} "
            f"({short_f['videos']} videos)."
        )
    for v in breakouts[:2]:
        findings.append(
            f"Breakout: {short(v['title'])} by {v['channel_title']} "
            f"({v['views']:,} views, {v['views_per_day']:,.0f} views per day, score {v['breakout_score']}x)."
        )
    if engagement:
        top = engagement[0]
        findings.append(
            f"Highest engagement: {top['engagement_rate']:.2%} on {short(top['title'])} "
            f"by {top['channel_title']} ({top['views']:,} views)."
        )

    opportunities = []
    if long_f.get("videos") and short_f.get("videos"):
        better, worse = (
            ("long-form", "Shorts")
            if long_f["median_views_per_day"] >= short_f["median_views_per_day"]
            else ("Shorts", "long-form")
        )
        opportunities.append(
            f"Lead with {better}: its median views per day beat {worse} in this data, so test {better} first."
        )
    for v in breakouts[:2]:
        opportunities.append(
            f"Study the breakout {short(v['title'])} ({v['breakout_score']}x its channel's median) and test a version of its angle."
        )
    if engagement:
        top = engagement[0]
        opportunities.append(
            f"Copy the structure of the engagement leader {short(top['title'])} ({top['engagement_rate']:.2%} engagement)."
        )
    if active:
        name, count = active[0]
        opportunities.append(
            f"Benchmark against {name}, the most active channel in this window with {count} videos."
        )
    if scoped and matched < MIN_SAMPLE:
        opportunities.append(
            f"Re-run next week: {matched} videos is a thin sample, so confirm any trend across more weeks."
        )

    narrative = {
        "title": title,
        "headline": headline,
        "key_findings": [f[:MAX_LINE] for f in findings[:MAX_FINDINGS]],
        "content_opportunities": [
            o[:MAX_LINE] for o in opportunities[:MAX_OPPORTUNITIES]
        ],
    }
    validate(narrative)
    return narrative


def validate(narrative: dict) -> None:
    for key in ("title", "headline", "key_findings", "content_opportunities"):
        if not narrative.get(key):
            raise ValueError(f"narrative is missing {key!r}")
    if len(narrative["key_findings"]) > MAX_FINDINGS:
        raise ValueError("too many key_findings")
    if len(narrative["content_opportunities"]) > MAX_OPPORTUNITIES:
        raise ValueError("too many content_opportunities")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic-label", default=None)
    args = parser.parse_args()

    tmp = ensure_tmp_dir()
    analysis = json.loads((tmp / "trend_analysis.json").read_text(encoding="utf-8"))
    narrative = build_narrative(analysis, args.topic_label, date.today().isoformat())
    (tmp / "narrative.json").write_text(
        json.dumps(narrative, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Narrative written: {narrative['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
