"""Build the branded PDF report from the weekly analysis (design: "Signal Architecture", see .tmp/pdf/design_philosophy.md).

Inputs: .tmp/trend_analysis.json, .tmp/narrative.json, config/youtube_deck_style.json,
        Brand_Assets/Logo Image.png (cleaned copy written to .tmp/pdf/logo_clean.png),
        assets/fonts/ (Montserrat, Inter; OFL).
Outputs: .tmp/pdf/AI_YouTube_Trends_<YYYY-MM-DD>.pdf and .tmp/pdf/pdf_result.json.
The PDF is uploaded to Drive as a private file (no sharing change) unless --skip-upload is given.

Usage:
    python tools/build_pdf_report.py [--skip-upload]
"""

import argparse
import json
import re
import sys
from datetime import date
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import requests
from PIL import Image
from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.utils import PROJECT_ROOT, ensure_tmp_dir, load_config

W, H = 1280, 720  # 16:9 landscape, in points
M = 72  # outer margin
CONTENT_TOP = H - 170
FOOTER_Y = 58
ALPHA_CUT = 200  # logo speckles are semi-transparent; keep only solid pixels
FONT_DIR = PROJECT_ROOT / "assets" / "fonts"
FONT_FILES = {
    "Heading": "Montserrat-ExtraBold.ttf",
    "Heading-Bold": "Montserrat-Bold.ttf",
    "Body": "Inter_18pt-Regular.ttf",
    "Body-Medium": "Inter_18pt-Medium.ttf",
    "Body-Semi": "Inter_18pt-SemiBold.ttf",
}


def hex_color(value: str) -> Color:
    return HexColor(value)


def with_alpha(color: Color, alpha: float) -> Color:
    return Color(color.red, color.green, color.blue, alpha=alpha)


def register_fonts() -> None:
    for name, filename in FONT_FILES.items():
        pdfmetrics.registerFont(TTFont(name, FONT_DIR / filename))


def clean_logo(src: Path, dst: Path) -> Path:
    """Drop the semi-transparent speckles around the logo and trim empty margins."""
    img = Image.open(src).convert("RGBA")
    r, g, b, a = img.split()
    a = a.point(lambda v: 255 if v >= ALPHA_CUT else 0)
    img = Image.merge("RGBA", (r, g, b, a))
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    img.save(dst)
    return dst


def clean_text(text: str, limit: int = 70) -> str:
    """Strip characters Latin fonts cannot draw (emoji, Tamil/Telugu), then trim."""
    text = text.encode("ascii", "ignore").decode()
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"\s+", " ", text).strip(" -|")
    if len(text) > limit:
        text = text[: limit - 3].rstrip() + "..."
    return text or "(non-Latin title)"


def fit(text: str, font: str, size: float, max_width: float) -> str:
    if pdfmetrics.stringWidth(text, font, size) <= max_width:
        return text
    while text and pdfmetrics.stringWidth(text + "...", font, size) > max_width:
        text = text[:-1]
    return text.rstrip() + "..."


def fmt_int(value: float) -> str:
    return f"{value:,.0f}"


def fmt_pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def para(c, text, x, top, width, font, size, color, leading=None) -> float:
    """Draw wrapped text with its top edge at `top`; returns the height used."""
    style = ParagraphStyle(
        "p",
        fontName=font,
        fontSize=size,
        leading=leading or size * 1.35,
        textColor=color,
        alignment=TA_LEFT,
    )
    p = Paragraph(escape(text), style)
    _, h = p.wrap(width, 2000)
    p.drawOn(c, x, top - h)
    return h


def background(c, palette: dict) -> None:
    c.setFillColor(palette["background"])
    c.rect(0, 0, W, H, stroke=0, fill=1)


def ribbon(c, palette: dict) -> None:
    """The logo's folded-ribbon geometry, reduced to one hairline in the top-right corner."""
    c.saveState()
    c.setStrokeColor(with_alpha(palette["primary"], 0.35))
    c.setLineWidth(0.9)
    path = c.beginPath()
    path.moveTo(W - 330, H)
    path.curveTo(W - 250, H - 40, W - 190, H - 120, W - 90, H - 112)
    path.lineTo(W, H - 96)
    c.drawPath(path, stroke=1, fill=0)
    c.restoreState()


def header(c, palette: dict, kicker: str, title: str, size: float = 30) -> None:
    c.setFillColor(palette["primary"])
    c.setFont("Body-Semi", 11)
    c.drawString(M, H - 62, kicker.upper())
    para(
        c,
        title,
        M,
        H - 92,
        860,
        "Heading",
        size,
        palette["heading"],
        leading=size * 1.2,
    )


def footer(c, palette: dict, page_no: int, logo: ImageReader, tagline: str) -> None:
    c.setStrokeColor(with_alpha(palette["muted"], 0.3))
    c.setLineWidth(0.6)
    c.line(M, FOOTER_Y, W - M, FOOTER_Y)
    logo_h = 22
    logo_w = logo_h * logo.getSize()[0] / logo.getSize()[1]
    c.drawImage(logo, M, 24, width=logo_w, height=logo_h, mask="auto")
    c.setFillColor(palette["muted"])
    c.setFont("Body", 10)
    c.drawRightString(W - M, 29, f"{tagline}     {page_no:02d}")


def hbars(c, palette, rows, x0, top, label_w, bar_w, row_h, fmt, label_size=14):
    """Horizontal bar list. rows: (label, sublabel or None, value)."""
    vmax = max((v for _, _, v in rows), default=1) or 1
    bar_x = x0 + label_w + 20
    for i, (label, sub, value) in enumerate(rows):
        row_top = top - i * row_h
        mid = row_top - row_h / 2
        c.setFillColor(palette["heading"])
        c.setFont("Body-Semi", label_size)
        if sub:
            c.drawString(x0, row_top - 16, fit(label, "Body-Semi", label_size, label_w))
            c.setFillColor(palette["muted"])
            c.setFont("Body", 11)
            c.drawString(x0, row_top - 31, fit(sub, "Body", 11, label_w))
        else:
            c.drawString(x0, mid - 5, fit(label, "Body-Semi", label_size, label_w))
        width = max(bar_w * value / vmax, 3)
        c.setFillColor(palette["primary"] if i == 0 else palette["accent"])
        c.roundRect(bar_x, mid - 7, width, 14, 3, stroke=0, fill=1)
        c.setFillColor(palette["heading"])
        c.setFont("Heading-Bold", 13)
        c.drawString(bar_x + width + 12, mid - 5, fmt(value))


def numbered_list(c, palette, items, top, spacing=92) -> None:
    for i, text in enumerate(items):
        row_top = top - i * spacing
        muted = text.lower().startswith("caveat")
        c.setFillColor(palette["primary"])
        c.setFont("Heading-Bold", 22)
        c.drawString(M, row_top - 22, f"{i + 1:02d}")
        para(
            c,
            text,
            M + 90,
            row_top,
            W - 2 * M - 90,
            "Body",
            19,
            palette["muted"] if muted else palette["text"],
            leading=27,
        )
        if i < len(items) - 1:
            c.setStrokeColor(with_alpha(palette["muted"], 0.2))
            c.setLineWidth(0.5)
            c.line(M, row_top - spacing + 22, W - M, row_top - spacing + 22)


def fetch_thumb(video_id: str, dest: Path) -> Path | None:
    """Download the 16:9 part of a YouTube thumbnail (hqdefault is letterboxed 4:3)."""
    if dest.exists():
        return dest
    try:
        resp = requests.get(
            f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg", timeout=20
        )
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert("RGB")
        w, h = img.size
        crop_h = round(w * 9 / 16)
        top = (h - crop_h) // 2
        img.crop((0, top, w, top + crop_h)).save(dest, quality=92)
        return dest
    except Exception as exc:  # network or image problem: the page still renders
        print(f"Thumbnail unavailable for {video_id}: {exc}")
        return None


def page_cover(
    c, palette, logo: ImageReader, narrative: dict, today: str, company: str
) -> None:
    background(c, palette)
    ribbon(c, palette)
    lw = 460
    lh = lw * logo.getSize()[1] / logo.getSize()[0]
    c.drawImage(logo, M, H - 96 - lh, width=lw, height=lh, mask="auto")
    c.setFillColor(palette["primary"])
    c.setFont("Body-Semi", 13)
    c.drawString(M, 330, "WEEKLY INTELLIGENCE REPORT")
    h = para(c, narrative["title"], M, 300, 1000, "Heading", 46, palette["heading"], 52)
    para(
        c,
        f"Trends from the most active AI and AI-automation channels  |  {today}",
        M,
        300 - h - 18,
        1000,
        "Body",
        18,
        palette["muted"],
    )
    c.setStrokeColor(with_alpha(palette["muted"], 0.3))
    c.setLineWidth(0.6)
    c.line(M, 96, W - M, 96)
    c.setFillColor(palette["muted"])
    c.setFont("Body", 13)
    c.drawString(M, 70, f"Prepared by {company}")


def page_thanks(c, palette, logo: ImageReader, tagline: str) -> None:
    background(c, palette)
    ribbon(c, palette)
    c.setFillColor(palette["heading"])
    c.setFont("Heading", 84)
    c.drawString(M, 380, "Thank you")
    c.setFillColor(palette["primary"])
    c.setFont("Body-Semi", 13)
    c.drawString(M, 340, "END OF REPORT")
    c.setFillColor(palette["muted"])
    c.setFont("Body", 20)
    c.drawString(M, 300, "Questions and feedback are welcome.")
    lw = 300
    lh = lw * logo.getSize()[1] / logo.getSize()[0]
    c.drawImage(logo, M, 120, width=lw, height=lh, mask="auto")
    c.setFillColor(palette["primary"])
    c.setFont("Body-Semi", 13)
    c.drawRightString(W - M, 120, tagline)


def page_overview(c, palette, narrative: dict, totals: dict) -> None:
    background(c, palette)
    header(c, palette, "This week", narrative["headline"], size=28)
    kpis = [
        (fmt_int(totals["videos"]), "videos analyzed"),
        (fmt_int(totals["channels"]), "channels tracked"),
        (fmt_int(totals["median_views_per_day"]), "median views / day"),
        (fmt_pct(totals["median_engagement_rate"]), "median engagement"),
    ]
    col = (W - 2 * M) / len(kpis)
    for i, (value, label) in enumerate(kpis):
        x = M + i * col
        if i:
            c.setStrokeColor(with_alpha(palette["muted"], 0.25))
            c.setLineWidth(0.6)
            c.line(x, 330, x, 200)
        c.setFillColor(palette["primary"] if i == 2 else palette["heading"])
        c.setFont("Heading", 64)
        c.drawString(x + (24 if i else 0), 292, value)
        c.setFillColor(palette["muted"])
        c.setFont("Body", 15)
        c.drawString(x + (24 if i else 0), 258, label)


def page_breakout(c, palette, analysis: dict) -> None:
    background(c, palette)
    header(c, palette, "Breakouts", "Breakout videos: outperforming their own channel")
    rows = [
        (
            clean_text(v["title"]),
            f"{clean_text(v['channel_title'], 40)}  |  {v['format']}-form  |  "
            f"{fmt_int(v['views_per_day'])} views/day",
            v["breakout_score"],
        )
        for v in analysis["top_breakout"][:10]
    ]
    hbars(c, palette, rows, M, CONTENT_TOP, 560, 420, 40, lambda v: f"{v:.2f}x")
    c.setFillColor(palette["muted"])
    c.setFont("Body", 11)
    c.drawString(
        M,
        FOOTER_Y + 22,
        "Breakout score = video views per day divided by its channel's median views per day.",
    )


def page_top_three(c, palette, analysis: dict, thumbs_dir: Path) -> None:
    background(c, palette)
    header(c, palette, "Top breakouts", "The three videos pulling furthest ahead")
    card_w, gap = 344, 32
    thumb_h = card_w * 9 / 16
    for i, v in enumerate(analysis["top_breakout"][:3]):
        x = M + i * (card_w + gap)
        top = H - 190
        thumb = fetch_thumb(v["video_id"], thumbs_dir / f"{v['video_id']}.jpg")
        if thumb:
            c.drawImage(str(thumb), x, top - thumb_h, width=card_w, height=thumb_h)
        else:
            c.setFillColor(palette["panel"])
            c.rect(x, top - thumb_h, card_w, thumb_h, stroke=0, fill=1)
        c.setFillColor(palette["primary"])
        c.setFont("Heading-Bold", 14)
        c.drawString(x, top - thumb_h - 38, f"{i + 1:02d}")
        c.setFillColor(palette["heading"])
        c.setFont("Heading", 40)
        c.drawString(x, top - thumb_h - 72, f"{v['breakout_score']:.2f}x")
        para(
            c,
            clean_text(v["title"], 90),
            x,
            top - thumb_h - 106,
            card_w,
            "Body-Medium",
            14,
            palette["text"],
            leading=19,
        )
        c.setFillColor(palette["muted"])
        c.setFont("Body", 12)
        c.drawString(
            x,
            top - thumb_h - 176,
            fit(clean_text(v["channel_title"], 60), "Body", 12, card_w),
        )


def page_engagement(c, palette, analysis: dict) -> None:
    background(c, palette)
    header(c, palette, "Engagement", "Engagement leaders: where viewers act")
    rows = [
        (
            clean_text(v["title"]),
            f"{clean_text(v['channel_title'], 40)}  |  {v['format']}-form  |  "
            f"{fmt_int(v['views'])} views",
            v["engagement_rate"] * 100,
        )
        for v in analysis["top_engagement"][:10]
    ]
    hbars(c, palette, rows, M, CONTENT_TOP, 560, 420, 40, lambda v: f"{v:.2f}%")
    c.setFillColor(palette["muted"])
    c.setFont("Body", 11)
    c.drawString(
        M,
        FOOTER_Y + 22,
        "Engagement = (likes + comments) / views. Hidden like counts count as 0.",
    )


def page_formats_topics(c, palette, analysis: dict) -> None:
    background(c, palette)
    header(c, palette, "Formats and topics", "Shorts vs long-form, and rising topics")
    formats = analysis["formats"]
    c.setFillColor(palette["heading"])
    c.setFont("Heading-Bold", 16)
    c.drawString(M, CONTENT_TOP - 4, "Median views per day")
    base, max_h = 250, 220
    vmax = max(
        formats["short"]["median_views_per_day"],
        formats["long"]["median_views_per_day"],
    )
    bars = [
        ("Shorts", formats["short"], palette["accent"]),
        ("Long-form", formats["long"], palette["primary"]),
    ]
    for i, (name, d, color) in enumerate(bars):
        bx = M + 40 + i * 230
        bw = 150
        h = max_h * d["median_views_per_day"] / vmax
        c.setFillColor(color)
        c.roundRect(bx, base, bw, h, 4, stroke=0, fill=1)
        c.setFillColor(palette["heading"])
        c.setFont("Heading-Bold", 24)
        c.drawCentredString(
            bx + bw / 2, base + h + 12, fmt_int(d["median_views_per_day"])
        )
        c.setFillColor(palette["muted"])
        c.setFont("Body", 13)
        c.drawCentredString(bx + bw / 2, base - 24, f"{name} (n={d['videos']})")
    c.setFillColor(palette["text"])
    c.setFont("Body", 13)
    c.drawString(
        M,
        base - 70,
        f"Median engagement: Shorts {fmt_pct(formats['short']['median_engagement_rate'])}  |  "
        f"Long-form {fmt_pct(formats['long']['median_engagement_rate'])}",
    )

    right = M + 600
    c.setFillColor(palette["heading"])
    c.setFont("Heading-Bold", 16)
    c.drawString(right, CONTENT_TOP - 4, "Rising topics in titles")
    topics = [(t.title(), None, n) for t, n in analysis["topics"][:10]]
    hbars(
        c,
        palette,
        topics,
        right,
        CONTENT_TOP - 30,
        150,
        300,
        30,
        fmt_int,
        label_size=13,
    )
    c.setFillColor(palette["muted"])
    c.setFont("Body", 11)
    c.drawString(
        right, FOOTER_Y + 22, "Count = number of videos whose title contains the word."
    )


def page_list(c, palette, kicker: str, title: str, items: list[str]) -> None:
    background(c, palette)
    header(c, palette, kicker, title)
    numbered_list(c, palette, items, CONTENT_TOP + 4)


def page_method_close(c, palette, analysis: dict, logo: ImageReader) -> None:
    background(c, palette)
    header(c, palette, "Method and scope", "How these numbers were measured")
    totals = analysis["totals"]
    notes = [
        (
            "Scope",
            f"{totals['videos']} videos from {totals['channels']} channels, from public YouTube statistics.",
        ),
        (
            "Breakout score",
            "Video views per day divided by its channel's median views per day. Channels need at least 3 videos; videos need at least 500 views.",
        ),
        ("Engagement", "(likes + comments) / views. Hidden like counts count as 0."),
        ("Source", "YouTube Data API v3 statistics only. No transcripts."),
    ]
    y = CONTENT_TOP + 4
    for label, text in notes:
        c.setFillColor(palette["primary"])
        c.setFont("Heading-Bold", 14)
        c.drawString(M, y - 4, label.upper())
        h = para(c, text, M, y - 26, 600, "Body", 16, palette["text"], leading=23)
        y -= 26 + h + 30

    px, py, pw, ph = 760, 150, W - M - 760, 360
    c.setFillColor(palette["panel"])
    c.roundRect(px, py, pw, ph, 12, stroke=0, fill=1)
    lw = 300
    lh = lw * logo.getSize()[1] / logo.getSize()[0]
    c.drawImage(
        logo, px + (pw - lw) / 2, py + ph - 60 - lh, width=lw, height=lh, mask="auto"
    )
    c.setFillColor(palette["primary"])
    c.setFont("Body-Semi", 13)
    c.drawCentredString(
        px + pw / 2, py + 60, "Smarter Automation / Greater Possibilities"
    )


def upload_private(pdf: Path) -> str:
    """Upload to the user's Drive. The file stays private; no sharing is changed."""
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    from tools.utils import get_google_credentials

    drive = build("drive", "v3", credentials=get_google_credentials())
    created = (
        drive.files()
        .create(
            body={"name": pdf.name, "mimeType": "application/pdf"},
            media_body=MediaFileUpload(str(pdf), mimetype="application/pdf"),
            fields="id,webViewLink",
        )
        .execute()
    )
    return created["webViewLink"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-upload", action="store_true")
    args = parser.parse_args()

    tmp = ensure_tmp_dir()
    out_dir = tmp / "pdf"
    thumbs_dir = out_dir / "thumbs"
    thumbs_dir.mkdir(parents=True, exist_ok=True)

    analysis = json.loads((tmp / "trend_analysis.json").read_text(encoding="utf-8"))
    narrative = json.loads((tmp / "narrative.json").read_text(encoding="utf-8"))
    style = load_config("youtube_deck_style.json")
    palette = {k: hex_color(v) for k, v in style["palette"].items()}

    logo_path = clean_logo(
        PROJECT_ROOT / style["logo_path"], out_dir / "logo_clean.png"
    )
    logo = ImageReader(str(logo_path))
    register_fonts()

    today = date.today()
    pdf_path = out_dir / f"AI_YouTube_Trends_{today.isoformat()}.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=(W, H))
    c.setTitle(narrative["title"])
    c.setAuthor(style["company"])
    c.setSubject("Weekly AI and AI-automation YouTube trends")

    tagline = style["tagline"]
    page_cover(
        c,
        palette,
        logo,
        narrative,
        today.strftime("%d %b %Y"),
        style["company"],
    )
    c.showPage()

    pages = [
        lambda: page_overview(c, palette, narrative, analysis["totals"]),
        lambda: page_breakout(c, palette, analysis),
        lambda: page_top_three(c, palette, analysis, thumbs_dir),
        lambda: page_engagement(c, palette, analysis),
        lambda: page_formats_topics(c, palette, analysis),
        lambda: page_list(
            c,
            palette,
            "Key findings",
            "What the data shows",
            narrative["key_findings"][:5],
        ),
        lambda: page_list(
            c,
            palette,
            "Content opportunities",
            "Where to put the next videos",
            narrative["content_opportunities"][:5],
        ),
        lambda: page_method_close(c, palette, analysis, logo),
    ]
    for number, draw in enumerate(pages, start=2):
        draw()
        footer(c, palette, number, logo, tagline)
        c.showPage()
    page_thanks(c, palette, logo, tagline)
    c.showPage()
    c.save()

    result = {"pdf_path": str(pdf_path), "pages": len(pages) + 2, "url": None}
    if not args.skip_upload:
        result["url"] = upload_private(pdf_path)
    (out_dir / "pdf_result.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(f"PDF built ({result['pages']} pages): {pdf_path}")
    if result["url"]:
        print(f"Uploaded to Drive (private): {result['url']}")


if __name__ == "__main__":
    main()
