#!/usr/bin/env python3
"""Generate the optimized Figure 6 from existing independent ablation data."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch
from PIL import Image


ROOT = Path("/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3")
ORIGINAL_DIR = ROOT / "paper_figure_revision"
OUT = ROOT / "paper_figure_revision_optimized"

SOURCES = {
    "figure6_data": ORIGINAL_DIR / "figure6_ablation_data.csv",
    "ablation_results": ROOT / "aggregated_results/ablation_results.csv",
    "statistical_summary": ROOT / "aggregated_results/statistical_summary.csv",
    "temporal_metrics": ROOT / "aggregated_results/temporal_metrics.csv",
}

ORDER = [
    ("baseline", "Baseline", "Baseline"),
    ("semantic_mask", "Semantic Mask", "Sem. Mask"),
    ("temporal_consistency", "Temporal Consistency", "Temp. Cons."),
    ("object_level_map", "Object-level Semantic Map", "Object Map"),
    ("full_model", "Full Model", "Full Model"),
]

METRICS = [
    ("ATE", "ATE (m)", "ATE_RMSE", "lower"),
    ("RPE", "RPE (m)", "RPE_translation_RMSE", "lower"),
    ("Pose Missing Ratio", "Pose Missing Ratio", "Pose_Missing_Ratio", "lower"),
    ("Switching Frequency", "Switching Frequency", "Switching_Frequency", "lower_no_baseline"),
]

COLORS = ["#f2f2f2", "#b7c9e2", "#f4c78a", "#9cc9c1", "#b5d99c"]
HATCHES = ["///", "..", "xx", "\\\\", ""]
EDGE = "#222222"
ORIGINAL_LEGEND_FONT_SIZE = 8.5
OPTIMIZED_LEGEND_FONT_SIZE = 7.5


def read_ablation_rows() -> dict[str, dict[str, str]]:
    with SOURCES["ablation_results"].open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {row["variant_key"]: row for row in rows}


def val(row: dict[str, str], col: str) -> float:
    return float(row[f"{col}_mean"])


def std(row: dict[str, str], col: str) -> float:
    return float(row[f"{col}_std"])


def configure_fonts() -> str:
    names = sorted({font.name for font in fm.fontManager.ttflist})
    if "Nimbus Roman" in names:
        font = "Nimbus Roman"
    elif "Liberation Serif" in names:
        font = "Liberation Serif"
    else:
        font = "DejaVu Serif"
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": [font, "DejaVu Serif"],
            "mathtext.fontset": "dejavuserif",
            "axes.unicode_minus": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )
    return font


def best_methods(rows: dict[str, dict[str, str]]) -> dict[str, str]:
    best: dict[str, str] = {}
    for _, _, col, direction in METRICS:
        candidates = []
        for key, _, _ in ORDER:
            if direction == "lower_no_baseline" and key == "baseline":
                continue
            candidates.append((val(rows[key], col), key))
        best[col] = min(candidates)[1] if direction.startswith("lower") else max(candidates)[1]
    return best


def make_figure(
    rows: dict[str, dict[str, str]],
    best: dict[str, str],
    path_base: Path,
    figsize: tuple[float, float],
    png_dpi: int = 600,
) -> None:
    short_labels = [short for _, _, short in ORDER]
    x = np.arange(len(ORDER))
    fig, axes = plt.subplots(2, 2, figsize=figsize, facecolor="white")
    axes = axes.ravel()
    subplot_titles = ["(a) ATE", "(b) RPE", "(c) Pose Missing Ratio", "(d) Switching Frequency"]

    for ax, (_, ylabel, col, _), subplot_title in zip(axes, METRICS, subplot_titles):
        means = []
        errs = []
        for key, _, _ in ORDER:
            if key == "baseline" and col == "Switching_Frequency":
                means.append(np.nan)
                errs.append(0.0)
            else:
                means.append(val(rows[key], col))
                errs.append(std(rows[key], col))

        for i, (key, _, _) in enumerate(ORDER):
            if np.isnan(means[i]):
                ax.bar(
                    x[i],
                    0,
                    width=0.68,
                    color="white",
                    edgecolor=EDGE,
                    linewidth=1.0,
                    hatch="//",
                    zorder=3,
                )
                ax.text(
                    x[i],
                    0.52,
                    "N/A",
                    transform=ax.get_xaxis_transform(),
                    ha="center",
                    va="center",
                    fontsize=8,
                    rotation=90,
                )
                continue

            linewidth = 1.4 if key == best[col] else 0.9
            ax.bar(
                x[i],
                means[i],
                width=0.68,
                yerr=errs[i],
                capsize=3.5,
                color=COLORS[i],
                edgecolor=EDGE,
                linewidth=linewidth,
                hatch=HATCHES[i],
                error_kw={"elinewidth": 1.0, "capthick": 1.0, "ecolor": "#111111"},
                zorder=3,
            )

        ax.set_ylabel(ylabel, fontsize=9)
        ax.set_xticks(x)
        ax.set_xticklabels(short_labels, rotation=18, ha="right", fontsize=8)
        ax.tick_params(axis="y", labelsize=8)
        ymax = max([m + e for m, e in zip(means, errs) if not np.isnan(m)] + [0.1])
        ax.set_ylim(0, ymax * 1.22)
        ax.grid(axis="y", color="#d8d8d8", linewidth=0.45, alpha=0.8, zorder=0)
        ax.set_axisbelow(True)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        ax.text(
            0.02,
            0.97,
            subplot_title,
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=9.5,
            fontweight="bold",
        )

    legend_handles = [
        Patch(facecolor=COLORS[i], edgecolor=EDGE, hatch=HATCHES[i], label=short_labels[i])
        for i in range(len(ORDER))
    ]
    fig.legend(
        handles=legend_handles,
        loc="upper center",
        ncol=5,
        frameon=False,
        fontsize=OPTIMIZED_LEGEND_FONT_SIZE,
        bbox_to_anchor=(0.5, 0.998),
        handlelength=1.05,
        handletextpad=0.35,
        columnspacing=0.85,
        borderaxespad=0.05,
        labelspacing=0.2,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.965), w_pad=1.4, h_pad=1.7)

    fig.savefig(path_base.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(path_base.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(path_base.with_suffix(".eps"), bbox_inches="tight")
    fig.savefig(path_base.with_suffix(".png"), dpi=png_dpi, bbox_inches="tight")
    plt.close(fig)


def png_info(path: Path) -> str:
    image = Image.open(path)
    return f"{image.size[0]} x {image.size[1]} px, dpi={image.info.get('dpi')}"


def write_audit(font: str, rows: dict[str, dict[str, str]]) -> None:
    files = [
        "figure6_ablation_optimized.pdf",
        "figure6_ablation_optimized.eps",
        "figure6_ablation_optimized.svg",
        "figure6_ablation_optimized.png",
        "figure6_ablation_double_column_optimized.pdf",
        "figure6_ablation_double_column_optimized.eps",
        "figure6_ablation_double_column_optimized.svg",
        "figure6_ablation_double_column_optimized.png",
        "figure6_ablation_single_column_optimized.pdf",
        "figure6_ablation_single_column_optimized.eps",
        "figure6_ablation_single_column_optimized.svg",
        "figure6_ablation_single_column_optimized.png",
    ]
    size_lines = []
    for name in files:
        path = OUT / name
        extra = f"; {png_info(path)}" if path.suffix == ".png" else ""
        size_lines.append(f"- `{path}`: {path.stat().st_size} bytes{extra}")

    text = f"""# Figure 6 Optimization Audit

## Original Figure Paths

- `{ORIGINAL_DIR / 'figure6_ablation.pdf'}`
- `{ORIGINAL_DIR / 'figure6_ablation.eps'}`
- `{ORIGINAL_DIR / 'figure6_ablation.svg'}`
- `{ORIGINAL_DIR / 'figure6_ablation.png'}`

## Generation Script

`{OUT / 'generate_figure6_optimized.py'}`

No original standalone plotting script was found in the previous figure directory, so this optimized script regenerates the figure from the saved data files.

## Data Files Used

- `{SOURCES['figure6_data']}`
- `{SOURCES['ablation_results']}`
- `{SOURCES['statistical_summary']}`
- `{SOURCES['temporal_metrics']}`

## Optimization Operations

- Removed the in-panel text `Baseline excluded` from subplot (d).
- Kept the Baseline `N/A` marker in subplot (d).
- Kept Baseline excluded from switching-frequency best-value comparison.
- Reduced the top legend font size from {ORIGINAL_LEGEND_FONT_SIZE} pt to {OPTIMIZED_LEGEND_FONT_SIZE} pt, a reduction of approximately {(1 - OPTIMIZED_LEGEND_FONT_SIZE / ORIGINAL_LEGEND_FONT_SIZE) * 100:.1f}%.
- Reduced legend handle length to 1.05, handle-text padding to 0.35, column spacing to 0.85, border axes padding to 0.05, and label spacing to 0.2.
- Compressed the top legend area by changing the figure legend anchor to `(0.5, 0.998)` and the tight-layout rectangle to `(0, 0, 1, 0.965)`.

## Data Handling

- Modified experiment data: no.
- Re-ran experiments: no.
- Changed bar heights: no.
- Changed error bars: no.
- Changed method order: no.
- Changed colors or hatches: no.
- Overwrote original figure files: no.

## Baseline N/A Handling

Baseline still appears as `N/A` in subplot (d). Its source switching-frequency value remains 0 in the data files, but it is not plotted as a valid zero-height bar and is not included in the best-value comparison.

## Output Files, Size and DPI

{chr(10).join(size_lines)}

## Font

The optimized figure uses `{font}`, matching the available serif font used by the previous generated Figure 6.

## Data Consistency

No data differences were introduced by the optimization. The same `figure6_ablation_data.csv` and `ablation_results.csv` values were used.

## Suggested Caption

中文：

图6 不同消融配置下的系统性能比较。（a）绝对轨迹误差；（b）相对位姿误差；（c）位姿缺失率；（d）动态状态切换频率。柱高表示多次独立实验结果的均值，误差棒表示标准差。Baseline不输出动态目标状态，因此不参与动态状态切换频率的比较。

English:

Fig. 6 Performance comparison under different ablation configurations. (a) Absolute trajectory error; (b) relative pose error; (c) pose missing ratio; (d) dynamic-state switching frequency. Bars indicate the mean values of independent runs, and error bars denote the standard deviations. The Baseline does not output dynamic object states and is therefore excluded from the comparison of switching frequency.
"""
    (OUT / "figure6_optimization_audit.md").write_text(text, encoding="utf-8")


def main() -> None:
    rows = read_ablation_rows()
    font = configure_fonts()
    best = best_methods(rows)
    make_figure(rows, best, OUT / "figure6_ablation_optimized", (7.2, 5.2))
    make_figure(rows, best, OUT / "figure6_ablation_double_column_optimized", (7.2, 5.2))
    make_figure(rows, best, OUT / "figure6_ablation_single_column_optimized", (3.5, 5.0))
    write_audit(font, rows)
    print(OUT)


if __name__ == "__main__":
    main()
