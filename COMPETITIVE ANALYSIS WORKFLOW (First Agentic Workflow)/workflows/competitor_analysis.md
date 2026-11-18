# Competitor Analysis Workflow

## Objective

Research and analyze competitors in the AI automation / workflow automation space, then produce a branded PDF report with actionable insights. This workflow is designed for on-demand use with 30-day caching so subsequent runs are fast and cheap.

## Required Inputs

- `ANTHROPIC_API_KEY` in `.env` — for competitor discovery, data extraction, and analysis
- `TAVILY_API_KEY` in `.env` — for web search and website content extraction
- `Brand_Assets/Logo Image.png` — company logo
- `Brand_Assets/brand_config.json` — brand colors, fonts, company info

## Expected Outputs

- `.tmp/business_profile.json` — persistent business profile (created once, reused)
- `.tmp/competitors_list.json` — discovered competitors with relevance scores
- `.tmp/competitors/[name].json` — cached research per competitor (30-day TTL)
- `.tmp/analysis_history/analysis_YYYYMM.json` — structured analysis (archived monthly)
- `.tmp/charts/positioning_matrix.png` — visual positioning chart
- `.tmp/charts/pricing_comparison.png` — pricing comparison chart
- `.tmp/competitor_report_YYYYMMDD.pdf` — final branded PDF report with:
  - **Gap Analysis Section:** Key insights about what competitors are doing that AAA is NOT doing
  - **Brand Improvement Recommendations:** Specific, actionable recommendations to improve AAA's brand and market position based on competitor practices and identified gaps

## Estimated Cost Per Run

- **First run (6 competitors, no cache):** ~$0.85
  - Competitor discovery (Anthropic): ~$0.20
  - Web research (Tavily, ~4 pages × 6): ~$0.50
  - Data extraction (Anthropic, 6 calls): ~$0.10
  - Competitive analysis (Anthropic): ~$0.05
- **Subsequent runs (30-day cache active):** ~$0.05
  - Only regenerates analysis; all research reused from cache

---

## Steps

### Step 0: Validate Prerequisites

Before running anything:
1. Check `.env` exists and has `ANTHROPIC_API_KEY` and `TAVILY_API_KEY` set (not empty)
2. Check `Brand_Assets/Logo Image.png` exists
3. Check `Brand_Assets/brand_config.json` exists
4. Create `.tmp/competitors/` and `.tmp/analysis_history/` and `.tmp/charts/` directories if missing

If any API keys are missing, tell the user exactly which ones to add to `.env` and stop.

### Step 1: Collect Business Profile

Run: `python tools/collect_business_info.py`

- If `.tmp/business_profile.json` already exists, ask the user: "Use existing profile or update it?"
- If updating, the tool prompts only for fields the user wants to change
- On first run, the tool auto-populates from `Brand_Assets/Ammar AI Automation Solution Company Overview and Business Information.md`
- Expected output: `.tmp/business_profile.json`

Review the profile briefly before continuing — confirm it accurately describes the business.

### Step 2: Discover Competitors

Run: `python tools/discover_competitors.py`

- Uses the business profile to ask Claude to identify 6-8 relevant competitors
- Returns: name, website, relevance_score (0-100), reasoning for inclusion
- Saves to `.tmp/competitors_list.json`
- Review the list with the user — they may want to add or remove competitors
- If fewer than 3 competitors found, expand the search scope or add manually before continuing

### Step 3: Research Competitors

Run: `python tools/research_competitor.py`

- For each competitor, checks if `.tmp/competitors/[name].json` exists and is <30 days old
- **IMPORTANT: Fresh Data Priority**
  - If cache is fresh (< 30 days) AND user hasn't explicitly asked for a full refresh: Use cached data BUT also run targeted searches for NEW information (pricing changes, new services, new partnerships, recent announcements)
  - If stale (≥ 30 days) OR user asks for full refresh: runs complete research pipeline
  - **Always flag what's NEW or CHANGED** from previous report (if available in analysis history)
- Full research pipeline if stale/missing:
  - Tavily Extract on competitor's website (homepage, /pricing, /services, /about pages)
  - Targeted Tavily searches: "{name} pricing", "{name} reviews", "{name} AI automation services", "{name} new features", "{name} recent news"
  - Anthropic extracts structured data: services, pricing tiers, tech stack, messaging, target audience
- **Fallback chain:** Tavily Extract → Tavily Search → Anthropic knowledge → flag "Limited Data"
- **Parallel processing:** Up to 3 workers, 1s delay between Tavily API calls
- **Completeness scoring:** Each competitor scored 0-100%
  - <30%: Flag for manual research, warn user
  - 30-70%: Include with "Limited Data" disclaimer in PDF
  - 70%+: Full confidence

After this step, review `.tmp/competitors/` — confirm each competitor has a JSON file with **new/updated content**, not recycled old data.

### Step 4: Analyze Competitors

Run: `python tools/analyze_competitors.py`

- Loads `.tmp/business_profile.json` + all `.tmp/competitors/[name].json` files
- For each competitor, generates analysis across 4 dimensions:
  1. **Product/service features** — services offered, tech stack, feature gaps vs AAA
  2. **Pricing & business model** — tiers, free/paid, revenue model, positioning
  3. **Marketing & messaging** — positioning statement, channels, content strategy, tone
  4. **Strengths & weaknesses vs AAA** — where they win, where we win, threat level (Low/Medium/High)
- **NEW DATA TRACKING:** If previous analysis exists in `analysis_history/`, automatically compare and flag:
  - What's NEW about each competitor (new services, new pricing, new positioning)
  - What's CHANGED (pricing updates, service expansions, messaging shifts)
  - What REMAINS THE SAME (avoid repeating stale data)
- Generates overall market overview, strategic insights, and **THREE CRITICAL SECTIONS:**
  1. **What's New/Changed:** Highlights new information discovered about competitors vs. previous report
  2. **Gap Analysis:** Identifies key practices, features, services, or positioning that competitors are using that AAA is currently NOT doing. Highlight what's missing from AAA's offering.
  3. **Brand Improvement Recommendations:** Provides specific, actionable recommendations for improving AAA's brand, messaging, services, and market position based on competitor practices and identified gaps.
- **Month-over-month:** If previous month's analysis exists in `analysis_history/`, highlights changes and new developments
- Saves to `.tmp/analysis_history/analysis_YYYYMM.json`

Review strategic insights, new/changed data, gap analysis, and recommendations briefly — they feed directly into the PDF recommendations section.

### Step 5: Generate Branded PDF

Run: `python tools/generate_competitor_pdf.py`

**Brand Requirements (NON-NEGOTIABLE):**
- Use AAA logo from `Brand_Assets/Logo Image.png` — place on every page header/footer
- Apply brand colors from `Brand_Assets/Branding Guideline.png`:
  - Primary Blue (#2563EB) for headings, CTAs, emphasis
  - Light Blue (#60A5FA) for accents and secondary elements
  - Dark Navy (#0F172A) for body text
  - Light Gray (#E5E7EB) for backgrounds/dividers
- Use brand typography: Montserrat Bold for headings, Inter Regular for body text
- Professional, consistent design matching AAA brand identity throughout all pages

**PDF Content Requirements:**
- Generates matplotlib charts (positioning matrix, pricing comparison) with brand colors
- Renders Jinja2 HTML template with all data, embeds charts and logo
- **MUST INCLUDE sections:** 
  - What's New/Changed section highlighting new information discovered about competitors vs. previous reports
  - Gap Analysis showing what competitors are doing that AAA is NOT
  - Brand Improvement Recommendations with specific, actionable steps
- Converts to PDF via WeasyPrint
- Saves to `.tmp/competitor_report_YYYYMMDD.pdf`

**Tell the user:** "Your branded report is ready at `.tmp/competitor_report_YYYYMMDD.pdf` — includes new/changed competitor data, gap analysis, and brand improvement recommendations."

Open or share the file. Ask if they want to re-run any section or adjust anything.

---

## Edge Cases

| Situation | Action |
|-----------|--------|
| API key missing | Stop, tell user exactly which key to add to `.env` |
| Competitor website blocks scraping | Fallback chain: Tavily Search → Anthropic knowledge → flag "Limited Data" |
| <3 competitors found | Prompt to expand search or add manually; option to search adjacent markets |
| Tavily rate limit (429) | Exponential backoff: wait 2s, 4s, 8s. Max 3 retries then skip that call |
| Data completeness <30% | Flag competitor for manual research; still include with strong disclaimer |
| Font loading fails | Log warning, PDF generates with Helvetica system fallback |
| Previous analysis missing for comparison | Skip month-over-month section; note "First analysis — no historical data" |

---

## When to Use This Workflow

**Use this workflow ALWAYS when:**
- User asks to "run competitor analysis"
- User asks to "compare competitors"
- User asks "who are my competitors?"
- User asks to "analyze my competitors' businesses"

**Do NOT skip this workflow.** This is the authoritative method for competitor research at AAA. Direct web searches bypass the tools pipeline and miss context.

## Critical Requirements

⚠️ **Every competitive analysis MUST include:**
1. **Fresh/New Data Section** — "What's New/Changed" highlighting new information discovered about competitors vs. previous reports. Never recycle the same competitor data from past reports. Always include what's changed, what's new, and what moved.
2. **Gap Analysis Section** — What competitors are doing that AAA is NOT doing. This identifies competitive gaps and missing services/practices.
3. **Brand Improvement Recommendations** — Specific, actionable recommendations to improve AAA's brand, messaging, and market position based on competitor practices.
4. **Complete PDF Branding** — All reports MUST be generated as PDF with complete brand assets:
   - AAA logo from `Brand_Assets/Logo Image.png` prominently displayed
   - Brand colors from `Brand_Assets/Branding Guideline.png` applied throughout (Primary Blue #2563EB, Light Blue #60A5FA, Dark Navy #0F172A, Light Gray #E5E7EB)
   - Typography: Montserrat Bold for headings, Inter Regular for body (per brand guideline)
   - Professional, consistent visual design matching AAA brand identity
   - Logo and branding on every page header/footer

If these sections are missing from the output, the analysis is incomplete. Reports must NEVER be plain text or HTML — always PDF with full branding. Reports must NEVER recycle old competitor data — always highlight what's new/changed.

## Maintenance Notes

- **Update business profile** when services, pricing, or target markets change: re-run `collect_business_info.py`
- **Force re-research a competitor** (bypass 30-day cache): delete `.tmp/competitors/[name].json` and re-run Step 3
- **Add a new competitor manually:** Add entry to `.tmp/competitors_list.json`, then run Step 3 onwards
- **Brand changes:** Update `Brand_Assets/brand_config.json` — the PDF generator reads it fresh each run
- **Search query tuning:** If wrong competitors are appearing, the search strategy is in `tools/discover_competitors.py` — adjust the system prompt's industry context
- **Gap Analysis & Recommendations:** These are non-negotiable outputs. If missing, ask for clarification or re-run the analysis.

---

## Tool Reference

| Tool | Input | Output |
|------|-------|--------|
| `tools/collect_business_info.py` | Interactive / markdown file | `.tmp/business_profile.json` |
| `tools/discover_competitors.py` | `.tmp/business_profile.json` | `.tmp/competitors_list.json` |
| `tools/research_competitor.py` | `.tmp/competitors_list.json` | `.tmp/competitors/[name].json` (per competitor) |
| `tools/analyze_competitors.py` | business profile + all competitor JSONs | `.tmp/analysis_history/analysis_YYYYMM.json` |
| `tools/generate_competitor_pdf.py` | analysis JSON + brand config + logo | `.tmp/competitor_report_YYYYMMDD.pdf` |
