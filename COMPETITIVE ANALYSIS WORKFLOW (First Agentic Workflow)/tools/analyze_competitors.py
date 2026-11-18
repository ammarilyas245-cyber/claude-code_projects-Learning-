"""
analyze_competitors.py

Loads business profile + all cached competitor data and generates
a structured comparative analysis across 4 dimensions using Claude.
Saves results to .tmp/analysis_history/analysis_YYYYMM.json.
Compares with previous month's analysis if available.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import anthropic
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

PROFILE_PATH = ROOT / ".tmp" / "business_profile.json"
CACHE_DIR = ROOT / ".tmp" / "competitors"
HISTORY_DIR = ROOT / ".tmp" / "analysis_history"

ANALYSIS_PROMPT = """You are a senior competitive intelligence analyst. Analyze the following competitor data relative to our company.

OUR COMPANY:
{our_company}

COMPETITOR: {competitor_name}
DATA:
{competitor_data}

Provide a structured analysis across exactly 4 dimensions. Respond with valid JSON only:

{{
  "competitor_name": "{competitor_name}",
  "website": "...",
  "competitor_type": "direct/indirect/aspirational",
  "threat_level": "Low/Medium/High",
  "threat_reasoning": "1-2 sentences explaining threat level",
  "dimensions": {{
    "product_features": {{
      "services_offered": ["list their main services"],
      "tech_stack": ["technologies they use or offer"],
      "feature_gaps_vs_us": ["things they offer that we don't"],
      "our_gaps_vs_them": ["things we offer that they might lack"],
      "notable_strengths": ["2-3 standout capabilities"]
    }},
    "pricing_model": {{
      "model_type": "project-based/retainer/subscription/freemium/unknown",
      "tiers": ["pricing tiers if known"],
      "price_range": "rough range or null",
      "positioning": "budget/mid-market/premium/enterprise",
      "our_advantage": "how our pricing/model compares"
    }},
    "marketing_messaging": {{
      "positioning_statement": "how they describe themselves",
      "target_audience": "who they're clearly targeting",
      "key_messages": ["top 3 messages they emphasize"],
      "channels": ["marketing channels they use"],
      "content_strategy": "brief description",
      "tone": "professional/casual/technical/friendly"
    }},
    "strengths_weaknesses": {{
      "their_strengths_vs_us": ["areas where they clearly outperform us"],
      "our_advantages_vs_them": ["areas where we clearly outperform them"],
      "opportunities_for_us": ["gaps in their offering we can exploit"],
      "threats_to_us": ["ways they could take business from us"]
    }}
  }}
}}

Base your analysis only on the data provided. If a field is unknown, use null or an empty list.
No markdown, no explanation. JSON only."""

SUMMARY_PROMPT = """You are a senior competitive intelligence analyst. Based on this competitive analysis data, provide a strategic market summary.

OUR COMPANY: {company_name}
Industry: {industry}

COMPETITIVE LANDSCAPE DATA:
{all_competitors_summary}

Provide a strategic summary in this JSON format:

{{
  "market_overview": "3-4 sentence overview of the competitive landscape",
  "market_positioning": "where our company sits relative to competitors",
  "key_themes": ["3-5 patterns observed across competitors"],
  "strategic_insights": [
    {{
      "insight": "specific actionable insight",
      "priority": "High/Medium/Low",
      "rationale": "why this matters"
    }}
  ],
  "recommendations": [
    {{
      "recommendation": "specific action to take",
      "priority": "High/Medium/Low",
      "effort": "Low/Medium/High",
      "rationale": "why and expected impact"
    }}
  ],
  "competitive_summary_table": [
    {{
      "competitor": "name",
      "threat_level": "Low/Medium/High",
      "top_strength": "their biggest advantage",
      "our_advantage": "where we beat them"
    }}
  ]
}}

Provide 3-5 strategic insights and 4-6 prioritized recommendations.
No markdown, no explanation. JSON only."""


def load_profile() -> dict:
    if not PROFILE_PATH.exists():
        print(f"ERROR: Business profile not found at {PROFILE_PATH}")
        sys.exit(1)
    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_competitor_cache() -> list:
    if not CACHE_DIR.exists():
        print(f"ERROR: No competitor cache found at {CACHE_DIR}")
        print("Run tools/research_competitor.py first.")
        sys.exit(1)
    competitors = []
    for f in CACHE_DIR.glob("*.json"):
        with open(f, "r", encoding="utf-8") as fh:
            competitors.append(json.load(fh))
    if not competitors:
        print("ERROR: No competitor data found in cache.")
        sys.exit(1)
    return competitors


def load_previous_analysis() -> dict | None:
    if not HISTORY_DIR.exists():
        return None
    now = datetime.now()
    # Look for last month's analysis
    if now.month == 1:
        prev_key = f"analysis_{now.year - 1}12.json"
    else:
        prev_key = f"analysis_{now.year}{now.month - 1:02d}.json"
    prev_path = HISTORY_DIR / prev_key
    if prev_path.exists():
        with open(prev_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def analyze_competitor(
    competitor: dict, profile: dict, client: anthropic.Anthropic
) -> dict:
    name = competitor.get("company_name", competitor.get("name", "Unknown"))
    print(f"  Analyzing {name}...")

    our_company = {
        "name": profile.get("company_name", ""),
        "services": profile.get("services", []),
        "differentiators": profile.get("differentiators", []),
        "target_markets": profile.get("target_markets", []),
        "value_proposition": profile.get("value_proposition", ""),
    }

    prompt = ANALYSIS_PROMPT.format(
        our_company=json.dumps(our_company, indent=2),
        competitor_name=name,
        competitor_data=json.dumps(competitor, indent=2)[:6000],
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        analysis = json.loads(raw.strip())
        analysis["data_completeness"] = competitor.get("data_completeness", 0)
        if competitor.get("data_note"):
            analysis["data_note"] = competitor["data_note"]
        return analysis
    except Exception as e:
        print(f"    ERROR analyzing {name}: {e}")
        return {
            "competitor_name": name,
            "error": str(e),
            "data_completeness": 0,
        }


def build_summary(
    profile: dict, competitor_analyses: list, client: anthropic.Anthropic
) -> dict:
    print("\n  Generating market overview and strategic recommendations...")

    summaries = []
    for a in competitor_analyses:
        name = a.get("competitor_name", "?")
        threat = a.get("threat_level", "?")
        dims = a.get("dimensions", {})
        sw = dims.get("strengths_weaknesses", {})
        summaries.append(
            {
                "name": name,
                "threat_level": threat,
                "their_strengths": sw.get("their_strengths_vs_us", [])[:3],
                "our_advantages": sw.get("our_advantages_vs_them", [])[:3],
            }
        )

    prompt = SUMMARY_PROMPT.format(
        company_name=profile.get("company_name", ""),
        industry=profile.get("industry", "AI automation services"),
        all_competitors_summary=json.dumps(summaries, indent=2),
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        print(f"    ERROR generating summary: {e}")
        return {"error": str(e)}


def detect_changes(current: list, previous_data: dict) -> list:
    """Compare current analysis with previous month to surface changes."""
    if not previous_data:
        return []
    prev_competitors = {
        c.get("competitor_name"): c
        for c in previous_data.get("competitor_analyses", [])
    }
    changes = []
    for curr in current:
        name = curr.get("competitor_name")
        if name not in prev_competitors:
            changes.append(f"NEW: {name} added to analysis")
            continue
        prev = prev_competitors[name]
        if curr.get("threat_level") != prev.get("threat_level"):
            changes.append(
                f"THREAT CHANGE: {name} — {prev.get('threat_level')} → {curr.get('threat_level')}"
            )
    removed = set(prev_competitors.keys()) - {c.get("competitor_name") for c in current}
    for name in removed:
        changes.append(f"REMOVED: {name} no longer in analysis")
    return changes


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set in .env")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    print("Loading business profile...")
    profile = load_profile()

    print("Loading competitor cache...")
    competitors = load_competitor_cache()
    print(f"  Found {len(competitors)} cached competitors")

    previous = load_previous_analysis()
    if previous:
        prev_date = previous.get("analysis_date", "unknown")
        print(f"  Found previous analysis from {prev_date[:7]} for comparison")

    print(f"\nAnalyzing {len(competitors)} competitors...")
    analyses = []
    for c in competitors:
        analysis = analyze_competitor(c, profile, client)
        analyses.append(analysis)

    summary = build_summary(profile, analyses, client)

    changes = detect_changes(analyses, previous)

    now = datetime.now()
    output = {
        "analysis_date": now.isoformat(),
        "analysis_month": now.strftime("%Y-%m"),
        "our_company": {
            "name": profile.get("company_name"),
            "services": profile.get("services", []),
            "differentiators": profile.get("differentiators", []),
            "target_markets": profile.get("target_markets", []),
        },
        "total_competitors": len(analyses),
        "market_summary": summary,
        "competitor_analyses": analyses,
        "month_over_month_changes": (
            changes if changes else ["First analysis — no historical data to compare"]
        ),
    }

    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"analysis_{now.strftime('%Y%m')}.json"
    output_path = HISTORY_DIR / filename
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nAnalysis complete. Saved to {output_path}")

    # Print threat summary
    print("\nThreat Summary:")
    for a in sorted(
        analyses,
        key=lambda x: {"High": 0, "Medium": 1, "Low": 2}.get(
            x.get("threat_level", "Low"), 3
        ),
    ):
        threat = a.get("threat_level", "?")
        name = a.get("competitor_name", "?")
        print(f"  [{threat:6s}] {name}")

    if changes:
        print("\nChanges from last month:")
        for c in changes:
            print(f"  • {c}")

    # Print top recommendations
    recs = summary.get("recommendations", [])
    if recs:
        high_prio = [r for r in recs if r.get("priority") == "High"]
        print(f"\nTop {len(high_prio)} High-Priority Recommendations:")
        for r in high_prio[:3]:
            print(f"  • {r.get('recommendation', '')}")


if __name__ == "__main__":
    main()
