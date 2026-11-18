# Scrape Jobs → Excel

**Objective:** Scrape remote job listings from any supported platform for a given role and export them to an auto-opening Excel file.

**Trigger:** User asks to scrape jobs in any form.

**Intake (always ask before executing):**
1. What role or job type? (e.g., "social media manager", "AI automation", "copywriter")
2. What platform? (e.g., DailyRemote, Upwork, LinkedIn, Indeed)

Capture any extra filters mentioned (seniority, location, job type) and fold into the search query — do not ask a third question.

---

## Platform Routing

| Platform | Listings tool | Detail tool | Notes |
|---|---|---|---|
| DailyRemote | `tools/scrape_dailyremote_listings.py` | `tools/scrape_dailyremote_details.py` | `--search` accepts any keyword |
| Other | Build a new tool following the DailyRemote pattern | Same | See "Adding a new platform" below |

---

## Workflow Steps

### Step 1: Scrape Listing Pages
- **Tool:** Platform-specific listings scraper (see routing table above)
- **Input:** `--search "<role + filters>" --pages <N> --output .tmp/<platform>_<role>_listings.json`
- **Output:** JSON file with basic job metadata and URLs for every listing
- **Success Check:** File exists, `count` > 0, every object has a `job_url`

### Step 2: Fetch Job Detail Pages
- **Tool:** `tools/scrape_dailyremote_details.py` (or platform equivalent)
- **Input:** `--input .tmp/..._listings.json --limit 100 --output .tmp/<platform>_<role>_jobs_full.json`
- **Default limit:** 100 for demos; increase when user asks for a full run
- **Output:** Listings enriched with `full_description`
- **Success Check:** File exists, record count matches `--limit`, `full_description` populated on most rows

### Step 3: Export to Excel
- **Tool:** `tools/export_jobs_excel.py`
- **Input:** `--input .tmp/..._jobs_full.json --output .tmp/<platform>_<role>_jobs.xlsx`
- **Output:** Formatted Excel file — auto-opens on completion
- **Success Check:** Excel opens automatically with header row frozen and all columns present

---

## Naming Convention for Output Files

```
.tmp/<platform>_<role_slug>_listings.json       # raw listing data
.tmp/<platform>_<role_slug>_jobs_full.json      # enriched with descriptions
.tmp/<platform>_<role_slug>_jobs.xlsx           # final deliverable
```

Examples:
- `.tmp/dailyremote_social_media_jobs.xlsx`
- `.tmp/upwork_ai_automation_jobs.xlsx`

---

## Adding a New Platform

When the user requests a platform with no existing tool:

1. Inspect the target site's structure (pagination pattern, job card HTML, URL scheme)
2. Create `tools/scrape_<platform>_listings.py` following the exact pattern in `tools/scrape_dailyremote_listings.py`:
   - `argparse` with `--search`, `--pages`, `--output`, `--api-key`
   - Firecrawl REST API for fetching (`FIRECRAWL_API_KEY` from `.env`)
   - Markdown parsing to extract job cards
   - JSON output: `{"status": "success", "count": N, "data": [...]}`
3. Create `tools/scrape_<platform>_details.py` if the detail page structure differs from DailyRemote; otherwise reuse `tools/scrape_dailyremote_details.py`
4. Add the platform to the routing table in this file and in `CLAUDE.md`
5. Run the full pipeline and verify the Excel output

---

## Edge Cases & Error Handling

| Scenario | Error Sign | Recovery |
|----------|-----------|----------|
| Firecrawl rate limit (429) | Tool prints "Rate limited — waiting 60s" | Built-in backoff; if persistent, reduce `--pages` or add `--delay 2` |
| Platform not supported | No tool exists in `tools/` | Build the tool first (see "Adding a new platform") |
| Excel file locked | `PermissionError` on `.xlsx` | Close the open Excel window, then rerun Step 3 |
| Zero jobs found | `count: 0` in listings JSON | Check search term spelling; verify platform URL is reachable |
| Detail page obfuscated | `full_description` is Lorem Ipsum | Known anti-scrape behavior; acceptable data gap |

---

## Success Criteria

- [ ] Listings JSON contains the expected number of jobs
- [ ] Full-description JSON has exactly `--limit` records
- [ ] Excel file opens automatically with 100 rows + header, all columns present
- [ ] Job URL column contains working hyperlinks

---

## Notes

- DailyRemote hides company names behind a paywall — expect "Company hidden" on most rows
- Keep `--limit 100` as the default for demos; use higher values only when user explicitly asks for a full run
- All intermediate files go to `.tmp/` and are disposable — regenerate as needed
- Firecrawl rate limits typically trigger every ~10 requests; each backoff adds 60s to runtime
