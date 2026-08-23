#!/usr/bin/env python3
"""Run exactly 15 Full-mode TUM experiments for the P1 paper evaluation."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "experiments/final_paper/01_tum_full"
BUILD = REPO / "build_p1_tum_full_active"
BINARY = REPO / "Examples/RGB-D/rgbd_tum"
LIBRARY = REPO / "lib/libORB_SLAM2.so"
WEIGHTS = REPO / "yolov5_RemoveDynamic/weights/yolov5s.pt"
RUNNER = REPO / "scripts/run_tum_rgbd_experiment.py"
SETTINGS = REPO / "Examples/RGB-D/TUM3.yaml"
FLAGS = "-DENABLE_OBJECT_DYNAMIC_SHADOW_MODE=1 -DENABLE_OBJECT_DYNAMIC_ACTIVE_MODE=1"
SEQUENCES = {
    "fr3_walking_xyz": {
        "dataset": Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz"),
        "association": REPO / "dataset_associations/fr3_walking_xyz_associate.txt",
        "frames": 827,
    },
    "fr3_walking_rpy": {
        "dataset": Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_rpy"),
        "association": REPO / "dataset_associations/fr3_walking_rpy_associate.txt",
        "frames": 866,
    },
    "fr3_walking_halfsphere": {
        "dataset": Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_halfsphere"),
        "association": REPO / "dataset_associations/fr3_walking_halfsphere_associate.txt",
        "frames": 1021,
    },
}

FATAL_PATTERNS = (
    "segmentation fault", "segfault", "out of memory", "oom-killer",
    "timed out", "timeout expired",
)


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def data_lines(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()
               if line.strip() and not line.lstrip().startswith("#"))


def command_output(command: list[str]) -> str:
    try:
        return subprocess.check_output(command, text=True, stderr=subprocess.STDOUT).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        return f"unavailable: {exc}"


def build_and_verify() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    build_log = ROOT / "build.log"
    commands = [
        ["cmake", "-S", str(REPO), "-B", str(BUILD), f"-DCMAKE_CXX_FLAGS={FLAGS}"],
        ["cmake", "--build", str(BUILD), "-j8", "--target", "rgbd_tum"],
    ]
    with build_log.open("w", encoding="utf-8") as output:
        for command in commands:
            output.write("COMMAND: " + " ".join(command) + "\n")
            output.flush()
            result = subprocess.run(command, cwd=REPO, stdout=output, stderr=subprocess.STDOUT, text=True)
            if result.returncode:
                raise RuntimeError(f"Build failed ({result.returncode}); see {build_log}")
    cache = (BUILD / "CMakeCache.txt").read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"^CMAKE_CXX_FLAGS:STRING=(.*)$", cache, re.MULTILINE)
    actual = match.group(1) if match else ""
    if actual != FLAGS:
        raise RuntimeError(f"Unexpected CMAKE_CXX_FLAGS: {actual!r}")


def semantic_defaults() -> dict[str, float]:
    text = (REPO / "include/SemanticConfig.h").read_text(encoding="utf-8")
    names = [
        "kDynamicScoreThreshold", "kDynamicScoreIncrement", "kDynamicScoreDecay",
        "kPersonDynamicScoreThreshold", "kPersonDynamicScoreIncrement", "kPersonDynamicScoreDecay",
    ]
    values: dict[str, float] = {}
    for name in names:
        match = re.search(rf"{name}\s*=\s*([0-9.]+)f", text)
        if not match:
            raise RuntimeError(f"Cannot read {name} from SemanticConfig.h")
        values[name] = float(match.group(1))
    return values


def write_environment() -> None:
    associations = {}
    for sequence, info in SEQUENCES.items():
        actual = data_lines(info["association"])
        if actual != info["frames"]:
            raise RuntimeError(f"{sequence}: expected {info['frames']} association rows, got {actual}")
        associations[sequence] = {"path": str(info["association"]), "total_frames": actual}
    status = command_output(["git", "status", "--short"])
    environment = {
        "recorded_at": now(),
        "project": str(REPO),
        "git_commit": command_output(["git", "rev-parse", "HEAD"]),
        "git_diff_status": status,
        "semantic_mode": 2,
        "shadow_macro": 1,
        "active_macro": 1,
        "cmake_cxx_flags": FLAGS,
        "binary": {"path": str(BINARY), "sha256": sha256(BINARY)},
        "shared_library": {"path": str(LIBRARY), "sha256": sha256(LIBRARY)},
        "yolo_weights": {"path": str(WEIGHTS.resolve()), "sha256": sha256(WEIGHTS)},
        "semantic_defaults": semantic_defaults(),
        "settings": {"path": str(SETTINGS), "sha256": sha256(SETTINGS)},
        "associations": associations,
        "cpu": command_output(["lscpu"]),
        "gpu": command_output(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"]),
        "memory": command_output(["free", "-h"]),
        "os": command_output(["uname", "-a"]),
        "platform": platform.platform(),
        "trajectory_evaluation": {
            "script": "scripts/evaluate_tum_metrics.py",
            "timestamp_max_diff_seconds": 0.02,
            "alignment": "SE(3) rigid alignment",
        },
    }
    (ROOT / "experiment_environment.json").write_text(
        json.dumps(environment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def raw_process_status(return_code: int | None, timed_out: bool = False) -> str:
    if timed_out:
        return "timeout"
    if return_code is None:
        return "unknown"
    if return_code < 0:
        return "killed"
    return f"exit_{return_code}"


def completion_status(run_dir: Path) -> tuple[str, list[str]]:
    reasons: list[str] = []
    slam_log = run_dir / "slam.log"
    terminal_log = run_dir / "terminal.log"
    combined = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in (slam_log, terminal_log)
        if path.exists()
    ).lower()
    slam_complete = (
        "trajectory saved!" in combined
        and "semantic dynamic statistics saved!" in combined
    )
    trajectory = run_dir / "CameraTrajectory.txt"
    trajectory_ok = trajectory.exists() and trajectory.stat().st_size > 0
    evaluation = run_dir / "eval/metrics.json"
    evaluation_ok = evaluation.exists() and evaluation.stat().st_size > 0
    fatal = [pattern for pattern in FATAL_PATTERNS if pattern in combined]
    if not slam_complete:
        reasons.append("missing_slam_completion_marker")
    if not trajectory_ok:
        reasons.append("missing_or_empty_trajectory")
    if not evaluation_ok:
        reasons.append("missing_or_empty_evaluation")
    reasons.extend(f"fatal_log_pattern:{pattern}" for pattern in fatal)
    if fatal:
        return "invalid", reasons
    if slam_complete and trajectory_ok and evaluation_ok:
        return "completed", reasons
    return "incomplete", reasons


def run_one(sequence: str, run_id: int) -> None:
    info = SEQUENCES[sequence]
    run_dir = ROOT / sequence / f"run_{run_id:02d}"
    if run_dir.exists():
        print(f"[{now()}] preserve existing run without replacement: {run_dir}", flush=True)
        return
    run_dir.mkdir(parents=True)
    socket_path = Path(f"/tmp/orbslam2_p1_{sequence}_{run_id:02d}_{os.getpid()}.sock")
    command = [
        sys.executable, str(RUNNER), "--sequence", sequence, "--method", "full",
        "--dataset", str(info["dataset"]), "--association", str(info["association"]),
        "--settings", str(SETTINGS), "--out-dir", str(run_dir), "--device", "0",
    ]
    config = {
        "sequence": sequence, "run_id": run_id, "status": "running", "started_at": now(),
        "raw_process_status": "unknown", "experiment_completion_status": "incomplete",
        "association_total_frames": info["frames"], "semantic_mode": 2,
        "shadow_macro": 1, "active_macro": 1, "socket_path": str(socket_path),
        "command": command, "environment_snapshot": str(ROOT / "experiment_environment.json"),
    }
    config_path = run_dir / "p1_run_config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    env = os.environ.copy()
    env["ORB_SLAM2_SOCKET_PATH"] = str(socket_path)
    env["ORB_SLAM2_SEMANTIC_MODE"] = "2"
    env.pop("ORB_SLAM2_DYNAMIC_LAMBDA", None)
    env.pop("ORB_SLAM2_DYNAMIC_THETA", None)
    env.pop("ORB_SLAM2_PERSON_DYNAMIC_THETA", None)
    start = time.monotonic()
    try:
        with (run_dir / "terminal.log").open("w", encoding="utf-8") as terminal:
            result = subprocess.run(command, cwd=REPO, env=env, stdout=terminal,
                                    stderr=subprocess.STDOUT, text=True)
        status = "success" if result.returncode == 0 else "failed"
        return_code = result.returncode
        timed_out = False
    except KeyboardInterrupt:
        status, return_code, timed_out = "interrupted", 130, False
    except subprocess.TimeoutExpired:
        status, return_code, timed_out = "timeout", None, True
    except Exception as exc:  # retain all unexpected attempts
        status, return_code, timed_out = "failed", None, False
        (run_dir / "driver_exception.txt").write_text(repr(exc) + "\n", encoding="utf-8")
    finally:
        try:
            socket_path.unlink()
        except FileNotFoundError:
            pass
    completion, completion_reasons = completion_status(run_dir)
    config.update({"status": status, "return_code": return_code,
                   "raw_process_status": raw_process_status(return_code, timed_out),
                   "experiment_completion_status": completion,
                   "completion_evidence_failures": completion_reasons,
                   "finished_at": now(), "runtime_seconds": time.monotonic() - start})
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"[{now()}] {sequence} run_{run_id:02d}: {status} rc={return_code}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-build", action="store_true")
    args = parser.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    lock_stream = (ROOT / ".p1.lock").open("w")
    try:
        fcntl.flock(lock_stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("Another P1 runner owns the experiment lock.")
    if not args.no_build:
        build_and_verify()
        write_environment()
    for sequence in SEQUENCES:
        for run_id in range(1, 6):
            run_one(sequence, run_id)


if __name__ == "__main__":
    main()
