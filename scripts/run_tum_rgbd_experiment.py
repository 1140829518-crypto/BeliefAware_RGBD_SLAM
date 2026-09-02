#!/usr/bin/env python3
"""Run one TUM RGB-D experiment row and evaluate it.

This script handles:
- optional YOLO socket server for semantic modes
- ORB_SLAM2_SEMANTIC_MODE / ORB_SLAM2_OBJECT_MAP settings
- per-run output directories
- ATE/RPE evaluation
- runtime summary extraction
"""

from __future__ import annotations

import argparse
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SOCKET = Path(os.environ.get("ORB_SLAM2_SOCKET_PATH", "/tmp/orbslam2_semantic_socket"))


def wait_for_socket(path: Path, timeout: float = 90.0) -> None:
    start = time.time()
    while time.time() - start < timeout:
        if path.exists():
            return
        time.sleep(0.2)
    raise TimeoutError(f"Timed out waiting for socket {path}")


def start_yolo(dataset: Path, run_name: str, device: str, log_path: Path) -> subprocess.Popen:
    if SOCKET.exists():
        SOCKET.unlink()
    cmd = [
        sys.executable,
        "detect_speedup_send.py",
        "--source",
        str(dataset / "rgb"),
        "--weights",
        "./weights/yolov5s.pt",
        "--conf-thres",
        "0.4",
        "--save-txt",
        "--img-size",
        "224",
        "--device",
        device,
        "--project",
        str(REPO / "YOLO_runs"),
        "--name",
        run_name,
        "--exist-ok",
    ]
    env = os.environ.copy()
    env["ORB_SLAM2_SOCKET_PATH"] = str(SOCKET)
    env["MPLCONFIGDIR"] = str(REPO / ".matplotlib_cache")
    log_file = log_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        cmd,
        cwd=REPO / "yolov5_RemoveDynamic",
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )
    proc._codex_log_file = log_file  # type: ignore[attr-defined]
    return proc


def parse_runtime(log: str) -> tuple[str, str]:
    median = ""
    mean = ""
    m = re.search(r"median tracking time:\s*([0-9.]+)", log)
    if m:
        median = m.group(1)
    m = re.search(r"mean tracking time:\s*([0-9.]+)", log)
    if m:
        mean = m.group(1)
    return median, mean


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one ORB-SLAM2 RGB-D experiment.")
    parser.add_argument("--sequence", required=True)
    parser.add_argument("--method", choices=["orb", "hard", "frame-temporal", "dynamic", "full"], required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--association", type=Path, required=True)
    parser.add_argument("--settings", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--socket-timeout", type=float, default=90.0,
                        help="YOLO Unix-socket readiness timeout; does not affect SLAM frames.")
    parser.add_argument("--dynamic-lambda", type=float, default=None)
    parser.add_argument("--dynamic-theta", type=float, default=None)
    parser.add_argument("--person-dynamic-theta", type=float, default=None)
    parser.add_argument("--dynamic-increment", type=float, default=None)
    parser.add_argument("--person-dynamic-increment", type=float, default=None)
    parser.add_argument("--person-dynamic-lambda", type=float, default=None)
    args = parser.parse_args()

    method_mode = {
        "orb": ("0", "0"),
        "hard": ("1", "0"),
        "frame-temporal": ("3", "0"),
        "dynamic": ("2", "0"),
        "full": ("2", "1"),
    }
    semantic_mode, object_map = method_mode[args.method]
    args.out_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["ORB_SLAM2_SEMANTIC_MODE"] = semantic_mode
    env["ORB_SLAM2_OBJECT_MAP"] = object_map
    env["ORB_SLAM2_OUTPUT_DIR"] = str(args.out_dir)
    env["ORB_SLAM2_SOCKET_PATH"] = str(SOCKET)
    env["MPLCONFIGDIR"] = str(REPO / ".matplotlib_cache")
    if args.dynamic_lambda is not None:
        env["ORB_SLAM2_DYNAMIC_LAMBDA"] = str(args.dynamic_lambda)
    if args.dynamic_theta is not None:
        env["ORB_SLAM2_DYNAMIC_THETA"] = str(args.dynamic_theta)
    if args.person_dynamic_theta is not None:
        env["ORB_SLAM2_PERSON_DYNAMIC_THETA"] = str(args.person_dynamic_theta)
    if args.dynamic_increment is not None:
        env["ORB_SLAM2_DYNAMIC_INCREMENT"] = str(args.dynamic_increment)
    if args.person_dynamic_increment is not None:
        env["ORB_SLAM2_PERSON_DYNAMIC_INCREMENT"] = str(args.person_dynamic_increment)
    if args.person_dynamic_lambda is not None:
        env["ORB_SLAM2_PERSON_DYNAMIC_LAMBDA"] = str(args.person_dynamic_lambda)

    yolo_proc: subprocess.Popen | None = None
    yolo_log = args.out_dir / "yolo.log"
    if args.method != "orb":
        yolo_proc = start_yolo(args.dataset, f"{args.sequence}_{args.method}", args.device, yolo_log)
        try:
            wait_for_socket(SOCKET, timeout=args.socket_timeout)
        except Exception:
            yolo_proc.terminate()
            try:
                yolo_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                yolo_proc.kill()
            log_file = getattr(yolo_proc, "_codex_log_file", None)
            if log_file is not None:
                log_file.close()
            raise

    cmd = [
        str(REPO / "Examples/RGB-D/rgbd_tum"),
        str(REPO / "Vocabulary/ORBvoc.txt"),
        str(args.settings),
        str(args.dataset),
        str(args.association),
    ]
    with (args.out_dir / "slam.log").open("w", encoding="utf-8") as slam_log:
        slam = subprocess.run(cmd, cwd=REPO, env=env, text=True, stdout=slam_log, stderr=subprocess.STDOUT)

    if yolo_proc is not None:
        try:
            yolo_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            yolo_proc.terminate()
            try:
                yolo_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                yolo_proc.kill()
        log_file = getattr(yolo_proc, "_codex_log_file", None)
        if log_file is not None:
            log_file.close()

    if slam.returncode != 0:
        raise RuntimeError(f"SLAM failed with code {slam.returncode}; see {args.out_dir / 'slam.log'}")

    gt = args.dataset / "groundtruth.txt"
    eval_dir = args.out_dir / "eval"
    eval_cmd = [
        sys.executable,
        str(REPO / "scripts/evaluate_tum_metrics.py"),
        "--gt",
        str(gt),
        "--est",
        str(args.out_dir / "CameraTrajectory.txt"),
        "--out-dir",
        str(eval_dir),
        "--title",
        f"{args.sequence} - {args.method}",
    ]
    subprocess.run(eval_cmd, cwd=REPO, check=True)

    median, mean = parse_runtime((args.out_dir / "slam.log").read_text(encoding="utf-8"))
    runtime_path = args.out_dir / "runtime.txt"
    runtime_path.write_text(
        f"median_tracking_time {median}\nmean_tracking_time {mean}\nfps {1.0 / float(mean) if mean else ''}\n",
        encoding="utf-8",
    )
    print(f"completed {args.sequence} {args.method}: {args.out_dir}")


if __name__ == "__main__":
    main()
