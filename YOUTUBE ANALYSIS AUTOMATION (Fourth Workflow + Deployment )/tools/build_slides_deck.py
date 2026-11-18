"""Build the weekly private Google Slides deck from the analysis, charts and narrative.

Inputs: .tmp/trend_analysis.json, .tmp/charts/*.png, .tmp/narrative.json (written by the agent before this runs).
Charts are uploaded to Drive as temporary "anyone with link" files so Slides can fetch them, then deleted.
The deck itself is never shared publicly.

Usage:
    python tools/build_slides_deck.py
"""

import json
import sys
from datetime import date
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.utils import (
    PROJECT_ROOT,
    ensure_tmp_dir,
    get_google_credentials,
    load_config,
)

PAGE_W, PAGE_H = 720, 405  # points, Slides default 16:9


def pt(value: float) -> dict:
    return {"magnitude": value, "unit": "PT"}


def rgb(hex_color: str) -> dict:
    h = hex_color.lstrip("#")
    return {
        "red": int(h[0:2], 16) / 255,
        "green": int(h[2:4], 16) / 255,
        "blue": int(h[4:6], 16) / 255,
    }


def place(page: str, x: float, y: float, w: float, h: float) -> dict:
    return {
        "pageObjectId": page,
        "size": {"width": pt(w), "height": pt(h)},
        "transform": {
            "scaleX": 1,
            "scaleY": 1,
            "translateX": x,
            "translateY": y,
            "unit": "PT",
        },
    }


class Deck:
    def __init__(self, drive, style: dict):
        self.drive = drive
        self.style = style
        self.palette = style["palette"]
        self.requests: list[dict] = []
        self.temp_file_ids: list[str] = []

    def add_slide(self, index: int) -> str:
        page = f"page{index}"
        self.requests.append(
            {
                "createSlide": {
                    "objectId": page,
                    "slideLayoutReference": {"predefinedLayout": "BLANK"},
                }
            }
        )
        self.requests.append(
            {
                "updatePageProperties": {
                    "objectId": page,
                    "fields": "pageBackgroundFill.solidFill.color",
                    "pageProperties": {
                        "pageBackgroundFill": {
                            "solidFill": {
                                "color": {"rgbColor": rgb(self.palette["background"])}
                            }
                        }
                    },
                }
            }
        )
        return page

    def text(
        self, page, name, x, y, w, h, body, size=14, bold=False, color=None
    ) -> None:
        oid = f"{page}_{name}"
        self.requests += [
            {
                "createShape": {
                    "objectId": oid,
                    "shapeType": "TEXT_BOX",
                    "elementProperties": place(page, x, y, w, h),
                }
            },
            {"insertText": {"objectId": oid, "text": body}},
            {
                "updateTextStyle": {
                    "objectId": oid,
                    "textRange": {"type": "ALL"},
                    "style": {
                        "fontSize": pt(size),
                        "bold": bold,
                        "fontFamily": (
                            self.style["font_heading"]
                            if bold
                            else self.style["font_body"]
                        ),
                        "foregroundColor": {
                            "opaqueColor": {
                                "rgbColor": rgb(color or self.palette["text"])
                            }
                        },
                    },
                    "fields": "fontSize,bold,fontFamily,foregroundColor",
                }
            },
        ]

    def image(self, page, name, source: str, x, y, w, h) -> None:
        url = source if source.startswith("http") else self.upload_temp(Path(source))
        self.requests.append(
            {
                "createImage": {
                    "objectId": f"{page}_{name}",
                    "url": url,
                    "elementProperties": place(page, x, y, w, h),
                }
            }
        )

    def upload_temp(self, path: Path) -> str:
        meta = {"name": f"tmp_{path.name}", "mimeType": "image/png"}
        media = MediaFileUpload(str(path), mimetype="image/png")
        file_id = (
            self.drive.files()
            .create(body=meta, media_body=media, fields="id")
            .execute()["id"]
        )
        self.temp_file_ids.append(file_id)
        self.drive.permissions().create(
            fileId=file_id, body={"type": "anyone", "role": "reader"}
        ).execute()
        return f"https://drive.google.com/uc?export=view&id={file_id}"


def fmt_int(value: float) -> str:
    return f"{value:,.0f}"


def build_slides(
    deck: Deck, analysis: dict, narrative: dict, charts: Path, logo: Path, today: str
) -> None:
    palette = deck.palette
    totals = analysis["totals"]
    formats = analysis["formats"]
    top_three = analysis["top_breakout"][:3]

    s = deck.add_slide(1)
    if logo.exists():
        from PIL import Image

        with Image.open(logo) as img:
            logo_w = 140
            logo_h = logo_w * img.height / img.width
        deck.image(s, "logo", str(logo), 50, 50, logo_w, logo_h)
    deck.text(s, "title", 50, 120, 620, 130, narrative["title"], size=28, bold=True)
    deck.text(
        s,
        "subtitle",
        50,
        262,
        620,
        40,
        f"Weekly AI and AI-automation YouTube trends  |  {today}",
        size=16,
        color=palette["muted"],
    )
    deck.text(
        s,
        "brandline",
        50,
        340,
        620,
        30,
        f"{deck.style['company']}  |  {deck.style['tagline']}",
        size=12,
        color=palette["primary"],
    )

    s = deck.add_slide(2)
    deck.text(s, "headline", 40, 30, 640, 90, narrative["headline"], size=22, bold=True)
    kpis = [
        (fmt_int(totals["videos"]), "videos analyzed"),
        (fmt_int(totals["channels"]), "channels in scope"),
        (fmt_int(totals["median_views_per_day"]), "median views / day"),
        (f"{totals['median_engagement_rate'] * 100:.2f}%", "median engagement"),
    ]
    for i, (value, label) in enumerate(kpis):
        x = 40 + i * 165
        deck.text(
            s,
            f"kpi{i}",
            x,
            170,
            150,
            50,
            value,
            size=28,
            bold=True,
            color=palette["primary"],
        )
        deck.text(
            s, f"kpilabel{i}", x, 225, 150, 30, label, size=11, color=palette["muted"]
        )

    s = deck.add_slide(3)
    deck.text(
        s,
        "title",
        40,
        22,
        640,
        40,
        "Breakout videos: outperforming their own channel",
        size=20,
        bold=True,
    )
    deck.image(s, "chart", str(charts / "breakout.png"), 40, 80, 640, 288)

    s = deck.add_slide(4)
    deck.text(s, "title", 40, 22, 640, 40, "Top breakout videos", size=20, bold=True)
    for i, v in enumerate(top_three):
        x = 40 + i * 225
        deck.image(
            s,
            f"thumb{i}",
            f"https://i.ytimg.com/vi/{v['video_id']}/hqdefault.jpg",
            x,
            80,
            200,
            150,
        )
        label = f"{v['title'][:70]}\n{v['breakout_score']}x  |  {v['channel_title']}"
        deck.text(s, f"label{i}", x, 240, 200, 90, label, size=11)

    s = deck.add_slide(5)
    deck.text(s, "title", 40, 22, 640, 40, "Engagement leaders", size=20, bold=True)
    deck.image(s, "chart", str(charts / "engagement.png"), 40, 80, 640, 288)

    s = deck.add_slide(6)
    deck.text(
        s,
        "title",
        40,
        22,
        640,
        40,
        "Shorts vs long-form, and rising topics",
        size=20,
        bold=True,
    )
    deck.image(s, "formats", str(charts / "formats.png"), 40, 80, 310, 242)
    deck.image(s, "topics", str(charts / "topics.png"), 370, 80, 310, 242)
    deck.text(
        s,
        "formatnote",
        40,
        335,
        640,
        50,
        f"Shorts: {formats['short']['median_views_per_day']:,.0f} median views/day, "
        f"{formats['short']['median_engagement_rate'] * 100:.2f}% engagement  |  "
        f"Long-form: {formats['long']['median_views_per_day']:,.0f} median views/day, "
        f"{formats['long']['median_engagement_rate'] * 100:.2f}% engagement",
        size=12,
    )

    s = deck.add_slide(7)
    deck.text(s, "title", 40, 22, 640, 40, "Key findings", size=20, bold=True)
    deck.text(
        s,
        "body",
        40,
        85,
        640,
        300,
        "\n\n".join(f"- {f}" for f in narrative["key_findings"][:5]),
        size=15,
    )

    s = deck.add_slide(8)
    deck.text(s, "title", 40, 22, 640, 40, "Content opportunities", size=20, bold=True)
    deck.text(
        s,
        "body",
        40,
        85,
        640,
        300,
        "\n\n".join(f"- {o}" for o in narrative["content_opportunities"][:5]),
        size=15,
    )

    s = deck.add_slide(9)
    deck.text(s, "title", 40, 22, 640, 40, "Method and scope", size=20, bold=True)
    deck.text(
        s,
        "body",
        40,
        85,
        640,
        300,
        f"- Videos analyzed: {totals['videos']} from {totals['channels']} channels"
        + (
            f" (topic scope: titles mentioning {analysis['scope']['topic_label']}; "
            f"baselines use all {analysis['scope']['niche_videos']} niche videos)\n\n"
            if analysis.get("scope", {}).get("topic_pattern")
            else "\n\n"
        )
        + "- Breakout score = video views per day divided by its channel's median views per day "
        f"(channels with at least 3 videos, videos with at least 500 views)\n\n"
        "- Engagement = (likes + comments) / views. Hidden like counts count as 0\n\n"
        "- Stats only, no transcripts. Source: YouTube Data API v3",
        size=13,
    )

    s = deck.add_slide(10)
    if logo.exists():
        from PIL import Image

        with Image.open(logo) as img:
            logo_w = 220
            logo_h = logo_w * img.height / img.width
        deck.image(s, "logo", str(logo), 50, 60, logo_w, logo_h)
    deck.text(s, "title", 50, 170, 620, 70, "Thank you", size=40, bold=True)
    deck.text(
        s,
        "subtitle",
        50,
        235,
        620,
        36,
        "Questions and feedback are welcome.",
        size=16,
        color=palette["muted"],
    )
    deck.text(
        s,
        "brandline",
        50,
        340,
        620,
        30,
        f"{deck.style['company']}  |  {deck.style['tagline']}",
        size=12,
        color=palette["primary"],
    )


def main() -> None:
    tmp = ensure_tmp_dir()
    analysis = json.loads((tmp / "trend_analysis.json").read_text(encoding="utf-8"))
    narrative = json.loads((tmp / "narrative.json").read_text(encoding="utf-8"))
    style = load_config("youtube_deck_style.json")
    logo = PROJECT_ROOT / style["logo_path"]
    today = date.today().strftime("%d %b %Y")

    creds = get_google_credentials()
    slides = build("slides", "v1", credentials=creds)
    drive = build("drive", "v3", credentials=creds)
    presentation = (
        slides.presentations()
        .create(body={"title": f"AI YouTube Trends - {today}"})
        .execute()
    )
    pid = presentation["presentationId"]

    deck = Deck(drive, style)
    deck.requests.append(
        {"deleteObject": {"objectId": presentation["slides"][0]["objectId"]}}
    )
    try:
        build_slides(deck, analysis, narrative, tmp / "charts", logo, today)
        slides.presentations().batchUpdate(
            presentationId=pid, body={"requests": deck.requests}
        ).execute()
    finally:
        for file_id in deck.temp_file_ids:
            drive.files().delete(fileId=file_id).execute()

    url = f"https://docs.google.com/presentation/d/{pid}/edit"
    (tmp / "deck_result.json").write_text(
        json.dumps({"presentation_id": pid, "url": url}, indent=2), encoding="utf-8"
    )
    print(f"Deck built (private): {url}")


if __name__ == "__main__":
    main()
