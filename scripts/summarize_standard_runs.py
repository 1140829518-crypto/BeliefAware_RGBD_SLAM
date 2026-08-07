#!/usr/bin/env python3
"""Summarize completed standard experiment runs into paper tables."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


METHOD_DIRS = {
    "orb_slam2": "ORB-SLAM2",
    "hard_remove": "Hard Remove",
    "dynamic_score": "Dynamic Score",
    "full_method": "Full Method",
}

METHOD_ORDER = ["ORB-SLAM2", "Hard Remove", "Dynamic Score", "Full Method"]
SEQUENCE_ORDER = [
    "fr3_walking_xyz",
    "fr3_walking_rpy",
    "fr3_walking_halfsphere",
    "fr3_walking_static",
    "fr1_xyz",
    "fr1_desk",
]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_runtime(path: Path) -> Dict[str, float]:
    values: Dict[str, float] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2:
            try:
                values[parts[0]] = float(parts[1])
            except ValueError:
                pass
    return values


def metric_row(sequence: str, method: str, run_dir: Path, source: str) -> Dict[str, object]:
    metrics = read_json(run_dir / "eval" / "metrics.json")
    runtime = read_runtime(run_dir / "runtime.txt")
    return {
        "sequence": sequence,
        "method": method,
        "source": source,
        "matches": metrics.get("matches", ""),
        "ate_rmse": metrics["ate"]["rmse"],
        "rpe_trans_rmse": metrics["rpe_trans"]["rmse"],
        "rpe_rot_rmse_deg": metrics["rpe_rot_deg"]["rmse"],
        "mean_tracking_time": runtime.get("mean_tracking_time", ""),
        "median_tracking_time": runtime.get("median_tracking_time", ""),
        "fps": runtime.get("fps", ""),
        "run_dir": str(run_dir),
    }


def load_existing_summary(path: Path) -> Iterable[Dict[str, object]]:
    if not path.exists():
        return []
    rows: List[Dict[str, object]] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row.get("eval_status") != "ok":
                continue
            rows.append(
                {
                    "sequence": row["sequence"],
                    "method": row["method"],
                    "source": "manifest",
                    "matches": row.get("matches", ""),
                    "ate_rmse": row.get("ate_rmse", ""),
                    "rpe_trans_rmse": row.get("rpe_trans_rmse", ""),
                    "rpe_rot_rmse_deg": row.get("rpe_rot_rmse_deg", ""),
                    "mean_tracking_time": "",
                    "median_tracking_time": "",
                    "fps": "",
                    "run_dir": row.get("out_dir", ""),
                }
            )
    return rows


def load_standard_runs(root: Path) -> Iterable[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    if not root.exists():
        return rows
    for sequence_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for method_dir_name, method in METHOD_DIRS.items():
            run_dir = sequence_dir / method_dir_name
            if (run_dir / "eval" / "metrics.json").exists():
                rows.append(metric_row(sequence_dir.name, method, run_dir, "standard_runs"))
    return rows


def sort_key(row: Dict[str, object]) -> Tuple[int, int]:
    sequence = str(row["sequence"])
    method = str(row["method"])
    seq_idx = SEQUENCE_ORDER.index(sequence) if sequence in SEQUENCE_ORDER else len(SEQUENCE_ORDER)
    method_idx = METHOD_ORDER.index(method) if method in METHOD_ORDER else len(METHOD_ORDER)
    return seq_idx, method_idx


def fmt(value: object) -> str:
    if value == "":
        return ""
    try:
        return f"{float(value):.6f}"
    except (TypeError, ValueError):
        return str(value)


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    fieldnames = [
        "sequence",
        "method",
        "source",
        "matches",
        "ate_rmse",
        "rpe_trans_rmse",
        "rpe_rot_rmse_deg",
        "mean_tracking_time",
        "median_tracking_time",
        "fps",
        "run_dir",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_metric_table(path: Path, rows: List[Dict[str, object]], metric: str, title: str) -> None:
    by_key = {(str(row["sequence"]), str(row["method"])): row for row in rows}
    lines = [
        f"# {title}",
        "",
        "| Sequence | ORB-SLAM2 | Hard Remove | Dynamic Score | Full Method |",
        "|---|---:|---:|---:|---:|",
    ]
    for sequence in SEQUENCE_ORDER:
        vals = []
        for method in METHOD_ORDER:
            row = by_key.get((sequence, method))
            vals.append(fmt(row.get(metric, "")) if row else "")
        lines.append(f"| {sequence} | " + " | ".join(vals) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_runtime_table(path: Path, rows: List[Dict[str, object]]) -> None:
    by_key = {(str(row["sequence"]), str(row["method"])): row for row in rows}
    lines = [
        "# Runtime / FPS",
        "",
        "| Sequence | Method | Mean tracking time (s) | FPS |",
        "|---|---|---:|---:|",
    ]
    for sequence in SEQUENCE_ORDER:
        for method in METHOD_ORDER:
            row = by_key.get((sequence, method))
            if not row:
                continue
            lines.append(
                f"| {sequence} | {method} | {fmt(row.get('mean_tracking_time', ''))} | {fmt(row.get('fps', ''))} |"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize completed standard_runs metrics.")
    parser.add_argument("--runs-root", type=Path, default=Path("standard_runs"))
    parser.add_argument("--existing-summary", type=Path, default=Path("evaluation_tables/standard_eval_summary.csv"))
    parser.add_argument("--out-csv", type=Path, default=Path("evaluation_tables/standard_runs_summary.csv"))
    parser.add_argument("--out-dir", type=Path, default=Path("evaluation_tables"))
    args = parser.parse_args()

    merged: Dict[Tuple[str, str], Dict[str, object]] = {}
    for row in load_existing_summary(args.existing_summary):
        merged[(str(row["sequence"]), str(row["method"]))] = row
    for row in load_standard_runs(args.runs_root):
        merged[(str(row["sequence"]), str(row["method"]))] = row

    rows = sorted(merged.values(), key=sort_key)
    write_csv(args.out_csv, rows)
    write_metric_table(args.out_dir / "standard_runs_table_ate_rmse.md", rows, "ate_rmse", "ATE RMSE")
    write_metric_table(args.out_dir / "standard_runs_table_rpe_trans_rmse.md", rows, "rpe_trans_rmse", "RPE-trans RMSE")
    write_metric_table(args.out_dir / "standard_runs_table_rpe_rot_rmse.md", rows, "rpe_rot_rmse_deg", "RPE-rot RMSE (deg)")
    write_runtime_table(args.out_dir / "standard_runs_table_runtime_fps.md", rows)
    print(f"Wrote {args.out_csv}")


if __name__ == "__main__":
    main()
