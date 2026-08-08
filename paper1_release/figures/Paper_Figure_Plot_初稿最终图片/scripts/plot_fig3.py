#!/usr/bin/env python3
"""Fig3 dynamic evidence curve."""

from __future__ import annotations

from plot_style import DATA_ROOT, apply_style, finite_float, read_csv, save_figure
import matplotlib.pyplot as plt


def main() -> None:
    apply_style()
    rows = read_csv(DATA_ROOT / "Fig3_Dynamic_Evidence" / "dynamic_evidence.csv")
    frames = [int(float(r["frame"])) for r in rows]
    candidates = [
        ("dynamic_evidence", "Dynamic Evidence Score", "#2ca02c", "-"),
        ("temporal_score", "Dynamic Evidence Score", "#2ca02c", "-"),
    ]
    fig, ax = plt.subplots(figsize=(3.5, 2.35))
    ax.grid(False)
    plotted = 0
    for col, label, color, linestyle in candidates:
        if col not in rows[0]:
            continue
        values = [finite_float(r.get(col, "")) for r in rows]
        if all(v != v for v in values):
            continue
        ax.plot(frames, values, color=color, linestyle=linestyle, linewidth=1.5, label=label)
        plotted += 1
        break
    if "threshold" in rows[0]:
        threshold_values = [finite_float(r.get("threshold", "")) for r in rows]
        threshold_values = [v for v in threshold_values if v == v]
        if threshold_values:
            ax.axhline(threshold_values[0], color="#d62728", linestyle="--", linewidth=1.2, label="Threshold")
    if "dynamic_state" in rows[0]:
        states = [finite_float(r.get("dynamic_state", "0")) for r in rows]
        ax2 = ax.twinx()
        ax2.grid(False)
        ax2.step(frames, states, where="mid", color="#1f77b4", linestyle="--", linewidth=1.2, label="Dynamic State")
        ax2.set_ylabel("Dynamic State")
        ax2.set_ylim(-0.05, 1.15)
        ax2.set_yticks([0, 1])
    else:
        ax2 = None
    ax.set_xlabel("Frame Index")
    ax.set_ylabel("Dynamic Evidence Score")
    ax.set_ylim(bottom=0)
    if plotted:
        handles, labels = ax.get_legend_handles_labels()
        if ax2 is not None:
            h2, l2 = ax2.get_legend_handles_labels()
            handles += h2
            labels += l2
        ax.legend(handles, labels, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.18), ncol=2, handlelength=1.8, columnspacing=0.9)
    fig.tight_layout()
    save_figure(fig, "Fig3")


if __name__ == "__main__":
    main()
