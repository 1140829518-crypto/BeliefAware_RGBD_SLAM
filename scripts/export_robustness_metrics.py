#!/usr/bin/env python3
"""Export tracking robustness metrics for paper tables.

Metrics:
- Tracking Success Rate: trajectory poses / dataset RGB frames.
- Trajectory Drift: ATE RMSE from the existing evaluation summary.
- Relocalization Robustness: recovered lost segments / lost segments.

A lost segment is a consecutive RGB-frame interval without a nearby trajectory
timestamp. A segment is counted as recovered when tracking resumes after it.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from statistics import mean
from typing import Dict, List, Optional, Tuple


OUT_DIR = Path("paper_ready_outputs_v10")
TABLE_DIR = OUT_DIR / "tables"
SUMMARY_PATH = Path("paper_ready_outputs_v7/summary_completed_baselines.csv")
TIMESTAMP_TOLERANCE = 0.04

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


def read_rgb_timestamps(path: Path) -> List[float]:
    timestamps: List[float] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            timestamps.append(float(line.split()[0]))
        except (IndexError, ValueError):
            continue
    return timestamps


def read_trajectory_timestamps(path: Optional[Path]) -> List[float]:
    if not path or not path.exists():
        return []
    timestamps: List[float] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            timestamps.append(float(line.split()[0]))
        except (IndexError, ValueError):
            continue
    return sorted(timestamps)


def read_summary() -> Dict[Tuple[str, str], Dict[str, str]]:
    rows: Dict[Tuple[str, str], Dict[str, str]] = {}
    with SUMMARY_PATH.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows[(row["sequence"], row["method"])] = row
    return rows


def trajectory_path(sequence: str, method_key: str, row: Optional[Dict[str, str]]) -> Optional[Path]:
    if method_key == "ORB-SLAM3":
        return ORB_SLAM3_TRAJECTORIES.get(sequence)
    if row:
        return Path(row["run_dir"]) / "CameraTrajectory.txt"
    return None


def tracked_mask(rgb_times: List[float], traj_times: List[float]) -> List[bool]:
    if not traj_times:
        return [False] * len(rgb_times)
    mask: List[bool] = []
    j = 0
    for rgb_t in rgb_times:
        while j + 1 < len(traj_times) and abs(traj_times[j + 1] - rgb_t) <= abs(traj_times[j] - rgb_t):
            j += 1
        mask.append(abs(traj_times[j] - rgb_t) <= TIMESTAMP_TOLERANCE)
    return mask


def lost_segment_stats(mask: List[bool]) -> Tuple[int, int]:
    lost_segments = 0
    recovered_segments = 0
    i = 0
    while i < len(mask):
        if mask[i]:
            i += 1
            continue
        start = i
        while i < len(mask) and not mask[i]:
            i += 1
        end = i - 1
        lost_segments += 1
        if start > 0 and end < len(mask) - 1 and mask[start - 1] and mask[end + 1]:
            recovered_segments += 1
    return lost_segments, recovered_segments


def as_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def fmt(value: float, percent: bool = False) -> str:
    if math.isnan(value):
        return "--"
    if percent:
        return f"{100.0 * value:.2f}%"
    return f"{value:.6f}"


def bold_best(table: List[List[str]], raw: Dict[str, Dict[str, float]]) -> None:
    specs = [
        (1, "success_rate", max),
        (2, "drift", min),
        (3, "relocalization_robustness", max),
    ]
    for col, metric, selector in specs:
        candidates = [(method, values[metric]) for method, values in raw.items() if not math.isnan(values[metric])]
        if not candidates:
            continue
        best, _ = selector(candidates, key=lambda item: item[1])
        for row in table:
            if row[0] == best and row[col] != "--":
                row[col] = f"**{row[col]}**"


def write_markdown(path: Path, table: List[List[str]]) -> None:
    lines = [
        "# Robustness Metrics",
        "",
        "| Method | Tracking Success Rate ↑ | Trajectory Drift / ATE RMSE ↓ | Relocalization Robustness ↑ |",
        "|---|---:|---:|---:|",
    ]
    for row in table:
        lines.append("| " + " | ".join(row) + " |")
    lines.extend(
        [
            "",
            f"Note: Tracking Success Rate is trajectory poses / RGB frames. Trajectory Drift uses ATE RMSE from `{SUMMARY_PATH}`. Relocalization Robustness is recovered lost segments / lost segments after timestamp alignment with {TIMESTAMP_TOLERANCE:.2f}s tolerance. For sequences without a local trajectory, success and relocalization are counted as 0.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(path: Path, table: List[List[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Method", "Tracking Success Rate", "Trajectory Drift ATE RMSE", "Relocalization Robustness"])
        for row in table:
            writer.writerow([cell.replace("**", "") for cell in row])


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    summary = read_summary()
    rgb_times = {sequence: read_rgb_timestamps(path) for sequence, path in DATASETS.items()}

    raw: Dict[str, Dict[str, float]] = {}
    details: List[Dict[str, str]] = []

    for label, method_key in METHODS:
        success_rates: List[float] = []
        drifts: List[float] = []
        robustness_values: List[float] = []

        for sequence, times in rgb_times.items():
            row = summary.get((sequence, method_key))
            traj_path = trajectory_path(sequence, method_key, row)
            traj_times = read_trajectory_timestamps(traj_path)
            mask = tracked_mask(times, traj_times)
            lost_segments, recovered_segments = lost_segment_stats(mask)

            frame_count = len(times)
            pose_count = len(traj_times)
            success_rate = (pose_count / frame_count) if frame_count else float("nan")
            if not math.isnan(success_rate):
                success_rate = min(success_rate, 1.0)
                success_rates.append(success_rate)

            drift = as_float(row["ate_rmse"]) if row else float("nan")
            if not math.isnan(drift):
                drifts.append(drift)

            if lost_segments == 0:
                robustness = 1.0
            else:
                robustness = recovered_segments / lost_segments
            robustness_values.append(robustness)

            details.append(
                {
                    "sequence": sequence,
                    "method": label,
                    "frames": str(frame_count),
                    "poses": str(pose_count),
                    "tracking_success_rate": fmt(success_rate, percent=True),
                    "trajectory_drift_ate_rmse": fmt(drift),
                    "lost_segments": str(lost_segments),
                    "recovered_segments": str(recovered_segments),
                    "relocalization_robustness": fmt(robustness, percent=True),
                    "trajectory": str(traj_path) if traj_path else "",
                }
            )

        raw[label] = {
            "success_rate": mean(success_rates) if success_rates else float("nan"),
            "drift": mean(drifts) if drifts else float("nan"),
            "relocalization_robustness": mean(robustness_values) if robustness_values else float("nan"),
        }

    table = [
        [
            label,
            fmt(values["success_rate"], percent=True),
            fmt(values["drift"]),
            fmt(values["relocalization_robustness"], percent=True),
        ]
        for label, values in raw.items()
    ]
    bold_best(table, raw)
    write_markdown(TABLE_DIR / "table_robustness_metrics.md", table)
    write_csv(TABLE_DIR / "table_robustness_metrics.csv", table)

    with (OUT_DIR / "robustness_metrics_by_sequence.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "sequence",
                "method",
                "frames",
                "poses",
                "tracking_success_rate",
                "trajectory_drift_ate_rmse",
                "lost_segments",
                "recovered_segments",
                "relocalization_robustness",
                "trajectory",
            ],
        )
        writer.writeheader()
        writer.writerows(details)

    print(f"Wrote robustness metrics to {OUT_DIR}")


if __name__ == "__main__":
    main()
