# Scrape DailyRemote Jobs → Excel

**Objective:** Scrape remote job listings from dailyremote.com for a given search term and export them to an Excel file for review.

**Use Case:** When you need to build a list of remote job opportunities for a specific role or keyword. Run as a 3-step pipeline: collect listing metadata, enrich with full descriptions, export to Excel.

---

## Required Inputs

- `FIRECRAWL_API_KEY`: In `.env` — used for all HTTP scraping calls
- Search term: The keyword to search (e.g., `social media`)
- Number of pages: How many search result pages to scrape (DailyRemote shows 30 results/page)
- Detail limit: How many individual job pages to fetch for full descriptions (use a subset for demos, e.g., 200)

---

## Workflow Steps

### Step 1: Scrape Listing Pages
- **Tool:** `tools/scrape_dailyremote_listings.py`
- **Input:** `--search "social media" --pages 23 --output .tmp/listings.json`
- **Output:** `.tmp/listings.json` — array of job objects with basic metadata and URLs
- **Success Check:** File exists, `count` field equals expected total (should be ~684 for social media), every object has a `job_url`

### Step 2: Fetch Job Detail Pages
- **Tool:** `tools/scrape_dailyremote_details.py`
- **Input:** `--input .tmp/listings.json --limit 200 --output .tmp/jobs_full.json`
- **Output:** `.tmp/jobs_full.json` — same array enriched with `full_description` from each job page
- **Success Check:** File exists, length equals limit value (200), `full_description` is non-empty on most records

### Step 3: Export to Excel
- **Tool:** `tools/export_jobs_excel.py`
- **Input:** `--input .tmp/jobs_full.json --output .tmp/social_media_jobs.xlsx`
- **Output:** `.tmp/social_media_jobs.xlsx` — 12-column Excel file, one row per job
- **Success Check:** File opens in Excel, row count matches JSON length, all column headers present

---

## Edge Cases & Error Handling

| Scenario | Error Sign | Recovery |
|----------|-----------|----------|
| Firecrawl rate limit | HTTP 429 | Tool backs off 60s and retries once; if still 429, reduce `--pages` or add `time.sleep(2)` between calls |
| Page returns no jobs | Empty jobs list for a page | Tool skips the page and logs a warning; check if page number exceeds actual total |
| Missing optional fields | `salary`, `experience`, `company` are blank | Expected — not all listings include these; leave empty in Excel |
| Job detail page obfuscated | `full_description` is Lorem Ipsum or very short | Known DailyRemote anti-scrape behavior on some listings; acceptable data gap |
| `.tmp/` directory missing | FileNotFoundError | Tools create it automatically via `Path.mkdir(parents=True, exist_ok=True)` |
| `FIRECRAWL_API_KEY` not set | `ValueError: FIRECRAWL_API_KEY not set` | Add key to `.env` file |

---

## Success Criteria

- [ ] `.tmp/listings.json` created with ~30 × (number of pages) job objects
- [ ] `.tmp/jobs_full.json` created with exactly `--limit` rows, each having `full_description`
- [ ] `.tmp/social_media_jobs.xlsx` opens cleanly with header row frozen and all 12 columns visible
- [ ] No unhandled exceptions in any tool's stderr output

---

## Execution Commands

```bash
# Step 1: Collect all listing pages
python tools/scrape_dailyremote_listings.py --search "social media" --pages 23 --output .tmp/listings.json

# Step 2: Enrich first 200 with full descriptions (demo limit)
python tools/scrape_dailyremote_details.py --input .tmp/listings.json --limit 200 --output .tmp/jobs_full.json

# Step 3: Export to Excel
python tools/export_jobs_excel.py --input .tmp/jobs_full.json --output .tmp/social_media_jobs.xlsx
```

---

## Notes

- DailyRemote hides company names behind a paywall — expect `"Company hidden"` for most listings
- Apply links route through `/get-started?utm_source=apply_detailed_job` (DailyRemote sign-up gate), not direct employer URLs
- Some detail pages use Lorem Ipsum placeholder text as anti-scrape obfuscation
- As of November 2026: "social media" search returns ~684 results across 23 pages (30/page)
- Firecrawl markdown format is used for parsing — cleaner than raw HTML and doesn't require CSS class knowledge
