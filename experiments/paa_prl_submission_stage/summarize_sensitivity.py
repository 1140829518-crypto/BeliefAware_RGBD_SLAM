#!/usr/bin/env python3
"""Summarize the two-parameter sensitivity protocol."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from datetime import datetime
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
from paa_prl_common import association_path, trajectory_coverage
from summarize_paa_prl_results import switching_frequency


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path,
                        default=REPO / "results/paa_prl_submission_stage/sensitivity")
    args = parser.parse_args(); root = args.root.resolve()
    grouped = {}
    for path in sorted(root.glob("*/factor_*/run_*/sensitivity_metadata.json")):
        meta = json.loads(path.read_text()); run = path.parent
        status_path = run / "sensitivity_status.json"
        status = json.loads(status_path.read_text()) if status_path.exists() else {"status": "failed"}
        total, valid, gaps, tsr, pmr = trajectory_coverage(association_path(meta["sequence"]), run / "CameraTrajectory.txt")
        metrics_path = run / "eval/metrics.json"
        metrics = json.loads(metrics_path.read_text()) if metrics_path.exists() and valid >= 2 else {}
        _, _, sf = switching_frequency(run / "mappoint_evidence_raw.csv")
        failure = status.get("status") != "success" or (math.isfinite(tsr) and tsr < .90)
        grouped.setdefault((meta["parameter"], float(meta["factor"])), []).append(
            {"ATE": float(metrics["ate"]["rmse"]) if metrics else math.nan,
             "TSR": tsr, "PMR": pmr, "SF": sf, "failure": int(failure)})
    headers = ["parameter", "factor", "ATE_mean", "ATE_std", "TSR", "PMR", "SF", "failure_count"]
    rows = []
    for key, runs in sorted(grouped.items()):
        if len(runs) != 5:
            raise RuntimeError(f"expected 5 preserved runs for {key}, found {len(runs)}")
        def values(metric): return [run[metric] for run in runs if math.isfinite(run[metric])]
        ate = values("ATE")
        rows.append({"parameter": key[0], "factor": key[1],
                     "ATE_mean": statistics.mean(ate) if ate else "",
                     "ATE_std": statistics.stdev(ate) if len(ate) > 1 else 0 if ate else "",
                     "TSR": statistics.mean(values("TSR")), "PMR": statistics.mean(values("PMR")),
                     "SF": statistics.mean(values("SF")) if values("SF") else "",
                     "failure_count": sum(run["failure"] for run in runs)})
    output = root / "sensitivity_summary.csv"
    with output.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers); writer.writeheader(); writer.writerows(rows)
    audit = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "git_commit": json.loads((root / "sensitivity_protocol.json").read_text())["git_commit"],
        "source_root": str(root), "groups": len(rows), "runs_total": sum(len(v) for v in grouped.values()),
        "runs_per_group": 5, "failed_or_low_coverage_runs": sum(r["failure_count"] for r in rows),
        "failure_policy": "process failure or TSR < 0.90", "sample_standard_deviation": True,
    }
    (root / "sensitivity_summary_metadata.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(output)


if __name__ == "__main__":
    main()
