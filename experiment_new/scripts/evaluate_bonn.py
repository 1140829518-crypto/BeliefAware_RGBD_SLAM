#!/usr/bin/env python3
"""Evaluate and summarize Bonn RGB-D Dynamic Dataset runs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiment_new"
RESULT_DIR = EXP / "results"
TABLE_DIR = EXP / "tables"
RUN_ROOT = RESULT_DIR / "bonn_runs"
EVAL_SCRIPT = ROOT / "scripts/evaluate_tum_metrics.py"
os.environ.setdefault("MPLCONFIGDIR", str(EXP / ".matplotlib_cache"))

METHODS = ["ORB-SLAM3", "DS-SLAM", "Dyna-SLAM", "Ours"]


def safe_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def read_manifest(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def count_frames(sequence_dir: Path) -> int:
    rgb_txt = sequence_dir / "rgb.txt"
    if rgb_txt.exists():
        return sum(1 for line in rgb_txt.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip() and not line.startswith("#"))
    return len(list((sequence_dir / "rgb").glob("*.png")))


def runtime_fps(run_dir: Path, sequence_dir: Path) -> float:
    runtime_path = run_dir / "runtime.txt"
    if runtime_path.exists():
        values: Dict[str, str] = {}
        for line in runtime_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            parts = line.split()
            if len(parts) >= 2:
                values[parts[0]] = parts[1]
        if "fps" in values:
            return safe_float(values["fps"])
        if "mean_tracking_time" in values:
            mean_time = safe_float(values["mean_tracking_time"])
            return 1.0 / mean_time if mean_time > 0 else float("nan")
        if "wall_time" in values:
            elapsed = safe_float(values["wall_time"])
            frames = count_frames(sequence_dir)
            return frames / elapsed if elapsed > 0 else float("nan")
    for log_name in ["slam.log", "run.log"]:
        log_path = run_dir / log_name
        if not log_path.exists():
            continue
        text = log_path.read_text(encoding="utf-8", errors="ignore")
        match = re.search(r"mean tracking time:\s*([0-9.eE+-]+)", text)
        if match:
            mean_time = safe_float(match.group(1))
            return 1.0 / mean_time if mean_time > 0 else float("nan")
    return float("nan")


def evaluate_run(sequence: str, method: str, sequence_dir: Path, run_dir: Path) -> Dict[str, object]:
    metrics_path = run_dir / "eval/metrics.json"
    trajectory = run_dir / "CameraTrajectory.txt"
    gt = sequence_dir / "groundtruth.txt"
    status = "ok"

    if not trajectory.exists():
        status = "missing_trajectory"
    elif not gt.exists():
        status = "missing_groundtruth"
    elif not metrics_path.exists():
        try:
            env = os.environ.copy()
            env.setdefault("MPLCONFIGDIR", str(EXP / ".matplotlib_cache"))
            subprocess.run(
                [
                    sys.executable,
                    str(EVAL_SCRIPT),
                    "--gt",
                    str(gt),
                    "--est",
                    str(trajectory),
                    "--out-dir",
                    str(run_dir / "eval"),
                    "--title",
                    f"Bonn {sequence} {method}",
                ],
                cwd=ROOT,
                env=env,
                check=True,
            )
        except Exception as exc:  # keep table generation resumable
            status = f"eval_failed:{exc}"

    ate = rpe = float("nan")
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        ate = safe_float(metrics.get("ate", {}).get("rmse"))
        rpe = safe_float(metrics.get("rpe_trans", {}).get("rmse"))

    fps = runtime_fps(run_dir, sequence_dir)
    return {
        "Dataset": sequence,
        "Method": method,
        "ATE": ate,
        "RPE": rpe,
        "FPS": fps,
        "Status": status,
    }


def fmt(value: object) -> str:
    if isinstance(value, float):
        return "--" if math.isnan(value) else f"{value:.6f}"
    return str(value)


def write_csv(path: Path, rows: Sequence[Dict[str, object]], include_status: bool) -> None:
    fields = ["Dataset", "Method", "ATE", "RPE", "FPS"]
    if include_status:
        fields.append("Status")
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: fmt(row[field]) for field in fields})


def write_latex(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    lines = [
        "\\begin{table}[t]",
        "\\centering",
        "\\caption{Bonn RGB-D Dynamic Dataset comparison.}",
        "\\label{tab:bonn_dynamic_comparison}",
        "\\begin{tabular}{lrrr}",
        "\\toprule",
        "Method & ATE(m) & RPE(m) & FPS \\\\",
        "\\midrule",
    ]
    grouped: Dict[str, List[Dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault(str(row["Dataset"]), []).append(row)
    for dataset, items in grouped.items():
        lines.append(f"\\multicolumn{{4}}{{l}}{{\\textit{{{dataset}}}}} \\\\")
        for row in items:
            lines.append(f"{row['Method']} & {fmt(row['ATE'])} & {fmt(row['RPE'])} & {fmt(row['FPS'])} \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def summarize(manifest_path: Path, run_root: Path) -> List[Dict[str, object]]:
    manifest = read_manifest(manifest_path)
    rows: List[Dict[str, object]] = []
    for item in manifest:
        sequence = item["Dataset"]
        sequence_dir = Path(item["Path"])
        for method in METHODS:
            rows.append(evaluate_run(sequence, method, sequence_dir, run_root / sequence / method.lower().replace("-", "_").replace(" ", "_")))
    if not rows:
        for sequence in ["person_tracking", "synchronous", "crowd"]:
            for method in METHODS:
                rows.append({"Dataset": sequence, "Method": method, "ATE": float("nan"), "RPE": float("nan"), "FPS": float("nan"), "Status": "pending_dataset"})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Bonn dynamic runs and generate CSV/LaTeX table.")
    parser.add_argument("--manifest", type=Path, default=RESULT_DIR / "bonn_selected_sequences.csv")
    parser.add_argument("--run-root", type=Path, default=RUN_ROOT)
    args = parser.parse_args()

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    rows = summarize(args.manifest, args.run_root)
    write_csv(RESULT_DIR / "bonn_dynamic_comparison.csv", rows, include_status=False)
    write_csv(RESULT_DIR / "bonn_dynamic_comparison_status.csv", rows, include_status=True)
    write_latex(TABLE_DIR / "table_bonn_dynamic_comparison.tex", rows)
    print(f"Saved {RESULT_DIR / 'bonn_dynamic_comparison.csv'}")
    print(f"Saved {TABLE_DIR / 'table_bonn_dynamic_comparison.tex'}")


if __name__ == "__main__":
    main()
