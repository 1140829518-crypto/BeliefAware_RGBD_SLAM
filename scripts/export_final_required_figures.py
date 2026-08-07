#!/usr/bin/env python3
"""Export final required paper figures as vector graphics.

Outputs:
- SLAM trajectory comparison: PDF/SVG vector + PNG preview
- System pipeline block diagram: PDF/SVG vector + PNG preview
- Ablation stability bar chart with unified fonts: PDF/SVG vector + PNG preview
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


OUT_DIR = Path("paper_ready_outputs_v15")
FIG_DIR = OUT_DIR / "figures"
TABLE_DIR = OUT_DIR / "tables"
COMPOSITE_SCRIPT = Path(__file__).with_name("export_ablation_figure4_composite.py")
CJK_FONT = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")


def setup_fonts() -> str:
    if CJK_FONT.exists():
        font_manager.fontManager.addfont(str(CJK_FONT))
        family = font_manager.FontProperties(fname=str(CJK_FONT)).get_name()
    else:
        family = "DejaVu Sans"
    plt.rcParams.update(
        {
            "font.family": family,
            "font.size": 9,
            "axes.labelsize": 9,
            "axes.titlesize": 10,
            "legend.fontsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
            "grid.alpha": 0.22,
            "grid.linewidth": 0.6,
        }
    )
    return family


def load_composite_module():
    spec = importlib.util.spec_from_file_location("figure4_composite", COMPOSITE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {COMPOSITE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT_DIR = OUT_DIR
    module.FIG_DIR = FIG_DIR
    module.TABLE_DIR = TABLE_DIR
    return module


def save_all(fig, stem: str) -> None:
    fig.savefig(FIG_DIR / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(FIG_DIR / f"{stem}.svg", bbox_inches="tight")
    fig.savefig(FIG_DIR / f"{stem}.png", bbox_inches="tight")
    plt.close(fig)


def export_vector_trajectory(m, summary) -> None:
    fig, axes = plt.subplots(
        1,
        5,
        figsize=(13.8, 3.2),
        gridspec_kw={"width_ratios": [1, 1, 1, 1, 0.95]},
        constrained_layout=True,
    )
    for ax, (short_name, sequence, gt_path, _) in zip(axes[:4], m.SEQUENCES):
        _, gt_xyz = m.read_tum_xyz(gt_path)
        ax.plot(gt_xyz[:, 0], gt_xyz[:, 2], color="#2ca02c", linestyle="-.", linewidth=1.05, label="Ground Truth")
        for label, method_key, color, _, linestyle in m.METHODS:
            run_dir = Path(summary[(sequence, method_key)]["run_dir"])
            est, _, _ = m.aligned_to_gt(run_dir / "CameraTrajectory.txt", gt_path)
            if len(est) == 0:
                continue
            ax.plot(est[:, 0], est[:, 2], color=color, linestyle=linestyle, linewidth=1.05, label=label)
        ax.set_title(short_name, fontweight="bold")
        ax.set_xlabel("x (m)")
        ax.set_ylabel("z (m)")
        ax.set_aspect("equal", adjustable="box")
        ax.grid(False)

    axes[4].axis("off")
    handles, labels = axes[0].get_legend_handles_labels()
    axes[4].legend(handles, labels, loc="center left", frameon=True)
    save_all(fig, "fig_slam_trajectory_compare_vector")


def add_box(ax, xy, width, height, title, subtitle="", fc="#f7f9fb", ec="#34495e") -> None:
    box = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.018,rounding_size=0.02",
        linewidth=1.2,
        edgecolor=ec,
        facecolor=fc,
    )
    ax.add_patch(box)
    x, y = xy
    ax.text(x + width / 2, y + height * 0.62, title, ha="center", va="center", fontsize=10, fontweight="bold")
    if subtitle:
        ax.text(x + width / 2, y + height * 0.34, subtitle, ha="center", va="center", fontsize=8.2, color="#2c3e50")


def add_arrow(ax, start, end, color="#34495e", rad=0.0) -> None:
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=12,
        linewidth=1.2,
        color=color,
        connectionstyle=f"arc3,rad={rad}",
    )
    ax.add_patch(arrow)


def export_system_pipeline() -> None:
    fig, ax = plt.subplots(figsize=(12.2, 5.6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.axis("off")

    colors = {
        "input": "#e8f1ff",
        "front": "#eef8ef",
        "semantic": "#fff3df",
        "dynamic": "#f9e8ef",
        "map": "#eef0ff",
        "output": "#eaf7f7",
    }

    add_box(ax, (0.45, 3.95), 1.55, 0.86, "RGB-D Input", "TUM sequence", colors["input"])
    add_box(ax, (2.55, 4.18), 1.65, 0.86, "ORB Feature\nExtraction", "keypoints + descriptors", colors["front"])
    add_box(ax, (2.55, 2.95), 1.65, 0.86, "YOLO Semantic\nDetection", "object boxes/classes", colors["semantic"])
    add_box(ax, (4.85, 4.18), 1.85, 0.86, "Semantic Mask\nFiltering", "remove dynamic pixels", colors["semantic"])
    add_box(ax, (4.85, 2.95), 1.85, 0.86, "Temporal Dynamic\nScore", "score accumulation", colors["dynamic"])
    add_box(ax, (7.2, 4.18), 1.75, 0.86, "Tracking", "pose estimation", colors["front"])
    add_box(ax, (7.05, 2.95), 2.05, 0.86, "Object-level\nSemantic Map", "object association", colors["map"])
    add_box(ax, (9.45, 4.18), 1.75, 0.86, "Local Mapping", "map point update", colors["front"])
    add_box(ax, (9.45, 2.95), 1.75, 0.86, "Loop Closing", "global correction", colors["front"])
    add_box(ax, (9.45, 1.35), 1.75, 0.86, "Final Outputs", "trajectory + map", colors["output"])

    add_arrow(ax, (2.0, 4.38), (2.55, 4.58))
    add_arrow(ax, (2.0, 4.18), (2.55, 3.38))
    add_arrow(ax, (4.2, 4.58), (4.85, 4.58))
    add_arrow(ax, (4.2, 3.38), (4.85, 3.38))
    add_arrow(ax, (5.78, 3.81), (5.78, 4.18), color="#b03a5b")
    add_arrow(ax, (6.7, 4.58), (7.2, 4.58))
    add_arrow(ax, (6.7, 3.38), (7.05, 3.38))
    add_arrow(ax, (8.95, 4.58), (9.45, 4.58))
    add_arrow(ax, (9.1, 3.38), (9.45, 3.38))
    add_arrow(ax, (10.32, 4.18), (10.32, 3.81))
    add_arrow(ax, (10.32, 2.95), (10.32, 2.21))
    add_arrow(ax, (8.08, 2.95), (8.08, 1.78), color="#5b5fc7")
    add_arrow(ax, (8.95, 1.78), (9.45, 1.78), color="#5b5fc7")
    add_arrow(ax, (9.45, 1.78), (8.95, 4.18), color="#7f8c8d", rad=-0.25)

    ax.text(6.0, 5.65, "System Pipeline", ha="center", va="center", fontsize=13, fontweight="bold")
    ax.text(5.78, 2.58, "temporal consistency", ha="center", va="center", fontsize=8.2, color="#8e244d")
    ax.text(8.08, 1.08, "semantic object constraints", ha="center", va="center", fontsize=8.2, color="#4044a7")

    save_all(fig, "fig_system_pipeline_block_diagram")


def export_uniform_ablation_bars(m, summary) -> None:
    stability = m.collect_stability(summary)
    metric_specs = [
        ("smoothness", "Smoothness ↓", "Smoothness", "{:.4f}"),
        ("variance", "Variance ↓", "Variance", "{:.5f}"),
        ("failure_rate", "Failure Rate ↓", "Failure Rate (%)", "{:.2f}%"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(12.4, 3.7), constrained_layout=True)
    colors = [item[2] for item in m.METHODS]
    method_labels = [item[0] for item in m.METHODS]

    for ax, (metric_key, title, ylabel, value_fmt) in zip(axes, metric_specs):
        values = [stability[label][metric_key] for label in method_labels]
        plot_values = [100.0 * value if metric_key == "failure_rate" else value for value in values]
        ax.bar(range(len(plot_values)), plot_values, color=colors, alpha=0.82, width=0.62)
        ax.set_title(title, fontweight="bold")
        ax.set_ylabel(ylabel)
        ax.set_xticks(range(len(plot_values)))
        ax.set_xticklabels(["Baseline\n(ORB-SLAM2)", "w/o Temporal\nConsistency", "w/o Object-level\nMap", "Full (Ours)"], rotation=15, ha="right")
        ax.tick_params(axis="x", labelsize=8)
        ax.grid(False)
        for i, value in enumerate(plot_values):
            ax.text(i, value + max(plot_values) * 0.025, value_fmt.format(value), ha="center", va="bottom", fontsize=8)

    save_all(fig, "fig_ablation_bars_uniform_font")


def main() -> None:
    setup_fonts()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    m = load_composite_module()
    summary = m.read_summary()
    export_vector_trajectory(m, summary)
    export_system_pipeline()
    export_uniform_ablation_bars(m, summary)
    print(f"Wrote final required figures to {OUT_DIR}")


if __name__ == "__main__":
    main()
