#!/usr/bin/env python3
"""Prepare final paper figures from experiment_new results.

This script does not modify experiment data. It only reads existing CSV files,
trajectories, and generated visualization assets, then exports a clean set of
300 dpi paper figures under experiment_new/paper_figures.
"""

from __future__ import annotations

import csv
import os
import shutil
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiment_new"
RESULT_DIR = EXP / "results"
FIG_DIR = EXP / "figures"
PAPER_DIR = EXP / "paper_figures"
RUN_ROOT = RESULT_DIR / "bonn_runs"
os.environ.setdefault("MPLCONFIGDIR", str(EXP / ".matplotlib_cache"))

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from PIL import Image

import sys

sys.path.insert(0, str(EXP / "scripts"))
from generate_experiment_new import build_detection_signal, moving_average  # noqa: E402
from plot_bonn_results import aligned_to_gt, load_tum, method_slug  # noqa: E402


COLORS = {
    "Ground Truth": "#1A1A1A",
    "ORB-SLAM3": "#4C78A8",
    "ORB-SLAM2": "#4C78A8",
    "DS-SLAM": "#72B7B2",
    "Dyna-SLAM": "#F58518",
    "Ours": "#54A24B",
    "YOLO": "#4C78A8",
    "YOLO+Motion": "#F58518",
    "Temporal Consistency": "#54A24B",
    "Precision": "#4C78A8",
    "Recall": "#F58518",
    "F1-score": "#54A24B",
}


def set_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9.5,
            "axes.titlesize": 10.5,
            "axes.labelsize": 9.5,
            "legend.fontsize": 8.5,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.22,
            "grid.linewidth": 0.6,
            "lines.linewidth": 1.8,
        }
    )


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def save(fig: plt.Figure, name: str) -> None:
    PAPER_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(PAPER_DIR / name, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_dynamic_probability() -> None:
    sequences = ["fr3_walking_xyz", "fr3_walking_rpy"]
    signals = []
    for sequence in sequences:
        try:
            signal = build_detection_signal(sequence)
            if len(signal.frame):
                signals.append(signal)
        except Exception:
            continue

    if not signals:
        copy_with_300dpi(FIG_DIR / "dynamic_probability_curve.png", PAPER_DIR / "Fig1_dynamic_probability.png")
        return

    fig, axes = plt.subplots(len(signals), 1, figsize=(7.6, 4.8), sharex=False, sharey=True)
    if len(signals) == 1:
        axes = [axes]
    for ax, signal in zip(axes, signals):
        ax.plot(signal.frame, moving_average(signal.yolo, 5), label="YOLO", color=COLORS["YOLO"])
        ax.plot(signal.frame, moving_average(signal.motion, 5), label="YOLO+Motion", color=COLORS["YOLO+Motion"])
        ax.plot(signal.frame, moving_average(signal.temporal, 5), label="Temporal Consistency", color=COLORS["Temporal Consistency"])
        ax.fill_between(signal.frame, 0, 1, where=signal.label, color="#BDBDBD", alpha=0.20, label="Dynamic interval")
        ax.axhline(0.5, color="#333333", linestyle="--", linewidth=0.9)
        ax.set_title(signal.sequence.replace("_", " "))
        ax.set_ylabel("Dynamic probability")
        ax.set_ylim(-0.03, 1.05)
    axes[-1].set_xlabel("Frame index")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False)
    fig.tight_layout(rect=[0, 0, 1, 0.91])
    save(fig, "Fig1_dynamic_probability.png")


def plot_detection_accuracy() -> None:
    rows = read_csv(RESULT_DIR / "dynamic_detection_accuracy.csv")
    methods = [
        row["Method"]
        .replace("YOLO raw detection", "YOLO")
        .replace("YOLO+motion consistency", "YOLO+Motion")
        .replace("YOLO+temporal consistency (Ours)", "Temporal")
        for row in rows
    ]
    metrics = ["Precision", "Recall", "F1-score"]
    x = np.arange(len(rows))
    width = 0.23
    fig, ax = plt.subplots(figsize=(6.8, 3.8))
    for i, metric in enumerate(metrics):
        ax.bar(
            x + (i - 1) * width,
            [float(row[metric]) for row in rows],
            width=width,
            label=metric,
            color=COLORS[metric],
            edgecolor="white",
            linewidth=0.7,
        )
    ax.set_xticks(x)
    ax.set_xticklabels(methods)
    ax.set_ylabel("Score")
    ax.set_ylim(0, 1.05)
    ax.legend(frameon=False, ncol=3, loc="upper center")
    ax.set_axisbelow(True)
    save(fig, "Fig2_detection_accuracy.png")


def plot_window_analysis() -> None:
    rows = read_csv(RESULT_DIR / "time_window_sensitivity.csv")
    n = [int(row["N"]) for row in rows]
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.6))
    axes[0].plot(n, [float(row["ATE"]) for row in rows], marker="o", color="#4C78A8")
    axes[0].set_xlabel("Temporal window size N [frames]")
    axes[0].set_ylabel("ATE RMSE [m]")
    axes[0].set_title("Accuracy")
    axes[1].plot(n, [float(row["Smoothness"]) for row in rows], marker="s", color="#F58518")
    axes[1].set_xlabel("Temporal window size N [frames]")
    axes[1].set_ylabel("Trajectory smoothness [m/frame$^2$]")
    axes[1].set_title("Smoothness")
    for ax in axes:
        ax.set_xticks(n)
        ax.set_axisbelow(True)
    fig.tight_layout()
    save(fig, "Fig3_window_analysis.png")


def plot_bonn_trajectory() -> None:
    manifest = read_csv(RESULT_DIR / "bonn_selected_sequences.csv")
    methods = ["Ground Truth", "ORB-SLAM3", "DS-SLAM", "Dyna-SLAM", "Ours"]
    fig, axes = plt.subplots(1, len(manifest), figsize=(14.4, 4.2), squeeze=False)
    for ax, item in zip(axes[0], manifest):
        dataset = item["Dataset"]
        sequence_dir = Path(item["Path"])
        gt_path = sequence_dir / "groundtruth.txt"
        _, gt_xyz = load_tum(gt_path)
        if len(gt_xyz):
            ax.plot(gt_xyz[:, 0], gt_xyz[:, 2], color=COLORS["Ground Truth"], linestyle="--", linewidth=1.5)
        for method in methods[1:]:
            est_path = RUN_ROOT / dataset / method_slug(method) / "CameraTrajectory.txt"
            est, _, _ = aligned_to_gt(est_path, gt_path)
            if len(est):
                ax.plot(est[:, 0], est[:, 2], color=COLORS[method], linewidth=1.35)
        ax.set_title(dataset)
        ax.set_xlabel("X [m]")
        ax.set_ylabel("Z [m]")
        ax.set_aspect("equal", adjustable="box")
        ax.set_axisbelow(True)
    handles = [
        Line2D([0], [0], color=COLORS["Ground Truth"], linestyle="--", linewidth=1.5),
        Line2D([0], [0], color=COLORS["ORB-SLAM3"], linewidth=1.5),
        Line2D([0], [0], color=COLORS["DS-SLAM"], linewidth=1.5),
        Line2D([0], [0], color=COLORS["Dyna-SLAM"], linewidth=1.5),
        Line2D([0], [0], color=COLORS["Ours"], linewidth=1.5),
    ]
    fig.legend(handles, methods, loc="upper center", ncol=5, frameon=False)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    save(fig, "Fig4_bonn_trajectory.png")


def plot_ablation() -> None:
    rows = read_csv(RESULT_DIR / "ablation_comparison.csv")
    labels = ["Baseline", "Semantic\nMask", "Temporal\nConsistency", "Object-level\nMap", "Full\nModel"]
    metrics = [
        ("ATE", "ATE RMSE [m]", "#4C78A8"),
        ("RPE", "RPE RMSE [m]", "#72B7B2"),
        ("FPS", "Processing speed [FPS]", "#F58518"),
        ("Failure Rate", "Failure rate", "#E45756"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(8.6, 5.8))
    for ax, (metric, ylabel, color) in zip(axes.ravel(), metrics):
        values = []
        missing = []
        for i, row in enumerate(rows):
            try:
                values.append(float(row[metric]))
                missing.append(False)
            except ValueError:
                values.append(0.0)
                missing.append(True)
        bars = ax.bar(np.arange(len(rows)), values, color=color, edgecolor="white", linewidth=0.7)
        for bar, is_missing in zip(bars, missing):
            if is_missing:
                ax.text(bar.get_x() + bar.get_width() / 2, 0.02, "N/A", ha="center", va="bottom", fontsize=8)
                bar.set_alpha(0.25)
        ax.set_xticks(np.arange(len(rows)))
        ax.set_xticklabels(labels, rotation=0)
        ax.set_ylabel(ylabel)
        ax.set_axisbelow(True)
    fig.tight_layout()
    save(fig, "Fig5_ablation.png")


def copy_with_300dpi(src: Path, dst: Path) -> None:
    PAPER_DIR.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        raise FileNotFoundError(src)
    with Image.open(src) as image:
        image.save(dst, dpi=(300, 300))


def export_semantic_map() -> None:
    src = FIG_DIR / "semantic_map_showcase.png"
    dst = PAPER_DIR / "Fig6_semantic_map.png"
    copy_with_300dpi(src, dst)


def write_captions() -> None:
    text = """# Figure Captions

**Fig. 1. Dynamic probability evolution with temporal consistency.** Dynamic probability curves on TUM RGB-D dynamic sequences. The gray intervals denote frames containing dynamic human motion, and the dashed line indicates the decision threshold. Compared with single-frame YOLO and YOLO+motion cues, temporal consistency produces smoother probability estimates across adjacent frames.

**Fig. 2. Dynamic object detection accuracy.** Precision, recall, and F1-score of YOLO, YOLO+Motion, and the proposed temporal consistency strategy. The temporal model improves recall and F1-score while maintaining high precision, indicating more stable dynamic target identification.

**Fig. 3. Temporal window sensitivity analysis.** Influence of the temporal window size N on ATE RMSE and trajectory smoothness. A larger window improves smoothness, while an overly large window may introduce response delay and does not continuously reduce ATE.

**Fig. 4. Trajectory comparison on the Bonn RGB-D Dynamic Dataset.** Trajectories of Ground Truth, ORB-SLAM3, DS-SLAM, Dyna-SLAM, and the proposed method on walking, sitting, and crowd sequences. All trajectories are aligned to the same coordinate frame and plotted in meters.

**Fig. 5. Ablation study.** Quantitative comparison of Baseline, Semantic Mask, Temporal Consistency, Object-level Semantic Map, and Full Model using ATE, RPE, FPS, and Failure Rate. The figure is intended to analyze module-level effects rather than claim that each module independently optimizes every metric.

**Fig. 6. Object-level semantic map visualization.** Visualization of semantic mapping and dynamic point handling in a dynamic RGB-D scene. The map demonstrates how semantic information and dynamic-object reasoning are integrated into the SLAM output.
"""
    (PAPER_DIR / "figure_caption.md").write_text(text, encoding="utf-8")


def main() -> None:
    set_style()
    PAPER_DIR.mkdir(parents=True, exist_ok=True)
    plot_dynamic_probability()
    plot_detection_accuracy()
    plot_window_analysis()
    plot_bonn_trajectory()
    plot_ablation()
    export_semantic_map()
    write_captions()
    print(f"Saved paper figures to {PAPER_DIR}")


if __name__ == "__main__":
    main()
