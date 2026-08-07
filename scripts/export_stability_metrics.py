#!/usr/bin/env python3
"""Export trajectory stability metrics for paper tables.

Metrics:
- Smoothness: mean norm of the second-order translation difference.
- Variance: variance of frame-to-frame translation step lengths.
- Failure Rate: 1 - trajectory poses / dataset RGB frames.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from statistics import mean, pvariance
from typing import Dict, List, Optional, Tuple


OUT_DIR = Path("paper_ready_outputs_v9")
TABLE_DIR = OUT_DIR / "tables"
SUMMARY_PATH = Path("paper_ready_outputs_v7/summary_completed_baselines.csv")

DATASETS = {
    "fr1_xyz": Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg1_xyz/rgb.txt"),
    "fr1_desk": Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg1_desk/rgb.txt"),
    "fr3_walking_xyz": Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz/rgb.txt"),
    "fr3_walking_rpy": Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_rpy/rgb.txt"),
    "fr3_walking_halfsphere": Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_halfsphere/rgb.txt"),
    "fr3_walking_static": Path("rgbd_dataset_freiburg3_walking_static/rgb.txt"),
}

METHODS = [
    ("ORB-SLAM2", "ORB-SLAM2"),
    ("ORB-SLAM3", "ORB-SLAM3"),
    ("DS-SLAM", "DS-SLAM"),
    ("Dyna-SLAM", "Dyna-SLAM"),
    ("Hard Remove", "Hard Remove"),
    ("Ours", "Full Method"),
]

ORB_SLAM3_TRAJECTORIES = {
    "fr3_walking_xyz": Path("ORB_SLAM3_trajectory/freiburg3_walking_xyz/CameraTrajectory.txt"),
    "fr3_walking_rpy": Path("ORB_SLAM3_trajectory/freiburg3_walking_rpy/CameraTrajectory.txt"),
    "fr3_walking_halfsphere": Path("ORB_SLAM3_trajectory/freiburg3_walking_halfsphere/CameraTrajectory.txt"),
    "fr3_walking_static": Path("ORB_SLAM3_trajectory/freiburg3_walking_static/CameraTrajectory.txt"),
}


def count_frames(path: Path) -> int:
    count = 0
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            count += 1
    return count


def read_summary() -> Dict[Tuple[str, str], Dict[str, str]]:
    rows: Dict[Tuple[str, str], Dict[str, str]] = {}
    with SUMMARY_PATH.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows[(row["sequence"], row["method"])] = row
    return rows


def read_trajectory(path: Path) -> List[Tuple[float, float, float, float]]:
    poses: List[Tuple[float, float, float, float]] = []
    if not path.exists():
        return poses
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        try:
            poses.append((float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3])))
        except ValueError:
            continue
    poses.sort(key=lambda item: item[0])
    return poses


def trajectory_path(sequence: str, method_key: str, row: Optional[Dict[str, str]]) -> Optional[Path]:
    if method_key == "ORB-SLAM3":
        return ORB_SLAM3_TRAJECTORIES.get(sequence)
    if row:
        return Path(row["run_dir"]) / "CameraTrajectory.txt"
    return None


def dist(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def trajectory_stats(poses: List[Tuple[float, float, float, float]]) -> Tuple[float, float]:
    xyz = [(x, y, z) for _, x, y, z in poses]
    if len(xyz) < 3:
        return float("nan"), float("nan")

    second_diff = []
    for i in range(1, len(xyz) - 1):
        ax = xyz[i + 1][0] - 2.0 * xyz[i][0] + xyz[i - 1][0]
        ay = xyz[i + 1][1] - 2.0 * xyz[i][1] + xyz[i - 1][1]
        az = xyz[i + 1][2] - 2.0 * xyz[i][2] + xyz[i - 1][2]
        second_diff.append(math.sqrt(ax * ax + ay * ay + az * az))

    steps = [dist(xyz[i + 1], xyz[i]) for i in range(len(xyz) - 1)]
    return mean(second_diff), pvariance(steps) if len(steps) > 1 else 0.0


def fmt(value: float, percent: bool = False) -> str:
    if math.isnan(value):
        return "--"
    if percent:
        return f"{100.0 * value:.2f}%"
    return f"{value:.6f}"


def bold_best(rows: List[List[str]], raw: Dict[str, Dict[str, float]]) -> None:
    for col, metric in [(1, "smoothness"), (2, "variance"), (3, "failure_rate")]:
        candidates = [(method, values[metric]) for method, values in raw.items() if not math.isnan(values[metric])]
        if not candidates:
            continue
        best, _ = min(candidates, key=lambda item: item[1])
        for row in rows:
            if row[0] == best and row[col] != "--":
                row[col] = f"**{row[col]}**"


def write_markdown(path: Path, table: List[List[str]]) -> None:
    lines = [
        "# Stability Metrics",
        "",
        "| Method | Smoothness ↓ | Variance ↓ | Failure Rate ↓ |",
        "|---|---:|---:|---:|",
    ]
    for row in table:
        lines.append("| " + " | ".join(row) + " |")
    lines.extend(
        [
            "",
            "Note: Smoothness is the mean second-order translation difference; Variance is the variance of frame-to-frame translation step length; Failure Rate is `1 - trajectory poses / RGB frames`. Lower is better.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(path: Path, table: List[List[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Method", "Smoothness", "Variance", "Failure Rate"])
        for row in table:
            writer.writerow([cell.replace("**", "") for cell in row])


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    summary = read_summary()
    frame_counts = {seq: count_frames(path) for seq, path in DATASETS.items()}

    raw: Dict[str, Dict[str, float]] = {}
    details: List[Dict[str, str]] = []

    for label, method_key in METHODS:
        smoothness_values: List[float] = []
        variance_values: List[float] = []
        failure_rates: List[float] = []

        for sequence, frame_count in frame_counts.items():
            row = summary.get((sequence, method_key))
            traj_path = trajectory_path(sequence, method_key, row)
            poses = read_trajectory(traj_path) if traj_path else []
            smoothness, variance = trajectory_stats(poses)
            pose_count = len(poses)
            failure_rate = max(0.0, 1.0 - (pose_count / frame_count)) if frame_count else float("nan")

            if not math.isnan(smoothness):
                smoothness_values.append(smoothness)
            if not math.isnan(variance):
                variance_values.append(variance)
            if not math.isnan(failure_rate):
                failure_rates.append(failure_rate)

            details.append(
                {
                    "sequence": sequence,
                    "method": label,
                    "poses": str(pose_count),
                    "frames": str(frame_count),
                    "smoothness": fmt(smoothness),
                    "variance": fmt(variance),
                    "failure_rate": fmt(failure_rate, percent=True),
                    "trajectory": str(traj_path) if traj_path else "",
                }
            )

        raw[label] = {
            "smoothness": mean(smoothness_values) if smoothness_values else float("nan"),
            "variance": mean(variance_values) if variance_values else float("nan"),
            "failure_rate": mean(failure_rates) if failure_rates else float("nan"),
        }

    table = [
        [label, fmt(values["smoothness"]), fmt(values["variance"]), fmt(values["failure_rate"], percent=True)]
        for label, values in raw.items()
    ]
    bold_best(table, raw)
    write_markdown(TABLE_DIR / "table_stability_metrics.md", table)
    write_csv(TABLE_DIR / "table_stability_metrics.csv", table)

    with (OUT_DIR / "stability_metrics_by_sequence.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["sequence", "method", "poses", "frames", "smoothness", "variance", "failure_rate", "trajectory"],
        )
        writer.writeheader()
        writer.writerows(details)

    print(f"Wrote stability metrics to {OUT_DIR}")


if __name__ == "__main__":
    main()
