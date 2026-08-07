#!/usr/bin/env python3
"""Build per-sequence diagnostics table for baseline/method runs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple


SEQUENCES = [
    ("fr1_xyz", "fr1_xyz"),
    ("fr1_desk", "fr1_desk"),
    ("fr3_walking_xyz", "fr3_xyz"),
    ("fr3_walking_rpy", "fr3_rpy"),
    ("fr3_walking_halfsphere", "fr3_halfsphere"),
    ("fr3_walking_static", "fr3_static"),
]

ASSOCIATIONS = {
    "fr1_xyz": Path("dataset_associations/fr1_xyz_associate.txt"),
    "fr1_desk": Path("dataset_associations/fr1_desk_associate.txt"),
    "fr3_walking_xyz": Path("dataset_associations/fr3_walking_xyz_associate.txt"),
    "fr3_walking_rpy": Path("dataset_associations/fr3_walking_rpy_associate.txt"),
    "fr3_walking_halfsphere": Path("dataset_associations/fr3_walking_halfsphere_associate.txt"),
    "fr3_walking_static": Path("dataset_associations/fr3_walking_static_associate.txt"),
}

METHOD_RUNS = {
    "ORB-SLAM2": {
        seq: Path("standard_runs") / seq / "orb_slam2" for seq, _ in SEQUENCES
    },
    "ORB-SLAM3": {
        seq: Path("orbslam3_runs_missing") / seq for seq, _ in SEQUENCES
    },
    "DS-SLAM": {
        seq: Path("baseline_runs_missing/ds_slam") / seq for seq, _ in SEQUENCES
    },
    "Dyna-SLAM": {
        "fr1_xyz": Path("baseline_runs_missing/dyna_slam/fr1_xyz"),
        "fr1_desk": Path("baseline_runs_retry3_patched/dyna_slam/fr1_desk"),
        "fr3_walking_xyz": Path("baseline_runs_missing/dyna_slam/fr3_walking_xyz"),
        "fr3_walking_rpy": Path("baseline_runs_missing/dyna_slam/fr3_walking_rpy"),
        "fr3_walking_halfsphere": Path("baseline_runs_missing/dyna_slam/fr3_walking_halfsphere"),
        "fr3_walking_static": Path("baseline_runs_missing/dyna_slam/fr3_walking_static"),
    },
    "Hard Remove": {
        seq: Path("standard_runs") / seq / "hard_remove" for seq, _ in SEQUENCES
    },
    "Ours": {
        seq: Path("standard_runs") / seq / "full_method" for seq, _ in SEQUENCES
    },
}


def count_data_lines(path: Path) -> Optional[int]:
    if not path.exists():
        return None
    count = 0
    with path.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                count += 1
    return count


def read_runtime_ms(path: Path) -> Optional[float]:
    runtime = path / "runtime.txt"
    if not runtime.exists():
        return None
    values: Dict[str, float] = {}
    for line in runtime.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.split()
        if len(parts) == 2:
            try:
                values[parts[0]] = float(parts[1])
            except ValueError:
                pass
    if "mean_tracking_time" in values:
        return values["mean_tracking_time"] * 1000.0
    if "fps" in values and values["fps"] > 0:
        return 1000.0 / values["fps"]
    if "wall_time" in values and "frames" in values and values["frames"] > 0:
        return values["wall_time"] * 1000.0 / values["frames"]
    return None


def read_matches(path: Path) -> Optional[int]:
    metrics = path / "eval" / "metrics.json"
    if not metrics.exists():
        return None
    try:
        return int(json.loads(metrics.read_text(encoding="utf-8"))["matches"])
    except (KeyError, ValueError, json.JSONDecodeError):
        return None


def read_avg_dynamic_keypoints(path: Path) -> Optional[float]:
    stats = path / "SemanticDynamicStatistics.txt"
    if not stats.exists():
        return None
    by_frame: Dict[str, List[float]] = {}
    with stats.open(encoding="utf-8", errors="ignore") as f:
        header = f.readline().split()
        if "dynamic_keypoints" not in header:
            return None
        idx_frame = header.index("frame_id")
        idx_dyn = header.index("dynamic_keypoints")
        for line in f:
            parts = line.split()
            if len(parts) <= max(idx_frame, idx_dyn):
                continue
            try:
                by_frame.setdefault(parts[idx_frame], []).append(float(parts[idx_dyn]))
            except ValueError:
                continue
    if not by_frame:
        return None
    per_frame = [sum(vals) / len(vals) for vals in by_frame.values()]
    return sum(per_frame) / len(per_frame)


def count_semantic_objects(path: Path) -> Optional[int]:
    objects = path / "SemanticObjects.txt"
    return count_data_lines(objects)


def fmt_num(value: Optional[float], digits: int = 2) -> str:
    if value is None:
        return "--"
    return f"{value:.{digits}f}"


def fmt_int(value: Optional[int]) -> str:
    if value is None:
        return "--"
    return str(value)


def build_rows() -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for method, run_map in METHOD_RUNS.items():
        for seq, seq_label in SEQUENCES:
            run_dir = run_map[seq]
            input_frames = count_data_lines(ASSOCIATIONS[seq])
            keyframes = count_data_lines(run_dir / "KeyFrameTrajectory.txt")
            mean_time_ms = read_runtime_ms(run_dir)
            avg_dynamic = read_avg_dynamic_keypoints(run_dir)
            semantic_objects = count_semantic_objects(run_dir)
            matches = read_matches(run_dir)
            completeness = None
            if input_frames and matches is not None:
                completeness = 100.0 * matches / input_frames
            rows.append(
                {
                    "method": method,
                    "sequence": seq_label,
                    "input_frames": input_frames,
                    "keyframes": keyframes,
                    "mean_tracking_time_ms": mean_time_ms,
                    "avg_dynamic_points": avg_dynamic,
                    "semantic_objects": semantic_objects,
                    "trajectory_completeness_percent": completeness,
                    "run_dir": str(run_dir),
                }
            )
    return rows


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "method",
        "sequence",
        "input_frames",
        "keyframes",
        "mean_tracking_time_ms",
        "avg_dynamic_points",
        "semantic_objects",
        "trajectory_completeness_percent",
        "run_dir",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_md(path: Path, rows: List[Dict[str, object]]) -> None:
    lines = [
        "# Sequence Diagnostics",
        "",
        "| Method | Sequence | 输入帧数 | 关键帧数 | 平均跟踪时间 (ms) | 平均动态点数 | 语义对象数 | 轨迹完整率 (%) |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {method} | {sequence} | {input_frames} | {keyframes} | {time_ms} | {dynamic} | {objects} | {complete} |".format(
                method=row["method"],
                sequence=row["sequence"],
                input_frames=fmt_int(row["input_frames"]),
                keyframes=fmt_int(row["keyframes"]),
                time_ms=fmt_num(row["mean_tracking_time_ms"]),
                dynamic=fmt_num(row["avg_dynamic_points"]),
                objects=fmt_int(row["semantic_objects"]),
                complete=fmt_num(row["trajectory_completeness_percent"]),
            )
        )
    lines.extend(
        [
            "",
            "Notes:",
            "",
            "- `平均动态点数` uses the per-frame average of `dynamic_keypoints` when `SemanticDynamicStatistics.txt` is available.",
            "- `语义对象数` counts rows in `SemanticObjects.txt`; `--` means that method did not export object-level semantic map data.",
            "- `轨迹完整率` is `timestamp matches / input frames * 100` using each run's `eval/metrics.json`.",
            "- Dyna-SLAM has no valid local trajectory for `fr3_xyz` and `fr3_halfsphere`, so those fields remain `--`.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rows = build_rows()
    write_csv(Path("evaluation_tables/sequence_diagnostics.csv"), rows)
    write_md(Path("evaluation_tables/sequence_diagnostics.md"), rows)
    print("Wrote evaluation_tables/sequence_diagnostics.csv")
    print("Wrote evaluation_tables/sequence_diagnostics.md")


if __name__ == "__main__":
    main()
