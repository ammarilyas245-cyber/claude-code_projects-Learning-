"""
collect_business_info.py

Collects and saves business profile information to .tmp/business_profile.json.
On first run, auto-populates from the company overview markdown file.
On subsequent runs, allows updating specific fields.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
TMP = ROOT / ".tmp"
PROFILE_PATH = TMP / "business_profile.json"
MD_SOURCE = (
    ROOT
    / "Brand_Assets"
    / "Ammar AI Automation Solution Company Overview and Business Information.md"
)


def ensure_dirs():
    for d in [TMP, TMP / "competitors", TMP / "analysis_history", TMP / "charts"]:
        d.mkdir(parents=True, exist_ok=True)


def load_existing_profile() -> dict:
    if PROFILE_PATH.exists():
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_profile(profile: dict):
    profile["last_updated"] = datetime.now().isoformat()
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    print(f"\nProfile saved to {PROFILE_PATH}")


def parse_markdown_profile() -> dict:
    """Extract key fields from the company overview markdown."""
    if not MD_SOURCE.exists():
        return {}

    text = MD_SOURCE.read_text(encoding="utf-8")
    profile = {}

    # Company name — stop at next ** or end of line
    m = re.search(r"\*\*Company:\*\*\s*([^*\n]+)", text)
    if m:
        profile["company_name"] = m.group(1).strip()

    # Principal
    m = re.search(r"\*\*(?:Founder and Principal|Principal):\*\*\s*([^*\n]+)", text)
    if m:
        profile["principal"] = m.group(1).strip()

    # Website
    m = re.search(r"\*\*Website:\*\*\s*([^*\n]+)", text)
    if m:
        profile["website"] = m.group(1).strip()

    # Location
    m = re.search(r"\*\*(?:Location|Country of Operation):\*\*\s*([^*\n]+)", text)
    if m:
        profile["location"] = m.group(1).strip()

    # Mission
    m = re.search(r"\*\*Mission:\*\*\s*([^*\n]+)", text)
    if m:
        profile["mission"] = m.group(1).strip()

    # Vision
    m = re.search(r"\*\*Vision:\*\*\s*([^*\n]+)", text)
    if m:
        profile["vision"] = m.group(1).strip()

    # Services — extract section 2 headings
    services = re.findall(r"### \d+\.\d+\s+(.+)", text)
    if services:
        profile["services"] = services

    # Target markets
    m = re.search(r"(?:South Asia|Middle East)[^\n]*", text)
    if m:
        profile["target_markets"] = ["South Asia", "Middle East"]
        profile["target_segments"] = [
            "Small businesses",
            "Mid-sized businesses",
            "Service businesses",
        ]

    # Differentiators — extract core values
    differentiators = re.findall(
        r"\*\*([^*]+)\*\*[^*]*(?:We build|Business|Client|Transparency)", text
    )
    if not differentiators:
        differentiators = [
            "Reliability over novelty",
            "Deterministic logic for business rules",
            "Transparency — no vendor lock-in",
            "Continuous learning approach",
        ]
    profile["differentiators"] = differentiators[:4]

    # Description
    m = re.search(r"is an (.+?)\.", text)
    if m:
        profile["description"] = (
            "Ammar AI Automation Solution is an " + m.group(1).strip() + "."
        )

    # Value proposition
    profile["value_proposition"] = (
        "Give growing businesses the operational capacity of a much larger team "
        "through practical, well-engineered automation."
    )

    # Competitor search context
    profile["industry"] = "AI automation and workflow automation services"
    profile["search_context"] = (
        "AI automation agency, workflow automation consulting, n8n implementation, "
        "GoHighLevel automation, AI agent development for small businesses, "
        "WhatsApp automation, South Asia Middle East automation services"
    )

    profile["known_competitors"] = []
    profile["source"] = "auto-parsed from company overview markdown"

    return profile


def prompt_field(label: str, current: str = "", required: bool = False) -> str:
    """Prompt user for a field value, showing current value if set."""
    if current:
        display = f"[current: {current[:60]}{'...' if len(current) > 60 else ''}]"
        val = input(f"  {label} {display}: ").strip()
        return val if val else current
    else:
        while True:
            val = input(f"  {label}: ").strip()
            if val or not required:
                return val
            print("  This field is required.")


def interactive_update(profile: dict) -> dict:
    """Let user update specific fields interactively."""
    print("\nWhich sections would you like to update?")
    print("  1. Company basics (name, website, location)")
    print("  2. Value proposition and description")
    print("  3. Services list")
    print("  4. Target markets and segments")
    print("  5. Differentiators")
    print("  6. Known competitors (optional)")
    print("  7. All of the above")
    print("  Enter to skip / keep existing")

    choice = input("\nEnter number(s) separated by commas (e.g. 1,3): ").strip()
    sections = [s.strip() for s in choice.split(",")] if choice else []
    if "7" in sections:
        sections = ["1", "2", "3", "4", "5", "6"]

    if "1" in sections:
        print("\n--- Company Basics ---")
        profile["company_name"] = prompt_field(
            "Company name", profile.get("company_name", "")
        )
        profile["website"] = prompt_field("Website", profile.get("website", ""))
        profile["location"] = prompt_field(
            "Location / Country", profile.get("location", "")
        )
        profile["principal"] = prompt_field(
            "Principal / Founder", profile.get("principal", "")
        )

    if "2" in sections:
        print("\n--- Value Proposition ---")
        profile["description"] = prompt_field(
            "One-sentence company description", profile.get("description", "")
        )
        profile["value_proposition"] = prompt_field(
            "Value proposition (what problem you solve)",
            profile.get("value_proposition", ""),
        )
        profile["mission"] = prompt_field(
            "Mission statement", profile.get("mission", "")
        )

    if "3" in sections:
        print("\n--- Services ---")
        print("  Current services:", ", ".join(profile.get("services", [])))
        raw = input(
            "  Enter services as comma-separated list (Enter to keep current): "
        ).strip()
        if raw:
            profile["services"] = [s.strip() for s in raw.split(",") if s.strip()]

    if "4" in sections:
        print("\n--- Target Markets ---")
        print("  Current markets:", ", ".join(profile.get("target_markets", [])))
        raw = input(
            "  Target geographic markets (comma-separated, Enter to keep): "
        ).strip()
        if raw:
            profile["target_markets"] = [m.strip() for m in raw.split(",") if m.strip()]
        print("  Current segments:", ", ".join(profile.get("target_segments", [])))
        raw = input("  Customer segments (comma-separated, Enter to keep): ").strip()
        if raw:
            profile["target_segments"] = [
                s.strip() for s in raw.split(",") if s.strip()
            ]

    if "5" in sections:
        print("\n--- Differentiators ---")
        print("  Current differentiators:")
        for i, d in enumerate(profile.get("differentiators", []), 1):
            print(f"    {i}. {d}")
        raw = input(
            "  Enter differentiators as comma-separated list (Enter to keep): "
        ).strip()
        if raw:
            profile["differentiators"] = [
                d.strip() for d in raw.split(",") if d.strip()
            ]

    if "6" in sections:
        print("\n--- Known Competitors (optional) ---")
        print("  These will be added to the discovery list automatically.")
        print("  Current:", ", ".join(profile.get("known_competitors", [])))
        raw = input(
            "  Enter competitor names or websites (comma-separated, Enter to keep): "
        ).strip()
        if raw:
            profile["known_competitors"] = [
                c.strip() for c in raw.split(",") if c.strip()
            ]

    return profile


def main():
    ensure_dirs()
    existing = load_existing_profile()

    if existing:
        print(
            f"\nExisting business profile found (last updated: {existing.get('last_updated', 'unknown')})"
        )
        print(f"  Company: {existing.get('company_name', 'N/A')}")
        print(f"  Services: {len(existing.get('services', []))} listed")
        choice = input("\nUse existing profile? (Y/n/update): ").strip().lower()

        if choice in ("", "y", "yes"):
            print("Using existing profile.")
            print(json.dumps(existing, indent=2))
            return

        if choice in ("u", "update"):
            profile = interactive_update(existing)
            save_profile(profile)
            print("\nUpdated profile:")
            print(json.dumps(profile, indent=2))
            return

    # No existing profile — try auto-parse from markdown
    print(
        "\nNo existing profile found. Attempting to auto-populate from company overview document..."
    )
    profile = parse_markdown_profile()

    if profile:
        print(f"  Auto-populated {len(profile)} fields from markdown.")
        print("\nParsed profile preview:")
        for k, v in profile.items():
            if k not in ("source", "last_updated"):
                val_str = str(v)[:80] + "..." if len(str(v)) > 80 else str(v)
                print(f"  {k}: {val_str}")

        choice = input("\nAccept this profile? (Y/n/update): ").strip().lower()
        if choice in ("n", "no"):
            profile = {}
        elif choice in ("u", "update"):
            profile = interactive_update(profile)

    if not profile:
        print("\nPlease provide business information:")
        profile = {}
        profile["company_name"] = prompt_field("Company name", required=True)
        profile["website"] = prompt_field("Website URL")
        profile["location"] = prompt_field("Location / Country")
        profile["description"] = prompt_field(
            "One-sentence company description", required=True
        )
        profile["value_proposition"] = prompt_field(
            "Value proposition (what problem you solve)", required=True
        )
        profile["industry"] = prompt_field(
            "Industry / space (e.g. AI automation services)", required=True
        )
        raw = input("  Services (comma-separated): ").strip()
        profile["services"] = (
            [s.strip() for s in raw.split(",") if s.strip()] if raw else []
        )
        raw = input(
            "  Target markets (comma-separated, e.g. South Asia, Middle East): "
        ).strip()
        profile["target_markets"] = (
            [m.strip() for m in raw.split(",") if m.strip()] if raw else []
        )
        raw = input("  Customer segments (comma-separated): ").strip()
        profile["target_segments"] = (
            [s.strip() for s in raw.split(",") if s.strip()] if raw else []
        )
        raw = input("  Key differentiators (comma-separated): ").strip()
        profile["differentiators"] = (
            [d.strip() for d in raw.split(",") if d.strip()] if raw else []
        )
        raw = input("  Known competitors (comma-separated, optional): ").strip()
        profile["known_competitors"] = (
            [c.strip() for c in raw.split(",") if c.strip()] if raw else []
        )
        profile["search_context"] = prompt_field(
            "Search context for finding competitors"
        )

    save_profile(profile)
    print("\nFinal profile:")
    print(json.dumps(profile, indent=2))


if __name__ == "__main__":
    main()
