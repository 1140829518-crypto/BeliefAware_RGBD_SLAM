#!/usr/bin/env python3
"""Execute the frozen runtime-only campaign serially and retain provenance."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "runtime_experiment"


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
    tum = Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz")
    bonn = REPO / "experiment_new/dataset/bonn_rgbd_dynamic/rgbd_bonn_person_tracking"
    sequences = [
        ("TUM", "fr3_walking_xyz", tum,
         REPO / "dataset_associations/fr3_walking_xyz_associate.txt",
         REPO / "Examples/RGB-D/TUM3.yaml"),
        ("Bonn", "rgbd_bonn_person_tracking", bonn,
         bonn / "associate.txt",
         REPO / "experiment_new/dataset/bonn_rgbd_dynamic/Bonn.yaml"),
    ]
    methods = [
        ("Vanilla", "baseline", "CLEAN", "BELIEF_ONLY"),
        ("Legacy Temporal", "legacy-temporal", "CLEAN", "BELIEF_ONLY"),
        ("V3 BELIEF_ONLY", "belief-active", "PERSISTENT", "BELIEF_ONLY"),
        ("V4 GEOMETRY_PROTECTED", "belief-active", "PERSISTENT", "GEOMETRY_PROTECTED"),
    ]
    for _, _, dataset, association, settings in sequences:
        for required in (dataset, association, settings, dataset / "groundtruth.txt"):
            if not required.exists():
                raise FileNotFoundError(required)

    artifacts = {
        "Examples/RGB-D/rgbd_tum": sha256(REPO / "Examples/RGB-D/rgbd_tum"),
        "lib/libORB_SLAM2.so": sha256(REPO / "lib/libORB_SLAM2.so"),
        "scripts/evaluate_tum_metrics.py": sha256(REPO / "scripts/evaluate_tum_metrics.py"),
    }
    protocol = {
        "created_at": datetime.now().astimezone().isoformat(),
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=REPO, text=True).strip(),
        "runtime_instrumented_artifacts": artifacts,
        "logging_mode": "LIGHTWEIGHT",
        "runs_per_cell": {"warmup": 1, "measured": 3},
        "execution": "strictly serial",
        "device": "0",
        "platform": platform.platform(),
        "python": sys.version,
        "thread_environment": {k: os.environ.get(k) for k in
                               ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                                "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")},
        "sequences": [x[1] for x in sequences],
        "methods": [x[0] for x in methods],
    }
    write_json(OUT / "runtime_protocol.json", protocol)

    outcomes: list[dict[str, object]] = []
    cases = [(d, s, ds, a, c, *m, r)
             for d, s, ds, a, c in sequences
             for m in methods for r in range(4)]
    for index, (dataset_label, sequence, dataset, association, settings,
                method_label, runner_method, uncertainty, policy, run) in enumerate(cases, 1):
        run_label = "warmup" if run == 0 else f"run_{run:02d}"
        method_dir = method_label.lower().replace(" ", "_")
        run_dir = OUT / "runs" / sequence / method_dir / run_label
        manifest_path = run_dir / "runtime_run_manifest.json"
        if manifest_path.exists():
            prior = json.loads(manifest_path.read_text(encoding="utf-8"))
            if prior.get("status") == "success":
                outcomes.append(prior)
                print(f"[{index:02d}/{len(cases)}] RETAIN SUCCESS {sequence} {method_label} {run_label}", flush=True)
                continue

        command = [sys.executable, str(REPO / "scripts/run_tum_rgbd_experiment.py"),
                   "--sequence", sequence, "--method", runner_method,
                   "--dataset", str(dataset), "--association", str(association),
                   "--settings", str(settings), "--out-dir", str(run_dir),
                   "--device", "0", "--socket-timeout", "300"]
        env = os.environ.copy()
        env.update({
            "ORB_SLAM2_RUNTIME_LIGHTWEIGHT": "1",
            "ORB_SLAM2_UNCERTAINTY_MODE": uncertainty,
            "ORB_SLAM2_MEASUREMENT_POLICY": policy,
            "ORB_SLAM2_CONFLICT_AWARE_UNCERTAINTY_ENABLED": "1" if uncertainty == "PERSISTENT" else "0",
        })
        for heavy in ("ORB_SLAM2_BELIEF_LOG", "ORB_SLAM2_ABLATION_FRAME_LOG",
                      "ORB_SLAM2_OPTIMIZER_MEASUREMENT_LOG"):
            env.pop(heavy, None)
        manifest: dict[str, object] = {
            "index": index, "total": len(cases), "dataset": dataset_label,
            "sequence": sequence, "method": method_label, "runner_method": runner_method,
            "run": run_label, "measured": run > 0, "dataset_path": str(dataset),
            "association": str(association), "settings": str(settings),
            "association_sha256": sha256(association), "settings_sha256": sha256(settings),
            "groundtruth_sha256": sha256(dataset / "groundtruth.txt"),
            "configuration": {
                "ORB_SLAM2_RUNTIME_LIGHTWEIGHT": "1",
                "ORB_SLAM2_UNCERTAINTY_MODE": uncertainty,
                "ORB_SLAM2_MEASUREMENT_POLICY": policy,
                "ORB_SLAM2_CONFLICT_AWARE_UNCERTAINTY_ENABLED": env["ORB_SLAM2_CONFLICT_AWARE_UNCERTAINTY_ENABLED"],
            },
            "artifacts": artifacts, "command": command,
            "started_at": datetime.now().astimezone().isoformat(), "status": "running",
        }
        write_json(manifest_path, manifest)
        print(f"[{index:02d}/{len(cases)}] START {sequence} {method_label} {run_label}", flush=True)
        result = subprocess.run(command, cwd=REPO, env=env)
        manifest.update({
            "finished_at": datetime.now().astimezone().isoformat(),
            "return_code": result.returncode,
            "status": "success" if result.returncode == 0 else "failed",
            "trajectory_exists": (run_dir / "CameraTrajectory.txt").exists(),
            "runtime_breakdown_exists": (run_dir / "runtime_breakdown.csv").exists(),
            "evaluation_exists": (run_dir / "eval/metrics.json").exists(),
            "heavy_logs_absent": not any((run_dir / name).exists() for name in
                                         ("belief_updates.csv", "ablation_frames.csv", "optimizer_measurements.csv")),
        })
        write_json(manifest_path, manifest)
        outcomes.append(manifest)
        write_json(OUT / "runtime_outcomes.json", outcomes)
        print(f"[{index:02d}/{len(cases)}] {str(manifest['status']).upper()} {sequence} {method_label} {run_label}", flush=True)
        if result.returncode != 0:
            print("Stopping after runtime infrastructure/run failure; logs retained.", file=sys.stderr)
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
