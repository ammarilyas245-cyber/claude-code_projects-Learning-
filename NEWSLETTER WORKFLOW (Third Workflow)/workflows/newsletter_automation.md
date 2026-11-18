# Newsletter Automation

## Objective
Turn a topic into a researched, branded HTML newsletter with an AI infographic, send it through Gmail, and log it to Google Sheets. Triggered on demand: "I need a newsletter about X".

## Required inputs
- **topic** (from the user)
- Optional: depth (`shallow|medium|deep`, default medium), days to look back (default 30)

## Setup (once)
1. `pip install -r requirements.txt`
2. Copy `.env.template` to `.env`; fill `TAVILY_API_KEY`, `ANTHROPIC_API_KEY`, `KIE_API_KEY`, `NEWSLETTER_TEST_RECIPIENT`, `GOOGLE_SHEETS_ID`
3. Put `credentials.json` (Gmail + Sheets APIs enabled) in the project root. If a `token.json` already exists with older scopes, delete it so the new `gmail.send` and `spreadsheets` scopes are granted on first run
4. Fill `config/recipients.json`
5. Brand lives in `config/newsletter_style.json`; assets in `Brand_Assets/` (`Logo Image.png`, `Branding Guidline.png`). Every newsletter must carry the logo (header and footer) and follow the palette and fonts there

## Steps
1. **Research**: `python tools/research.py --topic "<topic>"` -> `.tmp/research_<slug>.json`. Read the JSON; confirm headline, sections and infographic numbers match the sources
2. **Infographic**: `python tools/generate_infographic.py --input .tmp/research_<slug>.json` -> `.tmp/infographics/<slug>.png` (+ `.b64.txt`). One paid Kie.ai call. Open the PNG and check every number and label against the research JSON
3. **Assemble**: `python tools/assemble_html.py --input .tmp/research_<slug>.json --infographic .tmp/infographics/<slug>.png` -> `.tmp/newsletter_<slug>.html`. Open in a browser; verify logo on navy header and footer, brand colors, fonts, infographic
4. **Show the user the preview and wait for approval.** Never send before this
5. **Test send**: `python tools/send_via_gmail.py --html <file> --subject "<subject>" --test`. Check inline images in Gmail
6. **Send**: dry run first (no flag) to confirm recipients, then `--send`
7. **Archive**: `python tools/archive_to_sheets.py --input <research json> --subject "<subject>" --recipients <n> --status sent --html <file> --infographic <png>`

## Edge cases and lessons
- **No Tavily results**: rephrase the topic or raise `--days`; ask the user
- **Tavily rate limit**: `research.py` retries 3 times with backoff
- **Kie.ai**: async; results are polled (3-10 s steps, 10 min timeout). Result URLs expire after 14 days, so the PNG is downloaded immediately. The tool never retries on its own because each call costs credits: ask the user before regenerating
- **Garbled infographic text**: AI image models can misspell or alter numbers. Compare against the research JSON; if wrong, ask before regenerating with a simpler `type` or fewer data points
- **Branding check fails in `assemble_html.py`** (missing logo or palette): the file is not saved; re-run
- **Gmail blocks base64 images**: `send_via_gmail.py` converts them to inline CID attachments automatically
- **Logo file**: white/blue on transparent, so it only works on the dark navy header/footer. The wordmark edges are rough; if it looks bad at 240 px, ask the user for a cleaner export
- **Google auth errors**: delete `token.json` and re-run any Google tool
