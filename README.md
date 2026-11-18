# claude-code_projects

Five AI workflows and automations built with Claude Code, following the **WAT framework** (Workflows, Agents, Tools). Each project has a **workflow** (a plain-English SOP in `workflows/`), **tools** (small Python or TypeScript scripts that do the actual work), and Claude as the agent that reads the SOP and runs the tools in order.

| # | Project | What it does |
|---|---|---|
| 1 | [Competitive Analysis](#1-competitive-analysis-workflow) | Researches competitors and produces a branded PDF report |
| 2 | [Job Scraper](#2-job-scraper-workflow) | Scrapes remote job listings into an Excel file |
| 3 | [Newsletter](#3-newsletter-workflow) | Turns a topic into a branded newsletter, sends it, and logs it |
| 4 | [Trigger.dev Lead Finder](#4-triggerdev-dental-lead-finder) | Weekly job that finds dental practices needing a website and adds them to ClickUp |
| 5 | [YouTube Analysis](#5-youtube-analysis-automation) | Weekly report on breakout AI YouTube videos, as a PDF, Slides deck, and Sheets log |

---

## 1. Competitive Analysis Workflow
**Folder:** `COMPETITIVE ANALYSIS WORKFLOW (First Agentic Workflow)`

Researches the competitors of an AI automation business and turns the findings into a branded PDF report.

1. **Collect business profile** (`collect_business_info.py`): builds a profile of the business from the brand assets file, saved once and reused.
2. **Discover competitors** (`discover_competitors.py`): Claude picks 6-8 relevant competitors with a relevance score and reasoning. You can add or remove entries.
3. **Research each competitor** (`research_competitor.py`): Tavily extracts the competitor's website (home, pricing, services, about) and runs targeted searches. Claude turns the results into structured data (services, pricing, tech stack, messaging). Results are cached for 30 days, and each competitor gets a completeness score.
4. **Analyze** (`analyze_competitors.py`): compares each competitor to the business across features, pricing, marketing, and strengths/weaknesses, and flags what is new since the last report.
5. **Report** (`generate_competitor_pdf.py`): builds positioning and pricing charts and a branded PDF with a gap analysis and brand improvement recommendations.

**Cost:** about $0.85 for a first run, about $0.05 once the cache is warm.
**Needs:** Anthropic and Tavily API keys.

---

## 2. Job Scraper Workflow
**Folder:** `JOB SCRAPER WORKFLOW (Second Agentic Workflow)`

Say "scrape jobs" and Claude asks two questions (role and platform), then runs a 3-step pipeline.

1. **Listings** (`scrape_dailyremote_listings.py`): searches the platform for the role and collects every listing's basic details and URL.
2. **Details** (`scrape_dailyremote_details.py`): opens each job page and adds the full description (default 100 jobs per run).
3. **Export** (`export_jobs_excel.py`): writes a formatted Excel file with a frozen header row and clickable links, and opens it.

Scraping runs through the Firecrawl API, with automatic backoff on rate limits. DailyRemote is fully supported. `scrape_indeed_listings.py` covers Indeed, and the workflow explains how to add other platforms by following the same pattern.
**Needs:** a Firecrawl API key.

---

## 3. Newsletter Workflow
**Folder:** `NEWSLETTER WORKFLOW (Third Workflow)`

Give Claude a topic and it produces and sends a branded newsletter.

1. **Research** (`research.py`): Tavily searches the topic and Claude writes the headline, sections, and infographic data.
2. **Infographic** (`generate_infographic.py`): Kie.ai generates an infographic image. Numbers and labels are checked against the research, since AI images can garble text.
3. **Assemble** (`assemble_html.py`): builds the HTML newsletter with the logo, brand colors, and fonts. It refuses to save if branding checks fail.
4. **Approval:** you review a preview. Nothing is sent without your OK.
5. **Test send, then send** (`send_via_gmail.py`): sends a test email first, then the full list via Gmail, with images embedded inline.
6. **Archive** (`archive_to_sheets.py`): logs the subject, recipients, and status to Google Sheets.

**Needs:** Tavily, Anthropic, and Kie.ai keys, plus Google OAuth (Gmail and Sheets).

---

## 4. Trigger.dev Dental Lead Finder
**Folder:** `TRIGGER.DEV (Workflow-Automation)`

A scheduled TypeScript automation on [Trigger.dev](https://trigger.dev) that finds dental practices likely to buy a website. It runs every Monday at 9:00 AM Pakistan time.

1. **`find-leads`** (scheduled): picks 5 of about 50 large US cities each week and searches Google Maps through SerpAPI. It skips practices already seen and caps the searches per run to protect the free quota.
2. **`create-lead`** (per practice): audits the practice's website (none, social-only, dead, outdated, or fine), finds a contact email on the site, and creates a ClickUp task with phone, address, rating, and a "why it's a fit" note.
3. **Priority:** practices with no website or an outdated one get High priority and a `website-opportunity` tag. Practices with a fine website get Low.
4. **No repeats:** the Google Place ID is stored in each task and checked before creating a new one, with a long-lived idempotency key as a second guard.
5. **`setup-clickup`** (one-off): creates the ClickUp Space, "Dental Leads" list, and tags.

About 100 new leads per week. See `PLAN.md` for decisions and status.
**Needs:** Trigger.dev, SerpAPI, and ClickUp keys.

---

## 5. YouTube Analysis Automation
**Folder:** `YOUTUBE ANALYSIS AUTOMATION (Fourth Workflow + Deployment )`

Finds which AI and AI-automation YouTube videos are breaking out, relative to each channel's own normal performance, and reports it.

1. **Ask first:** Claude asks for the report topic and whether to send the email.
2. **Discover channels** (`youtube_discover_channels.py`): finds active channels in the niche and updates the tracked list.
3. **Fetch videos** (`youtube_fetch_videos.py`): pulls recent videos and channel stats from the YouTube Data API.
4. **Analyze** (`analyze_youtube_trends.py`): scores each video against its channel's baseline to find breakouts, and looks at engagement, formats, and topics.
5. **Narrative and charts** (`generate_narrative.py`, `generate_charts.py`): writes headline, findings, and content opportunities, each backed by numbers from the analysis.
6. **Deliverables:** a PDF report (`build_pdf_report.py`) and a Google Slides deck (`build_slides_deck.py`), both with charts and thumbnails.
7. **Log:** two Google Sheets, a presentation log and a channel/video intelligence sheet (`update_tracking_sheet.py`, `update_channel_sheet.py`).
8. **Email** (`send_gmail_notification.py`): sends links to the deck and sheets.

`run_weekly_pipeline.py` chains all of it, and `modal_app.py` deploys it to [Modal](https://modal.com) so it runs in the cloud, with secrets kept in a Modal secret.
**Needs:** YouTube API key, Google OAuth (Gmail, Sheets, Slides, Drive), Anthropic key.

---

## Setup notes
- Each project has its own `requirements.txt` (or `package.json`), `CLAUDE.md`, and `workflows/` SOP.
- Copy `.env.example` / `.env.template` to `.env` and fill in your own keys. **Real `.env` files are never committed.**
