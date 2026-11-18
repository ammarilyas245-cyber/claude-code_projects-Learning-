"""
discover_competitors.py

Uses Claude to identify 6-8 relevant competitors based on the business profile.
Saves results to .tmp/competitors_list.json with name, website, relevance_score, reasoning.
"""

import json
import os
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

PROFILE_PATH = ROOT / ".tmp" / "business_profile.json"
OUTPUT_PATH = ROOT / ".tmp" / "competitors_list.json"

DISCOVERY_PROMPT = """You are a competitive intelligence analyst. Based on the business profile below, identify 6-8 direct competitors.

Focus on companies that:
- Offer similar services (AI automation, workflow automation, CRM implementation, AI agent development)
- Target similar customers (small and mid-sized businesses)
- Operate in overlapping or comparable markets

For each competitor, provide:
- name: Company name
- website: Their website URL (best guess if not certain, mark uncertain ones)
- relevance_score: 0-100 (how directly they compete)
- reasoning: 1-2 sentences explaining why they're a competitor and what overlap exists
- competitor_type: "direct" (same services, same market), "indirect" (similar services, different market), or "aspirational" (larger player they should track)

Include a mix of:
- Global platforms/tools (like Zapier, Make, n8n Cloud)
- Boutique agencies similar in size and focus
- Regional players if identifiable

Business Profile:
{profile}

Respond with valid JSON only — a list of competitor objects. No markdown, no explanation outside the JSON."""


def load_profile() -> dict:
    if not PROFILE_PATH.exists():
        print(f"ERROR: Business profile not found at {PROFILE_PATH}")
        print("Run tools/collect_business_info.py first.")
        sys.exit(1)
    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def discover_competitors(profile: dict) -> list:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    profile_text = json.dumps(profile, indent=2)
    prompt = DISCOVERY_PROMPT.format(profile=profile_text)

    print("  Asking Claude to identify competitors...")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    competitors = json.loads(raw)

    # Merge in any known competitors from the profile
    known = profile.get("known_competitors", [])
    existing_names = {c["name"].lower() for c in competitors}
    for k in known:
        if k.lower() not in existing_names:
            competitors.append(
                {
                    "name": k,
                    "website": "",
                    "relevance_score": 80,
                    "reasoning": "Manually specified by user.",
                    "competitor_type": "direct",
                }
            )

    return competitors


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set in .env")
        sys.exit(1)

    print("Loading business profile...")
    profile = load_profile()
    print(f"  Company: {profile.get('company_name', 'N/A')}")

    print("\nDiscovering competitors via Claude...")
    competitors = discover_competitors(profile)

    # Sort by relevance score descending
    competitors.sort(key=lambda c: c.get("relevance_score", 0), reverse=True)

    output = {
        "discovery_date": __import__("datetime").datetime.now().isoformat(),
        "based_on_company": profile.get("company_name", ""),
        "total_found": len(competitors),
        "competitors": competitors,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nFound {len(competitors)} competitors:")
    for c in competitors:
        score = c.get("relevance_score", "?")
        ctype = c.get("competitor_type", "?")
        print(
            f"  [{score:>3}] {c['name']} ({ctype}) — {c.get('website', 'no website')}"
        )

    print(f"\nSaved to {OUTPUT_PATH}")

    if len(competitors) < 3:
        print("\nWARNING: Fewer than 3 competitors found.")
        print(
            "Consider adding known competitors to .tmp/business_profile.json under 'known_competitors'"
        )
        print("or run this tool again with a broader industry description.")


if __name__ == "__main__":
    main()
