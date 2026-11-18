#!/usr/bin/env python3
"""
Fetch individual DailyRemote job detail pages and enrich listing data with full descriptions.

Usage:
    python tools/scrape_dailyremote_details.py --input .tmp/listings.json --limit 100 --output .tmp/jobs_full.json
    python tools/scrape_dailyremote_details.py --input .tmp/listings.json --limit 100 --batch-size 10 --batch-delay 60 --output .tmp/jobs_full.json
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

FIRECRAWL_URL = "https://api.firecrawl.dev/v1/scrape"


def fetch_page_markdown(url: str, api_key: str) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"url": url, "formats": ["markdown"]}

    for attempt in range(2):
        resp = requests.post(FIRECRAWL_URL, headers=headers, json=payload, timeout=60)
        if resp.status_code == 429:
            if attempt == 0:
                print("Rate limited — waiting 60s before retry...", file=sys.stderr)
                time.sleep(60)
                continue
            raise RuntimeError("Rate limit persists after backoff")
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            raise RuntimeError(f"Firecrawl returned failure: {data}")
        return data.get("data", {}).get("markdown", "")

    return ""


def extract_description(markdown: str) -> str:
    """Extract the main job description from a detail page's markdown."""
    if not markdown:
        return ""

    # Remove navigation, headers, and boilerplate by finding the main content block
    # DailyRemote detail pages have the description after the job metadata section

    # Strip markdown links and nav elements to get clean text blocks
    lines = markdown.split("\n")
    clean_lines = []
    skip_patterns = re.compile(
        r"^(#{1,3}\s|!\[|---|\*\*Apply|\*\*Share|Remote Jobs|Browse|Sign|Login|Register|©|\[!\[)",
        re.IGNORECASE,
    )

    in_description = False
    description_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if description_lines:
                description_lines.append("")
            continue

        # Heuristic: description usually comes after salary/location/date metadata
        # Look for the transition from metadata to body text
        if not in_description:
            # Long lines (>100 chars) with mostly prose = we've hit the description
            if (
                len(stripped) > 100
                and not stripped.startswith("[")
                and not stripped.startswith("#")
            ):
                in_description = True

        if in_description and not skip_patterns.match(stripped):
            description_lines.append(stripped)

        # Stop at footer-like sections
        if re.match(
            r"(apply now|similar jobs|related jobs|you might also|tags|share this)",
            stripped,
            re.IGNORECASE,
        ):
            break

    description = "\n".join(description_lines).strip()

    # Fallback: if heuristic failed, return all substantial non-nav text
    if len(description) < 100:
        fallback_lines = [
            l.strip()
            for l in lines
            if len(l.strip()) > 50
            and not l.strip().startswith("[")
            and not l.strip().startswith("#")
            and not l.strip().startswith("!")
        ]
        description = "\n".join(fallback_lines[:30])

    return description[:5000]  # Cap at 5000 chars for Excel compatibility


def main():
    parser = argparse.ArgumentParser(
        description="Enrich job listings with full descriptions"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to listings JSON from scrape_dailyremote_listings.py",
    )
    parser.add_argument(
        "--limit", type=int, required=True, help="Max number of job pages to fetch"
    )
    parser.add_argument("--output", required=True, help="Output JSON file path")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of jobs to fetch before pausing (default: 10)",
    )
    parser.add_argument(
        "--batch-delay",
        type=int,
        default=60,
        help="Seconds to wait between batches (default: 60)",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("FIRECRAWL_API_KEY"),
        help="Firecrawl API key (defaults to .env FIRECRAWL_API_KEY)",
    )
    args = parser.parse_args()

    if not args.api_key:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": "FIRECRAWL_API_KEY not set",
                    "error_type": "ValueError",
                }
            ),
            file=sys.stderr,
        )
        return 1

    # Load listings
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            raw = json.load(f)
        listings = raw.get("data", raw) if isinstance(raw, dict) else raw
    except Exception as e:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": f"Failed to read input: {e}",
                    "error_type": type(e).__name__,
                }
            ),
            file=sys.stderr,
        )
        return 1

    # Apply limit
    listings = listings[: args.limit]
    total = len(listings)
    batch_size = args.batch_size
    batch_delay = args.batch_delay
    num_batches = (total + batch_size - 1) // batch_size
    print(
        f"Enriching {total} jobs in {num_batches} batches of {batch_size} "
        f"(delay: {batch_delay}s between batches)...",
        file=sys.stderr,
    )

    enriched = []

    try:
        for batch_num in range(num_batches):
            batch_start = batch_num * batch_size
            batch = listings[batch_start : batch_start + batch_size]
            batch_end = batch_start + len(batch)

            print(
                f"\nBatch {batch_num + 1}/{num_batches} — jobs {batch_start + 1}–{batch_end}",
                file=sys.stderr,
            )

            for idx, job in enumerate(batch):
                global_idx = batch_start + idx
                job_url = job.get("job_url", "")
                print(
                    f"  [{global_idx + 1}/{total}] {job.get('title', 'Unknown')[:60]}",
                    file=sys.stderr,
                )

                if not job_url:
                    job["full_description"] = ""
                    enriched.append(job)
                    continue

                try:
                    markdown = fetch_page_markdown(job_url, args.api_key)
                    description = extract_description(markdown)
                    job["full_description"] = description
                except Exception as e:
                    print(
                        f"    Warning: failed to fetch {job_url} — {e}", file=sys.stderr
                    )
                    job["full_description"] = ""

                enriched.append(job)

                # 1s delay between individual requests within a batch
                if idx < len(batch) - 1:
                    time.sleep(1)

            # Pause between batches (not after the last one)
            if batch_num < num_batches - 1:
                print(
                    f"\nBatch {batch_num + 1} complete. Waiting {batch_delay}s before next batch...",
                    file=sys.stderr,
                )
                time.sleep(batch_delay)

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        result = {"status": "success", "count": len(enriched), "data": enriched}

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(
            json.dumps(
                {
                    "status": "success",
                    "count": len(enriched),
                    "output_path": args.output,
                }
            )
        )
        return 0

    except Exception as e:
        # Save partial results before exiting
        if enriched:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(
                    {"status": "partial", "count": len(enriched), "data": enriched},
                    f,
                    indent=2,
                )
            print(f"Partial results saved ({len(enriched)} jobs)", file=sys.stderr)

        print(
            json.dumps(
                {"status": "error", "error": str(e), "error_type": type(e).__name__}
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
