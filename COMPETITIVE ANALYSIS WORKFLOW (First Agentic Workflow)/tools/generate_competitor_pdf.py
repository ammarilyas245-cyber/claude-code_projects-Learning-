"""
generate_competitor_pdf.py

Loads the latest analysis, generates matplotlib charts, renders the
branded HTML/CSS template, and converts to PDF via WeasyPrint.
Output: .tmp/competitor_report_YYYYMMDD.pdf
"""

import base64
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

HISTORY_DIR = ROOT / ".tmp" / "analysis_history"
CHARTS_DIR = ROOT / ".tmp" / "charts"
OUTPUT_DIR = ROOT / ".tmp"
BRAND_CONFIG = ROOT / "Brand_Assets" / "brand_config.json"
LOGO_PATH = ROOT / "Brand_Assets" / "Logo Image.png"
TEMPLATE_DIR = Path(__file__).parent / "templates"
PROFILE_PATH = ROOT / ".tmp" / "business_profile.json"


def load_brand_config() -> dict:
    if not BRAND_CONFIG.exists():
        print("ERROR: brand_config.json not found. Run setup first.")
        sys.exit(1)
    with open(BRAND_CONFIG, "r", encoding="utf-8") as f:
        return json.load(f)


def load_latest_analysis() -> dict:
    if not HISTORY_DIR.exists():
        print("ERROR: No analysis history found.")
        print("Run tools/analyze_competitors.py first.")
        sys.exit(1)
    files = sorted(HISTORY_DIR.glob("analysis_*.json"), reverse=True)
    if not files:
        print("ERROR: No analysis files found in .tmp/analysis_history/")
        sys.exit(1)
    latest = files[0]
    print(f"  Using analysis: {latest.name}")
    with open(latest, "r", encoding="utf-8") as f:
        return json.load(f)


def load_profile() -> dict:
    if PROFILE_PATH.exists():
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def encode_image_b64(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        print(f"  WARNING: Could not encode image {path}: {e}")
        return None


def generate_positioning_chart(analyses: list, brand: dict) -> Path | None:
    """Generate a positioning matrix chart (service breadth vs specialization)."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        import numpy as np

        primary = brand["colors"]["primary"]
        secondary = brand["colors"]["secondary"]
        dark = brand["colors"]["dark"]
        light = brand["colors"]["light"]

        fig, ax = plt.subplots(figsize=(9, 6))
        fig.patch.set_facecolor("#F8FAFC")
        ax.set_facecolor("#F8FAFC")

        # Assign positions based on competitor_type and threat_level
        type_map = {"direct": 0.6, "indirect": 0.35, "aspirational": 0.75}
        threat_map = {"High": 0.75, "Medium": 0.5, "Low": 0.3}

        points = []
        for a in analyses:
            name = a.get("competitor_name", "?")
            ctype = a.get("competitor_type", "direct")
            threat = a.get("threat_level", "Medium")
            # x = service breadth estimate, y = specialization estimate
            x = type_map.get(ctype, 0.5) + np.random.uniform(-0.1, 0.1)
            y = threat_map.get(threat, 0.5) + np.random.uniform(-0.1, 0.1)
            x = max(0.05, min(0.95, x))
            y = max(0.05, min(0.95, y))
            points.append((name, x, y, threat))

        # Plot competitors
        threat_colors = {"High": "#DC2626", "Medium": "#D97706", "Low": "#16A34A"}
        for name, x, y, threat in points:
            color = threat_colors.get(threat, "#64748B")
            ax.scatter(x, y, s=120, color=color, zorder=5, alpha=0.85)
            ax.annotate(
                name,
                (x, y),
                textcoords="offset points",
                xytext=(8, 5),
                fontsize=8,
                fontfamily="sans-serif",
                color=dark,
            )

        # Plot "Us" marker
        ax.scatter(
            0.45, 0.55, s=200, color=primary, zorder=6, marker="*", label="Us (AAA)"
        )
        ax.annotate(
            brand.get("brand_abbreviation", "Us"),
            (0.45, 0.55),
            textcoords="offset points",
            xytext=(8, 5),
            fontsize=9,
            fontweight="bold",
            color=primary,
        )

        # Style
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xlabel("Service Breadth  →", fontsize=10, color=dark, labelpad=10)
        ax.set_ylabel("Market Specialization  →", fontsize=10, color=dark, labelpad=10)
        ax.set_title(
            "Competitive Positioning Matrix",
            fontsize=13,
            fontweight="bold",
            color=dark,
            pad=16,
        )
        ax.set_xticks([])
        ax.set_yticks([])

        for spine in ax.spines.values():
            spine.set_edgecolor(light)

        ax.axhline(0.5, color=light, linewidth=1, linestyle="--", alpha=0.6)
        ax.axvline(0.5, color=light, linewidth=1, linestyle="--", alpha=0.6)

        # Quadrant labels
        ax.text(
            0.25,
            0.9,
            "Specialists",
            fontsize=8,
            color="#94A3B8",
            ha="center",
            style="italic",
        )
        ax.text(
            0.75,
            0.9,
            "Full-Service",
            fontsize=8,
            color="#94A3B8",
            ha="center",
            style="italic",
        )
        ax.text(
            0.25,
            0.08,
            "Niche Players",
            fontsize=8,
            color="#94A3B8",
            ha="center",
            style="italic",
        )
        ax.text(
            0.75,
            0.08,
            "Generalists",
            fontsize=8,
            color="#94A3B8",
            ha="center",
            style="italic",
        )

        # Legend
        legend_elements = [
            mpatches.Patch(color="#DC2626", label="High Threat"),
            mpatches.Patch(color="#D97706", label="Medium Threat"),
            mpatches.Patch(color="#16A34A", label="Low Threat"),
        ]
        ax.legend(
            handles=legend_elements, loc="lower right", fontsize=8, framealpha=0.9
        )

        plt.tight_layout()
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)
        output = CHARTS_DIR / "positioning_matrix.png"
        plt.savefig(output, dpi=150, bbox_inches="tight", facecolor="#F8FAFC")
        plt.close()
        print(f"  Generated positioning matrix chart")
        return output
    except Exception as e:
        print(f"  WARNING: Could not generate positioning chart: {e}")
        return None


def generate_pricing_chart(analyses: list, brand: dict) -> Path | None:
    """Generate a pricing model comparison bar chart."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        primary = brand["colors"]["primary"]
        secondary = brand["colors"]["secondary"]
        dark = brand["colors"]["dark"]
        light = brand["colors"]["light"]

        model_counts: dict = {}
        for a in analyses:
            dims = a.get("dimensions", {})
            pm = dims.get("pricing_model", {}) if dims else {}
            model = pm.get("model_type", "unknown") if pm else "unknown"
            model_counts[model] = model_counts.get(model, 0) + 1

        if not model_counts:
            return None

        models = list(model_counts.keys())
        counts = [model_counts[m] for m in models]
        colors = [primary, secondary, "#7C3AED", "#059669", "#D97706"][: len(models)]

        fig, ax = plt.subplots(figsize=(8, 4))
        fig.patch.set_facecolor("#F8FAFC")
        ax.set_facecolor("#F8FAFC")

        bars = ax.bar(
            [m.replace("-", "\n") for m in models],
            counts,
            color=colors,
            width=0.5,
            edgecolor="white",
            linewidth=1.5,
        )

        for bar, count in zip(bars, counts):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.05,
                str(count),
                ha="center",
                va="bottom",
                fontsize=11,
                fontweight="bold",
                color=dark,
            )

        ax.set_title(
            "Pricing Model Distribution",
            fontsize=13,
            fontweight="bold",
            color=dark,
            pad=16,
        )
        ax.set_ylabel("Number of Competitors", fontsize=10, color=dark)
        ax.set_ylim(0, max(counts) + 1.2)
        ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
        ax.tick_params(colors=dark)

        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        for spine in ["left", "bottom"]:
            ax.spines[spine].set_edgecolor(light)

        plt.tight_layout()
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)
        output = CHARTS_DIR / "pricing_comparison.png"
        plt.savefig(output, dpi=150, bbox_inches="tight", facecolor="#F8FAFC")
        plt.close()
        print(f"  Generated pricing comparison chart")
        return output
    except Exception as e:
        print(f"  WARNING: Could not generate pricing chart: {e}")
        return None


def render_html(
    data: dict,
    brand: dict,
    profile: dict,
    logo_b64: str | None,
    pos_b64: str | None,
    price_b64: str | None,
) -> str:
    try:
        from jinja2 import Environment, FileSystemLoader
    except ImportError:
        print("ERROR: jinja2 not installed. Run: pip install jinja2")
        sys.exit(1)

    css_path = TEMPLATE_DIR / "report.css"
    css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("report.html")

    return template.render(
        brand=brand,
        data=data,
        our_company_full=profile,
        logo_b64=logo_b64,
        positioning_chart_b64=pos_b64,
        pricing_chart_b64=price_b64,
        report_date=datetime.now().strftime("%B %d, %Y"),
        css=css,
    )


def html_to_pdf(html: str, output_path: Path):
    try:
        from xhtml2pdf import pisa
    except ImportError:
        print("ERROR: xhtml2pdf not installed. Run: pip install xhtml2pdf")
        sys.exit(1)

    print("  Converting HTML to PDF...")
    with open(output_path, "w+b") as f:
        result = pisa.CreatePDF(html.encode("utf-8"), dest=f, encoding="utf-8")
    if result.err:
        print(f"  WARNING: PDF generated with {result.err} error(s). Check output.")
    return not result.err


def main():
    print("Loading brand config...")
    brand = load_brand_config()

    print("Loading latest analysis...")
    data = load_latest_analysis()

    print("Loading business profile...")
    profile = load_profile()

    print("Encoding logo...")
    logo_b64 = encode_image_b64(LOGO_PATH)
    if not logo_b64:
        print("  WARNING: Logo not found — report will show text fallback")

    analyses = data.get("competitor_analyses", [])

    print("Generating charts...")
    pos_chart = generate_positioning_chart(analyses, brand)
    price_chart = generate_pricing_chart(analyses, brand)

    pos_b64 = encode_image_b64(pos_chart) if pos_chart else None
    price_b64 = encode_image_b64(price_chart) if price_chart else None

    print("Rendering HTML template...")
    html = render_html(data, brand, profile, logo_b64, pos_b64, price_b64)

    today = datetime.now().strftime("%Y%m%d")
    output_path = OUTPUT_DIR / f"competitor_report_{today}.pdf"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Generating PDF...")
    html_to_pdf(html, output_path)

    if output_path.exists():
        size_kb = output_path.stat().st_size // 1024
        print(f"\nReport ready: {output_path}")
        print(f"Size: {size_kb} KB")
        print(f"Competitors covered: {data.get('total_competitors', '?')}")
    else:
        print("ERROR: PDF was not created.")
        sys.exit(1)


if __name__ == "__main__":
    main()
