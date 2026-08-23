
#!/usr/bin/env python3
"""Run one read-only projection-log pass for P4 Semantic and Temporal."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime


REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "experiments/final_paper/04_mappoint_gt_eval"
ONE = REPO / "scripts/run_tum_rgbd_experiment.py"
SETTINGS = REPO / "Examples/RGB-D/TUM3.yaml"
METHODS = {"Semantic": ("hard", 1), "Temporal": ("dynamic", 2)}
SEQUENCES = {
    "fr3_walking_xyz": (
        Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz"),
        REPO / "dataset_associations/fr3_walking_xyz_associate.txt", 827),
    "fr3_walking_rpy": (
        Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_rpy"),
        REPO / "dataset_associations/fr3_walking_rpy_associate.txt", 866),
    "fr3_walking_halfsphere": (
        Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_halfsphere"),
        REPO / "dataset_associations/fr3_walking_halfsphere_associate.txt", 1021),
}


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def association_count(path: Path) -> int:
    return sum(bool(line.strip()) and not line.lstrip().startswith("#")
               for line in path.read_text(errors="ignore").splitlines())


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    lock_file = (ROOT / ".stage1.lock").open("w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise SystemExit("another P4 Stage1 runner owns the lock") from exc

    binary = REPO / "Examples/RGB-D/rgbd_tum"
    library = REPO / "lib/libORB_SLAM2.so"
    weights = REPO / "yolov5_RemoveDynamic/weights/yolov5s.pt"
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()

    for method, (runner_method, semantic_mode) in METHODS.items():
        for sequence, (dataset, association, expected_count) in SEQUENCES.items():
            if association_count(association) != expected_count:
                raise RuntimeError(f"association count mismatch: {sequence}")
            run_dir = ROOT / "runs" / method / sequence / "run_01"
            if run_dir.exists():
                print("PRESERVE", run_dir, flush=True)
                continue
            run_dir.mkdir(parents=True)
            socket_path = Path(f"/tmp/p4_{method.lower()}_{sequence}_{os.getpid()}.sock")
            env = os.environ.copy()
            env["ORB_SLAM2_SOCKET_PATH"] = str(socket_path)
            env["ORB_SLAM2_SEMANTIC_MODE"] = str(semantic_mode)
            env["ORB_SLAM2_MAPPOINT_EVIDENCE_LOG"] = str(run_dir / "mappoint_evidence_raw.csv")
            env["ORB_SLAM2_MAPPOINT_PROJECTION_LOG"] = str(run_dir / "mappoint_projection_raw.csv")
            env["ORB_SLAM2_TRACKING_MPOINT_LOG"] = str(run_dir / "tracking_mappoint_count.csv")
            for key in ("ORB_SLAM2_DYNAMIC_LAMBDA", "ORB_SLAM2_DYNAMIC_THETA",
                        "ORB_SLAM2_PERSON_DYNAMIC_THETA"):
                env.pop(key, None)
            command = [
                sys.executable, str(ONE), "--sequence", sequence,
                "--method", runner_method, "--dataset", str(dataset),
                "--association", str(association), "--settings", str(SETTINGS),
                "--out-dir", str(run_dir), "--device", "0",
            ]
            config = {
                "purpose": "P4 Stage1 read-only MapPoint projection logging",
                "method": method, "sequence": sequence, "run_id": "run_01",
                "semantic_mode": semantic_mode, "shadow": 0, "active": 0,
                "association_total_frames": expected_count,
                "dataset": str(dataset), "association": str(association),
                "projection_log_env": "ORB_SLAM2_MAPPOINT_PROJECTION_LOG",
                "git_commit": commit, "binary_sha256": sha256(binary),
                "library_sha256": sha256(library),
                "yolo_weights": str(weights.resolve()), "yolo_sha256": sha256(weights),
                "started_at": now(), "command": command,
            }
            (run_dir / "p4_run_config.json").write_text(json.dumps(config, indent=2) + "\n")
            with (run_dir / "terminal.log").open("w") as output:
                result = subprocess.run(command, cwd=REPO, env=env,
                                        stdout=output, stderr=subprocess.STDOUT, text=True)
            config.update(exit_code=result.returncode, finished_at=now())
            projection = run_dir / "mappoint_projection_raw.csv"
            config["projection_log_exists"] = projection.exists()
            config["projection_log_bytes"] = projection.stat().st_size if projection.exists() else 0
            (run_dir / "p4_run_config.json").write_text(json.dumps(config, indent=2) + "\n")
            try:
                socket_path.unlink()
            except FileNotFoundError:
                pass
            print(method, sequence, "exit", result.returncode,
                  "projection_bytes", config["projection_log_bytes"], flush=True)
            if result.returncode != 0:
                raise RuntimeError(f"P4 run failed: {run_dir}")


if __name__ == "__main__":
    main()
