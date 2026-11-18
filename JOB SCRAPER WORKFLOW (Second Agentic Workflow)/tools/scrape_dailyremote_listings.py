#!/usr/bin/env python3
"""
Scrape DailyRemote search result pages and extract job listing metadata.

Usage:
    python tools/scrape_dailyremote_listings.py --search "social media" --pages 23 --output .tmp/listings.json
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

import requests
from dotenv import load_dotenv

load_dotenv()

FIRECRAWL_URL = "https://api.firecrawl.dev/v1/scrape"
BASE_URL = "https://dailyremote.com"


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


def parse_jobs_from_markdown(markdown: str) -> list:
    """Extract job cards from a DailyRemote search results page in markdown format."""
    jobs = []
    seen_urls = set()

    # DailyRemote job links appear as [Title](https://dailyremote.com/remote-job/...)
    # or [Title](/remote-job/...)
    job_link_pattern = re.compile(
        r"\[([^\]]+)\]\(((?:https://dailyremote\.com)?/remote-job/[^\)]+)\)"
    )

    # Split markdown into sections around each job link
    matches = list(job_link_pattern.finditer(markdown))

    for i, match in enumerate(matches):
        title = match.group(1).strip()
        raw_url = match.group(2).strip()
        job_url = raw_url if raw_url.startswith("http") else f"{BASE_URL}{raw_url}"

        # Skip pagination/nav links (very short titles, or duplicates)
        if job_url in seen_urls:
            continue
        if len(title) < 4 or title.lower() in ("apply", "view", "more", "here", "job"):
            continue
        seen_urls.add(job_url)

        # Grab the surrounding text block (up to 600 chars after the link)
        start = match.end()
        end = (
            matches[i + 1].start()
            if i + 1 < len(matches)
            else min(start + 800, len(markdown))
        )
        context = markdown[match.start() : end]

        job = {
            "title": title,
            "job_url": job_url,
            "company": _extract_company(context),
            "job_type": _extract_job_type(context),
            "date_posted": _extract_date(context),
            "location": _extract_location(context),
            "salary": _extract_salary(context),
            "experience": _extract_experience(context),
            "category": _extract_category(context),
            "description_snippet": _extract_snippet(context, title),
            "tags": _extract_tags(markdown[start:end]),
        }

        jobs.append(job)

    return jobs


def _extract_company(text: str) -> str:
    if re.search(r"company\s+hidden", text, re.IGNORECASE):
        return "Company hidden"
    # Look for company name patterns (e.g., "at CompanyName")
    m = re.search(r"at\s+([A-Z][A-Za-z0-9&\s\-\.]+?)(?:\s*[\|\•\|]|\s*\n)", text)
    return m.group(1).strip() if m else "Company hidden"


def _extract_job_type(text: str) -> str:
    for jtype in ["Full Time", "Part Time", "Freelance", "Internship", "Contract"]:
        if re.search(re.escape(jtype), text, re.IGNORECASE):
            return jtype
    return ""


def _extract_date(text: str) -> str:
    m = re.search(
        r"(\d+\s+(?:minute|hour|day|week|month)s?\s+ago|yesterday|today|just\s+now)",
        text,
        re.IGNORECASE,
    )
    return m.group(0).strip() if m else ""


def _extract_location(text: str) -> str:
    # Common DailyRemote location patterns
    patterns = [
        r"Worldwide",
        r"United States?(?:,\s*[A-Za-z\s]+)?",
        r"Canada(?:,\s*[A-Za-z\s]+)?",
        r"United Kingdom|UK",
        r"Europe(?:an Union)?",
        r"Philippines",
        r"India",
        r"Australia",
        r"Latin America",
        r"[A-Z][a-z]+,\s*[A-Z][a-z]+",
        r"Remote(?:\s+\w+)?",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()
    return ""


def _extract_salary(text: str) -> str:
    m = re.search(
        r"[\$€£₹][\d,\.K]+\s*[-–]\s*[\$€£₹]?[\d,\.K]+(?:\s*/\s*(?:yr|year|hr|hour|month))?"
        r"|[\d,\.K]+\s*[-–]\s*[\d,\.K]+\s*/\s*(?:yr|year|hr|hour|month)",
        text,
        re.IGNORECASE,
    )
    return m.group(0).strip() if m else ""


def _extract_experience(text: str) -> str:
    m = re.search(
        r"(\d+[-–]\d+)\s*(?:yrs?|years?)\s*(?:exp(?:erience)?)?", text, re.IGNORECASE
    )
    return m.group(0).strip() if m else ""


def _extract_category(text: str) -> str:
    # Category links look like [Remote Marketing Jobs](/remote-marketing-jobs)
    m = re.search(r"Remote\s+([A-Za-z\s]+?)\s+Jobs", text, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _extract_snippet(text: str, title: str) -> str:
    # Find the longest line that isn't the title or a URL
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    candidates = [
        l
        for l in lines
        if len(l) > 60
        and title.lower() not in l.lower()
        and not l.startswith("http")
        and not l.startswith("[")
        and not re.match(r"^[\|\-\*#]", l)
    ]
    return candidates[0][:500] if candidates else ""


def _extract_tags(text: str) -> str:
    # Tag links: [social-media](/remote-social-media-jobs)
    tag_pattern = re.compile(r"\[([a-z][a-z0-9\-]+)\]\(/remote-[a-z\-]+-jobs\)")
    tags = tag_pattern.findall(text)
    return ", ".join(tags) if tags else ""


def main():
    parser = argparse.ArgumentParser(
        description="Scrape DailyRemote search result pages"
    )
    parser.add_argument(
        "--search", required=True, help='Search term, e.g. "social media"'
    )
    parser.add_argument(
        "--pages", type=int, required=True, help="Number of pages to scrape"
    )
    parser.add_argument("--output", required=True, help="Output JSON file path")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of pages to fetch before pausing (default: 10)",
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

    all_jobs = []
    search_encoded = quote_plus(args.search)
    total_pages = args.pages
    batch_size = args.batch_size
    batch_delay = args.batch_delay
    num_batches = (total_pages + batch_size - 1) // batch_size

    print(
        f"Scraping {total_pages} pages for '{args.search}' in {num_batches} batches of {batch_size} "
        f"(delay: {batch_delay}s between batches)...",
        file=sys.stderr,
    )

    try:
        for batch_num in range(num_batches):
            batch_start_page = batch_num * batch_size + 1
            batch_end_page = min(batch_start_page + batch_size - 1, total_pages)

            print(
                f"\nBatch {batch_num + 1}/{num_batches} — pages {batch_start_page}–{batch_end_page}",
                file=sys.stderr,
            )

            for page_num in range(batch_start_page, batch_end_page + 1):
                url = f"{BASE_URL}/?search={search_encoded}&page={page_num}"
                print(f"  Page {page_num}/{total_pages}: {url}", file=sys.stderr)

                try:
                    markdown = fetch_page_markdown(url, args.api_key)
                    jobs = parse_jobs_from_markdown(markdown)
                    print(f"    Found {len(jobs)} jobs", file=sys.stderr)
                    all_jobs.extend(jobs)
                except Exception as e:
                    print(f"    Warning: page {page_num} failed — {e}", file=sys.stderr)

                if page_num < batch_end_page:
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

        result = {"status": "success", "count": len(all_jobs), "data": all_jobs}

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(
            json.dumps(
                {
                    "status": "success",
                    "count": len(all_jobs),
                    "output_path": args.output,
                }
            )
        )
        return 0

    except Exception as e:
        print(
            json.dumps(
                {"status": "error", "error": str(e), "error_type": type(e).__name__}
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
