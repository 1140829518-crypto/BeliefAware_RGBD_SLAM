#!/usr/bin/env python3
"""Generate a composite Figure 4 ablation plot matching the paper layout."""

from __future__ import annotations

import csv
import math
from pathlib import Path
from statistics import mean, pvariance
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np


OUT_DIR = Path("paper_ready_outputs_v12")
FIG_DIR = OUT_DIR / "figures"
TABLE_DIR = OUT_DIR / "tables"
SUMMARY_PATH = Path("evaluation_tables/standard_runs_summary.csv")

SEQUENCES = [
    ("fr3_xyz", "fr3_walking_xyz", Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz/groundtruth.txt"), "动态场景"),
    ("fr3_rpy", "fr3_walking_rpy", Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_rpy/groundtruth.txt"), "强动态场景"),
    (
        "fr3_halfsphere",
        "fr3_walking_halfsphere",
        Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_halfsphere/groundtruth.txt"),
        "动态场景",
    ),
    ("fr1_desk", "fr1_desk", Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg1_desk/groundtruth.txt"), "静态场景"),
]

RGB_FILES = {
    "fr1_xyz": Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg1_xyz/rgb.txt"),
    "fr1_desk": Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg1_desk/rgb.txt"),
    "fr3_walking_xyz": Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz/rgb.txt"),
    "fr3_walking_rpy": Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_rpy/rgb.txt"),
    "fr3_walking_halfsphere": Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_halfsphere/rgb.txt"),
    "fr3_walking_static": Path("rgbd_dataset_freiburg3_walking_static/rgb.txt"),
}

METHODS = [
    ("Baseline (ORB-SLAM2)", "ORB-SLAM2", "#222222", "P", "-."),
    ("w/o Temporal Consistency (仅去除时间一致性)", "Hard Remove", "#f47c35", "o", "--"),
    ("w/o Object-level Map (仅去除对象级语义建图)", "Dynamic Score", "#4169c9", "^", "-."),
    ("Full (Ours)", "Full Method", "#e5333a", "D", "-"),
]

BAR_LABELS = [
    "Baseline\n(ORB-SLAM2)",
    "w/o Temporal\nConsistency",
    "w/o Object-level\nMap",
    "Full (Ours)",
]

CJK_FONT = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
if CJK_FONT.exists():
    font_manager.fontManager.addfont(str(CJK_FONT))
    FONT_FAMILY = font_manager.FontProperties(fname=str(CJK_FONT)).get_name()
else:
    FONT_FAMILY = "DejaVu Sans"


plt.rcParams.update(
    {
        "font.family": FONT_FAMILY,
        "font.size": 9,
        "axes.labelsize": 9,
        "axes.titlesize": 10,
        "legend.fontsize": 8,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


def read_summary() -> Dict[Tuple[str, str], Dict[str, str]]:
    rows: Dict[Tuple[str, str], Dict[str, str]] = {}
    with SUMMARY_PATH.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows[(row["sequence"], row["method"])] = row
    return rows


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


def aligned_to_gt(est_path: Path, gt_path: Path) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    est_stamps, est_xyz = read_tum_xyz(est_path)
    gt_stamps, gt_xyz = read_tum_xyz(gt_path)
    matches = associate(est_stamps, gt_stamps)
    if not matches:
        return np.empty((0, 3)), np.empty((0, 3)), np.empty((0,))
    est_sel = np.asarray([est_xyz[i] for i, _ in matches])
    gt_sel = np.asarray([gt_xyz[j] for _, j in matches])
    stamps = np.asarray([gt_stamps[j] for _, j in matches])
    return umeyama_align(est_sel, gt_sel), gt_sel, stamps


def cumulative_distance(xyz: np.ndarray) -> np.ndarray:
    if len(xyz) == 0:
        return np.empty((0,))
    steps = np.linalg.norm(np.diff(xyz, axis=0), axis=1)
    return np.concatenate([[0.0], np.cumsum(steps)])


def prefix_ate_curve(est: np.ndarray, gt: np.ndarray, points: int = 9) -> Tuple[np.ndarray, np.ndarray]:
    dist = cumulative_distance(gt)
    if len(dist) < 4:
        return np.empty((0,)), np.empty((0,))
    bins = np.linspace(max(dist[-1] * 0.08, 1e-6), dist[-1], points)
    errors = np.linalg.norm(est - gt, axis=1)
    values: List[float] = []
    valid_bins: List[float] = []
    for threshold in bins:
        mask = dist <= threshold
        if mask.sum() < 3:
            continue
        valid_bins.append(float(threshold))
        values.append(float(np.sqrt(np.mean(errors[mask] ** 2))))
    return np.asarray(valid_bins), np.asarray(values)


def count_frames(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip() and not line.startswith("#"))


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
    steps = [math.dist(xyz[i + 1], xyz[i]) for i in range(len(xyz) - 1)]
    return len(xyz), mean(second_diff), pvariance(steps) if len(steps) > 1 else 0.0


def collect_stability(summary: Dict[Tuple[str, str], Dict[str, str]]) -> Dict[str, Dict[str, float]]:
    aggregate: Dict[str, Dict[str, float]] = {}
    rows: List[Dict[str, str]] = []
    for label, method_key, _, _, _ in METHODS:
        smoothness_values: List[float] = []
        variance_values: List[float] = []
        failure_values: List[float] = []
        for sequence, rgb_path in RGB_FILES.items():
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
    write_dict_csv(TABLE_DIR / "figure4_composite_stability_by_sequence.csv", rows)
    return aggregate


def draw_composite(summary: Dict[Tuple[str, str], Dict[str, str]]) -> None:
    fig = plt.figure(figsize=(14.8, 13.8))
    outer = fig.add_gridspec(3, 1, height_ratios=[1.0, 1.05, 1.0], hspace=0.72)
    top = outer[0].subgridspec(1, 4, wspace=0.32)
    middle = outer[1].subgridspec(1, 5, width_ratios=[1, 1, 1, 1, 0.75], wspace=0.32)
    bottom = outer[2].subgridspec(1, 3, wspace=0.35)

    curve_rows: List[Dict[str, str]] = []

    for col, (short_name, sequence, gt_path, scene_type) in enumerate(SEQUENCES):
        ax = fig.add_subplot(top[0, col])
        for label, method_key, color, marker, linestyle in METHODS:
            run_dir = Path(summary[(sequence, method_key)]["run_dir"])
            est, gt, _ = aligned_to_gt(run_dir / "CameraTrajectory.txt", gt_path)
            xs, ys = prefix_ate_curve(est, gt)
            if len(xs) == 0:
                continue
            ax.plot(xs, ys, color=color, linestyle=linestyle, marker=marker, markersize=3.3, linewidth=1.1, label=label)
            for distance, ate in zip(xs, ys):
                curve_rows.append(
                    {
                        "sequence": sequence,
                        "method": label,
                        "distance_m": f"{distance:.9f}",
                        "prefix_ate_rmse_m": f"{ate:.9f}",
                    }
                )
        ax.set_title(f"{short_name} ({scene_type})", fontweight="bold")
        ax.set_xlabel("距离 (m)")
        ax.set_ylabel("ATE RMSE (m)")
        ax.tick_params(axis="both", direction="out")

    handles, labels = fig.axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.982), ncol=4, frameon=True)
    fig.text(0.5, 0.655, "(a) 不同方法在多个序列上的 ATE RMSE 对比（消融：时间一致性与对象级语义建图）", ha="center", fontsize=11)

    for col, (short_name, sequence, gt_path, _) in enumerate(SEQUENCES):
        ax = fig.add_subplot(middle[0, col])
        _, gt_xyz = read_tum_xyz(gt_path)
        ax.plot(gt_xyz[:, 0], gt_xyz[:, 2], color="#2ca02c", linestyle="-.", linewidth=1.0, label="Ground Truth")
        for label, method_key, color, _, linestyle in METHODS:
            run_dir = Path(summary[(sequence, method_key)]["run_dir"])
            est, gt, _ = aligned_to_gt(run_dir / "CameraTrajectory.txt", gt_path)
            if len(est) == 0:
                continue
            ax.plot(est[:, 0], est[:, 2], color=color, linestyle=linestyle, linewidth=1.0, label=label)
        ax.set_title(short_name, fontweight="bold")
        ax.set_xlabel("x (m)")
        ax.set_ylabel("z (m)")
        ax.set_aspect("equal", adjustable="box")

    legend_ax = fig.add_subplot(middle[0, 4])
    legend_ax.axis("off")
    mid_handles, mid_labels = fig.axes[4].get_legend_handles_labels()
    legend_ax.legend(mid_handles, mid_labels, loc="center left", frameon=True)
    fig.text(0.5, 0.380, "(b) 不同方法的轨迹对比（以 TUM 数据集为例）", ha="center", fontsize=11)

    stability = collect_stability(summary)
    metric_specs = [
        ("smoothness", "Smoothness (越小越好)", "Smoothness", "{:.4f}"),
        ("variance", "Variance (越小越好)", "Variance", "{:.5f}"),
        ("failure_rate", "Failure Rate (越小越好)", "Failure Rate (%)", "{:.2f}%"),
    ]
    colors = [item[2] for item in METHODS]
    method_labels = [item[0] for item in METHODS]

    for col, (metric_key, title, ylabel, value_fmt) in enumerate(metric_specs):
        ax = fig.add_subplot(bottom[0, col])
        values = [stability[label][metric_key] for label in method_labels]
        plot_values = [100.0 * value if metric_key == "failure_rate" else value for value in values]
        ax.bar(np.arange(len(plot_values)), plot_values, color=colors, alpha=0.78, width=0.62)
        ax.set_title(title, fontweight="bold")
        ax.set_ylabel(ylabel)
        ax.set_xticks(np.arange(len(plot_values)))
        ax.set_xticklabels(BAR_LABELS, rotation=22, ha="right")
        for i, value in enumerate(plot_values):
            text = value_fmt.format(value)
            ax.text(i, value + max(plot_values) * 0.025, text, ha="center", va="bottom", fontsize=8)

    fig.text(0.5, 0.080, "(c) 不同方法在稳定性指标上的对比（越小越好）", ha="center", fontsize=11)
    fig.text(0.5, 0.035, "图 4  消融实验结果：时间一致性建模与对象级语义建图模块的有效性分析", ha="center", fontsize=12, fontweight="bold")
    fig.subplots_adjust(top=0.93, bottom=0.14, left=0.055, right=0.985)
    fig.savefig(FIG_DIR / "figure4_ablation_composite.png", bbox_inches="tight")
    fig.savefig(FIG_DIR / "figure4_ablation_composite.pdf", bbox_inches="tight")
    plt.close(fig)

    write_dict_csv(TABLE_DIR / "figure4_composite_ate_curves.csv", curve_rows)
    stability_rows = [
        {
            "method": label,
            "smoothness": f"{values['smoothness']:.9f}",
            "variance": f"{values['variance']:.9f}",
            "failure_rate": f"{values['failure_rate']:.9f}",
        }
        for label, values in stability.items()
    ]
    write_dict_csv(TABLE_DIR / "figure4_composite_stability_summary.csv", stability_rows)


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
    draw_composite(summary)
    print(f"Wrote composite Figure 4 to {OUT_DIR}")


if __name__ == "__main__":
    main()
