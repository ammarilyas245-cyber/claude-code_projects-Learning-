"""Render the weekly charts from .tmp/trend_analysis.json into .tmp/charts/.

Usage:
    python tools/generate_charts.py
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.utils import ensure_tmp_dir, load_config

WIDE = (8.0, 3.6)  # matches a 640x288 pt slot on the deck
SQUARE = (4.6, 3.6)  # matches a 310x242 pt slot on the deck


def truncate(text: str, limit: int = 42) -> str:
    text = text.encode("ascii", "ignore").decode().strip() or "(non-Latin title)"
    return text if len(text) <= limit else text[: limit - 3] + "..."


def horizontal_bars(
    labels, values, title, xlabel, path: Path, figsize, palette
) -> None:
    bg, text, bar = palette["background"], palette["text"], palette["primary"]
    fig, ax = plt.subplots(figsize=figsize, dpi=200)
    fig.patch.set_facecolor(bg)
    ax.set_facecolor(bg)
    ax.barh(labels[::-1], values[::-1], color=bar)
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold", color=text)
    ax.set_xlabel(xlabel, color=text, fontsize=8)
    ax.tick_params(colors=text, labelsize=7)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(palette["muted"])
    fig.tight_layout()
    fig.savefig(path, facecolor=bg)
    plt.close(fig)


def main() -> None:
    tmp = ensure_tmp_dir()
    analysis = json.loads((tmp / "trend_analysis.json").read_text(encoding="utf-8"))
    palette = load_config("youtube_deck_style.json")["palette"]
    out_dir = tmp / "charts"
    out_dir.mkdir(exist_ok=True)

    breakout = analysis["top_breakout"]
    horizontal_bars(
        [truncate(v["title"]) for v in breakout],
        [v["breakout_score"] for v in breakout],
        "Breakout videos (x their channel's median views/day)",
        "Breakout score",
        out_dir / "breakout.png",
        WIDE,
        palette,
    )

    engagement = analysis["top_engagement"]
    horizontal_bars(
        [truncate(v["title"]) for v in engagement],
        [v["engagement_rate"] * 100 for v in engagement],
        "Engagement leaders ((likes + comments) / views)",
        "Engagement rate (%)",
        out_dir / "engagement.png",
        WIDE,
        palette,
    )

    topics = analysis["topics"][:15]
    horizontal_bars(
        [t for t, _ in topics],
        [c for _, c in topics],
        "Rising topics in titles",
        "Videos mentioning topic",
        out_dir / "topics.png",
        SQUARE,
        palette,
    )

    fig, ax = plt.subplots(figsize=SQUARE, dpi=200)
    fig.patch.set_facecolor(palette["background"])
    ax.set_facecolor(palette["background"])
    formats = analysis["formats"]
    labels = [
        f"Shorts\n(n={formats['short']['videos']})",
        f"Long-form\n(n={formats['long']['videos']})",
    ]
    values = [
        formats["short"]["median_views_per_day"],
        formats["long"]["median_views_per_day"],
    ]
    ax.bar(labels, values, color=[palette["accent"], palette["primary"]], width=0.5)
    ax.set_title(
        "Median views per day by format",
        loc="left",
        fontsize=12,
        fontweight="bold",
        color=palette["text"],
    )
    ax.tick_params(colors=palette["text"], labelsize=8)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(palette["muted"])
    fig.tight_layout()
    fig.savefig(out_dir / "formats.png", facecolor=palette["background"])
    plt.close(fig)

    print(f"Charts written to {out_dir}")


if __name__ == "__main__":
    main()
