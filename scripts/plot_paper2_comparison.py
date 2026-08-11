#!/usr/bin/env python3

"""Generate publication-ready Paper2 comparison figures from experiment CSVs."""

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


SEQUENCES = (
    "fr3_walking_xyz",
    "fr3_walking_rpy",
    "fr3_walking_halfsphere",
)
SEQUENCE_LABELS = ("Walking XYZ", "Walking RPY", "Walking Halfsphere")
METHODS = ("baseline", "paper1", "shadow", "active")
METHOD_LABELS = ("ORB-SLAM2", "Paper1", "Shadow", "Active")
COLORS = ("#6c757d", "#4c78a8", "#f2a541", "#d1495b")


def load_comparison(path):
    values = {}
    with path.open("r", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            values[(row["sequence"], row["method"])] = row
    missing = [
        (sequence, method)
        for sequence in SEQUENCES
        for method in METHODS
        if (sequence, method) not in values
    ]
    if missing:
        raise ValueError("missing comparison rows: {}".format(missing))
    return values


def load_active_effect(path):
    frames = defaultdict(list)
    with path.open("r", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            sequence = row["sequence"]
            if sequence not in SEQUENCES:
                continue
            frames[sequence].append(
                {
                    "frame": int(row["frame"]),
                    "filtered": int(row["filtered_map_points"]),
                    "dynamic": int(row["dynamic_objects"]) if row["dynamic_objects"] else np.nan,
                }
            )
    for sequence in frames:
        frames[sequence].sort(key=lambda item: item["frame"])
    return frames


def save_figure(figure, output_dir, stem):
    figure.tight_layout()
    figure.savefig(output_dir / "{}.png".format(stem), dpi=300, bbox_inches="tight")
    figure.savefig(output_dir / "{}.pdf".format(stem), bbox_inches="tight")
    plt.close(figure)


def plot_ate(values, output_dir):
    x = np.arange(len(SEQUENCES))
    width = 0.19
    figure, axis = plt.subplots(figsize=(8.2, 4.8))
    for index, (method, label, color) in enumerate(zip(METHODS, METHOD_LABELS, COLORS)):
        data = [float(values[(sequence, method)]["ATE_RMSE"]) for sequence in SEQUENCES]
        bars = axis.bar(x + (index - 1.5) * width, data, width, label=label, color=color)
        axis.bar_label(bars, fmt="%.3f", padding=2, fontsize=7, rotation=90)
    axis.set_ylabel("ATE RMSE (m)")
    axis.set_xlabel("TUM RGB-D sequence")
    axis.set_title("Trajectory Accuracy Comparison")
    axis.set_xticks(x)
    axis.set_xticklabels(SEQUENCE_LABELS)
    axis.grid(axis="y", linestyle="--", alpha=0.35)
    axis.legend(ncol=4, frameon=False, loc="upper center")
    axis.set_ylim(top=axis.get_ylim()[1] * 1.16)
    save_figure(figure, output_dir, "ate_rmse_comparison")


def plot_shadow_active(values, output_dir):
    shadow = np.array([float(values[(sequence, "shadow")]["ATE_RMSE"]) for sequence in SEQUENCES])
    active = np.array([float(values[(sequence, "active")]["ATE_RMSE"]) for sequence in SEQUENCES])
    improvement = (shadow - active) / shadow * 100.0
    x = np.arange(len(SEQUENCES))
    width = 0.34
    figure, axis = plt.subplots(figsize=(8.0, 4.8))
    axis.bar(x - width / 2, shadow, width, label="Shadow", color=COLORS[2])
    axis.bar(x + width / 2, active, width, label="Active", color=COLORS[3])
    axis.set_ylabel("ATE RMSE (m)")
    axis.set_xlabel("TUM RGB-D sequence")
    axis.set_title("Effect of Active Dynamic MapPoint Filtering")
    axis.set_xticks(x)
    axis.set_xticklabels(SEQUENCE_LABELS)
    axis.grid(axis="y", linestyle="--", alpha=0.35)
    axis.legend(frameon=False)
    for position, value in enumerate(improvement):
        color = "#1b7837" if value >= 0 else "#b2182b"
        axis.text(
            position,
            max(shadow[position], active[position]) + 0.035,
            "{:+.1f}%".format(value),
            ha="center",
            va="bottom",
            color=color,
            fontweight="bold",
        )
    axis.set_ylim(top=max(shadow.max(), active.max()) * 1.20)
    save_figure(figure, output_dir, "shadow_vs_active_filtering_effect")


def plot_time_series(frames, output_dir, field, ylabel, title, stem):
    figure, axes = plt.subplots(3, 1, figsize=(9.0, 7.2), sharex=False)
    for axis, sequence, label, color in zip(axes, SEQUENCES, SEQUENCE_LABELS, COLORS[1:]):
        rows = frames.get(sequence, [])
        x = []
        y = []
        previous_frame = None
        for row in rows:
            if previous_frame is not None and row["frame"] > previous_frame + 1:
                x.append(previous_frame + 1)
                y.append(np.nan)
            x.append(row["frame"])
            y.append(row[field])
            previous_frame = row["frame"]
        axis.plot(x, y, linewidth=0.85, color=color)
        axis.fill_between(x, y, 0, color=color, alpha=0.15)
        axis.set_title(label, loc="left", fontsize=10)
        axis.set_ylabel(ylabel)
        axis.grid(linestyle="--", alpha=0.3)
    axes[-1].set_xlabel("Frame ID")
    figure.suptitle(title, fontsize=13)
    figure.subplots_adjust(top=0.91, hspace=0.42)
    save_figure(figure, output_dir, stem)


def main():
    project_root = Path(__file__).resolve().parents[1]
    comparison_root = project_root / "experiment_new" / "paper2" / "results" / "comparison"
    active_root = project_root / "experiment_new" / "paper2" / "results" / "active"
    output_dir = comparison_root / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)

    comparison = load_comparison(comparison_root / "trajectory_comparison.csv")
    active_effect = load_active_effect(active_root / "active_effect_analysis.csv")
    plot_ate(comparison, output_dir)
    plot_shadow_active(comparison, output_dir)
    plot_time_series(
        active_effect,
        output_dir,
        "dynamic",
        "Dynamic objects",
        "Dynamic Object Count over Time (Active Mode)",
        "dynamic_objects_over_time",
    )
    plot_time_series(
        active_effect,
        output_dir,
        "filtered",
        "Filtered MapPoints",
        "Active MapPoint Filtering over Time",
        "active_filtered_mappoints_over_time",
    )
    print("Wrote 8 figure files to {}".format(output_dir))


if __name__ == "__main__":
    main()
