#!/usr/bin/env python3
"""Fig6 ablation study."""

from __future__ import annotations

import numpy as np

from plot_style import DATA_ROOT, apply_style, add_panel_label, read_csv, save_figure
import matplotlib.pyplot as plt


DISPLAY_LABELS = ["Baseline", "Semantic Mask", "Temporal Consistency", "Object Map", "Full Model"]
METHOD_COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd", "#d62728"]


def main() -> None:
    apply_style()
    rows = read_csv(DATA_ROOT / "Fig6_Ablation" / "ablation_results.csv")
    x = np.arange(len(rows))
    panels = [
        ("ATE_mean", "ATE_std", "ATE (m)", "(a) ATE"),
        ("RPE_mean", "RPE_std", "RPE (m)", "(b) RPE"),
        ("Missing_ratio", "Missing_ratio_std", "Pose Missing Ratio", "(c) Pose Missing Ratio"),
        ("Switch_frequency", "Switch_frequency_std", "Switching Frequency", "(d) Switching Frequency"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.9))
    for ax, (mean_col, std_col, ylabel, label) in zip(axes.ravel(), panels):
        ax.grid(False)
        means = [float(r[mean_col]) for r in rows]
        stds = [float(r[std_col]) for r in rows]
        top = max((mean + std for mean, std in zip(means, stds)), default=1.0)
        bars = ax.bar(x, means, yerr=stds, capsize=3, color=METHOD_COLORS, edgecolor="black", linewidth=0.8, error_kw={"elinewidth": 0.9})
        if mean_col == "Switch_frequency":
            bars[0].set_facecolor("#ffffff")
            ax.text(x[0], 0.002, "N/A", ha="center", va="bottom", fontsize=8)
        for i, (bar, mean, std) in enumerate(zip(bars, means, stds)):
            if mean_col == "Switch_frequency" and i == 0:
                continue
            y = mean + std
            ax.text(bar.get_x() + bar.get_width() / 2.0, y + top * 0.035, f"{mean:.3f}\n±{std:.3f}", ha="center", va="bottom", fontsize=8, linespacing=0.9)
        add_panel_label(ax, label)
        ax.set_ylabel(ylabel)
        ax.set_xticks(x)
        ax.set_xticklabels(DISPLAY_LABELS, rotation=22, ha="right")
        ax.set_ylim(0, top * 1.27 if top > 0 else 1.0)
    fig.tight_layout()
    save_figure(fig, "Fig6")


if __name__ == "__main__":
    main()
