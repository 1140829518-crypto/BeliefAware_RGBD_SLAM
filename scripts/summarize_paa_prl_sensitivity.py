#!/usr/bin/env python3
"""Summarize sensitivity cases as ATE, TSR, PMR, and SF."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

from paa_prl_common import REPO, association_path, sample_mean_std, trajectory_coverage
from summarize_paa_prl_results import switching_frequency


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=REPO / "results/paa_prl_sensitivity")
    args = parser.parse_args()
    root = args.root.resolve()
    groups: dict[tuple[str, float], list[dict[str, float]]] = defaultdict(list)
    for metadata_path in sorted(root.glob("*/factor_*/run_*/sensitivity_metadata.json")):
        metadata = json.loads(metadata_path.read_text())
        case = metadata_path.parent
        metrics_path = case / "eval/metrics.json"
        if not metrics_path.exists():
            continue
        metrics = json.loads(metrics_path.read_text())
        _, _, gaps, tsr, pmr = trajectory_coverage(
            association_path(metadata["sequence"]), case / "CameraTrajectory.txt")
        _, _, sf = switching_frequency(case / "mappoint_evidence_raw.csv")
        groups[(metadata["parameter"], float(metadata["factor"]))].append({
            "ATE": float(metrics["ate"]["rmse"]), "TSR": tsr, "PMR": pmr,
            "SF": sf, "tracking_gaps": float(gaps),
        })
    rows = []
    for (parameter, factor), runs in sorted(groups.items()):
        row: dict[str, object] = {"parameter": parameter, "factor": factor,
                                  "n_runs": len(runs)}
        for metric in ("ATE", "TSR", "PMR", "SF", "tracking_gaps"):
            mean, std = sample_mean_std(run[metric] for run in runs)
            row[f"{metric}_mean"] = mean
            row[f"{metric}_std"] = std
        rows.append(row)
    output = root / "summary/sensitivity_summary.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    headers = (["parameter", "factor", "n_runs"] +
               [f"{metric}_{suffix}" for metric in
                ("ATE", "TSR", "PMR", "SF", "tracking_gaps") for suffix in ("mean", "std")])
    with output.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: ("" if isinstance(value, float) and not math.isfinite(value)
                                   else value) for key, value in row.items()})
    print(f"cases summarized: {len(rows)}; {output}")


if __name__ == "__main__":
    main()
