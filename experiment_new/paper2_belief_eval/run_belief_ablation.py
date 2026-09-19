#!/usr/bin/env python3
"""Run and summarize the Paper2 landmark-belief ablation."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from statistics import fmean, stdev

import yaml


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CONFIG_DIR = HERE / "configs"
DEFAULT_OUTPUT = HERE / "output"
RUNNER = ROOT / "scripts/run_tum_rgbd_experiment.py"
METHODS = ("probability_only", "probability_uncertainty", "full_model")
SEQUENCES = {
    "fr3_walking_xyz": {
        "dataset": "/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz",
        "association": str(ROOT / "dataset_associations/fr3_walking_xyz_associate.txt"),
    },
    "fr3_walking_rpy": {
        "dataset": "/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_rpy",
        "association": str(ROOT / "dataset_associations/fr3_walking_rpy_associate.txt"),
    },
    "fr3_walking_halfsphere": {
        "dataset": "/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_halfsphere",
        "association": str(ROOT / "dataset_associations/fr3_walking_halfsphere_associate.txt"),
    },
}
SUMMARY_FIELDS = (
    "method", "sequence", "run_id", "ATE", "RPE", "tracking_loss_count",
    "tracking_success_rate", "pose_validity_rate", "valid_mappoints_mean",
    "optimization_acceptance_rate", "optimization_failure_count",
    "dynamic_point_count", "average_reliability",
    "average_dynamic_probability", "uncertainty_mean", "reliability_std",
    "dynamic_probability_max",
)
AGGREGATE_METRICS = (
    "ATE", "RPE", "tracking_loss_count", "tracking_success_rate",
    "pose_validity_rate", "valid_mappoints_mean",
    "optimization_acceptance_rate", "optimization_failure_count",
    "average_reliability",
    "average_dynamic_probability", "uncertainty_mean", "reliability_std",
    "dynamic_probability_max",
)


def load_config(method: str) -> dict:
    with (CONFIG_DIR / f"{method}.yaml").open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def build_active(build_dir: Path) -> None:
    flags = "-DENABLE_OBJECT_DYNAMIC_SHADOW_MODE=1 -DENABLE_OBJECT_DYNAMIC_ACTIVE_MODE=1"
    subprocess.run(
        ["cmake", "-S", str(ROOT), "-B", str(build_dir),
         f"-DCMAKE_CXX_FLAGS={flags}"], cwd=ROOT, check=True)
    subprocess.run(
        ["cmake", "--build", str(build_dir), "--target", "rgbd_tum", "-j2"],
        cwd=ROOT, check=True)


def experiment_env(config: dict, run_dir: Path) -> dict[str, str]:
    params = config["parameters"]
    env = os.environ.copy()
    env.update({
        "ORB_SLAM2_BELIEF_ENABLED": "1" if params["belief_enabled"] else "0",
        "ORB_SLAM2_BELIEF_GAP_ENABLED": "1" if params["gap_enabled"] else "0",
        "ORB_SLAM2_UNCERTAINTY_ENABLED": "1" if params["uncertainty_enabled"] else "0",
        "ORB_SLAM2_RELIABILITY_ENABLED": "1" if params["reliability_enabled"] else "0",
        "ORB_SLAM2_BELIEF_LOG": str(run_dir / "belief_evolution.csv"),
        "ORB_SLAM2_ABLATION_FRAME_LOG": str(run_dir / "ablation_frames.csv"),
    })
    return env


def run_one(config: dict, sequence: str, run_id: int, output_root: Path, device: str,
            overwrite: bool) -> int:
    method = config["method"]
    sequence_config = SEQUENCES[sequence]
    run_dir = output_root / method / sequence / f"run_{run_id:02d}"
    marker = run_dir / "run_config.json"
    if marker.exists() and not overwrite:
        try:
            if json.loads(marker.read_text(encoding="utf-8")).get("status") == "success":
                print(f"SKIP existing success: {run_dir}", flush=True)
                return 0
        except (OSError, json.JSONDecodeError):
            pass
        raise RuntimeError(f"Refusing to overwrite incomplete result: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable, str(RUNNER), "--sequence", sequence,
        "--method", "full", "--dataset", sequence_config["dataset"],
        "--association", sequence_config["association"], "--settings", config["settings"],
        "--out-dir", str(run_dir), "--device", device,
    ]
    metadata = {
        "method": method, "sequence": sequence, "run_id": f"run_{run_id:02d}",
        "dataset": sequence_config["dataset"],
        "association": sequence_config["association"],
        "settings": config["settings"], "parameters": config["parameters"],
        "command": command, "started_at": datetime.now().astimezone().isoformat(),
        "status": "running",
    }
    marker.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    proc = subprocess.run(command, cwd=ROOT, env=experiment_env(config, run_dir))
    metadata.update({
        "finished_at": datetime.now().astimezone().isoformat(),
        "return_code": proc.returncode,
        "status": "success" if proc.returncode == 0 else "failed",
    })
    marker.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return proc.returncode


def summarize_run(run_dir: Path, method: str, sequence: str) -> dict:
    metrics_path = run_dir / "eval" / "metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    probabilities: list[float] = []
    uncertainties: list[float] = []
    reliabilities: list[float] = []
    dynamic_ids: set[str] = set()
    belief_path = run_dir / "belief_evolution.csv"
    if belief_path.exists():
        with belief_path.open(newline="", encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                # A process interrupted while flushing may leave one partial
                # final CSV record. Preserve the raw log and ignore only that
                # incomplete record during aggregation.
                if not row.get("dynamic_probability") or not row.get("reliability"):
                    continue
                probabilities.append(float(row["dynamic_probability"]))
                uncertainties.append(float(row["uncertainty"]))
                reliabilities.append(float(row["reliability"]))
                if row["status"] == "Dynamic":
                    dynamic_ids.add(row["map_point_id"])
    slam_text = (run_dir / "slam.log").read_text(encoding="utf-8", errors="replace")
    tracking_losses = len(re.findall(r"TRACK(?:ING)?[ _-]*LOST|Track lost", slam_text, re.I))
    frame_rows = []
    with (run_dir / "ablation_frames.csv").open(newline="", encoding="utf-8") as stream:
        frame_rows = list(csv.DictReader(stream))
    if not frame_rows:
        raise ValueError("empty ablation_frames.csv")
    tracking_success = [int(row["tracking_success"]) for row in frame_rows]
    pose_validity = [int(row["pose_validity"]) for row in frame_rows]
    accepted = [int(row["optimization_acceptance"]) for row in frame_rows]
    valid_points = [int(row["valid_mappoints"]) for row in frame_rows
                    if int(row["optimization_acceptance"]) == 1]
    return {
        "method": method,
        "sequence": sequence,
        "run_id": run_dir.name,
        "ATE": metrics["ate"]["rmse"],
        "RPE": metrics["rpe_trans"]["rmse"],
        "tracking_loss_count": tracking_losses,
        "tracking_success_rate": fmean(tracking_success),
        "pose_validity_rate": fmean(pose_validity),
        "valid_mappoints_mean": fmean(valid_points) if valid_points else 0.0,
        "optimization_acceptance_rate": fmean(accepted),
        "optimization_failure_count": accepted.count(0),
        "dynamic_point_count": len(dynamic_ids),
        "average_reliability": fmean(reliabilities) if reliabilities else "",
        "average_dynamic_probability": fmean(probabilities) if probabilities else "",
        "uncertainty_mean": fmean(uncertainties) if uncertainties else "",
        "reliability_std": stdev(reliabilities) if len(reliabilities) > 1 else 0.0,
        "dynamic_probability_max": max(probabilities) if probabilities else "",
    }


def write_summary(output_root: Path) -> Path:
    rows = []
    for method in METHODS:
        for run_config in sorted((output_root / method).glob("*/run_*/run_config.json")):
            metadata = json.loads(run_config.read_text(encoding="utf-8"))
            if metadata.get("status") != "success":
                continue
            run_dir = run_config.parent
            try:
                rows.append(summarize_run(
                    run_dir, method, metadata.get("sequence", run_dir.parent.name)))
            except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
                print(f"WARN cannot summarize {run_dir}: {exc}", file=sys.stderr)
    summary_path = output_root / "summary.csv"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return summary_path


def write_mean_std_summary(output_root: Path, rows: list[dict]) -> Path:
    fields = ["method", "sequence", "run_count"]
    for metric in AGGREGATE_METRICS:
        fields.extend((f"{metric}_mean", f"{metric}_std"))
    aggregate_rows = []
    for method in METHODS:
        for sequence in SEQUENCES:
            group = [row for row in rows
                     if row["method"] == method and row["sequence"] == sequence]
            if not group:
                continue
            aggregate = {"method": method, "sequence": sequence,
                         "run_count": len(group)}
            for metric in AGGREGATE_METRICS:
                values = [float(row[metric]) for row in group if row[metric] != ""]
                aggregate[f"{metric}_mean"] = fmean(values) if values else ""
                aggregate[f"{metric}_std"] = stdev(values) if len(values) > 1 else 0.0
            aggregate_rows.append(aggregate)
    path = output_root / "mean_std_summary.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(aggregate_rows)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--methods", nargs="+", choices=METHODS, default=list(METHODS))
    parser.add_argument("--sequences", nargs="+", choices=tuple(SEQUENCES),
                        default=list(SEQUENCES))
    parser.add_argument("--runs", nargs="+", type=int, default=[1, 2, 3])
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--device", default="0")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--summary-only", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    output_root = args.output_root.resolve()
    if not args.summary_only:
        if not args.skip_build:
            build_active(ROOT / "build_belief_ablation")
        for method in args.methods:
            config = load_config(method)
            for sequence in args.sequences:
                for run_id in args.runs:
                    if run_id not in config["run_ids"]:
                        raise ValueError(f"run {run_id} is not declared by {method}")
                    if run_one(config, sequence, run_id, output_root,
                               args.device, args.overwrite) != 0:
                        raise RuntimeError(
                            f"Experiment failed: {method}/{sequence}/run_{run_id:02d}")
    summary = write_summary(output_root)
    with summary.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    mean_std = write_mean_std_summary(output_root, rows)
    final_fields = [
        "method", "sequence", "run_count",
        "ATE_mean", "ATE_std", "RPE_mean", "RPE_std",
        "tracking_success_rate_mean", "tracking_success_rate_std",
        "valid_mappoints_mean_mean", "valid_mappoints_mean_std",
        "optimization_acceptance_rate_mean", "optimization_acceptance_rate_std",
        "optimization_failure_count_mean", "optimization_failure_count_std",
    ]
    final_path = output_root / "uncertainty_ablation_results.csv"
    with mean_std.open(newline="", encoding="utf-8") as stream:
        aggregate_rows = list(csv.DictReader(stream))
    with final_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=final_fields)
        writer.writeheader()
        for row in aggregate_rows:
            writer.writerow({field: row.get(field, "") for field in final_fields})
    print(f"summary: {summary}")
    print(f"mean/std summary: {mean_std}")
    print(f"paper results: {final_path}")


if __name__ == "__main__":
    main()
