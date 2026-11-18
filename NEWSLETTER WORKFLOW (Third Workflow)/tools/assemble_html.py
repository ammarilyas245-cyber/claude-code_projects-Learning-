"""Have Claude write the full branded newsletter HTML, then embed the logo and infographic.

Claude writes the layout with {{LOGO_SRC}} / {{INFOGRAPHIC_SRC}} placeholders; this script swaps in
base64 images (downscaled) and checks that the branding is present.

Usage:
    python tools/assemble_html.py --input .tmp/research_<topic>.json --infographic .tmp/infographics/<topic>.png
Output: .tmp/newsletter_<topic>.html  (open in a browser to preview)
"""

import argparse
import base64
import io
import json
import os
import re
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.utils import PROJECT_ROOT, ensure_tmp_dir, get_api_key, load_env, load_style

PROMPT = """Write a complete, production-quality HTML email newsletter.

BRAND (follow strictly):
{style}

CONTENT (use all of it, do not invent facts):
{content}

REQUIREMENTS
- Single 640px-wide centered column, table-based layout, ALL CSS inline (email clients strip <style>), mobile friendly.
- Header: background {navy}, containing <img src="{{{{LOGO_SRC}}}}" alt="{alt}" width="{logo_w}"> centered, undistorted, then the tagline in white small caps-style text. The logo is white/blue and MUST sit on the dark navy background.
- Headline in Montserrat bold (fallback Arial) in {navy}; body in Inter (fallback Arial); include the Google Fonts <link> from the brand config.
- Show the infographic once, after the summary, as <img src="{{{{INFOGRAPHIC_SRC}}}}" alt="{{infographic title}}" width="640" style="width:100%;height:auto;display:block">.
- Sections on white or {gray} bands, key points as clean bullet lists, primary blue {blue} for links and one CTA button, light blue {light} for small accents.
- A "Key takeaways" block, a "Sources" list with linked titles, and a footer on {navy} with the logo again (<img src="{{{{LOGO_SRC}}}}" ... width="{min_w}" ... >) , company name and tagline.
- Colors only from the brand palette. No shadows, no stretched images, no invented links.
Return ONLY the HTML document, starting with <!DOCTYPE html>."""


def data_uri(path: Path, max_width: int) -> str:
    img = Image.open(path)
    if img.width > max_width:
        img = img.resize((max_width, round(img.height * max_width / img.width)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def write_html(research: dict, style: dict) -> str:
    import anthropic

    c, logo = style["colors"], style["logo"]
    prompt = PROMPT.format(
        style=json.dumps({k: style[k] for k in ("name", "tagline", "colors", "fonts", "visual_style", "dos", "donts")}, indent=1),
        content=json.dumps({k: v for k, v in research.items() if k not in ("researched_at",)}, indent=1, ensure_ascii=False),
        navy=c["dark_navy"], gray=c["light_gray"], blue=c["primary_blue"], light=c["light_blue"],
        alt=logo["alt_text"], logo_w=logo["display_width_px"], min_w=logo["min_width_px"],
    )
    client = anthropic.Anthropic(api_key=get_api_key("ANTHROPIC_API_KEY"))
    msg = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}],
    )
    html = msg.content[0].text.strip()
    html = re.sub(r"^```(?:html)?\s*|\s*```$", "", html)
    return html[html.lower().find("<!doctype"):]


def check_branding(html: str, style: dict) -> list[str]:
    problems = []
    if html.count("{{LOGO_SRC}}") < 2:
        problems.append("logo must appear in header and footer")
    if "{{INFOGRAPHIC_SRC}}" not in html:
        problems.append("infographic placeholder missing")
    for name, hex_ in style["colors"].items():
        if name in ("dark_navy", "primary_blue") and hex_.lower() not in html.lower():
            problems.append(f"brand color {name} {hex_} not used")
    return problems


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--infographic", required=True)
    args = parser.parse_args()

    load_env()
    style = load_style()
    research = json.loads(Path(args.input).read_text(encoding="utf-8"))
    html = write_html(research, style)

    problems = check_branding(html, style)
    if problems:
        sys.exit("Branding check failed, not saving: " + "; ".join(problems))

    logo_uri = data_uri(PROJECT_ROOT / style["assets"]["logo"], style["logo"]["display_width_px"] * 2)
    html = html.replace("{{LOGO_SRC}}", logo_uri).replace("{{INFOGRAPHIC_SRC}}", data_uri(Path(args.infographic), 1280))
    out = ensure_tmp_dir() / f"newsletter_{Path(args.input).stem.removeprefix('research_')}.html"
    out.write_text(html, encoding="utf-8")
    print(f"Saved {out} ({len(html) // 1024} KB). Open it in a browser to review before sending.")
