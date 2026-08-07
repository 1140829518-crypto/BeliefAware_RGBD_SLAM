#!/usr/bin/env python3
"""Redraw the system pipeline as a clean publication block diagram."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, Rectangle


OUT_DIR = Path("paper_ready_outputs_v16")
FIG_DIR = OUT_DIR / "figures"
CJK_FONT = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")


def setup_style() -> None:
    if CJK_FONT.exists():
        font_manager.fontManager.addfont(str(CJK_FONT))
        family = font_manager.FontProperties(fname=str(CJK_FONT)).get_name()
    else:
        family = "DejaVu Sans"
    plt.rcParams.update(
        {
            "font.family": family,
            "font.size": 9,
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def box(ax, x, y, w, h, title, subtitle="", fc="#f6f8fb", ec="#2f4858") -> None:
    ax.add_patch(Rectangle((x, y), w, h, linewidth=1.15, edgecolor=ec, facecolor=fc))
    ax.text(x + w / 2, y + h * 0.62, title, ha="center", va="center", fontsize=9.5, fontweight="bold")
    if subtitle:
        ax.text(x + w / 2, y + h * 0.33, subtitle, ha="center", va="center", fontsize=7.6, color="#34495e")


def arrow(ax, start, end, color="#2f4858", lw=1.25, rad=0.0) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=11,
            linewidth=lw,
            color=color,
            connectionstyle=f"arc3,rad={rad}",
            shrinkA=2,
            shrinkB=2,
        )
    )


def elbow(ax, points, color="#2f4858", lw=1.15) -> None:
    for p0, p1 in zip(points[:-2], points[1:-1]):
        ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color=color, linewidth=lw)
    arrow(ax, points[-2], points[-1], color=color, lw=lw)


def draw() -> None:
    setup_style()
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(11.6, 4.9))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6.1)
    ax.axis("off")

    c_input = "#eaf2ff"
    c_front = "#edf7ef"
    c_sem = "#fff5e6"
    c_score = "#fdebf2"
    c_map = "#eef1ff"
    c_out = "#eaf7f7"
    dark = "#2f4858"
    accent = "#b33b63"
    semantic = "#555bd1"

    ax.text(6, 5.72, "System Pipeline", ha="center", va="center", fontsize=13, fontweight="bold")

    # Row 1: visual SLAM backbone.
    box(ax, 0.45, 3.78, 1.55, 0.86, "RGB-D Input", "TUM sequence", c_input)
    box(ax, 2.55, 4.18, 1.72, 0.86, "ORB Feature\nExtraction", "keypoints + descriptors", c_front)
    box(ax, 4.78, 4.18, 1.78, 0.86, "Semantic Mask\nFiltering", "remove dynamic pixels", c_sem)
    box(ax, 7.02, 4.18, 1.68, 0.86, "Tracking", "pose estimation", c_front)
    box(ax, 9.18, 4.18, 1.78, 0.86, "Local Mapping", "map point update", c_front)

    # Row 2: semantic and dynamic modules.
    box(ax, 2.55, 2.72, 1.72, 0.86, "YOLO Semantic\nDetection", "object boxes/classes", c_sem)
    box(ax, 4.78, 2.72, 1.78, 0.86, "Temporal Dynamic\nScore", "score accumulation", c_score)
    box(ax, 7.02, 2.72, 1.68, 0.86, "Object-level\nSemantic Map", "object association", c_map)
    box(ax, 9.18, 2.72, 1.78, 0.86, "Loop Closing", "global correction", c_front)

    # Output.
    box(ax, 9.18, 1.18, 1.78, 0.86, "Final Outputs", "trajectory + map", c_out)

    # Main data flow.
    arrow(ax, (2.0, 4.21), (2.55, 4.61), dark)
    arrow(ax, (2.0, 4.05), (2.55, 3.16), dark)
    arrow(ax, (4.27, 4.61), (4.78, 4.61), dark)
    arrow(ax, (4.27, 3.15), (4.78, 3.15), dark)
    arrow(ax, (6.56, 4.61), (7.02, 4.61), dark)
    arrow(ax, (8.7, 4.61), (9.18, 4.61), dark)
    arrow(ax, (10.07, 4.18), (10.07, 3.58), dark)
    arrow(ax, (10.07, 2.72), (10.07, 2.04), dark)

    # Semantic/dynamic constraints.
    arrow(ax, (5.67, 3.58), (5.67, 4.18), accent)
    arrow(ax, (6.56, 3.15), (7.02, 3.15), dark)
    arrow(ax, (8.7, 3.15), (9.18, 3.15), dark)
    elbow(ax, [(7.86, 3.58), (7.86, 3.92), (7.86, 4.18)], color="#7f8c8d")
    elbow(ax, [(7.86, 2.72), (7.86, 1.61), (9.18, 1.61)], color=semantic, lw=1.2)

    ax.text(5.67, 2.27, "temporal consistency", ha="center", va="center", fontsize=8, color=accent)
    ax.text(7.55, 0.78, "semantic object constraints", ha="center", va="center", fontsize=8, color=semantic)

    fig.tight_layout(pad=0.4)
    for suffix in ("pdf", "svg", "png"):
        fig.savefig(FIG_DIR / f"system_pipeline_redraw.{suffix}", bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote redrawn system pipeline to {OUT_DIR}")


if __name__ == "__main__":
    draw()
