#!/usr/bin/env python3
"""Aggregate frozen final internal baselines without running SLAM."""

from __future__ import annotations

import bisect
import csv
import hashlib
import json
import math
import re
import statistics
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "experiment_new/paper2_belief_eval/output/final_internal_baseline_benchmark"
TUM_V4 = REPO / "experiment_new/paper2_belief_eval/output/tum_v4_geometry_protected"
BONN_V4 = REPO / "experiment_new/paper2_belief_eval/output/bonn_v4_geometry_protected"
DS = REPO / "results/paa_prl_strengthening/dsslam_repeated/dsslam_all_runs.csv"
EXPECTED = {
    "rgbd_tum": "0079490eaf05c513ce18b5de95f66e54c98ba30e47511d17bd5a26ae4fcbddc9",
    "libORB_SLAM2.so": "85a1ec7d6c2786ad2fd2497ce0de2710c725a693ebd6b4d46c3bea63628c8687",
    "evaluate_tum_metrics.py": "cfdd35d556afcd5d080fe109396f5ffa7da1810a5e2c26a656c648216db24b13",
}
SEQUENCES = (
    "fr3_walking_xyz", "fr3_walking_static", "fr3_walking_rpy",
    "rgbd_bonn_person_tracking", "rgbd_bonn_synchronous", "rgbd_bonn_crowd",
)
DISPLAY = {
    "fr3_walking_xyz": "TUM xyz", "fr3_walking_static": "TUM static",
    "fr3_walking_rpy": "TUM rpy", "rgbd_bonn_person_tracking": "Bonn person_tracking",
    "rgbd_bonn_synchronous": "Bonn synchronous", "rgbd_bonn_crowd": "Bonn crowd",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def read_csv(path: Path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows):
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)


def mean(v): return statistics.fmean(v) if v else math.nan
def std(v): return statistics.stdev(v) if len(v) > 1 else (0.0 if len(v) == 1 else math.nan)


def association_path(sequence: str) -> Path:
    if sequence.startswith("fr3_"):
        return REPO / "dataset_associations" / f"{sequence}_associate.txt"
    return REPO / "experiment_new/dataset/bonn_rgbd_dynamic" / sequence / "associate.txt"


def stamps(path: Path):
    return [float(x.split()[0]) for x in path.read_text().splitlines() if x.strip() and not x.startswith("#")]


def trajectory_stamps(path: Path):
    return sorted(float(x.split()[0]) for x in path.read_text().splitlines() if x.strip() and not x.startswith("#"))


def coverage(association, trajectory):
    mask = []
    for t in association:
        i = bisect.bisect_left(trajectory, t)
        distance = min((abs(trajectory[j] - t) for j in (i - 1, i) if 0 <= j < len(trajectory)), default=math.inf)
        mask.append(distance <= 0.02)
    gaps = 0; inside = False; tracked = lost = max_tracked = max_lost = 0
    for ok in mask:
        if ok:
            tracked += 1; lost = 0; inside = False; max_tracked = max(max_tracked, tracked)
        else:
            lost += 1; tracked = 0; max_lost = max(max_lost, lost)
            if not inside: gaps += 1; inside = True
    return sum(mask) / len(mask), gaps, max_tracked, max_lost, sum(mask)


def aggregate(rows, method, sequence, attempts, total_execution_attempts=None, infrastructure_failed_attempts=0):
    metrics = ("ATE_RMSE", "RPE_translation", "RPE_rotation_deg", "TSR", "PMR",
               "gaps", "longest_tracked_segment", "longest_lost_segment",
               "initial_correspondences", "final_inliers", "optimization_acceptance",
               "trajectory_length", "valid_pose_count")
    out = {"Method": method, "Sequence": DISPLAY[sequence], "runs": attempts,
           "planned_valid_runs": attempts, "valid_algorithm_runs": len(rows),
           "total_execution_attempts": total_execution_attempts if total_execution_attempts is not None else attempts,
           "infrastructure_failed_attempts": infrastructure_failed_attempts,
           "valid_runs": len(rows), "process_success": len(rows)}
    for key in metrics:
        values = [float(x[key]) for x in rows if key in x and x[key] not in ("", None)]
        out[key + "_mean"] = mean(values)
        out[key + "_std"] = std(values)
    out["coverage_warning"] = "YES" if out["TSR_mean"] < 0.9 else "NO"
    return out


def baseline_rows(sequence, label):
    rows = []; association = stamps(association_path(sequence))
    for run in range(1, 4):
        d = ROOT / sequence / label / f"run_{run:02d}"
        manifest = json.loads((d / "final_run_manifest.json").read_text())
        if manifest["status"] != "success":
            continue
        metric = json.loads((d / "eval/metrics.json").read_text())
        frame = read_csv(d / "ablation_frames.csv")
        trajectory = trajectory_stamps(d / "CameraTrajectory.txt")
        tsr, gaps, longest_tracked, longest_lost, valid = coverage(association, trajectory)
        rows.append({
            "run": f"run_{run:02d}", "ATE_RMSE": metric["ate"]["rmse"],
            "RPE_translation": metric["rpe_trans"]["rmse"], "RPE_rotation_deg": metric["rpe_rot_deg"]["rmse"],
            "TSR": tsr, "PMR": 1 - tsr, "gaps": gaps,
            "longest_tracked_segment": longest_tracked, "longest_lost_segment": longest_lost,
            "initial_correspondences": mean([int(x["initial_correspondences"]) for x in frame]),
            "final_inliers": mean([int(x["final_inliers"]) for x in frame]),
            "optimization_acceptance": mean([int(x["optimization_acceptance"]) for x in frame]),
            "trajectory_length": len(trajectory), "valid_pose_count": valid,
        })
    if sequence == "fr3_walking_xyz" and label == "legacy_temporal":
        d = ROOT / sequence / label / "run_04_replacement_for_run01"
        manifest = json.loads((d / "replacement_manifest.json").read_text())
        if manifest["status"] == "success":
            metric = json.loads((d / "eval/metrics.json").read_text())
            frame = read_csv(d / "ablation_frames.csv")
            trajectory = trajectory_stamps(d / "CameraTrajectory.txt")
            tsr, gaps, longest_tracked, longest_lost, valid = coverage(association, trajectory)
            rows.append({
                "run": "run_04_replacement_for_run01", "ATE_RMSE": metric["ate"]["rmse"],
                "RPE_translation": metric["rpe_trans"]["rmse"], "RPE_rotation_deg": metric["rpe_rot_deg"]["rmse"],
                "TSR": tsr, "PMR": 1 - tsr, "gaps": gaps,
                "longest_tracked_segment": longest_tracked, "longest_lost_segment": longest_lost,
                "initial_correspondences": mean([int(x["initial_correspondences"]) for x in frame]),
                "final_inliers": mean([int(x["final_inliers"]) for x in frame]),
                "optimization_acceptance": mean([int(x["optimization_acceptance"]) for x in frame]),
                "trajectory_length": len(trajectory), "valid_pose_count": valid,
                "replacement_for": "run_01", "attempt_type": "INFRASTRUCTURE_FAILURE_REPLACEMENT",
            })
    return rows


def frozen_rows(sequence, mode):
    root = TUM_V4 if sequence.startswith("fr3_") else BONN_V4
    rows = read_csv(root / sequence / "analysis/per_run_metrics.csv")
    selected = [dict(x) for x in rows if x["mode"] == mode]
    association = stamps(association_path(sequence))
    for row in selected:
        d = root / sequence / mode / row["run"]
        trajectory = trajectory_stamps(d / "CameraTrajectory.txt")
        _, _, lt, ll, valid = coverage(association, trajectory)
        row.update(longest_tracked_segment=lt, longest_lost_segment=ll,
                   trajectory_length=len(trajectory), valid_pose_count=valid)
    return selected


def main():
    actual = {
        "rgbd_tum": sha256(REPO / "Examples/RGB-D/rgbd_tum"),
        "libORB_SLAM2.so": sha256(REPO / "lib/libORB_SLAM2.so"),
        "evaluate_tum_metrics.py": sha256(REPO / "scripts/evaluate_tum_metrics.py"),
    }
    if actual != EXPECTED:
        raise SystemExit("frozen hash mismatch")

    per_run = []; comparison = []
    for sequence in SEQUENCES:
        for label, method in (("vanilla", "Vanilla ORB-SLAM2"), ("legacy_temporal", "Legacy Temporal")):
            rows = baseline_rows(sequence, label)
            per_run.extend({"Method": method, "Sequence": DISPLAY[sequence], **x} for x in rows)
            replacement_cell = sequence == "fr3_walking_xyz" and label == "legacy_temporal"
            comparison.append(aggregate(rows, method, sequence, 3,
                                        total_execution_attempts=4 if replacement_cell else 3,
                                        infrastructure_failed_attempts=1 if replacement_cell else 0))
        for mode, method in (("belief_only", "V3 Persistent Belief"), ("geometry_protected", "V4 Full")):
            rows = frozen_rows(sequence, mode)
            per_run.extend({"Method": method, "Sequence": DISPLAY[sequence], **x} for x in rows)
            comparison.append(aggregate(rows, method, sequence, len(rows)))
    write_csv(ROOT / "final_internal_per_run.csv", per_run)
    write_csv(ROOT / "final_internal_comparison.csv", comparison)

    ds_rows = read_csv(DS)
    ds_out = []
    for sequence in sorted({x["sequence"] for x in ds_rows}):
        z = [x for x in ds_rows if x["sequence"] == sequence]
        row = {"ResultType": "OUR RUN", "Implementation": "local DS-SLAM import",
               "UpstreamProvenance": "NOT_VERIFIABLE", "ProtocolComparableToFrozenV4": "NO",
               "Sequence": sequence, "runs": len(z)}
        for source, target in (("ATE_RMSE", "ATE"), ("RPE_translation", "RPE_t"),
                               ("RPE_rotation", "RPE_r"), ("TSR", "TSR"), ("PMR", "PMR")):
            values = [float(x[source]) for x in z if x[source] != ""]
            row[target + "_mean"] = mean(values); row[target + "_std"] = std(values)
        ds_out.append(row)
    write_csv(ROOT / "external_reference_dsslam.csv", ds_out)

    manifests = [json.loads(x.read_text()) for x in ROOT.glob("*/**/final_run_manifest.json")]
    config = []
    expected_cfg = {
        "vanilla": {"ACTIVE_MODE":"0", "BELIEF_ENABLED":"0", "RELIABILITY_ENABLED":"0", "LEGACY_TEMPORAL_WEIGHT_ENABLED":"0", "LEGACY_TEMPORAL_HARD_REJECTION_ENABLED":"0", "MEASUREMENT_POLICY":"BELIEF_ONLY"},
        "legacy_temporal": {"ACTIVE_MODE":"0", "BELIEF_ENABLED":"0", "RELIABILITY_ENABLED":"0", "LEGACY_TEMPORAL_WEIGHT_ENABLED":"1", "LEGACY_TEMPORAL_HARD_REJECTION_ENABLED":"1", "MEASUREMENT_POLICY":"BELIEF_ONLY"},
    }
    for manifest in manifests:
        d = ROOT / manifest["sequence"] / manifest["method"] / f"run_{manifest['run']:02d}"
        cfg = {}
        if (d / "slam.log").exists():
            line = next((x for x in (d / "slam.log").read_text(errors="replace").splitlines() if "[BeliefConfiguration]" in x), "")
            cfg = dict(re.findall(r"([A-Z_]+)=([^ ]+)", line))
        infrastructure_failure = (manifest["method"] == "legacy_temporal" and
                                  manifest["sequence"] == "fr3_walking_xyz" and
                                  manifest["run"] == 1 and manifest["status"] == "failed")
        config.append({"method": manifest["method"], "sequence": manifest["sequence"], "run": manifest["run"],
                       "attempt_type": "ORIGINAL_FORMAL_ATTEMPT",
                       "failure_class": "FAILED_INFRASTRUCTURE_PRE_SLAM" if infrastructure_failure else "",
                       "failure_reason": "YOLO Unix socket bind PermissionError: [Errno 1] Operation not permitted" if infrastructure_failure else "",
                       "included_in_metric_statistics": int(manifest["status"] == "success"),
                       "status": manifest["status"], "startup_config_present": int(bool(cfg)),
                       "startup_config_ok": int(bool(cfg) and all(cfg.get(k) == v for k, v in expected_cfg[manifest["method"]].items())),
                       "trajectory_exists": int((d / "CameraTrajectory.txt").exists()),
                       "evaluation_exists": int((d / "eval/metrics.json").exists()),
                       "ablation_log_exists": int((d / "ablation_frames.csv").exists()),
                       "optimizer_log_exists": int((d / "optimizer_measurements.csv").exists())})
    replacement_path = ROOT / "fr3_walking_xyz/legacy_temporal/run_04_replacement_for_run01"
    replacement = json.loads((replacement_path / "replacement_manifest.json").read_text())
    line = next((x for x in (replacement_path / "slam.log").read_text(errors="replace").splitlines() if "[BeliefConfiguration]" in x), "")
    cfg = dict(re.findall(r"([A-Z_]+)=([^ ]+)", line))
    config.append({"method": "legacy_temporal", "sequence": "fr3_walking_xyz", "run": "run_04_replacement_for_run01",
                   "attempt_type": "INFRASTRUCTURE_FAILURE_REPLACEMENT", "replacement_for": "run_01",
                   "failure_class": "", "failure_reason": "", "included_in_metric_statistics": int(replacement["status"] == "success"),
                   "status": replacement["status"], "startup_config_present": int(bool(cfg)),
                   "startup_config_ok": int(bool(cfg) and all(cfg.get(k) == v for k, v in expected_cfg["legacy_temporal"].items())),
                   "trajectory_exists": int((replacement_path / "CameraTrajectory.txt").exists()),
                   "evaluation_exists": int((replacement_path / "eval/metrics.json").exists()),
                   "ablation_log_exists": int((replacement_path / "ablation_frames.csv").exists()),
                   "optimizer_log_exists": int((replacement_path / "optimizer_measurements.csv").exists())})
    write_csv(ROOT / "final_integrity_runs.csv", config)
    report = {"original_formal_attempts": len(manifests), "replacement_attempts": 1,
              "total_execution_attempts": len(manifests) + 1, "valid_algorithm_runs": 36,
              "process_success": sum(x["status"] == "success" for x in manifests) + int(replacement["status"] == "success"),
              "pre_slam_infrastructure_failures": 1,
              "original_failed_attempt": {"method": "legacy_temporal", "sequence": "fr3_walking_xyz", "run": "run_01",
                  "status": "FAILED_INFRASTRUCTURE_PRE_SLAM",
                  "reason": "YOLO Unix socket bind PermissionError: [Errno 1] Operation not permitted",
                  "included_in_metric_statistics": False},
              "replacement_attempt": {"run": "run_04_replacement_for_run01", "status": replacement["status"],
                  "included_in_metric_statistics": replacement["status"] == "success"}, "hashes": actual,
              "hashes_match": actual == EXPECTED, "successful_trajectory_count": sum(x["trajectory_exists"] for x in config),
              "successful_evaluation_count": sum(x["evaluation_exists"] for x in config),
              "startup_config_valid_count": sum(x["startup_config_ok"] for x in config),
              "association_hashes": {s: sha256(association_path(s)) for s in SEQUENCES}}
    (ROOT / "final_integrity_report.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
