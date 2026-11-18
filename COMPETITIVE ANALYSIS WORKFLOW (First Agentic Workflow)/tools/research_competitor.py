"""
research_competitor.py

Researches each competitor using Tavily search and extract.
Caches results in .tmp/competitors/[name].json with 30-day TTL.
Scores each competitor on data completeness (0-100%).
"""

import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from tavily import TavilyClient

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

COMPETITORS_LIST = ROOT / ".tmp" / "competitors_list.json"
CACHE_DIR = ROOT / ".tmp" / "competitors"
CACHE_TTL_DAYS = 30
MAX_WORKERS = 3
TAVILY_DELAY = 1.0  # seconds between calls

EXTRACTION_PROMPT = """You are extracting structured competitive intelligence from raw web content about a company.

Company: {name}
Website: {website}

Raw web content:
{content}

Extract the following and respond with valid JSON only:

{{
  "company_name": "...",
  "website": "...",
  "tagline": "... or null",
  "description": "2-3 sentence company description",
  "founded": "year or null",
  "company_size": "solo/small/medium/large or null",
  "services": ["list of main services/products"],
  "tech_stack": ["technologies they use or offer"],
  "pricing": {{
    "model": "project-based/retainer/subscription/freemium/unknown",
    "tiers": ["list pricing tiers if visible, e.g. Starter $X/mo"],
    "range": "rough range if visible, e.g. $500-5000/project, or null",
    "notes": "any pricing context"
  }},
  "target_market": {{
    "segments": ["customer types they serve"],
    "geographies": ["regions/countries they focus on"],
    "company_sizes": ["SMB/Enterprise/etc"]
  }},
  "marketing": {{
    "positioning": "how they position themselves in 1-2 sentences",
    "channels": ["channels they use: SEO/YouTube/LinkedIn/etc"],
    "content_strategy": "brief description or null",
    "tone": "professional/casual/technical/friendly"
  }},
  "key_features": ["top 5-8 distinguishing features or capabilities"],
  "data_sources": ["which sources had useful data"],
  "data_completeness": 0
}}

For data_completeness: score 0-100 based on how much real information you found.
- 0-30: Very sparse, mostly guesses
- 31-70: Partial — some real data, some gaps
- 71-100: Good — confident in most fields

No markdown, no explanation. JSON only."""


def cache_path(name: str) -> Path:
    safe_name = re.sub(r"[^\w\-]", "_", name.lower())
    return CACHE_DIR / f"{safe_name}.json"


def is_cache_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    return datetime.now() - mtime < timedelta(days=CACHE_TTL_DAYS)


def load_competitors() -> list:
    if not COMPETITORS_LIST.exists():
        print(f"ERROR: Competitors list not found at {COMPETITORS_LIST}")
        print("Run tools/discover_competitors.py first.")
        sys.exit(1)
    with open(COMPETITORS_LIST, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("competitors", [])


def tavily_search_with_backoff(
    client: TavilyClient, query: str, retries: int = 3
) -> list:
    for attempt in range(retries):
        try:
            result = client.search(query=query, search_depth="advanced", max_results=5)
            return result.get("results", [])
        except Exception as e:
            if "429" in str(e) and attempt < retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"    Rate limited. Waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"    Search failed for '{query}': {e}")
                return []
    return []


def tavily_extract_with_backoff(
    client: TavilyClient, urls: list, retries: int = 3
) -> dict:
    for attempt in range(retries):
        try:
            result = client.extract(urls=urls)
            return result
        except Exception as e:
            if "429" in str(e) and attempt < retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"    Rate limited. Waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"    Extract failed: {e}")
                return {}
    return {}


def build_research_content(name: str, website: str, tavily: TavilyClient) -> str:
    """Gather raw text from multiple sources for a competitor."""
    sections = []

    # 1. Extract homepage and key pages
    if website:
        urls_to_try = [website]
        for path in ["/pricing", "/services", "/about", "/features"]:
            base = website.rstrip("/")
            urls_to_try.append(base + path)

        print(f"    Extracting website content from {website}...")
        extract_result = tavily_extract_with_backoff(tavily, urls_to_try[:3])
        time.sleep(TAVILY_DELAY)

        if extract_result and "results" in extract_result:
            for r in extract_result["results"]:
                if r.get("raw_content"):
                    sections.append(
                        f"[Website: {r.get('url', '')}]\n{r['raw_content'][:3000]}"
                    )

    # 2. General search
    queries = [
        f"{name} AI automation services features",
        f"{name} pricing plans",
        f"{name} reviews competitors",
    ]
    for q in queries:
        results = tavily_search_with_backoff(tavily, q)
        time.sleep(TAVILY_DELAY)
        for r in results[:2]:
            snippet = r.get("content", "")
            if snippet:
                sections.append(f"[Search: {q}]\n{r.get('url', '')}\n{snippet[:1000]}")

    return "\n\n---\n\n".join(sections) if sections else ""


def extract_structured_data(
    name: str, website: str, content: str, anthropic_client: anthropic.Anthropic
) -> dict:
    """Use Claude to extract structured competitor data from raw content."""
    if not content.strip():
        return {
            "company_name": name,
            "website": website,
            "data_completeness": 0,
            "data_note": "No content could be retrieved. Manual research needed.",
        }

    prompt = EXTRACTION_PROMPT.format(
        name=name,
        website=website,
        content=content[:8000],
    )

    try:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        print(f"    Extraction error for {name}: {e}")
        return {
            "company_name": name,
            "website": website,
            "data_completeness": 15,
            "data_note": f"Extraction failed: {e}",
        }


def research_one(
    competitor: dict, tavily: TavilyClient, anthropic_client: anthropic.Anthropic
) -> dict:
    name = competitor["name"]
    website = competitor.get("website", "")
    path = cache_path(name)

    if is_cache_fresh(path):
        print(f"  [CACHED] {name}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"  [RESEARCHING] {name}...")
    content = build_research_content(name, website, tavily)

    if not content:
        print(f"    WARNING: No content retrieved for {name}. Using fallback.")

    data = extract_structured_data(name, website, content, anthropic_client)
    data["researched_at"] = datetime.now().isoformat()
    data["competitor_type"] = competitor.get("competitor_type", "direct")
    data["relevance_score"] = competitor.get("relevance_score", 50)

    completeness = data.get("data_completeness", 0)
    if completeness < 30:
        data["data_note"] = "Limited data — manual research recommended."
        print(f"    WARNING: Low completeness ({completeness}%) for {name}")
    elif completeness < 70:
        data["data_note"] = "Partial data — some fields may be incomplete."

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return data


def main():
    for key in ["ANTHROPIC_API_KEY", "TAVILY_API_KEY"]:
        if not os.environ.get(key):
            print(f"ERROR: {key} not set in .env")
            sys.exit(1)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    competitors = load_competitors()
    print(
        f"Researching {len(competitors)} competitors (cache TTL: {CACHE_TTL_DAYS} days)...\n"
    )

    results = []

    # Use thread pool but respect rate limits via delays in research_one
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(research_one, c, tavily, anthropic_client): c["name"]
            for c in competitors
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                data = future.result()
                results.append(data)
            except Exception as e:
                print(f"  ERROR researching {name}: {e}")

    # Summary
    print(f"\nResearch complete. Results:")
    for r in sorted(results, key=lambda x: x.get("data_completeness", 0), reverse=True):
        completeness = r.get("data_completeness", 0)
        flag = (
            " ⚠ LOW DATA"
            if completeness < 30
            else (" ~ PARTIAL" if completeness < 70 else " ✓")
        )
        print(f"  {r.get('company_name', '?'):30s} {completeness:>3}%{flag}")

    low_data = [r for r in results if r.get("data_completeness", 0) < 30]
    if low_data:
        print(f"\n{len(low_data)} competitor(s) need manual research:")
        for r in low_data:
            print(f"  - {r.get('company_name')} ({r.get('website', 'no website')})")

    print(f"\nCached to {CACHE_DIR}/")


if __name__ == "__main__":
    main()
