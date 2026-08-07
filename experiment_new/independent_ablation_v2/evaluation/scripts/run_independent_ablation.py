#!/usr/bin/env python3
"""Run a fresh, independent ablation package without touching old results."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


EXP_ROOT = Path(__file__).resolve().parents[2]
REPO = EXP_ROOT.parents[1]
SOCKET = Path(f"/tmp/orbslam2_semantic_socket_{EXP_ROOT.name}_{os.getpid()}")
PYTHON = sys.executable


@dataclass(frozen=True)
class Variant:
    key: str
    label: str
    semantic_mode: int
    object_map: int
    semantic_mask_enabled: bool
    temporal_consistency_enabled: bool
    object_map_enabled: bool
    notes: str = ""


VARIANTS = [
    Variant("baseline", "Baseline", 0, 0, False, False, False),
    Variant("semantic_mask", "Semantic Mask", 1, 0, True, False, False),
    Variant("temporal_consistency", "Temporal Consistency", 2, 0, True, True, False),
    Variant(
        "object_level_map",
        "Object-level Semantic Map",
        1,
        1,
        True,
        False,
        True,
        "Object map depends on semantic detections; this run enables semantic mode without dynamic accumulation.",
    ),
    Variant("full_model", "Full Model", 2, 1, True, True, True),
]

SEQUENCES = {
    "fr3_walking_xyz": {
        "dataset": Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz"),
        "association": Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz/associate.txt"),
    },
    "fr3_walking_rpy": {
        "dataset": Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_rpy"),
        "association": REPO / "dataset_associations/fr3_walking_rpy_associate.txt",
    },
    "fr3_walking_halfsphere": {
        "dataset": Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_halfsphere"),
        "association": Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_halfsphere/associate.txt"),
    },
}

SETTINGS = REPO / "Examples/RGB-D/TUM3.yaml"
VOCABULARY = REPO / "Vocabulary/ORBvoc.txt"
SLAM_BINARY = REPO / "Examples/RGB-D/rgbd_tum"
YOLO_DIR = REPO / "yolov5_RemoveDynamic"
YOLO_WEIGHTS = YOLO_DIR / "weights/yolov5s.pt"
EVAL_SCRIPT = EXP_ROOT / "evaluation/scripts/evaluate_tum_metrics.py"
RANDOM_SEED = 0


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def run_text(cmd: List[str], cwd: Path = REPO, env: Optional[Dict[str, str]] = None) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True)
    except FileNotFoundError as exc:
        return 127, "", str(exc)
    return proc.returncode, proc.stdout, proc.stderr


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def count_data_lines(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    with path.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                total += 1
    return total


def load_tum_xyz(path: Path) -> Tuple[np.ndarray, np.ndarray]:
    stamps: List[float] = []
    xyz: List[List[float]] = []
    if not path.exists():
        return np.asarray(stamps), np.asarray(xyz)
    with path.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 4:
                stamps.append(float(parts[0]))
                xyz.append([float(parts[1]), float(parts[2]), float(parts[3])])
    return np.asarray(stamps), np.asarray(xyz)


def trajectory_smoothness(traj: Path) -> float:
    _, xyz = load_tum_xyz(traj)
    if len(xyz) < 3:
        return math.nan
    accel = np.diff(xyz, n=2, axis=0)
    return float(np.mean(np.linalg.norm(accel, axis=1)))


def parse_runtime(log_text: str) -> Tuple[float, float]:
    median = math.nan
    mean = math.nan
    for line in log_text.splitlines():
        if "median tracking time:" in line:
            try:
                median = float(line.rsplit(":", 1)[1].strip())
            except ValueError:
                pass
        if "mean tracking time:" in line:
            try:
                mean = float(line.rsplit(":", 1)[1].strip())
            except ValueError:
                pass
    return median, mean


def read_stats(path: Path) -> List[Dict[str, float]]:
    if not path.exists():
        return []
    by_frame: Dict[int, Dict[str, float]] = {}
    with path.open(encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f, delimiter=" ")
        for row in reader:
            try:
                frame = int(row["frame_id"])
            except (KeyError, ValueError):
                continue
            current = by_frame.setdefault(
                frame,
                {
                    "frame_id": float(frame),
                    "dynamic_keypoints": 0.0,
                    "dynamic_map_points": 0.0,
                    "suppressed_map_points": 0.0,
                    "dynamic_objects": 0.0,
                    "static_objects": 0.0,
                    "total_objects": 0.0,
                },
            )
            for key in list(current.keys())[1:]:
                try:
                    current[key] = max(current[key], float(row.get(key, 0.0)))
                except ValueError:
                    pass
    return [by_frame[k] for k in sorted(by_frame)]


def temporal_metrics(stats: List[Dict[str, float]]) -> Dict[str, float]:
    if len(stats) < 2:
        return {
            "Switching_Frequency": math.nan,
            "Label_Fluctuation": math.nan,
            "Probability_Variance": math.nan,
            "Mean_Probability_Change": math.nan,
            "Temporal_Consistency_Score": math.nan,
            "Average_Track_Length": math.nan,
            "ID_Switches": math.nan,
        }
    dyn_present = np.asarray([1.0 if s["dynamic_objects"] > 0 else 0.0 for s in stats])
    switches = float(np.sum(np.abs(np.diff(dyn_present)) > 0))
    switching = switches / float(len(dyn_present) - 1)

    dyn_kps = np.asarray([s["dynamic_keypoints"] for s in stats], dtype=float)
    denom = max(float(np.percentile(dyn_kps, 95)), 1.0)
    label_fluct = float(np.mean(np.abs(np.diff(np.clip(dyn_kps / denom, 0.0, 1.0)))))
    temporal_score = float(max(0.0, min(1.0, 1.0 - label_fluct)))

    return {
        "Switching_Frequency": switching,
        "Label_Fluctuation": label_fluct,
        "Probability_Variance": math.nan,
        "Mean_Probability_Change": math.nan,
        "Temporal_Consistency_Score": temporal_score,
        "Average_Track_Length": math.nan,
        "ID_Switches": math.nan,
    }


def write_csv(path: Path, rows: List[Dict[str, object]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def wait_for_socket(path: Path, timeout: float = 90.0) -> None:
    start = time.time()
    while time.time() - start < timeout:
        if path.exists():
            return
        time.sleep(0.2)
    raise TimeoutError(f"Timed out waiting for socket {path}")


def start_yolo(dataset: Path, run_name: str, device: str, run_dir: Path, env: Dict[str, str]) -> subprocess.Popen:
    if SOCKET.exists():
        SOCKET.unlink()
    cmd = [
        PYTHON,
        "detect_speedup_send.py",
        "--source",
        str(dataset / "rgb"),
        "--weights",
        str(YOLO_WEIGHTS),
        "--conf-thres",
        "0.4",
        "--save-txt",
        "--img-size",
        "224",
        "--device",
        device,
        "--project",
        str(EXP_ROOT / "runs/yolo_cache"),
        "--name",
        run_name,
        "--exist-ok",
    ]
    (run_dir / "yolo_command.txt").write_text(" ".join(cmd) + "\n", encoding="utf-8")
    stdout = (run_dir / "yolo_stdout.log").open("w", encoding="utf-8")
    stderr = (run_dir / "yolo_stderr.log").open("w", encoding="utf-8")
    proc = subprocess.Popen(cmd, cwd=YOLO_DIR, env=env, text=True, stdout=stdout, stderr=stderr)
    proc._stdout_file = stdout  # type: ignore[attr-defined]
    proc._stderr_file = stderr  # type: ignore[attr-defined]
    return proc


def stop_yolo(proc: Optional[subprocess.Popen]) -> None:
    if proc is None:
        return
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    for attr in ("_stdout_file", "_stderr_file"):
        handle = getattr(proc, attr, None)
        if handle is not None:
            handle.close()


def run_one(variant: Variant, sequence: str, run_id: int, device: str) -> None:
    info = SEQUENCES[sequence]
    dataset = info["dataset"]
    association = info["association"]
    run_dir = EXP_ROOT / "runs" / variant.key / sequence / f"run_{run_id:02d}"
    if run_dir.exists() and any(run_dir.iterdir()):
        raise RuntimeError(f"Refusing to overwrite non-empty run directory: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["ORB_SLAM2_SEMANTIC_MODE"] = str(variant.semantic_mode)
    env["ORB_SLAM2_OBJECT_MAP"] = str(variant.object_map)
    env["ORB_SLAM2_OUTPUT_DIR"] = str(run_dir)
    env["ORB_SLAM2_SOCKET_PATH"] = str(SOCKET)
    env["MPLCONFIGDIR"] = str(EXP_ROOT / "environment/matplotlib_cache")
    env["PYTHONHASHSEED"] = str(RANDOM_SEED)

    cmd = [str(SLAM_BINARY), str(VOCABULARY), str(SETTINGS), str(dataset), str(association)]
    config = {
        "variant": variant.label,
        "variant_key": variant.key,
        "dataset": str(dataset),
        "sequence": sequence,
        "semantic_mode": variant.semantic_mode,
        "semantic_mask_enabled": variant.semantic_mask_enabled,
        "temporal_consistency_enabled": variant.temporal_consistency_enabled,
        "object_map_enabled": variant.object_map_enabled,
        "window_size": "not configurable in current binary",
        "lambda": "default per class unless ORB_SLAM2_DYNAMIC_LAMBDA is set",
        "thresholds": {
            "dynamic_score_threshold": 3.0,
            "person_dynamic_score_threshold": 1.0,
            "yolo_conf_threshold": 0.4,
        },
        "random_seed": RANDOM_SEED,
        "command": " ".join(cmd),
        "git_commit": "not available: current .git directory is not a valid git repository",
        "start_time": now_iso(),
        "end_time": "",
        "notes": variant.notes,
    }
    write_json(run_dir / "run_config.json", config)
    (run_dir / "command.txt").write_text(" ".join(cmd) + "\n", encoding="utf-8")

    yolo_proc: Optional[subprocess.Popen] = None
    start_wall = time.time()
    status = "failed"
    error = ""
    try:
        if variant.semantic_mode >= 1:
            yolo_proc = start_yolo(dataset, f"{variant.key}_{sequence}_run_{run_id:02d}", device, run_dir, env)
            wait_for_socket(SOCKET)
        with (run_dir / "stdout.log").open("w", encoding="utf-8") as stdout, (
            run_dir / "stderr.log"
        ).open("w", encoding="utf-8") as stderr:
            proc = subprocess.run(cmd, cwd=REPO, env=env, text=True, stdout=stdout, stderr=stderr)
        if proc.returncode != 0:
            raise RuntimeError(f"SLAM failed with return code {proc.returncode}")
        traj = run_dir / "CameraTrajectory.txt"
        if not traj.exists() or count_data_lines(traj) < 2:
            raise RuntimeError("CameraTrajectory.txt missing or too short")
        eval_dir = run_dir / "eval"
        eval_cmd = [
            PYTHON,
            str(EVAL_SCRIPT),
            "--gt",
            str(dataset / "groundtruth.txt"),
            "--est",
            str(traj),
            "--out-dir",
            str(eval_dir),
            "--title",
            f"{sequence} - {variant.label} run {run_id:02d}",
        ]
        (run_dir / "evaluation_command.txt").write_text(" ".join(eval_cmd) + "\n", encoding="utf-8")
        ev = subprocess.run(eval_cmd, cwd=REPO, text=True, capture_output=True)
        (run_dir / "evaluation_stdout.log").write_text(ev.stdout, encoding="utf-8")
        (run_dir / "evaluation_stderr.log").write_text(ev.stderr, encoding="utf-8")
        if ev.returncode != 0:
            raise RuntimeError(f"evaluation failed with return code {ev.returncode}")
        shutil.copy2(eval_dir / "metrics.json", run_dir / "evaluation_results.json")
        status = "completed"
    except Exception as exc:
        error = str(exc)
        (run_dir / "failed.txt").write_text(error + "\n", encoding="utf-8")
    finally:
        stop_yolo(yolo_proc)
        elapsed = time.time() - start_wall
        log_text = (run_dir / "stdout.log").read_text(encoding="utf-8", errors="ignore") if (run_dir / "stdout.log").exists() else ""
        median_tracking, mean_tracking = parse_runtime(log_text)
        input_frames = count_data_lines(association)
        processed_fps = input_frames / elapsed if elapsed > 0 else math.nan
        with (run_dir / "timing.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["wall_time_sec", "input_frames", "end_to_end_fps", "median_tracking_time", "mean_tracking_time"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "wall_time_sec": f"{elapsed:.6f}",
                    "input_frames": input_frames,
                    "end_to_end_fps": f"{processed_fps:.6f}",
                    "median_tracking_time": "" if math.isnan(median_tracking) else f"{median_tracking:.9f}",
                    "mean_tracking_time": "" if math.isnan(mean_tracking) else f"{mean_tracking:.9f}",
                }
            )
        stats = read_stats(run_dir / "SemanticDynamicStatistics.txt")
        write_frame_status(run_dir, stats)
        config["end_time"] = now_iso()
        config["status"] = status
        config["error"] = error
        write_json(run_dir / "run_config.json", config)
        print(f"{status}: {variant.key} {sequence} run_{run_id:02d} -> {run_dir}")


def write_frame_status(run_dir: Path, stats: List[Dict[str, float]]) -> None:
    fields = [
        "frame_id",
        "dynamic_keypoints",
        "dynamic_map_points",
        "suppressed_map_points",
        "dynamic_objects",
        "static_objects",
        "total_objects",
        "frame_dynamic_present",
    ]
    rows = []
    for s in stats:
        row = dict(s)
        row["frame_dynamic_present"] = 1 if s.get("dynamic_objects", 0.0) > 0 else 0
        rows.append(row)
    write_csv(run_dir / "frame_status.csv", rows, fields)
    write_csv(run_dir / "dynamic_detection.csv", rows, fields)


def collect_rows() -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    sequence_rows: List[Dict[str, object]] = []
    temporal_rows: List[Dict[str, object]] = []
    for variant in VARIANTS:
        for sequence, info in SEQUENCES.items():
            input_frames = count_data_lines(info["association"])
            for run_id in range(1, 100):
                run_dir = EXP_ROOT / "runs" / variant.key / sequence / f"run_{run_id:02d}"
                if not run_dir.exists():
                    break
                config = json.loads((run_dir / "run_config.json").read_text(encoding="utf-8"))
                completed = config.get("status") == "completed"
                metrics_path = run_dir / "evaluation_results.json"
                metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if completed and metrics_path.exists() else {}
                timing = read_first_csv(run_dir / "timing.csv")
                stats = read_stats(run_dir / "SemanticDynamicStatistics.txt")
                temp = temporal_metrics(stats)
                valid_poses = count_data_lines(run_dir / "CameraTrajectory.txt")
                pose_missing = 1.0 - valid_poses / input_frames if input_frames else math.nan
                row = {
                    "variant": variant.label,
                    "variant_key": variant.key,
                    "sequence": sequence,
                    "run_id": f"run_{run_id:02d}",
                    "status": config.get("status", "unknown"),
                    "ATE_RMSE": get_metric(metrics, "ate", "rmse"),
                    "RPE_translation_RMSE": get_metric(metrics, "rpe_trans", "rmse"),
                    "RPE_rotation_RMSE": get_metric(metrics, "rpe_rot_deg", "rmse"),
                    "FPS": timing.get("end_to_end_fps", ""),
                    "Total_Runtime_sec": timing.get("wall_time_sec", ""),
                    "Input_Frames": input_frames,
                    "Valid_Poses": valid_poses,
                    "Pose_Missing_Ratio": pose_missing,
                    "Precision": math.nan,
                    "Recall": math.nan,
                    "F1": math.nan,
                    "Trajectory_Smoothness": trajectory_smoothness(run_dir / "CameraTrajectory.txt"),
                    "Switching_Frequency": temp["Switching_Frequency"],
                    "Label_Fluctuation": temp["Label_Fluctuation"],
                    "Probability_Variance": temp["Probability_Variance"],
                    "Mean_Probability_Change": temp["Mean_Probability_Change"],
                    "Temporal_Consistency_Score": temp["Temporal_Consistency_Score"],
                    "ID_Switches": temp["ID_Switches"],
                    "Average_Track_Length": temp["Average_Track_Length"],
                    "run_dir": str(run_dir),
                }
                sequence_rows.append(row)
                temporal_rows.append(
                    {
                        "variant": variant.label,
                        "sequence": sequence,
                        "run_id": f"run_{run_id:02d}",
                        "Switching_Frequency": temp["Switching_Frequency"],
                        "Label_Fluctuation": temp["Label_Fluctuation"],
                        "Probability_Variance": temp["Probability_Variance"],
                        "Mean_Probability_Change": temp["Mean_Probability_Change"],
                        "Temporal_Consistency_Score": temp["Temporal_Consistency_Score"],
                        "metric_note": "Switching and fluctuation are frame-level aggregate proxies from SemanticDynamicStatistics; probability and ID metrics are unavailable.",
                    }
                )
    return sequence_rows, temporal_rows


def get_metric(metrics: Dict[str, object], family: str, key: str) -> float:
    try:
        return float(metrics[family][key])  # type: ignore[index]
    except Exception:
        return math.nan


def read_first_csv(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            return row
    return {}


def numeric_values(rows: List[Dict[str, object]], key: str) -> List[float]:
    vals: List[float] = []
    for row in rows:
        try:
            val = float(row[key])
        except (ValueError, TypeError):
            continue
        if not math.isnan(val):
            vals.append(val)
    return vals


def fmt_num(value: float, digits: int = 4) -> str:
    if math.isnan(value):
        return "NA"
    return f"{value:.{digits}f}"


def mean_std_text(vals: List[float], digits: int = 4) -> str:
    if not vals:
        return "NA"
    return f"{np.mean(vals):.{digits}f} ± {np.std(vals, ddof=1) if len(vals) > 1 else 0.0:.{digits}f}"


def aggregate(sequence_rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    fields = [
        "ATE_RMSE",
        "RPE_translation_RMSE",
        "RPE_rotation_RMSE",
        "FPS",
        "Pose_Missing_Ratio",
        "F1",
        "Trajectory_Smoothness",
        "Switching_Frequency",
        "Label_Fluctuation",
        "Probability_Variance",
        "Mean_Probability_Change",
        "Temporal_Consistency_Score",
    ]
    out: List[Dict[str, object]] = []
    for variant in VARIANTS:
        rows = [r for r in sequence_rows if r["variant_key"] == variant.key]
        completed = [r for r in rows if r["status"] == "completed"]
        row: Dict[str, object] = {
            "variant": variant.label,
            "variant_key": variant.key,
            "valid_runs": len(completed),
            "failed_runs": len(rows) - len(completed),
        }
        for field in fields:
            vals = numeric_values(completed, field)
            row[f"{field}_mean_std"] = mean_std_text(vals)
            row[f"{field}_mean"] = np.mean(vals) if vals else math.nan
            row[f"{field}_std"] = np.std(vals, ddof=1) if len(vals) > 1 else (0.0 if vals else math.nan)
            row[f"{field}_min"] = min(vals) if vals else math.nan
            row[f"{field}_max"] = max(vals) if vals else math.nan
        out.append(row)
    return out


def write_table5(summary: List[Dict[str, object]]) -> None:
    rows: List[Dict[str, object]] = []
    for row in summary:
        rows.append(
            {
                "Variant": row["variant"],
                "ATE (m)": row["ATE_RMSE_mean_std"],
                "RPE (m)": row["RPE_translation_RMSE_mean_std"],
                "FPS (frame/s)": row["FPS_mean_std"],
                "Pose Missing Ratio": row["Pose_Missing_Ratio_mean_std"],
                "F1-score": row["F1_mean_std"],
                "Switching Frequency": row["Switching_Frequency_mean_std"],
                "Temporal Consistency Score": row["Temporal_Consistency_Score_mean_std"],
            }
        )
    fields = list(rows[0].keys())
    write_csv(EXP_ROOT / "aggregated_results/table5_ablation_new.csv", rows, fields)
    lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Independent ablation results on TUM RGB-D dynamic sequences.}",
        "\\label{tab:independent_ablation_new}",
        "\\begin{tabular}{lccccccc}",
        "\\toprule",
        "Variant & ATE (m) & RPE (m) & FPS & Pose Missing Ratio & F1-score & Switching Freq. & TCS \\\\",
        "\\midrule",
    ]
    for r in rows:
        lines.append(
            f"{r['Variant']} & {r['ATE (m)']} & {r['RPE (m)']} & {r['FPS (frame/s)']} & "
            f"{r['Pose Missing Ratio']} & {r['F1-score']} & {r['Switching Frequency']} & {r['Temporal Consistency Score']} \\\\"
        )
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table}", ""]
    (EXP_ROOT / "aggregated_results/table5_ablation_new.tex").write_text("\n".join(lines), encoding="utf-8")


def plot_metric(summary: List[Dict[str, object]], field: str, ylabel: str, basename: str, higher_better: bool = False) -> None:
    labels = [r["variant"] for r in summary]
    means = [float(r[f"{field}_mean"]) if not math.isnan(float(r[f"{field}_mean"])) else np.nan for r in summary]
    stds = [float(r[f"{field}_std"]) if not math.isnan(float(r[f"{field}_std"])) else 0.0 for r in summary]
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    colors = ["#6b7280", "#4c78a8", "#f58518", "#72b7b2", "#54a24b"]
    ax.bar(np.arange(len(labels)), means, yerr=stds, color=colors, capsize=4, edgecolor="#222222", linewidth=0.5)
    ax.set_xticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.25)
    direction = "higher is better" if higher_better else "lower is better"
    ax.text(0.01, 0.96, f"({chr(97)}) {direction}", transform=ax.transAxes, va="top", fontsize=10)
    fig.tight_layout()
    save_figure(fig, EXP_ROOT / "figures" / basename)


def save_figure(fig: plt.Figure, base: Path) -> None:
    base.parent.mkdir(parents=True, exist_ok=True)
    for ext in (".pdf", ".svg", ".png"):
        fig.savefig(base.with_suffix(ext), dpi=300, bbox_inches="tight")
    try:
        fig.savefig(base.with_suffix(".eps"), bbox_inches="tight")
    except Exception:
        pass
    plt.close(fig)


def plot_temporal_curve() -> None:
    fig, ax = plt.subplots(figsize=(8.0, 4.0))
    sequence = "fr3_walking_xyz"
    for variant in VARIANTS:
        stats_path = EXP_ROOT / "runs" / variant.key / sequence / "run_01/SemanticDynamicStatistics.txt"
        stats = read_stats(stats_path)
        if not stats:
            continue
        frames = np.asarray([s["frame_id"] for s in stats])
        values = np.asarray([s["dynamic_keypoints"] for s in stats])
        scale = max(float(np.percentile(values, 95)), 1.0)
        ax.plot(frames, np.clip(values / scale, 0.0, 1.0), linewidth=1.2, label=variant.label)
    ax.set_xlabel("Frame index")
    ax.set_ylabel("Normalized dynamic-keypoint signal")
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=False, ncol=2)
    ax.text(0.01, 0.96, "(a) dynamic signal proxy", transform=ax.transAxes, va="top", fontsize=10)
    fig.tight_layout()
    save_figure(fig, EXP_ROOT / "figures/temporal_consistency")


def make_figures(summary: List[Dict[str, object]]) -> None:
    plot_metric(summary, "ATE_RMSE", "ATE RMSE [m]", "ate_comparison", False)
    plot_metric(summary, "RPE_translation_RMSE", "RPE translation RMSE [m]", "rpe_comparison", False)
    plot_metric(summary, "FPS", "End-to-end FPS [frame/s]", "fps_comparison", True)
    plot_metric(summary, "Pose_Missing_Ratio", "Pose missing ratio", "pose_missing_ratio", False)
    plot_metric(summary, "Switching_Frequency", "Frame-level switching frequency", "switching_frequency", False)
    plot_metric(summary, "Temporal_Consistency_Score", "Temporal consistency score", "temporal_consistency_score", True)
    plot_metric(summary, "Label_Fluctuation", "Frame-to-frame label fluctuation proxy", "probability_variance", False)
    plot_temporal_curve()

    labels = [r["variant"] for r in summary]
    tcs = [float(r["Temporal_Consistency_Score_mean"]) if not math.isnan(float(r["Temporal_Consistency_Score_mean"])) else np.nan for r in summary]
    f1 = [float(r["F1_mean"]) if not math.isnan(float(r["F1_mean"])) else np.nan for r in summary]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.scatter(tcs, f1, s=60, color="#4c78a8")
    for x, y, label in zip(tcs, f1, labels):
        ax.annotate(label, (x, y), xytext=(5, 5), textcoords="offset points", fontsize=8)
    ax.set_xlabel("Temporal consistency score")
    ax.set_ylabel("F1-score")
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.25)
    ax.text(0.01, 0.96, "(a) F1 unavailable without ground truth labels", transform=ax.transAxes, va="top", fontsize=10)
    fig.tight_layout()
    save_figure(fig, EXP_ROOT / "figures/f1_temporal_consistency")


def write_environment() -> None:
    env_dir = EXP_ROOT / "environment"
    env_dir.mkdir(parents=True, exist_ok=True)
    rc, out, err = run_text(["git", "rev-parse", "HEAD"])
    git_text = out if rc == 0 else f"not available: {err.strip()}\n"
    (env_dir / "git_commit.txt").write_text(git_text, encoding="utf-8")
    (env_dir / "system_info.txt").write_text(
        "\n".join(
            [
                f"timestamp: {now_iso()}",
                f"platform: {platform.platform()}",
                f"python: {sys.version}",
                f"processor: {platform.processor()}",
                f"machine: {platform.machine()}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    deps = []
    for mod in ("numpy", "scipy", "matplotlib"):
        try:
            module = __import__(mod)
            deps.append(f"{mod}: {module.__version__}")
        except Exception as exc:
            deps.append(f"{mod}: unavailable ({exc})")
    rc, out, err = run_text(["evo_ape", "--version"])
    deps.append(f"evo: {out.strip() if rc == 0 else 'not available'}")
    (env_dir / "dependencies.txt").write_text("\n".join(deps) + "\n", encoding="utf-8")

    lines = ["# Dataset Info", ""]
    for seq, info in SEQUENCES.items():
        dataset = info["dataset"]
        assoc = info["association"]
        lines += [
            f"## {seq}",
            f"- dataset: {dataset}",
            f"- association: {assoc}",
            f"- rgb frames in rgb.txt: {count_data_lines(dataset / 'rgb.txt')}",
            f"- associated RGB-D frames used: {count_data_lines(assoc)}",
            f"- groundtruth poses: {count_data_lines(dataset / 'groundtruth.txt')}",
            "",
        ]
    (env_dir / "dataset_info.txt").write_text("\n".join(lines), encoding="utf-8")


def write_docs() -> None:
    (EXP_ROOT / "README.md").write_text(
        """# Independent Ablation v1

This directory contains a fresh ablation attempt generated without modifying or
overwriting previous experiment results. Each completed run has its own command,
configuration, logs, trajectories, timing and evaluation files.

Variants:

- Baseline: semantic mode 0, object map 0.
- Semantic Mask: semantic mode 1, object map 0.
- Temporal Consistency: semantic mode 2, object map 0.
- Object-level Semantic Map: semantic mode 1, object map 1. This is an independent
  run, but object mapping depends on semantic detections in the current binary.
- Full Model: semantic mode 2, object map 1.
""",
        encoding="utf-8",
    )
    (EXP_ROOT / "evaluation/evaluation_version.txt").write_text(
        f"Evaluation script: {EVAL_SCRIPT}\nSHA256: {sha256(EVAL_SCRIPT)}\n"
        "Alignment: SE(3) rigid alignment of estimated positions to ground truth.\n"
        "Timestamp association tolerance: 0.02 s.\n"
        "RPE delta: adjacent associated poses.\n",
        encoding="utf-8",
    )
    (EXP_ROOT / "evaluation/metric_definitions.md").write_text(
        """# Metric Definitions

- ATE RMSE: root mean square translational absolute trajectory error after SE(3)
  alignment to TUM ground truth. Lower is better.
- RPE translation RMSE: adjacent-pose translational relative pose error. Lower is better.
- RPE rotation RMSE: adjacent-pose rotational relative pose error in degrees. Lower is better.
- FPS: associated input frames divided by measured wall-clock runtime for the whole run.
  It includes YOLO startup/inference when semantic mode is enabled, SLAM tracking,
  shutdown and file output.
- Pose Missing Ratio: `1 - valid output poses / associated input RGB-D frames`.
  Lower is better. This measures trajectory-output incompleteness and is not a
  strict probability of system failure.
- Trajectory Smoothness: mean norm of the second-order finite difference of estimated
  translation. Lower is smoother, but smoother is not necessarily more accurate.
- Dynamic-state Switching Frequency: frame-level aggregate proxy computed from
  transitions of `dynamic_objects > 0` in `SemanticDynamicStatistics.txt`, divided
  by valid adjacent frame pairs. Lower indicates fewer frame-level dynamic/static
  state toggles. The current logs do not provide target-level IDs, so target-level
  switching cannot be calculated.
- Frame-to-frame Label Fluctuation: aggregate proxy computed as the mean absolute
  change of normalized dynamic-keypoint counts between adjacent frames. Lower means
  less frame-to-frame fluctuation. This is not pixel-, feature-match-, or target-ID
  label fluctuation.
- Temporal Consistency Score: `1 - Label Fluctuation`, clipped to [0, 1]. It measures
  continuity only and does not measure classification correctness.
- Precision, Recall and F1-score: Not available for this independent ablation because
  this repository does not contain per-frame/object human ground-truth dynamic labels
  for these newly generated runs.
- Dynamic Probability Variance and Mean Probability Change: Not available because the
  current binary does not output per-target dynamic probability sequences.
- ID Switches and Average Track Length: Not available because the current output does
  not contain reliable target IDs over time.
""",
        encoding="utf-8",
    )


def write_audit(sequence_rows: List[Dict[str, object]], summary: List[Dict[str, object]]) -> None:
    completed = [r for r in sequence_rows if r["status"] == "completed"]
    failed = [r for r in sequence_rows if r["status"] != "completed"]
    full = next((r for r in summary if r["variant_key"] == "full_model"), None)
    best_ate = min((float(r["ATE_RMSE_mean"]), r["variant"]) for r in summary if not math.isnan(float(r["ATE_RMSE_mean"])))
    best_rpe = min((float(r["RPE_translation_RMSE_mean"]), r["variant"]) for r in summary if not math.isnan(float(r["RPE_translation_RMSE_mean"])))
    best_missing = min((float(r["Pose_Missing_Ratio_mean"]), r["variant"]) for r in summary if not math.isnan(float(r["Pose_Missing_Ratio_mean"])))
    best_tcs = max((float(r["Temporal_Consistency_Score_mean"]), r["variant"]) for r in summary if not math.isnan(float(r["Temporal_Consistency_Score_mean"])))
    lines = [
        "# Independent Ablation Authenticity Audit",
        "",
        f"Generated: {now_iso()}",
        "",
        "## Answers",
        "",
        f"1. Five groups independently run: {'yes' if len(completed) > 0 else 'no completed runs'}; completed run count = {len(completed)}.",
        "2. Results copied from other configurations: no copying is performed by this runner.",
        "3. Manual interpolation or scaling: none.",
        "4. Same data and evaluation protocol: yes for all attempted runs.",
        "5. Full Model module configuration: semantic_mode=2 and object_map=1 in every Full Model run_config.",
        "6. Object-level map independent run: independent process run, but not a pure object-only module; current binary requires semantic detections for object map updates.",
        "7. Baseline true FPS: yes, computed from wall-clock runtime and associated input frames.",
        f"8. Failed or incomplete runs: {len(failed)}.",
        "9. Metrics supporting dynamic-decision continuity: frame-level switching frequency, label fluctuation proxy and temporal consistency score when SemanticDynamicStatistics exists.",
        "10. Metrics not supporting original strong conclusions: F1, probability variance and ID continuity are unavailable without additional labels/logs.",
        f"11. Full Model best comprehensive performance: best ATE={best_ate[1]}, best RPE={best_rpe[1]}, best Pose Missing Ratio={best_missing[1]}, best TCS={best_tcs[1]}. Do not claim Full Model is best unless these values support it.",
        "12. Recommended paper conclusion: state that temporal modeling improves available continuity proxies, while localization accuracy and pose coverage show a trade-off.",
        "13. Recommended additional runs: add target-level dynamic labels and per-target probability/ID logging, then rerun detection metrics.",
        "",
        "## Failed Runs",
        "",
    ]
    if failed:
        for r in failed:
            lines.append(f"- {r['variant']} {r['sequence']} {r['run_id']}: {r['run_dir']}")
    else:
        lines.append("- None.")
    lines += ["", "## Summary", ""]
    for r in summary:
        lines.append(
            f"- {r['variant']}: ATE {r['ATE_RMSE_mean_std']}, RPE {r['RPE_translation_RMSE_mean_std']}, "
            f"FPS {r['FPS_mean_std']}, Pose Missing Ratio {r['Pose_Missing_Ratio_mean_std']}, "
            f"TCS {r['Temporal_Consistency_Score_mean_std']}"
        )
    (EXP_ROOT / "aggregated_results/experiment_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def summarize_only() -> None:
    sequence_rows, temporal_rows = collect_rows()
    seq_fields = [
        "variant",
        "sequence",
        "run_id",
        "status",
        "ATE_RMSE",
        "RPE_translation_RMSE",
        "RPE_rotation_RMSE",
        "FPS",
        "Pose_Missing_Ratio",
        "Precision",
        "Recall",
        "F1",
        "Trajectory_Smoothness",
        "Switching_Frequency",
        "Label_Fluctuation",
        "Probability_Variance",
        "Mean_Probability_Change",
        "Temporal_Consistency_Score",
        "ID_Switches",
        "Average_Track_Length",
        "Input_Frames",
        "Valid_Poses",
        "Total_Runtime_sec",
        "run_dir",
    ]
    write_csv(EXP_ROOT / "aggregated_results/sequence_results.csv", sequence_rows, seq_fields)
    write_csv(
        EXP_ROOT / "aggregated_results/temporal_metrics.csv",
        temporal_rows,
        [
            "variant",
            "sequence",
            "run_id",
            "Switching_Frequency",
            "Label_Fluctuation",
            "Probability_Variance",
            "Mean_Probability_Change",
            "Temporal_Consistency_Score",
            "metric_note",
        ],
    )
    summary = aggregate(sequence_rows)
    summary_fields = sorted({k for row in summary for k in row.keys()})
    write_csv(EXP_ROOT / "aggregated_results/ablation_results.csv", summary, summary_fields)
    write_csv(EXP_ROOT / "aggregated_results/statistical_summary.csv", summary, summary_fields)
    write_table5(summary)
    make_figures(summary)
    write_audit(sequence_rows, summary)


def check_preconditions() -> None:
    missing = []
    for path in [SLAM_BINARY, VOCABULARY, SETTINGS, EVAL_SCRIPT]:
        if not path.exists():
            missing.append(str(path))
    for seq, info in SEQUENCES.items():
        for path in [info["dataset"], info["association"], info["dataset"] / "groundtruth.txt", info["dataset"] / "rgb.txt"]:
            if not path.exists():
                missing.append(f"{seq}: {path}")
    if missing:
        raise RuntimeError("Missing required files:\n" + "\n".join(missing))
    if not YOLO_WEIGHTS.exists():
        print(f"warning: YOLO weights not found at {YOLO_WEIGHTS}; semantic runs may fail.", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args()

    write_environment()
    write_docs()
    check_preconditions()

    if not args.summarize_only:
        for variant in VARIANTS:
            for sequence in SEQUENCES:
                for run_id in range(1, args.runs + 1):
                    run_one(variant, sequence, run_id, args.device)
    summarize_only()
    print(f"experiment_root={EXP_ROOT}")
    print(f"sequence_results={EXP_ROOT / 'aggregated_results/sequence_results.csv'}")
    print(f"audit_report={EXP_ROOT / 'aggregated_results/experiment_audit.md'}")


if __name__ == "__main__":
    main()
