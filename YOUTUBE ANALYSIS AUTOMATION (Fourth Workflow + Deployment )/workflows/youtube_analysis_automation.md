# YouTube Analysis Automation

## Objective
Every week, find the most active AI and AI-automation YouTube channels, measure which videos are breaking out relative to their own channel's norm, build a private Google Slides deck with charts and insights, log the run to a tracking Google Sheet, and email the user the deck and sheet links.

Triggers: weekly scheduled run, or on demand with "run youtube analysis".

## Required inputs
- Per run, asked before anything else (see Step 0): the **report topic**, which is required, plus whether to send the email.
- Keywords and thresholds live in `config/niche_keywords.json`. Tracked channels live in `config/tracked_channels.json` (maintained by discovery).
- Recipient: `REPORT_RECIPIENT` in `.env`.

## Setup (once)
1. `pip install -r requirements.txt`
2. In `.env`, fill `YOUTUBE_API_KEY` (YouTube Data API v3 enabled) and `REPORT_RECIPIENT`.
3. In Google Cloud, enable Gmail API, Google Sheets API, Google Slides API and Google Drive API. Create an OAuth Desktop client, then put its Client ID and Client secret in `.env` as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`. No credentials file is needed.
4. Publish the OAuth consent screen to **Production** (one-time "unverified app" click-through during first login). In Testing mode the refresh token expires after 7 days and the unattended weekly run will fail.
5. Optional: put the logo in `Brand_Assets/Logo Image.png` and replace the placeholder palette in `config/youtube_deck_style.json` with brand colors.
6. First run of any Google tool opens a browser once to create `token.json` (scopes: gmail.send, spreadsheets, presentations, drive.file). If scopes ever change, delete `token.json` and re-consent.

## Steps
0. **Ask questions first (every run, before any other action)**: when asked to run this automation, ask the user before running any tool, calling any API, or reading any data.
   - Question 1 (required): "What is the topic for this analysis report?" The answer is the subject of the presentation: it sets the report title, headline, findings, charts and thumbnails. The current week's data is the reference, not the subject. If the topic is not covered by the data, say so in the narrative instead of forcing it, and keep the charts to what the data shows.
   - Question 2: "Send the email when the run finishes, or stop before sending?" Default is send, per the user's standing decision.
   - Do not start step 1 until the topic is answered.
1. **Discover channels**: `python tools/youtube_discover_channels.py` -> `.tmp/discovered_channels.json`, updates `config/tracked_channels.json`. Check the output for obvious off-niche channels; remove any by editing `config/tracked_channels.json`.
2. **Fetch videos**: `python tools/youtube_fetch_videos.py` -> `.tmp/videos_raw.json`, `.tmp/channel_stats.json`. Confirm the video count is non-zero.
3. **Analyze**: `python tools/analyze_youtube_trends.py` -> `.tmp/trend_analysis.json`. Read it.
4. **Charts**: `python tools/generate_charts.py` -> `.tmp/charts/*.png`. Open each PNG and check labels and values against the analysis JSON.
5. **Topic scope (if the topic is narrower than the niche)**: re-run the analysis with `python tools/analyze_youtube_trends.py --topic-pattern "<regex>" --topic-label "<readable name>"`. Baselines still come from all fetched videos; only the output stats, charts and thumbnails are limited to matching titles. Run step 3 without flags to restore the full niche view before the sheets are logged, or log the scoped run on purpose and say so in the report.
6. **Narrative**: write `.tmp/narrative.json` with keys `title` (report title that names the topic from Step 0), `headline` (one sentence), `key_findings` (up to 5 strings), `content_opportunities` (up to 5 strings). The topic from Step 0 sets the subject; the analysis numbers are the reference. Every claim must cite a number from `trend_analysis.json`. Do not invent trends the stats do not show. If the data covers the topic thinly, say so in the headline and findings rather than forcing a trend.
7. **Charts, visuals and thumbnails**: `python tools/generate_charts.py` -> `.tmp/charts/*.png` (breakouts, engagement, formats, topics). Open each PNG and check labels against `trend_analysis.json`. Thumbnails for the top breakout videos are downloaded and placed by the PDF builder in `.tmp/pdf/thumbs/`.
8. **PDF report (the deliverable)**: `python tools/build_pdf_report.py` -> `.tmp/pdf/AI_YouTube_Trends_<date>.pdf`, uploaded to Drive as a private file, and `.tmp/pdf/pdf_result.json` with its link. Render each page (`.tmp/pdf/preview/`) and check layout, text overflow and chart labels. Use `--skip-upload` only for a local check.
8a. **Google Slides deck (required, every run)**: `python tools/build_slides_deck.py` -> prints the deck URL, writes `.tmp/deck_result.json`. Build it with the same narrative, charts and thumbnails as the PDF, so both carry the same content. Open the deck in the browser, check every slide for layout and text overflow, and fix the text or chart size in the tool before reporting the run as done. The PDF and the Slides deck are both deliverables; neither is optional.
7. **Sheets**: two separate spreadsheets, both appended each run.
   - Presentation log: `python tools/update_tracking_sheet.py --deck-url "<deck url>"` -> "Presentation Tracking" tab in `config/tracking_sheet.json`.
   - Channel intelligence: `python tools/update_channel_sheet.py` -> "Channel Details" and "Video Data" tabs in `config/channel_sheet.json`.
9. **Email**: dry run first (`python tools/send_gmail_notification.py --deck-url "<PDF or deck link>" --sheet-url "<sheet url>"`), then add `--send`. Pass the Slides link from `.tmp/deck_result.json` as `--deck-url` and the PDF's Drive link from `.tmp/pdf/pdf_result.json` in the email body, so both deliverables are in every run's email. The sheet URL is in `config/tracking_sheet.json` as `spreadsheet_url`.

## Edge cases and lessons
- **YouTube quota**: 10,000 units per day per project. `search.list` costs 100 units per call; discovery runs one search per keyword (12 keywords ~ 1,200 units). Everything else is about 1 unit per call. A `quotaExceeded` 403 means stop and wait until the daily reset. Do not retry.
- **Discovery is view-ranked within the lookback window**, so it finds channels with currently strong content, not the whole niche.
- **playlistItems returns only the latest 50 uploads per channel**. Very high-volume channels can exceed the lookback window within 50 uploads; that is acceptable for a weekly run.
- **Hidden like counts** come back as 0 likes, which lowers engagement for those videos. Hidden subscriber counts are treated as 0 and filtered out during discovery.
- **Shorts** are detected by duration of 180 seconds or less (YouTube Shorts can run up to 3 minutes).
- **Breakout score needs a baseline**: channels with fewer than 3 recent videos are excluded from breakout ranking. Videos under 500 views and videos under 2 days old are excluded.
- **Slides cannot read local images**: charts are uploaded to Drive as temporary "anyone with link" files and deleted after the deck is built. A Google Workspace policy that blocks link sharing will break this step; if so, tell the user.
- **Deck stays private**: nothing in `build_slides_deck.py` changes sharing on the deck itself.
- **Branding**: palette and fonts come from `config/youtube_deck_style.json` (Montserrat headings, Inter body, navy `#0F172A`, blue `#2563EB`/`#60A5FA`, light gray `#E5E7EB`), taken from `Brand_Assets/Branding Guidline.png`. The logo is white and blue, so it is only placed on navy. The email embeds the logo inline. The tracking sheet banner uses a Drive copy of the logo set to "anyone with link", because Sheets IMAGE formulas need a public URL; that file must not be deleted.
- **OAuth in Testing mode expires after 7 days**. See Setup step 4.
- **Sheet tabs must not be renamed or deleted**: the scripts append to "Presentation Tracking", "Channel Details" and "Video Data" by name.

## Notes
- Sonnet-level reasoning belongs in step 5 (narrative). Math stays in the tools.
- Keyword list and thresholds are tuned in `config/niche_keywords.json`. Record any changes here with the reason.

## Scheduled run on Modal (every Monday 06:00, Asia/Karachi)
The weekly run is deployed to Modal (`modal_app.py`). It runs with no questions, so the topic is chosen from a list and the narrative is built from the numbers.

- **Orchestrator**: `tools/run_weekly_pipeline.py` runs steps 1-9 in order by calling the existing tools. It stops at the first failure, emails a short notice to `REPORT_RECIPIENT` naming the step, and exits non-zero. Retries are off on purpose: a retry could append sheet rows twice or send two emails.
- **Topic**: `config/weekly_topics.json` lists the topics. The ISO week number picks one, cycling through the list. Edit the list to change topics. A `pattern` of `null` means the full niche. `--topic-index N` picks one by position for testing.
- **Narrative**: `tools/generate_narrative.py` fills the title, headline, findings and opportunities from fixed templates using `trend_analysis.json`. No AI call and no API key. Wording is plainer than a hand-written narrative; every number comes from the analysis.
- **Full niche for logs**: after the deck is built, the analysis is re-run without the topic scope (SOP step 5) before the sheets are logged.
- **Email**: sent with `--send` to `REPORT_RECIPIENT`. The PDF link comes from `.tmp/pdf/pdf_result.json`.
- **State**: the three files the tools rewrite (`tracked_channels.json`, `tracking_sheet.json`, `channel_sheet.json`) live in the Modal volume `youtube-analysis-state` and are restored before each run.
- **Secrets**: Modal secret `youtube-analysis-secrets` holds `YOUTUBE_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `REPORT_RECIPIENT` and `GOOGLE_TOKEN_JSON` (the contents of `token.json`). `.env` and `token.json` are never copied into the image.
- **Logs**: API keys and tokens are redacted from output (`redact()` in `tools/utils.py`) before they are printed or emailed. The YouTube key is sent in the `X-Goog-Api-Key` header, not in the URL.

Commands:
- Deploy or update: `python -m modal deploy modal_app.py`
- Full run without email (test): `python -m modal run modal_app.py --no-send`
- Full run with email (manual): `python -m modal run modal_app.py`
- Logs and history: the Modal dashboard, app `youtube-analysis`

Edge cases:
- **Google token**: `GOOGLE_TOKEN_JSON` is read-only on Modal and never opens a browser. If the token stops working, re-run auth locally (`token.json`), then update the Modal secret with the new contents.
- **Quota**: a `quotaExceeded` error stops the run and is reported. It is not retried; the next run is the following Monday.
- **Duplicates**: each run creates a new PDF in Drive and a new Slides deck, and appends sheet rows. Delete old copies by hand. A rerun after a mid-run failure can append duplicate sheet rows.
