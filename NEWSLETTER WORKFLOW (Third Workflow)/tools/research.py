"""Research a topic (Tavily) and have Claude turn it into structured newsletter JSON.

Usage:
    python tools/research.py --topic "AI automation for small business" --depth medium
Output: .tmp/research_<topic>.json
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.utils import ensure_tmp_dir, extract_json, get_api_key, load_env, slugify

DEPTH = {
    "shallow": {"search_depth": "basic", "max_results": 6},
    "medium": {"search_depth": "advanced", "max_results": 10},
    "deep": {"search_depth": "advanced", "max_results": 15},
}

SYSTEM = (
    "You are the research editor for the newsletter of Ammar AI Automation Solution, a company helping "
    "businesses work smarter through AI and automation. Tone: clear, professional, trustworthy, forward "
    "thinking. Use ONLY facts that appear in the provided sources; never invent numbers or quotes."
)

SCHEMA = """Return ONLY a JSON object with this shape:
{
  "headline": "string, max 70 chars",
  "subtitle": "string, one sentence",
  "email_subject": "string, max 60 chars",
  "summary": "2-3 sentence executive summary",
  "sections": [{"heading": "string", "body": "2 short paragraphs", "key_points": ["3-4 bullets"]}],
  "takeaways": ["3 short action-oriented takeaways"],
  "infographic": {
    "title": "string",
    "type": "stat_cards | comparison | process | timeline",
    "data_points": [{"label": "string", "value": "string exactly as in the sources", "source_url": "string"}]
  },
  "sources": [{"title": "string", "url": "string"}]
}
Use 3-4 sections and 3-5 infographic data_points. Every data point must come from the sources."""


def search(topic: str, depth: str, days: int) -> dict:
    from tavily import TavilyClient

    client = TavilyClient(api_key=get_api_key("TAVILY_API_KEY"))
    cfg = DEPTH[depth]
    last_err = None
    for attempt in range(3):
        try:
            return client.search(
                query=topic,
                search_depth=cfg["search_depth"],
                max_results=cfg["max_results"],
                topic="news" if days <= 30 else "general",
                days=days,
                include_answer=True,
            )
        except Exception as err:
            last_err = err
            time.sleep(2**attempt)
    raise RuntimeError(f"Tavily search failed after 3 attempts: {last_err}")


def structure(topic: str, results: dict) -> dict:
    import anthropic

    load_env()
    import os

    client = anthropic.Anthropic(api_key=get_api_key("ANTHROPIC_API_KEY"))
    sources = "\n\n".join(
        f"[{i + 1}] {r['title']}\nURL: {r['url']}\nDate: {r.get('published_date', 'n/a')}\n{r['content']}"
        for i, r in enumerate(results["results"])
        if r.get("content")
    )
    msg = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
        max_tokens=4000,
        system=SYSTEM,
        messages=[{"role": "user", "content": f"Newsletter topic: {topic}\n\nSOURCES:\n{sources}\n\n{SCHEMA}"}],
    )
    return extract_json(msg.content[0].text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--depth", choices=DEPTH, default="medium")
    parser.add_argument("--days", type=int, default=30, help="how far back to search")
    args = parser.parse_args()

    raw = search(args.topic, args.depth, args.days)
    if not raw.get("results"):
        sys.exit("No results. Try rephrasing the topic or increasing --days.")
    data = structure(args.topic, raw)
    data["topic"] = args.topic
    data["researched_at"] = datetime.now().isoformat(timespec="seconds")
    out = ensure_tmp_dir() / f"research_{slugify(args.topic)}.json"
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {out} ({len(data['sections'])} sections, {len(data['sources'])} sources)")
