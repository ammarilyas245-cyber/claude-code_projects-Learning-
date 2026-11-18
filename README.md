# claude-code_projects

Five AI workflows and automations built with Claude Code. Each project is a self-contained folder with its own README, `CLAUDE.md`, and workflow SOP, so see those for details. This page covers what each one is and how to set it up.

| # | Folder | What it does |
|---|---|---|
| 1 | `COMPETITIVE ANALYSIS WORKFLOW (First Agentic Workflow)` | Researches competitors and builds a branded PDF report |
| 2 | `JOB SCRAPER WORKFLOW (Second Agentic Workflow)` | Scrapes remote job listings into an Excel file |
| 3 | `NEWSLETTER WORKFLOW (Third Workflow)` | Turns a topic into a branded newsletter, sends it, and logs it |
| 4 | `TRIGGER.DEV (Workflow-Automation)` | Weekly job that finds dental practices needing a website and adds them to ClickUp |
| 5 | `YOUTUBE ANALYSIS AUTOMATION (Fourth Workflow + Deployment )` | Weekly report on breakout AI YouTube videos (PDF, Slides, Sheets, email) |

## General setup

**You need:** Python 3.10+ (projects 1, 2, 3, 5), Node.js 18+ (project 4), and [Claude Code](https://claude.com/claude-code) to run the workflows from their `CLAUDE.md` instructions.

```bash
git clone https://github.com/ammarilyas245-cyber/claude-code_projects.git
cd claude-code_projects/"<project folder>"
```

For Python projects: `pip install -r requirements.txt`.
Then copy the example env file (`.env.example` or `.env.template`) to `.env` and fill in your own keys. Real `.env` files are never committed.

## Per-project setup

**1. Competitive Analysis**
- Install: `pip install -r requirements.txt`
- Keys in `.env`: `ANTHROPIC_API_KEY`, `TAVILY_API_KEY`
- Put your logo and `brand_config.json` in `Brand_Assets/`
- Run: ask Claude to run the competitor analysis workflow

**2. Job Scraper**
- Install: `pip install -r requirements.txt` if present, otherwise install the packages the tools import
- Keys in `.env`: `FIRECRAWL_API_KEY`
- Run: tell Claude "scrape jobs", then give the role and platform

**3. Newsletter**
- Install: `pip install -r requirements.txt`
- Keys in `.env`: `TAVILY_API_KEY`, `ANTHROPIC_API_KEY`, `KIE_API_KEY`, `NEWSLETTER_TEST_RECIPIENT`, `GOOGLE_SHEETS_ID`
- Google: enable the Gmail and Sheets APIs, create an OAuth Desktop client, and add `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`. The first run opens a browser once to create `token.json`
- Add recipients in `config/recipients.json`
- Run: ask Claude for a newsletter about a topic

**4. Trigger.dev Lead Finder**
- Install: `npm install`
- Keys in `.env`: `TRIGGER_PROJECT_REF`, `SERPAPI_KEY`, `CLICKUP_API_KEY`, `CLICKUP_LIST_ID` (the list ID is printed by the `setup-clickup` task)
- Run locally: `npm run dev`. Deploy only when you are ready, and add the same variables in the Trigger.dev dashboard
- Check types: `npm run typecheck`

**5. YouTube Analysis**
- Install: `pip install -r requirements.txt`
- Keys in `.env`: `YOUTUBE_API_KEY`, `REPORT_RECIPIENT`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- Google: enable the Gmail, Sheets, Slides, and Drive APIs, and publish the OAuth consent screen to Production so the token doesn't expire after 7 days
- Run: ask Claude to "run youtube analysis"
- Optional cloud deploy: `pip install modal`, then `modal setup`, create the secret and volume, and `modal deploy modal_app.py` (see `modal_app.py` for the exact steps)

## Security
Never commit `.env`, `token.json`, or `credentials.json`. Rotate any key that was ever exposed.
