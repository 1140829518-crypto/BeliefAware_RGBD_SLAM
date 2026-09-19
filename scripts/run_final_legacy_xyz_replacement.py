#!/usr/bin/env python3
"""Execute the single approved pre-SLAM infrastructure replacement attempt."""

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUN = REPO / "experiment_new/paper2_belief_eval/output/final_internal_baseline_benchmark/fr3_walking_xyz/legacy_temporal/run_04_replacement_for_run01"
EXPECTED = {
    REPO / "Examples/RGB-D/rgbd_tum": "0079490eaf05c513ce18b5de95f66e54c98ba30e47511d17bd5a26ae4fcbddc9",
    REPO / "lib/libORB_SLAM2.so": "85a1ec7d6c2786ad2fd2497ce0de2710c725a693ebd6b4d46c3bea63628c8687",
    REPO / "scripts/evaluate_tum_metrics.py": "cfdd35d556afcd5d080fe109396f5ffa7da1810a5e2c26a656c648216db24b13",
}

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def save(value):
    RUN.mkdir(parents=True, exist_ok=True)
    (RUN / "replacement_manifest.json").write_text(json.dumps(value, indent=2) + "\n")

def main():
    if RUN.exists():
        raise SystemExit("replacement directory already exists; refusing a second attempt")
    actual = {str(p.relative_to(REPO)): sha256(p) for p in EXPECTED}
    if any(sha256(p) != h for p, h in EXPECTED.items()):
        raise SystemExit("frozen hash mismatch")
    dataset = Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz")
    association = REPO / "dataset_associations/fr3_walking_xyz_associate.txt"
    settings = REPO / "Examples/RGB-D/TUM3.yaml"
    command = [sys.executable, str(REPO / "scripts/run_tum_rgbd_experiment.py"),
               "--sequence", "fr3_walking_xyz", "--method", "legacy-temporal",
               "--dataset", str(dataset), "--association", str(association),
               "--settings", str(settings), "--out-dir", str(RUN),
               "--device", "0", "--socket-timeout", "300"]
    manifest = {
        "attempt_type": "INFRASTRUCTURE_FAILURE_REPLACEMENT",
        "replacement_for": "legacy_temporal/fr3_walking_xyz/run_01",
        "original_failure_class": "FAILED_INFRASTRUCTURE_PRE_SLAM",
        "original_failure_reason": "YOLO Unix socket bind PermissionError: [Errno 1] Operation not permitted",
        "method": "legacy_temporal", "sequence": "fr3_walking_xyz",
        "run_id": "run_04_replacement_for_run01", "frozen_hashes": actual,
        "dataset": str(dataset), "association": str(association), "settings": str(settings),
        "association_sha256": sha256(association), "settings_sha256": sha256(settings),
        "groundtruth_sha256": sha256(dataset / "groundtruth.txt"), "command": command,
        "started_at": datetime.now().astimezone().isoformat(), "status": "running",
    }
    save(manifest)
    env = os.environ.copy()
    env["ORB_SLAM2_UNCERTAINTY_MODE"] = "CLEAN"
    env["ORB_SLAM2_MEASUREMENT_POLICY"] = "BELIEF_ONLY"
    env["ORB_SLAM2_CONFLICT_AWARE_UNCERTAINTY_ENABLED"] = "0"
    result = subprocess.run(command, cwd=REPO, env=env)
    manifest.update(finished_at=datetime.now().astimezone().isoformat(), return_code=result.returncode,
                    status="success" if result.returncode == 0 else "failed",
                    trajectory_exists=(RUN / "CameraTrajectory.txt").exists(),
                    evaluation_exists=(RUN / "eval/metrics.json").exists(),
                    frame_log_exists=(RUN / "ablation_frames.csv").exists(),
                    optimizer_measurement_log_exists=(RUN / "optimizer_measurements.csv").exists())
    save(manifest)
    return result.returncode

if __name__ == "__main__":
    raise SystemExit(main())
