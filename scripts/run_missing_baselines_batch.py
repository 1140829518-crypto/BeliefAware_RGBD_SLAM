#!/usr/bin/env python3
"""Run missing DS-SLAM and Dyna-SLAM baselines and evaluate them.

The script is intentionally resumable: if a metrics.json already exists for a
sequence/method, that run is skipped.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List


REPO = Path(__file__).resolve().parents[1]
OUT_ROOT = REPO / "baseline_runs_missing"
EVAL_SCRIPT = REPO / "scripts" / "evaluate_tum_metrics.py"

SEQUENCES: List[Dict[str, str]] = [
    {
        "name": "fr1_xyz",
        "dataset": "/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg1_xyz",
        "association": "dataset_associations/fr1_xyz_associate.txt",
        "settings_ds": "baselines/DS-SLAM-master/Examples/ROS/ORB_SLAM2_PointMap_SegNetM/TUM1.yaml",
        "settings_dyna": "baselines/DynaSLAM-master/Examples/RGB-D/TUM1.yaml",
    },
    {
        "name": "fr1_desk",
        "dataset": "/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg1_desk",
        "association": "dataset_associations/fr1_desk_associate.txt",
        "settings_ds": "baselines/DS-SLAM-master/Examples/ROS/ORB_SLAM2_PointMap_SegNetM/TUM1.yaml",
        "settings_dyna": "baselines/DynaSLAM-master/Examples/RGB-D/TUM1.yaml",
    },
    {
        "name": "fr3_walking_xyz",
        "dataset": "/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz",
        "association": "/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz/associate.txt",
        "settings_ds": "baselines/DS-SLAM-master/Examples/ROS/ORB_SLAM2_PointMap_SegNetM/TUM3.yaml",
        "settings_dyna": "baselines/DynaSLAM-master/Examples/RGB-D/TUM3.yaml",
    },
    {
        "name": "fr3_walking_rpy",
        "dataset": "/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_rpy",
        "association": "dataset_associations/fr3_walking_rpy_associate.txt",
        "settings_ds": "baselines/DS-SLAM-master/Examples/ROS/ORB_SLAM2_PointMap_SegNetM/TUM3.yaml",
        "settings_dyna": "baselines/DynaSLAM-master/Examples/RGB-D/TUM3.yaml",
    },
    {
        "name": "fr3_walking_halfsphere",
        "dataset": "/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_halfsphere",
        "association": "/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_halfsphere/associate.txt",
        "settings_ds": "baselines/DS-SLAM-master/Examples/ROS/ORB_SLAM2_PointMap_SegNetM/TUM3.yaml",
        "settings_dyna": "baselines/DynaSLAM-master/Examples/RGB-D/TUM3.yaml",
    },
    {
        "name": "fr3_walking_static",
        "dataset": "/home/djn/123/ORB_SLAM2_AddSemantic/rgbd_dataset_freiburg3_walking_static",
        "association": "/home/djn/123/ORB_SLAM2_AddSemantic/rgbd_dataset_freiburg3_walking_static/associate.txt",
        "settings_ds": "baselines/DS-SLAM-master/Examples/ROS/ORB_SLAM2_PointMap_SegNetM/TUM3.yaml",
        "settings_dyna": "baselines/DynaSLAM-master/Examples/RGB-D/TUM3.yaml",
    },
]


def rel(path: str) -> str:
    p = Path(path)
    return str(p if p.is_absolute() else REPO / p)


def gt_path(seq: Dict[str, str]) -> str:
    return str(Path(seq["dataset"]) / "groundtruth.txt")


def count_images(seq: Dict[str, str]) -> int:
    rgb_dir = Path(seq["dataset"]) / "rgb"
    return len(list(rgb_dir.glob("*.png")))


def run_logged(cmd: List[str], cwd: Path, log_path: Path) -> float:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.time()
    with log_path.open("w", encoding="utf-8") as log:
        log.write("$ " + " ".join(cmd) + "\n")
        log.flush()
        subprocess.run(cmd, cwd=str(cwd), stdout=log, stderr=subprocess.STDOUT, check=True)
    return time.time() - start


def evaluate(seq: Dict[str, str], est: Path, out_dir: Path) -> None:
    cmd = [
        sys.executable,
        str(EVAL_SCRIPT),
        "--gt",
        gt_path(seq),
        "--est",
        str(est),
        "--out-dir",
        str(out_dir / "eval"),
        "--title",
        f"{seq['name']} {out_dir.parent.name}",
    ]
    subprocess.run(cmd, cwd=str(REPO), check=True)


def write_runtime(seq: Dict[str, str], out_dir: Path, elapsed: float) -> None:
    frames = max(count_images(seq), 1)
    fps = frames / elapsed if elapsed > 0 else 0.0
    (out_dir / "runtime.txt").write_text(
        f"wall_time {elapsed:.6f}\nframes {frames}\nfps {fps:.6f}\n",
        encoding="utf-8",
    )


def run_dyna(seq: Dict[str, str]) -> None:
    out_dir = OUT_ROOT / "dyna_slam" / seq["name"]
    if (out_dir / "eval" / "metrics.json").exists():
        print(f"[skip] Dyna-SLAM {seq['name']}", flush=True)
        return
    if (out_dir / "failed.txt").exists():
        print(f"[skip failed] Dyna-SLAM {seq['name']}", flush=True)
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(REPO / "baselines/DynaSLAM-master/Examples/RGB-D/rgbd_tum"),
        str(REPO / "baselines/DynaSLAM-master/Vocabulary/ORBvoc.txt"),
        rel(seq["settings_dyna"]),
        seq["dataset"],
        rel(seq["association"]),
    ]
    print(f"[run] Dyna-SLAM {seq['name']}", flush=True)
    try:
        elapsed = run_logged(cmd, out_dir, out_dir / "run.log")
    except subprocess.CalledProcessError as exc:
        (out_dir / "failed.txt").write_text(f"{exc}\n", encoding="utf-8")
        print(f"[failed] Dyna-SLAM {seq['name']}: {exc}", flush=True)
        return
    est = out_dir / "CameraTrajectory.txt"
    if not est.exists():
        fallback = REPO / "baselines/DynaSLAM-master/Examples/RGB-D/CameraTrajectory.txt"
        if fallback.exists():
            shutil.copy2(fallback, est)
    evaluate(seq, est, out_dir)
    write_runtime(seq, out_dir, elapsed)
    print(f"[done] Dyna-SLAM {seq['name']}", flush=True)


def run_ds(seq: Dict[str, str]) -> None:
    out_dir = OUT_ROOT / "ds_slam" / seq["name"]
    if (out_dir / "eval" / "metrics.json").exists():
        print(f"[skip] DS-SLAM {seq['name']}", flush=True)
        return
    if (out_dir / "failed.txt").exists():
        print(f"[skip failed] DS-SLAM {seq['name']}", flush=True)
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(REPO / "baselines/DS-SLAM-master/build/ds_rgbd_tum"),
        str(REPO / "Vocabulary/ORBvoc.txt"),
        rel(seq["settings_ds"]),
        seq["dataset"],
        rel(seq["association"]),
        str(REPO / "baselines/DS-SLAM-master/Examples/ROS/ORB_SLAM2_PointMap_SegNetM/prototxts/segnet_pascal.prototxt"),
        str(REPO / "baselines/DS-SLAM-master/Examples/ROS/ORB_SLAM2_PointMap_SegNetM/models/segnet_pascal.caffemodel"),
        str(REPO / "baselines/DS-SLAM-master/Examples/ROS/ORB_SLAM2_PointMap_SegNetM/tools/pascal.png"),
        str(out_dir),
    ]
    print(f"[run] DS-SLAM {seq['name']}", flush=True)
    try:
        elapsed = run_logged(cmd, REPO, out_dir / "run.log")
    except subprocess.CalledProcessError as exc:
        (out_dir / "failed.txt").write_text(f"{exc}\n", encoding="utf-8")
        print(f"[failed] DS-SLAM {seq['name']}: {exc}", flush=True)
        return
    est = out_dir / "CameraTrajectory.txt"
    if not est.exists():
        raise FileNotFoundError(est)
    evaluate(seq, est, out_dir)
    write_runtime(seq, out_dir, elapsed)
    print(f"[done] DS-SLAM {seq['name']}", flush=True)


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    status = OUT_ROOT / "batch_status.json"
    status.write_text(json.dumps({"status": "running", "started": time.time()}, indent=2), encoding="utf-8")
    try:
        for seq in SEQUENCES:
            run_dyna(seq)
        for seq in SEQUENCES:
            run_ds(seq)
        status.write_text(json.dumps({"status": "complete", "finished": time.time()}, indent=2), encoding="utf-8")
    except Exception as exc:
        status.write_text(json.dumps({"status": "failed", "error": str(exc), "time": time.time()}, indent=2), encoding="utf-8")
        raise


if __name__ == "__main__":
    main()
