#!/usr/bin/env python3
"""Generate Figure 4 ablation plots for temporal consistency/object map."""

from __future__ import annotations

import csv
import math
from pathlib import Path
from statistics import mean, pvariance
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np


OUT_DIR = Path("paper_ready_outputs_v11")
FIG_DIR = OUT_DIR / "figures"
TABLE_DIR = OUT_DIR / "tables"
SUMMARY_PATH = Path("evaluation_tables/standard_runs_summary.csv")
TRAJECTORY_SEQUENCE = "fr3_walking_xyz"

SEQUENCE_LABELS = {
    "fr1_xyz": "fr1_xyz",
    "fr1_desk": "fr1_desk",
    "fr3_walking_xyz": "fr3_xyz",
    "fr3_walking_rpy": "fr3_rpy",
    "fr3_walking_halfsphere": "fr3_half",
    "fr3_walking_static": "fr3_static",
}

DATASETS = {
    "fr1_xyz": Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg1_xyz/rgb.txt"),
    "fr1_desk": Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg1_desk/rgb.txt"),
    "fr3_walking_xyz": Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz/rgb.txt"),
    "fr3_walking_rpy": Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_rpy/rgb.txt"),
    "fr3_walking_halfsphere": Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_halfsphere/rgb.txt"),
    "fr3_walking_static": Path("rgbd_dataset_freiburg3_walking_static/rgb.txt"),
}

GROUNDTRUTH = {
    "fr3_walking_xyz": Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz/groundtruth.txt"),
}

FIG4A_METHODS = [
    ("ORB-SLAM2", "ORB-SLAM2", "#4c78a8", "o"),
    ("Ours w/o temporal consistency", "Hard Remove", "#f58518", "s"),
    ("Ours full", "Full Method", "#54a24b", "^"),
]

FIG4B_METHODS = [
    ("GT", "Ground Truth", "#111111", "--"),
    ("ORB-SLAM2", "ORB-SLAM2", "#4c78a8", "-"),
    ("Ours w/o module", "Hard Remove", "#f58518", "-"),
    ("Ours full", "Full Method", "#54a24b", "-"),
]

FIG4C_METHODS = [
    ("w/o temporal consistency", "Hard Remove", "#f58518"),
    ("w/o object-level map", "Dynamic Score", "#b279a2"),
    ("full model", "Full Method", "#54a24b"),
]


plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.labelsize": 9,
        "axes.titlesize": 10,
        "legend.fontsize": 8,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "axes.grid": True,
        "grid.alpha": 0.22,
        "grid.linewidth": 0.6,
    }
)


def read_summary() -> Dict[Tuple[str, str], Dict[str, str]]:
    rows: Dict[Tuple[str, str], Dict[str, str]] = {}
    with SUMMARY_PATH.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows[(row["sequence"], row["method"])] = row
    return rows


def as_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def read_tum_xyz(path: Path) -> Tuple[np.ndarray, np.ndarray]:
    stamps: List[float] = []
    xyz: List[List[float]] = []
    with path.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            try:
                stamps.append(float(parts[0]))
                xyz.append([float(parts[1]), float(parts[2]), float(parts[3])])
            except ValueError:
                continue
    return np.asarray(stamps), np.asarray(xyz)


def associate(stamps_a: np.ndarray, stamps_b: np.ndarray, max_diff: float = 0.02) -> List[Tuple[int, int]]:
    matches: List[Tuple[int, int]] = []
    if len(stamps_a) == 0 or len(stamps_b) == 0:
        return matches
    j = 0
    for i, ta in enumerate(stamps_a):
        while j + 1 < len(stamps_b) and abs(stamps_b[j + 1] - ta) < abs(stamps_b[j] - ta):
            j += 1
        if abs(stamps_b[j] - ta) <= max_diff:
            matches.append((i, j))
    return matches


def umeyama_align(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    mu_src = src.mean(axis=0)
    mu_dst = dst.mean(axis=0)
    src_c = src - mu_src
    dst_c = dst - mu_dst
    cov = src_c.T @ dst_c / src.shape[0]
    u, _, vt = np.linalg.svd(cov)
    r = vt.T @ u.T
    if np.linalg.det(r) < 0:
        vt[-1, :] *= -1
        r = vt.T @ u.T
    t = mu_dst - r @ mu_src
    return (r @ src.T).T + t


def count_frames(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip() and not line.startswith("#"))


def dist(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def trajectory_stats(path: Path) -> Tuple[int, float, float]:
    _, xyz_arr = read_tum_xyz(path)
    xyz = [tuple(row) for row in xyz_arr.tolist()]
    if len(xyz) < 3:
        return len(xyz), float("nan"), float("nan")

    second_diff = []
    for i in range(1, len(xyz) - 1):
        ax = xyz[i + 1][0] - 2.0 * xyz[i][0] + xyz[i - 1][0]
        ay = xyz[i + 1][1] - 2.0 * xyz[i][1] + xyz[i - 1][1]
        az = xyz[i + 1][2] - 2.0 * xyz[i][2] + xyz[i - 1][2]
        second_diff.append(math.sqrt(ax * ax + ay * ay + az * az))
    steps = [dist(xyz[i + 1], xyz[i]) for i in range(len(xyz) - 1)]
    return len(xyz), mean(second_diff), pvariance(steps) if len(steps) > 1 else 0.0


def plot_fig4a(summary: Dict[Tuple[str, str], Dict[str, str]]) -> None:
    sequences = list(SEQUENCE_LABELS)
    metrics = [
        ("ate_rmse", "ATE RMSE [m]"),
        ("rpe_trans_rmse", "RPE-trans RMSE [m]"),
        ("rpe_rot_rmse_deg", "RPE-rot RMSE [deg]"),
    ]

    rows: List[Dict[str, str]] = []
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.6), sharex=True)
    x = np.arange(len(sequences))

    for ax, (metric_key, ylabel) in zip(axes, metrics):
        for label, method_key, color, marker in FIG4A_METHODS:
            values = [as_float(summary[(seq, method_key)][metric_key]) for seq in sequences]
            ax.plot(x, values, marker=marker, linewidth=1.7, markersize=4.8, color=color, label=label)
            for seq, value in zip(sequences, values):
                rows.append({"figure": "4a", "metric": metric_key, "sequence": seq, "method": label, "value": f"{value:.9f}"})
        ax.set_ylabel(ylabel)
        ax.set_yscale("log")
        ax.set_xticks(x)
        ax.set_xticklabels([SEQUENCE_LABELS[seq] for seq in sequences], rotation=30, ha="right")
    axes[0].set_title("ATE")
    axes[1].set_title("RPE-trans")
    axes[2].set_title("RPE-rot")
    axes[0].legend(frameon=False, loc="best")
    fig.suptitle("Figure 4(a): Temporal consistency ablation (ATE/RPE)", y=1.02)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "figure4a_temporal_consistency_ate_rpe.png", bbox_inches="tight")
    fig.savefig(FIG_DIR / "figure4a_temporal_consistency_ate_rpe.pdf", bbox_inches="tight")
    plt.close(fig)

    write_dict_csv(TABLE_DIR / "figure4a_temporal_consistency_ate_rpe.csv", rows)


def plot_fig4b(summary: Dict[Tuple[str, str], Dict[str, str]]) -> None:
    gt_stamps, gt_xyz = read_tum_xyz(GROUNDTRUTH[TRAJECTORY_SEQUENCE])
    fig, ax = plt.subplots(figsize=(5.4, 4.2))
    ax.plot(gt_xyz[:, 0], gt_xyz[:, 2], color="#111111", linestyle="--", linewidth=1.4, label="GT")

    for label, method_key, color, linestyle in FIG4B_METHODS[1:]:
        run_dir = Path(summary[(TRAJECTORY_SEQUENCE, method_key)]["run_dir"])
        est_stamps, est_xyz = read_tum_xyz(run_dir / "CameraTrajectory.txt")
        matches = associate(est_stamps, gt_stamps)
        if not matches:
            continue
        est_sel = np.asarray([est_xyz[i] for i, _ in matches])
        gt_sel = np.asarray([gt_xyz[j] for _, j in matches])
        est_aligned = umeyama_align(est_sel, gt_sel)
        ax.plot(est_aligned[:, 0], est_aligned[:, 2], color=color, linestyle=linestyle, linewidth=1.35, label=label)

    ax.set_xlabel("X [m]")
    ax.set_ylabel("Z [m]")
    ax.set_title("Figure 4(b): Trajectory comparison")
    ax.set_aspect("equal", adjustable="box")
    ax.legend(frameon=False, loc="best")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "figure4b_trajectory_compare_temporal_ablation.png", bbox_inches="tight")
    fig.savefig(FIG_DIR / "figure4b_trajectory_compare_temporal_ablation.pdf", bbox_inches="tight")
    plt.close(fig)


def plot_fig4c(summary: Dict[Tuple[str, str], Dict[str, str]]) -> None:
    rows: List[Dict[str, str]] = []
    aggregate: Dict[str, Dict[str, float]] = {}

    for label, method_key, _ in FIG4C_METHODS:
        smoothness_values: List[float] = []
        variance_values: List[float] = []
        failure_values: List[float] = []

        for sequence, rgb_path in DATASETS.items():
            run_dir = Path(summary[(sequence, method_key)]["run_dir"])
            pose_count, smoothness, variance = trajectory_stats(run_dir / "CameraTrajectory.txt")
            frame_count = count_frames(rgb_path)
            failure_rate = max(0.0, 1.0 - pose_count / frame_count) if frame_count else float("nan")
            if not math.isnan(smoothness):
                smoothness_values.append(smoothness)
            if not math.isnan(variance):
                variance_values.append(variance)
            if not math.isnan(failure_rate):
                failure_values.append(failure_rate)
            rows.append(
                {
                    "figure": "4c",
                    "sequence": sequence,
                    "method": label,
                    "smoothness": f"{smoothness:.9f}",
                    "variance": f"{variance:.9f}",
                    "failure_rate": f"{failure_rate:.9f}",
                }
            )

        aggregate[label] = {
            "smoothness": mean(smoothness_values),
            "variance": mean(variance_values),
            "failure_rate": mean(failure_values),
        }

    metrics = [
        ("smoothness", "Smoothness ↓"),
        ("variance", "Variance ↓"),
        ("failure_rate", "Failure Rate ↓"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(10.2, 3.4))
    labels = [item[0] for item in FIG4C_METHODS]
    colors = [item[2] for item in FIG4C_METHODS]

    for ax, (metric_key, title) in zip(axes, metrics):
        values = [aggregate[label][metric_key] for label in labels]
        ax.bar(np.arange(len(labels)), values, color=colors, width=0.62)
        ax.set_title(title)
        ax.set_xticks(np.arange(len(labels)))
        ax.set_xticklabels(labels, rotation=18, ha="right")
        if metric_key == "failure_rate":
            ax.set_ylabel("Ratio")
        else:
            ax.set_ylabel("Value")

    fig.suptitle("Figure 4(c): Stability metrics ablation", y=1.02)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "figure4c_stability_metrics_ablation.png", bbox_inches="tight")
    fig.savefig(FIG_DIR / "figure4c_stability_metrics_ablation.pdf", bbox_inches="tight")
    plt.close(fig)

    aggregate_rows = [
        {
            "method": label,
            "smoothness": f"{aggregate[label]['smoothness']:.9f}",
            "variance": f"{aggregate[label]['variance']:.9f}",
            "failure_rate": f"{aggregate[label]['failure_rate']:.9f}",
        }
        for label in labels
    ]
    write_dict_csv(TABLE_DIR / "figure4c_stability_metrics_ablation.csv", aggregate_rows)
    write_dict_csv(TABLE_DIR / "figure4c_stability_metrics_by_sequence.csv", rows)


def write_dict_csv(path: Path, rows: List[Dict[str, str]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    summary = read_summary()
    plot_fig4a(summary)
    plot_fig4b(summary)
    plot_fig4c(summary)
    print(f"Wrote Figure 4 ablation plots to {OUT_DIR}")


if __name__ == "__main__":
    main()
