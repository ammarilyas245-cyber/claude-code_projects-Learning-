"""Email the weekly summary with the deck and sheet links through Gmail, styled with the brand guideline.

The logo is embedded inline (CID) so it renders without a public URL.
Safe by default: without --send it only prints the recipient and subject.
The recipient is REPORT_RECIPIENT in .env.

Usage:
    python tools/send_gmail_notification.py --deck-url "<url>" --sheet-url "<url>"           # dry run
    python tools/send_gmail_notification.py --deck-url "<url>" --sheet-url "<url>" --send
"""

import argparse
import base64
import html
import json
import re
import sys
import time
from datetime import date
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from googleapiclient.discovery import build

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.utils import (
    PROJECT_ROOT,
    ensure_tmp_dir,
    get_env,
    get_google_credentials,
    load_config,
)

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LOGO_CID = "brand-logo"


def build_html(
    narrative: dict,
    analysis: dict,
    deck_url: str,
    sheet_url: str,
    style: dict,
    pdf_url: str = "",
) -> str:
    p = style["palette"]
    heading_font = f"{style['font_heading']}, Arial, sans-serif"
    body_font = f"{style['font_body']}, Arial, sans-serif"
    findings = "".join(
        f'<li style="margin-bottom:8px">{html.escape(f)}</li>'
        for f in narrative["key_findings"][:3]
    )
    breakouts = "".join(
        f'<li style="margin-bottom:8px"><a href="{html.escape(v["url"])}" style="color:{p["accent"]}">'
        f"{html.escape(v['title'])}</a> "
        f'<span style="color:#64748B">({v["breakout_score"]}x, {html.escape(v["channel_title"])})</span></li>'
        for v in analysis["top_breakout"][:3]
    )
    pdf_button = (
        f'<a href="{html.escape(pdf_url)}" style="display:inline-block;margin-left:12px;background:{p["background"]};color:#FFFFFF;font-family:{heading_font};font-weight:700;font-size:15px;padding:12px 22px;text-decoration:none;border-radius:6px">Open the PDF report</a>'
        if pdf_url
        else ""
    )
    return f"""<html>
<body style="margin:0;padding:0;background:#F1F5F9;font-family:{body_font};color:{p["background"]}">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F1F5F9">
<tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%;background:#FFFFFF">
  <tr><td style="background:{p["background"]};padding:28px 32px;text-align:left">
    <img src="cid:{LOGO_CID}" alt="{html.escape(style["company"])}" width="220" style="display:block;width:220px;height:auto;border:0">
  </td></tr>
  <tr><td style="padding:32px 32px 8px 32px">
    <div style="font-family:{heading_font};font-size:22px;font-weight:700;line-height:1.3;color:{p["background"]}">{html.escape(narrative["headline"])}</div>
  </td></tr>
  <tr><td style="padding:16px 32px 0 32px">
    <div style="font-family:{heading_font};font-size:14px;font-weight:700;color:{p["accent"]};text-transform:uppercase;letter-spacing:1px">Key findings</div>
    <ul style="padding-left:20px;font-size:15px;line-height:1.6;color:#1E293B">{findings}</ul>
  </td></tr>
  <tr><td style="padding:8px 32px 0 32px">
    <div style="font-family:{heading_font};font-size:14px;font-weight:700;color:{p["accent"]};text-transform:uppercase;letter-spacing:1px">Top breakout videos</div>
    <ul style="padding-left:20px;font-size:15px;line-height:1.6;color:#1E293B">{breakouts}</ul>
  </td></tr>
  <tr><td style="padding:24px 32px 32px 32px">
    <a href="{html.escape(deck_url)}" style="display:inline-block;background:{p["accent"]};color:#FFFFFF;font-family:{heading_font};font-weight:700;font-size:15px;padding:12px 22px;text-decoration:none;border-radius:6px">Open the full deck</a>
    {pdf_button}
    <a href="{html.escape(sheet_url)}" style="display:inline-block;margin-left:12px;color:{p["accent"]};font-family:{body_font};font-size:15px;padding:12px 0;text-decoration:none">Tracking sheet</a>
  </td></tr>
  <tr><td style="background:{p["background"]};padding:20px 32px;font-family:{body_font};font-size:12px;color:{p["muted"]}">
    <strong style="color:{p["heading"]}">{html.escape(style["company"])}</strong><br>
    {html.escape(style["tagline"])}
  </td></tr>
</table>
</td></tr>
</table>
</body></html>"""


def build_message(
    html_body: str, plain: str, recipient: str, subject: str, logo: Path
) -> dict:
    root = MIMEMultipart("related")
    root["To"] = recipient
    root["Subject"] = subject
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(plain, "plain", "utf-8"))
    alt.attach(MIMEText(html_body, "html", "utf-8"))
    root.attach(alt)
    logo_part = MIMEImage(logo.read_bytes(), _subtype="png")
    logo_part.add_header("Content-ID", f"<{LOGO_CID}>")
    logo_part.add_header("Content-Disposition", "inline", filename=logo.name)
    root.attach(logo_part)
    return {"raw": base64.urlsafe_b64encode(root.as_bytes()).decode()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deck-url", required=True)
    parser.add_argument("--sheet-url", required=True)
    parser.add_argument(
        "--pdf-url",
        default="",
        help="Drive link to the PDF report. Defaults to the url in .tmp/pdf/pdf_result.json.",
    )
    parser.add_argument("--send", action="store_true")
    args = parser.parse_args()

    recipient = get_env("REPORT_RECIPIENT")
    if not EMAIL.match(recipient):
        print(f"REPORT_RECIPIENT in .env is not a valid email: {recipient!r}")
        return 1

    style = load_config("youtube_deck_style.json")
    logo = PROJECT_ROOT / style["logo_path"]
    if not logo.exists():
        print(
            f"Logo missing at {logo}. Add Brand_Assets/Logo Image.png before sending."
        )
        return 1

    tmp = ensure_tmp_dir()
    narrative = json.loads((tmp / "narrative.json").read_text(encoding="utf-8"))
    analysis = json.loads((tmp / "trend_analysis.json").read_text(encoding="utf-8"))
    subject = f"Weekly AI YouTube trends - {date.today().strftime('%d %b %Y')}"
    pdf_url = args.pdf_url
    pdf_result = tmp / "pdf" / "pdf_result.json"
    if not pdf_url and pdf_result.exists():
        pdf_url = json.loads(pdf_result.read_text(encoding="utf-8")).get("url", "")
    body_html = build_html(
        narrative, analysis, args.deck_url, args.sheet_url, style, pdf_url
    )
    pdf_line = f"PDF report: {pdf_url}\n" if pdf_url else ""
    plain = (
        f"{narrative['headline']}\n\n{pdf_line}Deck: {args.deck_url}\n"
        f"Sheet: {args.sheet_url}\n\n{style['company']} - {style['tagline']}"
    )

    if not args.send:
        print(
            f"Dry run. Would send to {recipient!r} with subject {subject!r}. Re-run with --send to deliver."
        )
        return 0

    raw = build_message(body_html, plain, recipient, subject, logo)
    service = build("gmail", "v1", credentials=get_google_credentials())
    for attempt in range(3):
        try:
            resp = service.users().messages().send(userId="me", body=raw).execute()
            print(f"Sent to {recipient} (message id {resp['id']}).")
            return 0
        except Exception as err:
            if attempt == 2:
                print(f"Send failed after 3 attempts: {err}")
                return 2
            time.sleep(2**attempt)
    return 2


if __name__ == "__main__":
    sys.exit(main())
