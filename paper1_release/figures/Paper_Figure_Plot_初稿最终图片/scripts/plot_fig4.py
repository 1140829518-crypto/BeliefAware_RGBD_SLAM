#!/usr/bin/env python3
"""Fig4 dynamic detection performance."""

from __future__ import annotations

import numpy as np

from plot_style import DATA_ROOT, apply_style, read_csv, save_figure
import matplotlib.pyplot as plt


def main() -> None:
    apply_style()
    rows = read_csv(DATA_ROOT / "Fig4_Detection_Performance" / "detection_metrics.csv")
    methods = [r["Method"] for r in rows]
    metrics = ["Precision", "Recall", "F1-score"]
    display_methods = [m.replace("Ours", "Temporal/Ours") for m in methods]
    x = np.arange(len(metrics))
    width = 0.23
    colors = {
        "YOLO": "#1f77b4",
        "YOLO+Motion": "#ff7f0e",
        "Ours": "#2ca02c",
    }
    fig, ax = plt.subplots(figsize=(3.6, 2.55))
    ax.grid(False)
    for i, (row, label) in enumerate(zip(rows, display_methods)):
        values = [float(row[metric]) for metric in metrics]
        bars = ax.bar(x + (i - 1) * width, values, width, label=label, color=colors[row["Method"]], edgecolor="black", linewidth=0.8)
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2.0, value + 0.015, f"{value:.2f}", ha="center", va="bottom", fontsize=8.5)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.set_ylabel("Detection Metric")
    ax.set_ylim(0, 1.18)
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.16), handlelength=1.2, columnspacing=0.8)
    fig.tight_layout()
    save_figure(fig, "Fig4")


if __name__ == "__main__":
    main()
