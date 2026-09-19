#!/usr/bin/env python3
"""Run the frozen final Vanilla/Legacy internal baseline protocol."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "experiment_new/paper2_belief_eval/output/final_internal_baseline_benchmark"
EXPECTED = {
    REPO / "Examples/RGB-D/rgbd_tum": "0079490eaf05c513ce18b5de95f66e54c98ba30e47511d17bd5a26ae4fcbddc9",
    REPO / "lib/libORB_SLAM2.so": "85a1ec7d6c2786ad2fd2497ce0de2710c725a693ebd6b4d46c3bea63628c8687",
    REPO / "scripts/evaluate_tum_metrics.py": "cfdd35d556afcd5d080fe109396f5ffa7da1810a5e2c26a656c648216db24b13",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    actual = {str(path.relative_to(REPO)): sha256(path) for path in EXPECTED}
    mismatch = [str(path) for path, expected in EXPECTED.items() if sha256(path) != expected]
    if mismatch:
        print("FROZEN HASH MISMATCH: " + ", ".join(mismatch), file=sys.stderr)
        return 2

    tum_root = Path("/home/djn/datasets/TUMRGBD")
    bonn_root = REPO / "experiment_new/dataset/bonn_rgbd_dynamic"
    sequences = [
        ("fr3_walking_xyz", tum_root / "rgbd_dataset_freiburg3_walking_xyz", REPO / "dataset_associations/fr3_walking_xyz_associate.txt", REPO / "Examples/RGB-D/TUM3.yaml"),
        ("fr3_walking_static", REPO / "rgbd_dataset_freiburg3_walking_static", REPO / "dataset_associations/fr3_walking_static_associate.txt", REPO / "Examples/RGB-D/TUM3.yaml"),
        ("fr3_walking_rpy", tum_root / "rgbd_dataset_freiburg3_walking_rpy", REPO / "dataset_associations/fr3_walking_rpy_associate.txt", REPO / "Examples/RGB-D/TUM3.yaml"),
        ("rgbd_bonn_person_tracking", bonn_root / "rgbd_bonn_person_tracking", bonn_root / "rgbd_bonn_person_tracking/associate.txt", bonn_root / "Bonn.yaml"),
        ("rgbd_bonn_synchronous", bonn_root / "rgbd_bonn_synchronous", bonn_root / "rgbd_bonn_synchronous/associate.txt", bonn_root / "Bonn.yaml"),
        ("rgbd_bonn_crowd", bonn_root / "rgbd_bonn_crowd", bonn_root / "rgbd_bonn_crowd/associate.txt", bonn_root / "Bonn.yaml"),
    ]
    methods = [("vanilla", "baseline"), ("legacy_temporal", "legacy-temporal")]
    cases = [(label, method, *sequence, run) for label, method in methods for sequence in sequences for run in range(1, 4)]
    protocol = {
        "created_at": datetime.now().astimezone().isoformat(),
        "frozen_hashes": actual,
        "runs_expected": len(cases),
        "methods": [label for label, _ in methods],
        "runs_per_cell": 3,
        "sequences": [row[0] for row in sequences],
        "logging": ["ablation_frames.csv", "optimizer_measurements.csv", "slam.log", "runtime_breakdown.csv"],
        "failed_runs_retained": True,
    }
    write_json(OUT / "protocol.json", protocol)

    controlled = os.environ.copy()
    controlled["ORB_SLAM2_UNCERTAINTY_MODE"] = "CLEAN"
    controlled["ORB_SLAM2_MEASUREMENT_POLICY"] = "BELIEF_ONLY"
    controlled["ORB_SLAM2_CONFLICT_AWARE_UNCERTAINTY_ENABLED"] = "0"
    outcomes = []
    for index, (label, method, sequence, dataset, association, settings, run) in enumerate(cases, 1):
        run_dir = OUT / sequence / label / f"run_{run:02d}"
        run_dir.mkdir(parents=True, exist_ok=True)
        prior_manifest_path = run_dir / "final_run_manifest.json"
        if prior_manifest_path.exists():
            prior = json.loads(prior_manifest_path.read_text(encoding="utf-8"))
            if prior.get("status") in {"success", "failed"}:
                outcomes.append(prior)
                print(f"[{index:02d}/{len(cases)}] RETAIN {prior['status'].upper()} {label} {sequence} run_{run:02d}", flush=True)
                continue
        command = [
            sys.executable, str(REPO / "scripts/run_tum_rgbd_experiment.py"),
            "--sequence", sequence, "--method", method,
            "--dataset", str(dataset), "--association", str(association),
            "--settings", str(settings), "--out-dir", str(run_dir),
            "--device", "0", "--socket-timeout", "300",
        ]
        manifest = {
            "index": index, "total": len(cases), "method": label,
            "runner_method": method, "sequence": sequence, "run": run,
            "dataset": str(dataset), "association": str(association),
            "settings": str(settings), "association_sha256": sha256(association),
            "settings_sha256": sha256(settings), "groundtruth_sha256": sha256(dataset / "groundtruth.txt"),
            "frozen_hashes": actual, "command": command,
            "started_at": datetime.now().astimezone().isoformat(), "status": "running",
        }
        write_json(run_dir / "final_run_manifest.json", manifest)
        print(f"[{index:02d}/{len(cases)}] START {label} {sequence} run_{run:02d}", flush=True)
        result = subprocess.run(command, cwd=REPO, env=controlled)
        manifest["finished_at"] = datetime.now().astimezone().isoformat()
        manifest["return_code"] = result.returncode
        manifest["status"] = "success" if result.returncode == 0 else "failed"
        manifest["trajectory_exists"] = (run_dir / "CameraTrajectory.txt").exists()
        manifest["evaluation_exists"] = (run_dir / "eval/metrics.json").exists()
        manifest["ablation_log_exists"] = (run_dir / "ablation_frames.csv").exists()
        manifest["optimizer_log_exists"] = (run_dir / "optimizer_measurements.csv").exists()
        write_json(run_dir / "final_run_manifest.json", manifest)
        outcomes.append(manifest)
        write_json(OUT / "outcomes.json", outcomes)
        print(f"[{index:02d}/{len(cases)}] {manifest['status'].upper()} {label} {sequence} run_{run:02d}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
