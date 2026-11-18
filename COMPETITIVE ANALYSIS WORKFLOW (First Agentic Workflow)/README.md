# Competitor Analysis Workflow

**Ammar AI Automation Solution — WAT Framework**

An on-demand competitive intelligence system that discovers competitors, researches their websites, analyzes them across four dimensions, and generates a fully branded PDF report.

---

## What This Does

1. **Discovers** 6-8 competitors relevant to your business using Claude
2. **Researches** each competitor's website (services, pricing, messaging, tech stack) via Tavily
3. **Analyzes** them against your business across four dimensions: features, pricing, marketing, and strengths/weaknesses
4. **Generates** a branded 10-section PDF report with charts, your AAA logo, and brand colors
5. **Tracks changes** month-over-month so you can see how the market is evolving

**First run cost:** ~$0.85 | **Cached re-runs:** ~$0.05

---

## Prerequisites

### 1. Python
Requires Python 3.9+. Check your version:
```
python --version
```

### 2. Install Dependencies
From the project root:
```
pip install -r requirements.txt
```

### 3. API Keys
Open `.env` and add your keys:
```
ANTHROPIC_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here
```

- **Anthropic API key:** [console.anthropic.com](https://console.anthropic.com)
- **Tavily API key:** [app.tavily.com](https://app.tavily.com)

### 4. Brand Assets (already included)
- `Brand_Assets/Logo Image.png` — your AAA logo
- `Brand_Assets/brand_config.json` — colors, fonts, tagline
- `Brand_Assets/Ammar AI Automation Solution Company Overview and Business Information.md` — your business info

---

## Running the Workflow

Follow these steps in order. Each step depends on the previous one.

---

### Step 1 — Collect Your Business Profile

```
python tools/collect_business_info.py
```

**What it does:** Reads your company overview markdown and saves a structured business profile to `.tmp/business_profile.json`.

**First run:** Auto-populates from your markdown file. Review the output and accept or update it.

**Subsequent runs:** Shows your existing profile and asks if you want to update it. Press Enter to keep it as-is — this is the fastest path.

**Output:** `.tmp/business_profile.json`

---

### Step 2 — Discover Competitors

```
python tools/discover_competitors.py
```

**What it does:** Sends your business profile to Claude and asks it to identify 6-8 direct and indirect competitors with relevance scores (0-100) and reasoning.

**Review the output:** The script prints each competitor found. If a known competitor is missing, add it to `.tmp/business_profile.json` under `"known_competitors": ["CompanyName"]` and re-run.

**Output:** `.tmp/competitors_list.json`

---

### Step 3 — Research Each Competitor

```
python tools/research_competitor.py
```

**What it does:**
- For each competitor, extracts content from their website via Tavily (homepage, /pricing, /services, /about)
- Runs targeted searches: `"{name} pricing"`, `"{name} reviews"`, `"{name} AI automation services"`
- Uses Claude to extract structured data: services, pricing tiers, tech stack, messaging, target audience
- Scores each competitor on data completeness (0-100%)
- Caches results for **30 days** — re-running this step within 30 days skips research and uses cached data

**Completeness scores:**
- **70-100%** — Full confidence, all fields populated
- **30-70%** — Partial data, included with "Limited Data" note in the PDF
- **0-30%** — Flagged for manual research; you can add data manually to `.tmp/competitors/[name].json`

**Fallback chain if scraping fails:** Tavily Extract → Tavily Search → Claude knowledge → flag as Limited Data

**Output:** `.tmp/competitors/[name].json` for each competitor

> **Note:** This step uses up most of the ~$0.85 first-run cost (Tavily credits for scraping). Cached runs skip this entirely.

---

### Step 4 — Analyze Competitors

```
python tools/analyze_competitors.py
```

**What it does:** Loads your business profile and all cached competitor data, then uses Claude to generate a structured analysis for each competitor across four dimensions:

| Dimension | What It Covers |
|-----------|---------------|
| **Product & Service Features** | Services offered, tech stack, feature gaps vs. you |
| **Pricing & Business Model** | Tiers, pricing model type, market positioning |
| **Marketing & Messaging** | How they position, key messages, channels, tone |
| **Strengths & Weaknesses vs. AAA** | Where they outperform you, where you have the edge, threat level |

Also generates:
- Market overview and key themes
- Strategic insights (High/Medium/Low priority)
- Prioritized recommendations
- Month-over-month comparison (if a previous month's analysis exists)

**Output:** `.tmp/analysis_history/analysis_YYYYMM.json`

---

### Step 5 — Generate the PDF Report

```
python tools/generate_competitor_pdf.py
```

**What it does:**
- Generates two matplotlib charts with your brand colors:
  - Competitive positioning matrix (service breadth vs. specialization)
  - Pricing model distribution
- Renders the full HTML template with all competitor data, charts, and your logo
- Converts to PDF via xhtml2pdf

**Report sections:**
1. Title page (logo, date, competitors analyzed)
2. Executive summary + competitive snapshot table
3. Your business profile
4. Competitive landscape (positioning + pricing charts)
5–N. Individual competitor profiles (one per competitor)
N+1. Pricing analysis table
N+2. Feature comparison matrix
N+3. Strategic insights & recommendations
Last. Closing page

**Output:** `.tmp/competitor_report_YYYYMMDD.pdf`

Open the file when it completes — it will be in `.tmp/`.

---

## Re-Running the Workflow

### Full re-run (new research)
Delete the cached competitor files to force fresh research:
```
# Delete all cached competitor data
del .tmp\competitors\*.json
```
Then run Steps 3-5.

### Quick re-run (re-analyze with cached data)
If competitor data is less than 30 days old, skip to Step 4:
```
python tools/analyze_competitors.py
python tools/generate_competitor_pdf.py
```
Cost: ~$0.05

### Force re-research one competitor
Delete only that competitor's cache file:
```
del ".tmp\competitors\competitorname.json"
```
Then re-run Step 3.

### Add a competitor manually
1. Add their name to `.tmp/competitors_list.json` under `"competitors"`
2. Run Step 3 (it will research the new one, skip cached ones)

---

## File Structure

```
FIRST AGENTIC WORKFLOW/
├── Brand_Assets/
│   ├── Logo Image.png                    ← Your logo (used in PDF)
│   ├── Branding Guidline.png             ← Visual brand reference
│   ├── brand_config.json                 ← Colors, fonts, tagline
│   └── Ammar AI Automation Solution      ← Company overview (source of truth)
│       Company Overview and Business
│       Information.md
├── .tmp/
│   ├── business_profile.json             ← Your saved business profile
│   ├── competitors_list.json             ← Discovered competitors
│   ├── competitors/                      ← Cached research (30-day TTL)
│   │   └── [name].json
│   ├── analysis_history/                 ← Monthly analysis archives
│   │   └── analysis_YYYYMM.json
│   ├── charts/                           ← Generated chart images
│   │   ├── positioning_matrix.png
│   │   └── pricing_comparison.png
│   └── competitor_report_YYYYMMDD.pdf    ← Final report
├── tools/
│   ├── collect_business_info.py          ← Step 1
│   ├── discover_competitors.py           ← Step 2
│   ├── research_competitor.py            ← Step 3
│   ├── analyze_competitors.py            ← Step 4
│   ├── generate_competitor_pdf.py        ← Step 5
│   └── templates/
│       ├── report.html                   ← Jinja2 PDF template
│       └── report.css                    ← Brand stylesheet
├── workflows/
│   └── competitor_analysis.md            ← Full SOP (for agent use)
├── .env                                  ← API keys (never commit this)
├── requirements.txt                      ← Python dependencies
└── README.md                             ← This file
```

---

## Troubleshooting

**"ANTHROPIC_API_KEY not set"**
Open `.env` and add your key. No quotes needed: `ANTHROPIC_API_KEY=sk-ant-...`

**"No competitors list found"**
Run Step 2 (`discover_competitors.py`) before Step 3.

**"No analysis files found"**
Run Step 4 (`analyze_competitors.py`) before Step 5.

**Low data completeness warnings**
Some competitor websites block scraping. The PDF will include a "Limited Data" disclaimer for those competitors. You can manually add data by editing `.tmp/competitors/[name].json`.

**PDF opens but charts are missing**
Charts are generated separately before the PDF. Check if `.tmp/charts/` has PNG files. If matplotlib failed silently, check the terminal output from Step 5 for warnings.

**Re-running Step 3 is slow**
If cache is fresh (<30 days), it should skip cached competitors and only research new ones. If it's researching everything again, check the file dates in `.tmp/competitors/`.

---

## Updating Your Business Profile

When your services, pricing, or target markets change, update your profile:
```
python tools/collect_business_info.py
```
Select "update" and change only the fields that have changed. The analysis will reflect the updated profile on the next run.

Also update `Brand_Assets/Ammar AI Automation Solution Company Overview and Business Information.md` to keep it as the source of truth.

---

## Cost Reference

| Scenario | Approx. Cost |
|----------|-------------|
| First run, 6 competitors | ~$0.85 |
| Re-run with 30-day cache | ~$0.05 |
| Re-run with 2 new competitors added | ~$0.44 |
| Re-run, force fresh research on all | ~$0.85 |

Costs are Anthropic + Tavily API usage. Tavily free tier includes 1,000 searches/month.
