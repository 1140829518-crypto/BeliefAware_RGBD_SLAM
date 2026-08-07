#!/usr/bin/env python3
"""Fig5 lambda parameter sensitivity."""

from __future__ import annotations

from plot_style import DATA_ROOT, apply_style, add_panel_label, read_csv, save_figure
import matplotlib.pyplot as plt


def main() -> None:
    apply_style()
    rows = read_csv(DATA_ROOT / "Fig5_Parameter_Analysis" / "lambda_analysis.csv")
    lambdas = [float(r["lambda"]) for r in rows]
    panels = [
        ("ATE", "ATE (m)", "(a) ATE", "#1f77b4"),
        ("RPE", "RPE (m)", "(b) RPE", "#d62728"),
        ("FPS", "FPS (frame/s)", "(c) FPS", "#2ca02c"),
        ("Switching_frequency", "Switching Frequency", "(d) Switching Frequency", "#ff7f0e"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(7.0, 4.7))
    for ax, (col, ylabel, label, color) in zip(axes.ravel(), panels):
        values = [float(r[col]) for r in rows]
        ax.grid(False)
        ax.plot(lambdas, values, color=color, marker="o", markersize=4.0, linewidth=1.5)
        add_panel_label(ax, label)
        ax.set_xlabel(r"Decay coefficient $\lambda$")
        ax.set_ylabel(ylabel)
        ax.set_xticks(lambdas)
        ax.set_xlim(min(lambdas) - 0.02, max(lambdas) + 0.02)
    fig.tight_layout()
    save_figure(fig, "Fig5")


if __name__ == "__main__":
    main()
