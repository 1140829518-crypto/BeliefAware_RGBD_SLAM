#!/usr/bin/env python3
"""Batch runner for standard TUM RGB-D trajectory evaluation.

The manifest is a CSV with at least:
sequence, method, gt, est, status

Rows with an existing ground-truth and estimate path are evaluated. The script
delegates metric computation and plotting to scripts/evaluate_tum_metrics.py.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List


def safe_name(text: str) -> str:
    keep = []
    for ch in text.lower().replace("+", "plus"):
        if ch.isalnum():
            keep.append(ch)
        elif ch in {" ", "-", "_", "/", "(", ")"}:
            keep.append("_")
    name = "".join(keep).strip("_")
    while "__" in name:
        name = name.replace("__", "_")
    return name or "unknown"


def read_metrics(path: Path) -> Dict[str, float]:
    data = json.loads(path.read_text())
    return {
        "matches": data["matches"],
        "ate_rmse": data["ate"]["rmse"],
        "rpe_trans_rmse": data["rpe_trans"]["rmse"],
        "rpe_rot_rmse_deg": data["rpe_rot_deg"]["rmse"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run standard batch ATE/RPE evaluation.")
    parser.add_argument("--manifest", type=Path, default=Path("evaluation_tables/standard_experiment_manifest.csv"))
    parser.add_argument("--out-root", type=Path, default=Path("standard_eval_results"))
    parser.add_argument("--max-diff", type=float, default=0.02)
    parser.add_argument("--include-candidates", action="store_true", help="Also evaluate candidate_existing rows.")
    parser.add_argument("--summary-csv", type=Path, default=Path("evaluation_tables/standard_eval_summary.csv"))
    args = parser.parse_args()

    repo = Path.cwd()
    eval_script = repo / "scripts" / "evaluate_tum_metrics.py"
    if not eval_script.exists():
        raise FileNotFoundError(eval_script)

    rows: List[Dict[str, str]] = []
    with args.manifest.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append(row)

    summary: List[Dict[str, object]] = []
    for row in rows:
        status = row.get("status", "")
        if status not in {"ready", "candidate_existing"}:
            continue
        if status == "candidate_existing" and not args.include_candidates:
            continue

        gt = repo / row.get("gt", "")
        est = repo / row.get("est", "")
        if not gt.exists() or not est.exists():
            summary.append({**row, "eval_status": "missing_file"})
            continue

        out_dir = args.out_root / safe_name(row["sequence"]) / safe_name(row["method"])
        title = f"{row['sequence']} - {row['method']}"
        cmd = [
            sys.executable,
            str(eval_script),
            "--gt",
            str(gt),
            "--est",
            str(est),
            "--out-dir",
            str(out_dir),
            "--max-diff",
            str(args.max_diff),
            "--title",
            title,
        ]
        print("Running:", " ".join(cmd))
        subprocess.run(cmd, check=True)
        metrics = read_metrics(out_dir / "metrics.json")
        summary.append({**row, **metrics, "eval_status": "ok", "out_dir": str(out_dir)})

    args.summary_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "sequence",
        "category",
        "method",
        "variant",
        "status",
        "eval_status",
        "matches",
        "ate_rmse",
        "rpe_trans_rmse",
        "rpe_rot_rmse_deg",
        "out_dir",
        "notes",
    ]
    with args.summary_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(summary)

    print(f"Wrote summary: {args.summary_csv}")


if __name__ == "__main__":
    main()
