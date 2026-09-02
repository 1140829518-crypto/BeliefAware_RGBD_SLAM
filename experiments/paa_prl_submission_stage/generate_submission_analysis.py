#!/usr/bin/env python3
"""Generate PAA submission tables and figures from frozen main-run outputs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


REPO = Path(__file__).resolve().parents[2]
CONFIGURATIONS = ("ORB-SLAM2", "Semantic", "Temporal", "Full")
SEQUENCES = (
    "fr3_walking_xyz", "fr3_walking_rpy", "fr3_walking_halfsphere",
    "fr3_sitting_xyz", "fr3_sitting_rpy", "fr3_sitting_halfsphere",
)


def number(value: object) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return math.nan
    return result if math.isfinite(result) else math.nan


def write_csv(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def change_percent(before: float, after: float) -> float:
    return (after - before) / before * 100.0 if math.isfinite(before) and before != 0 else math.nan


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-root", type=Path, default=REPO / "results/paa_prl")
    parser.add_argument("--out", type=Path,
                        default=REPO / "results/paa_prl_submission_stage/main_analysis")
    args = parser.parse_args()
    source_summary = args.main_root / "summary/configuration_sequence_summary.csv"
    source_attempts = args.main_root / "summary/all_attempts.csv"
    with source_summary.open(newline="", encoding="utf-8-sig") as stream:
        summaries = list(csv.DictReader(stream))
    with source_attempts.open(newline="", encoding="utf-8-sig") as stream:
        attempts = list(csv.DictReader(stream))
    selected = [row for row in attempts if row.get("is_selected_attempt") == "1"]
    by_key = {(row["sequence"], row["configuration"]): row for row in summaries}
    out = args.out.resolve()
    figures = out / "figures"
    figures.mkdir(parents=True, exist_ok=True)

    main_headers = ["Sequence", "Configuration", "ATE_mean", "ATE_std",
                    "RPE_translation", "RPE_rotation", "TSR", "PMR", "SF",
                    "Tracking_failure_count", "Tracking_gaps"]
    main_rows = []
    for sequence in SEQUENCES:
        for configuration in CONFIGURATIONS:
            row = by_key[sequence, configuration]
            main_rows.append({
                "Sequence": sequence, "Configuration": configuration,
                "ATE_mean": row["ATE_RMSE_mean"], "ATE_std": row["ATE_RMSE_std"],
                "RPE_translation": row["RPE_translation_RMSE_mean"],
                "RPE_rotation": row["RPE_rotation_RMSE_deg_mean"],
                "TSR": row["TSR_mean"], "PMR": row["PMR_mean"], "SF": row["SF_mean"],
                "Tracking_failure_count": row["n_tracking_failure"],
                "Tracking_gaps": row["tracking_gap_episodes_mean"],
            })
    write_csv(out / "main_results.csv", main_headers, main_rows)

    temporal_headers = ["Sequence", "ATE_change_percent",
                        "RPE_translation_change_percent", "RPE_rotation_change_percent",
                        "SF_reduction_percent", "TSR_change", "PMR_change"]
    temporal_rows = []
    full_headers = ["Sequence", "ATE_change_percent", "SF_change_percent",
                    "TSR_change", "PMR_change", "Failure_change", "classification"]
    full_rows = []
    for sequence in SEQUENCES:
        semantic, temporal = by_key[sequence, "Semantic"], by_key[sequence, "Temporal"]
        temporal_rows.append({
            "Sequence": sequence,
            "ATE_change_percent": change_percent(number(semantic["ATE_RMSE_mean"]), number(temporal["ATE_RMSE_mean"])),
            "RPE_translation_change_percent": change_percent(number(semantic["RPE_translation_RMSE_mean"]), number(temporal["RPE_translation_RMSE_mean"])),
            "RPE_rotation_change_percent": change_percent(number(semantic["RPE_rotation_RMSE_deg_mean"]), number(temporal["RPE_rotation_RMSE_deg_mean"])),
            "SF_reduction_percent": -change_percent(number(semantic["SF_mean"]), number(temporal["SF_mean"])),
            "TSR_change": number(temporal["TSR_mean"]) - number(semantic["TSR_mean"]),
            "PMR_change": number(temporal["PMR_mean"]) - number(semantic["PMR_mean"]),
        })
        full = by_key[sequence, "Full"]
        changes = {
            "ATE_change_percent": change_percent(number(temporal["ATE_RMSE_mean"]), number(full["ATE_RMSE_mean"])),
            "SF_change_percent": change_percent(number(temporal["SF_mean"]), number(full["SF_mean"])),
            "TSR_change": number(full["TSR_mean"]) - number(temporal["TSR_mean"]),
            "PMR_change": number(full["PMR_mean"]) - number(temporal["PMR_mean"]),
            "Failure_change": int(full["n_tracking_failure"]) - int(temporal["n_tracking_failure"]),
        }
        better = [changes["ATE_change_percent"] <= 0, changes["SF_change_percent"] <= 0,
                  changes["TSR_change"] >= 0, changes["PMR_change"] <= 0,
                  changes["Failure_change"] <= 0]
        worse = [changes["ATE_change_percent"] >= 0, changes["SF_change_percent"] >= 0,
                 changes["TSR_change"] <= 0, changes["PMR_change"] >= 0,
                 changes["Failure_change"] >= 0]
        classification = "improved" if all(better) else "degraded" if all(worse) else "scene_dependent"
        full_rows.append({"Sequence": sequence, **changes, "classification": classification})
    write_csv(out / "temporal_contribution.csv", temporal_headers, temporal_rows)
    write_csv(out / "full_module_analysis.csv", full_headers, full_rows)

    labels = [sequence.replace("fr3_", "") for sequence in SEQUENCES]
    semantic_sf = [number(by_key[s, "Semantic"]["SF_mean"]) for s in SEQUENCES]
    temporal_sf = [number(by_key[s, "Temporal"]["SF_mean"]) for s in SEQUENCES]
    x = np.arange(len(SEQUENCES)); width = 0.36
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.bar(x - width / 2, semantic_sf, width, label="Semantic", color="#d95f02")
    ax.bar(x + width / 2, temporal_sf, width, label="Temporal", color="#1b9e77")
    ax.set_ylabel("MapPoint state switching frequency (SF)")
    ax.set_xticks(x, labels, rotation=25, ha="right"); ax.legend(); ax.grid(axis="y", alpha=.25)
    fig.tight_layout(); fig.savefig(figures / "figure1_sf_reduction.png", dpi=300); fig.savefig(figures / "figure1_sf_reduction.pdf"); plt.close(fig)

    colors = {"ORB-SLAM2": "#4c78a8", "Semantic": "#f58518",
              "Temporal": "#54a24b", "Full": "#e45756"}
    fig, ax = plt.subplots(figsize=(8, 5.5))
    for configuration in CONFIGURATIONS:
        group = [row for row in selected if row["configuration"] == configuration]
        xs = [number(row["SF"]) for row in group]
        ys = [number(row["TSR"]) for row in group]
        missing = [not math.isfinite(value) for value in xs]
        plotted_x = [-0.012 if miss else value for value, miss in zip(xs, missing)]
        ax.scatter(plotted_x, ys, s=27, alpha=.7, label=configuration,
                   color=colors[configuration], marker="x" if all(missing) else "o")
    ax.axvline(-0.006, color="gray", linestyle="--", linewidth=.8)
    ax.text(-0.012, 1.02, "SF N/A", ha="center", fontsize=8)
    ax.set_xlabel("MapPoint state switching frequency (SF)"); ax.set_ylabel("TSR")
    ax.set_ylim(-.03, 1.07); ax.grid(alpha=.25); ax.legend(ncol=2)
    fig.tight_layout(); fig.savefig(figures / "figure2_sf_tsr_scatter.png", dpi=300); fig.savefig(figures / "figure2_sf_tsr_scatter.pdf"); plt.close(fig)

    group_rows = []
    for scene, token in (("Walking", "fr3_walking_"), ("Sitting", "fr3_sitting_")):
        for configuration in CONFIGURATIONS:
            group = [row for row in selected if row["configuration"] == configuration and row["sequence"].startswith(token)]
            sf_values = [number(row["SF"]) for row in group if math.isfinite(number(row["SF"]))]
            group_rows.append({"Scene": scene, "Configuration": configuration,
                               "mean_SF": sum(sf_values) / len(sf_values) if sf_values else math.nan,
                               "mean_TSR": sum(number(row["TSR"]) for row in group) / len(group),
                               "failure_rate": sum(int(row["tracking_failure"]) for row in group) / len(group)})
    write_csv(out / "walking_sitting_summary.csv",
              ["Scene", "Configuration", "mean_SF", "mean_TSR", "failure_rate"], group_rows)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))
    metrics = (("mean_SF", "Mean SF"), ("mean_TSR", "Mean TSR"), ("failure_rate", "Failure rate"))
    for ax, (metric, title) in zip(axes, metrics):
        for index, scene in enumerate(("Walking", "Sitting")):
            vals = [number(next(row[metric] for row in group_rows if row["Scene"] == scene and row["Configuration"] == cfg)) for cfg in CONFIGURATIONS]
            positions = np.arange(4) + (index - .5) * .34
            ax.bar(positions, vals, .34, label=scene)
        ax.set_title(title); ax.set_xticks(np.arange(4), CONFIGURATIONS, rotation=25, ha="right"); ax.grid(axis="y", alpha=.25)
    axes[0].legend(); fig.tight_layout(); fig.savefig(figures / "figure3_walking_vs_sitting.png", dpi=300); fig.savefig(figures / "figure3_walking_vs_sitting.pdf"); plt.close(fig)

    metadata = {"generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
                "git_status_short": subprocess.check_output(["git", "status", "--short"], cwd=REPO, text=True),
                "source_summary": str(source_summary), "source_attempts": str(source_attempts),
                "selected_attempts": len(selected), "algorithm_modified": False}
    (out / "analysis_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
