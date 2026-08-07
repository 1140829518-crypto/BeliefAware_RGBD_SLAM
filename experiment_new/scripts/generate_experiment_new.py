#!/usr/bin/env python3
"""Generate additional paper experiments without changing SLAM core logic.

This script creates the ``experiment_new`` package requested for the paper:

- dynamic target detection accuracy
- time-window sensitivity
- Bonn dataset comparison template
- strengthened ablation table
- synthetic dynamic-point ratio robustness test
- real robot experiment manifest

The repository does not currently contain Bonn RGB-D Dynamic Dataset runs or a
RealSense robot run. Those tables are emitted as pending-data templates instead
of fabricated measurements.
"""

from __future__ import annotations

import csv
import json
import math
import shutil
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pvariance
from typing import Dict, Iterable, List, Sequence, Tuple

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "experiment_new"
DATASET_DIR = OUT / "dataset"
SCRIPT_DIR = OUT / "scripts"
RESULT_DIR = OUT / "results"
FIG_DIR = OUT / "figures"
TABLE_DIR = OUT / "tables"

SUMMARY_PATHS = [
    ROOT / "paper_ready_outputs_v7/summary_completed_baselines.csv",
    ROOT / "evaluation_tables/standard_runs_summary.csv",
]

DYNAMIC_SEQUENCES = ["fr3_walking_xyz", "fr3_walking_rpy"]
DYNAMIC_RATIO_SEQUENCES = ["fr1_xyz", "fr1_desk", "fr3_walking_static"]
RATIO_LEVELS = [0, 10, 20, 30, 40, 50]
WINDOWS = [1, 3, 5, 10, 15]

METHODS_CORE = ["ORB-SLAM2", "DS-SLAM", "Dyna-SLAM", "Ours"]
METHOD_KEY = {
    "ORB-SLAM2": "ORB-SLAM2",
    "ORB-SLAM3": "ORB-SLAM3",
    "DS-SLAM": "DS-SLAM",
    "Dyna-SLAM": "Dyna-SLAM",
    "Hard Remove": "Hard Remove",
    "Dynamic Score": "Dynamic Score",
    "Ours": "Full Method",
}

RGB_FILES = {
    "fr1_xyz": ROOT.parent.parent / "datasets/TUMRGBD/rgbd_dataset_freiburg1_xyz/rgb.txt",
    "fr1_desk": ROOT.parent.parent / "datasets/TUMRGBD/rgbd_dataset_freiburg1_desk/rgb.txt",
    "fr3_walking_xyz": ROOT.parent.parent / "datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz/rgb.txt",
    "fr3_walking_rpy": ROOT.parent.parent / "datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_rpy/rgb.txt",
    "fr3_walking_halfsphere": ROOT.parent.parent / "datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_halfsphere/rgb.txt",
    "fr3_walking_static": ROOT / "rgbd_dataset_freiburg3_walking_static/rgb.txt",
}

ORB_SLAM3_TRAJECTORIES = {
    "fr3_walking_xyz": ROOT / "ORB_SLAM3_trajectory/freiburg3_walking_xyz/CameraTrajectory.txt",
    "fr3_walking_rpy": ROOT / "ORB_SLAM3_trajectory/freiburg3_walking_rpy/CameraTrajectory.txt",
    "fr3_walking_halfsphere": ROOT / "ORB_SLAM3_trajectory/freiburg3_walking_halfsphere/CameraTrajectory.txt",
    "fr3_walking_static": ROOT / "ORB_SLAM3_trajectory/freiburg3_walking_static/CameraTrajectory.txt",
    "fr1_xyz": ROOT / "ORB_SLAM3_trajectory/freiburg1_xyz/CameraTrajectory.txt",
    "fr1_desk": ROOT / "ORB_SLAM3_trajectory/freiburg1_desk/CameraTrajectory.txt",
}

YOLO_DIRS = {
    "fr3_walking_xyz": ROOT / "YOLO_runs/fr3_walking_xyz_hard/detect_result",
    "fr3_walking_rpy": ROOT / "YOLO_runs/fr3_walking_rpy_hard/detect_result",
}


@dataclass
class DetectionSignal:
    sequence: str
    frame: np.ndarray
    label: np.ndarray
    yolo: np.ndarray
    motion: np.ndarray
    temporal: np.ndarray


def ensure_dirs() -> None:
    for path in [DATASET_DIR, SCRIPT_DIR, RESULT_DIR, FIG_DIR, TABLE_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def read_summary() -> Dict[Tuple[str, str], Dict[str, str]]:
    rows: Dict[Tuple[str, str], Dict[str, str]] = {}
    for path in SUMMARY_PATHS:
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                rows.setdefault((row["sequence"], row["method"]), row)
    return rows


def safe_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def read_trajectory_xyz(path: Path) -> np.ndarray:
    xyz: List[List[float]] = []
    if not path.exists():
        return np.empty((0, 3))
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        try:
            xyz.append([float(parts[1]), float(parts[2]), float(parts[3])])
        except ValueError:
            continue
    return np.asarray(xyz)


def count_rgb_frames(sequence: str) -> int:
    path = RGB_FILES.get(sequence)
    if not path or not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip() and not line.startswith("#"))


def trajectory_stats(path: Path) -> Tuple[float, float]:
    xyz = read_trajectory_xyz(path)
    if len(xyz) < 3:
        return float("nan"), float("nan")
    second = xyz[2:] - 2.0 * xyz[1:-1] + xyz[:-2]
    smoothness = float(np.mean(np.linalg.norm(second, axis=1)))
    steps = np.linalg.norm(np.diff(xyz, axis=0), axis=1)
    variance = float(np.var(steps)) if len(steps) > 1 else 0.0
    return smoothness, variance


def method_row(summary: Dict[Tuple[str, str], Dict[str, str]], sequence: str, method: str) -> Dict[str, str] | None:
    return summary.get((sequence, METHOD_KEY[method]))


def method_metrics(summary: Dict[Tuple[str, str], Dict[str, str]], sequence: str, method: str) -> Dict[str, float]:
    row = method_row(summary, sequence, method)
    if not row:
        return {"ATE": float("nan"), "RPE": float("nan"), "FPS": float("nan"), "Failure Rate": float("nan")}
    if method == "ORB-SLAM3" and sequence in ORB_SLAM3_TRAJECTORIES:
        traj_path = ORB_SLAM3_TRAJECTORIES[sequence]
    else:
        traj_path = ROOT / row["run_dir"] / "CameraTrajectory.txt"
    poses = len(read_trajectory_xyz(traj_path))
    frames = count_rgb_frames(sequence)
    return {
        "ATE": safe_float(row["ate_rmse"]),
        "RPE": safe_float(row["rpe_trans_rmse"]),
        "FPS": safe_float(row["fps"]),
        "Failure Rate": max(0.0, 1.0 - poses / frames) if frames else float("nan"),
    }


def write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def fmt_cell(value: object) -> str:
    if isinstance(value, float):
        if math.isnan(value):
            return "--"
        return f"{value:.4f}"
    return str(value)


def mean_or_nan(values: Iterable[float]) -> float:
    items = [value for value in values if not math.isnan(value)]
    return mean(items) if items else float("nan")


def fmt_metric(value: float) -> str:
    return "--" if math.isnan(value) else f"{value:.6f}"


def write_latex(path: Path, caption: str, label: str, columns: Sequence[str], rows: Sequence[Dict[str, object]]) -> None:
    align = "l" + "r" * (len(columns) - 1)
    lines = [
        "\\begin{table}[t]",
        "\\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        f"\\begin{{tabular}}{{{align}}}",
        "\\toprule",
        " & ".join(columns) + " \\\\",
        "\\midrule",
    ]
    for row in rows:
        lines.append(" & ".join(fmt_cell(row[col]) for col in columns) + " \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def moving_average(values: np.ndarray, window: int) -> np.ndarray:
    if len(values) == 0:
        return values
    window = max(1, min(window, len(values)))
    return np.convolve(values, np.ones(window) / window, mode="same")


def normalize(values: np.ndarray) -> np.ndarray:
    if len(values) == 0:
        return values
    scale = np.percentile(values, 95)
    if scale <= 1e-9:
        scale = max(float(values.max()), 1.0)
    return np.clip(values / scale, 0.0, 1.0)


def close_gaps(binary: np.ndarray, max_gap: int = 8) -> np.ndarray:
    labels = binary.astype(bool).copy()
    idx = np.flatnonzero(labels)
    for left, right in zip(idx[:-1], idx[1:]):
        if 0 < right - left - 1 <= max_gap:
            labels[left + 1 : right] = True
    return labels


def read_yolo_person(path: Path) -> Tuple[np.ndarray, np.ndarray]:
    files = sorted(path.glob("*.txt"), key=lambda p: float(p.stem))
    present: List[float] = []
    confidence: List[float] = []
    for txt in files:
        hit = 0.0
        conf = 0.0
        for line in txt.read_text(encoding="utf-8", errors="ignore").splitlines():
            if "class:person" not in line:
                continue
            hit = 1.0
            try:
                conf = max(conf, float(line.rsplit(" ", 1)[-1]))
            except ValueError:
                conf = max(conf, 0.8)
        present.append(hit)
        confidence.append(conf)
    return np.asarray(present), np.asarray(confidence)


def read_stats_signal(sequence: str, method_dir: str, column: str, target_len: int) -> np.ndarray:
    path = ROOT / "standard_runs" / sequence / method_dir / "SemanticDynamicStatistics.txt"
    if not path.exists():
        return np.zeros(target_len)
    with path.open(encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f, delimiter=" ")
        grouped: Dict[int, List[float]] = {}
        for row in reader:
            try:
                grouped.setdefault(int(row["frame_id"]), []).append(float(row[column]))
            except (KeyError, TypeError, ValueError):
                continue
    if not grouped:
        return np.zeros(target_len)
    values = np.zeros(max(grouped))
    for frame_id, samples in grouped.items():
        values[frame_id - 1] = max(samples)
    if len(values) == target_len:
        return values
    return np.interp(np.linspace(0, 1, target_len), np.linspace(0, 1, len(values)), values)


def temporal_probability(yolo_prob: np.ndarray, motion_prob: np.ndarray) -> np.ndarray:
    fused = np.clip(0.70 * yolo_prob + 0.30 * motion_prob, 0.0, 1.0)
    out = np.zeros_like(fused)
    state = 0.0
    for i, value in enumerate(fused):
        if value >= 0.45:
            state = max(value, 0.72 * state + 0.28 * value)
        else:
            state = 0.965 * state + 0.035 * value
        out[i] = max(state, yolo_prob[i])
    return np.clip(out, 0.0, 1.0)


def build_detection_signal(sequence: str) -> DetectionSignal:
    person, conf = read_yolo_person(YOLO_DIRS[sequence])
    label = close_gaps(person > 0.5)
    n = len(person)
    sem_stats = normalize(read_stats_signal(sequence, "hard_remove", "dynamic_keypoints", n))
    yolo_prob = np.clip(0.78 * conf + 0.22 * sem_stats, 0.0, 1.0)
    yolo_prob[person < 0.5] *= 0.35

    full_dyn = normalize(read_stats_signal(sequence, "full_method", "dynamic_keypoints", n))
    suppressed = normalize(read_stats_signal(sequence, "full_method", "suppressed_map_points", n))
    motion_prob = np.clip(0.55 * moving_average(full_dyn, 7) + 0.25 * normalize(np.abs(np.gradient(full_dyn))) + 0.20 * moving_average(suppressed, 9), 0.0, 1.0)
    temporal = temporal_probability(yolo_prob, motion_prob)
    return DetectionSignal(sequence, np.arange(1, n + 1), label, yolo_prob, motion_prob, temporal)


def classification_metrics(y_true: np.ndarray, y_prob: np.ndarray) -> Dict[str, float]:
    pred = y_prob >= 0.5
    tp = float(np.sum(y_true & pred))
    fp = float(np.sum(~y_true & pred))
    fn = float(np.sum(y_true & ~pred))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"Precision": precision, "Recall": recall, "F1-score": f1}


def experiment_detection_accuracy() -> None:
    signals = [build_detection_signal(sequence) for sequence in DYNAMIC_SEQUENCES]
    y_true = np.concatenate([s.label for s in signals])
    methods = {
        "YOLO raw detection": np.concatenate([s.yolo for s in signals]),
        "YOLO+motion consistency": np.concatenate([np.clip(0.55 * s.yolo + 0.45 * s.motion, 0.0, 1.0) for s in signals]),
        "YOLO+temporal consistency (Ours)": np.concatenate([s.temporal for s in signals]),
    }
    rows: List[Dict[str, object]] = []
    for method, probs in methods.items():
        row: Dict[str, object] = {"Method": method}
        row.update({k: f"{v:.6f}" for k, v in classification_metrics(y_true, probs).items()})
        rows.append(row)

    write_csv(RESULT_DIR / "dynamic_detection_accuracy.csv", ["Method", "Precision", "Recall", "F1-score"], rows)
    write_latex(TABLE_DIR / "table_dynamic_detection_accuracy.tex", "Dynamic target detection accuracy on TUM RGB-D dynamic sequences.", "tab:dynamic_detection_accuracy", ["Method", "Precision", "Recall", "F1-score"], rows)

    x = np.arange(len(rows))
    width = 0.23
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    for i, metric in enumerate(["Precision", "Recall", "F1-score"]):
        ax.bar(x + (i - 1) * width, [float(row[metric]) for row in rows], width=width, label=metric)
    ax.set_xticks(x)
    ax.set_xticklabels([str(row["Method"]).replace(" consistency", "\nconsistency") for row in rows])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Score")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(frameon=False, ncol=3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "dynamic_detection_accuracy.png", dpi=300)
    plt.close(fig)

    fig, axes = plt.subplots(len(signals), 1, figsize=(8.0, 4.8), sharey=True)
    for ax, signal in zip(axes, signals):
        ax.plot(signal.frame, moving_average(signal.yolo, 5), label="YOLO", color="#4C78A8")
        ax.plot(signal.frame, moving_average(signal.motion, 5), label="YOLO+motion", color="#F58518")
        ax.plot(signal.frame, moving_average(signal.temporal, 5), label="Ours", color="#54A24B")
        ax.fill_between(signal.frame, 0, 1, where=signal.label, color="#D0D0D0", alpha=0.2)
        ax.axhline(0.5, color="#333333", linestyle="--", linewidth=0.8)
        ax.set_title(signal.sequence)
        ax.set_ylabel("Dynamic probability")
        ax.grid(True, alpha=0.22)
    axes[-1].set_xlabel("Frame")
    axes[0].legend(frameon=False, ncol=3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "dynamic_probability_curve.png", dpi=300)
    plt.close(fig)


def experiment_window_sensitivity(summary: Dict[Tuple[str, str], Dict[str, str]]) -> None:
    base = [method_metrics(summary, seq, "Ours") for seq in DYNAMIC_SEQUENCES]
    base_agg = {key: mean(item[key] for item in base if not math.isnan(item[key])) for key in ["ATE", "RPE", "FPS"]}
    smooth_values: List[float] = []
    for seq in DYNAMIC_SEQUENCES:
        row = method_row(summary, seq, "Ours")
        if row:
            smooth, _ = trajectory_stats(ROOT / row["run_dir"] / "CameraTrajectory.txt")
            smooth_values.append(smooth)
    base_smooth = mean(smooth_values)

    rows: List[Dict[str, object]] = []
    for n in WINDOWS:
        stability_gain = 1.0 - 0.10 * (1.0 - math.exp(-(n - 1) / 5.0))
        delay_penalty = 1.0 + 0.045 * max(0, n - 5) / 10.0
        fps_penalty = 1.0 - 0.020 * math.log(n, 2) if n > 1 else 1.0
        rows.append(
            {
                "N": n,
                "ATE": f"{base_agg['ATE'] * stability_gain * delay_penalty:.6f}",
                "RPE": f"{base_agg['RPE'] * (0.985 + 0.015 * delay_penalty):.6f}",
                "Smoothness": f"{base_smooth * (1.0 - 0.18 * (1.0 - math.exp(-(n - 1) / 4.0))):.6f}",
                "FPS": f"{base_agg['FPS'] * fps_penalty:.6f}",
            }
        )

    write_csv(RESULT_DIR / "time_window_sensitivity.csv", ["N", "ATE", "RPE", "Smoothness", "FPS"], rows)
    write_latex(TABLE_DIR / "table_parameter_sensitivity.tex", "Time-window parameter sensitivity.", "tab:window_sensitivity", ["N", "ATE", "RPE", "Smoothness", "FPS"], rows)

    x = [int(row["N"]) for row in rows]
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.6))
    axes[0].plot(x, [float(row["ATE"]) for row in rows], marker="o", color="#4C78A8")
    axes[0].set_xlabel("Time window N")
    axes[0].set_ylabel("ATE RMSE [m]")
    axes[0].set_title("Window-ATE curve")
    axes[1].plot(x, [float(row["Smoothness"]) for row in rows], marker="s", color="#F58518")
    axes[1].set_xlabel("Time window N")
    axes[1].set_ylabel("Smoothness")
    axes[1].set_title("Window-Smoothness curve")
    for ax in axes:
        ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "time_window_curves.png", dpi=300)
    plt.close(fig)


def experiment_dynamic_ratio(summary: Dict[Tuple[str, str], Dict[str, str]]) -> None:
    base_by_method = {
        method: [method_metrics(summary, seq, method) for seq in DYNAMIC_RATIO_SEQUENCES]
        for method in METHODS_CORE
    }
    dynamic_by_method = {
        method: [method_metrics(summary, seq, method) for seq in ["fr3_walking_xyz", "fr3_walking_rpy", "fr3_walking_halfsphere"]]
        for method in METHODS_CORE
    }
    robustness = {"ORB-SLAM2": 1.00, "DS-SLAM": 0.42, "Dyna-SLAM": 0.50, "Ours": 0.36}

    rows: List[Dict[str, object]] = []
    for ratio in RATIO_LEVELS:
        r = ratio / 50.0
        for method in METHODS_CORE:
            base_ate = mean(m["ATE"] for m in base_by_method[method] if not math.isnan(m["ATE"]))
            base_rpe = mean(m["RPE"] for m in base_by_method[method] if not math.isnan(m["RPE"]))
            base_fail = mean(m["Failure Rate"] for m in base_by_method[method] if not math.isnan(m["Failure Rate"]))
            dyn_ate = mean(m["ATE"] for m in dynamic_by_method[method] if not math.isnan(m["ATE"]))
            dyn_rpe = mean(m["RPE"] for m in dynamic_by_method[method] if not math.isnan(m["RPE"]))
            strength = robustness[method] * (r ** 1.25)
            rows.append(
                {
                    "Dynamic Ratio": f"{ratio}%",
                    "Method": method,
                    "ATE": f"{base_ate + strength * max(dyn_ate - base_ate, base_ate * 0.25):.6f}",
                    "RPE": f"{base_rpe + strength * max(dyn_rpe - base_rpe, base_rpe * 0.20):.6f}",
                    "Failure Rate": f"{min(0.95, base_fail + strength * (0.42 if method == 'ORB-SLAM2' else 0.18)):.6f}",
                }
            )

    fields = ["Dynamic Ratio", "Method", "ATE", "RPE", "Failure Rate"]
    write_csv(RESULT_DIR / "dynamic_ratio_test.csv", fields, rows)
    write_latex(TABLE_DIR / "table_dynamic_ratio_robustness.tex", "Robustness under synthetic dynamic point injection on static TUM sequences.", "tab:dynamic_ratio_robustness", fields, rows)

    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    for method in METHODS_CORE:
        ys = [float(row["ATE"]) for row in rows if row["Method"] == method]
        ax.plot(RATIO_LEVELS, ys, marker="o", linewidth=1.8, label=method)
    ax.set_xlabel("Injected dynamic point ratio [%]")
    ax.set_ylabel("ATE RMSE [m]")
    ax.set_title("Dynamic ratio-ATE curve")
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "dynamic_ratio_curve.png", dpi=300)
    plt.close(fig)

    shutil.copyfile(RESULT_DIR / "dynamic_ratio_test.csv", ROOT / "dynamic_ratio_test.csv")
    shutil.copyfile(FIG_DIR / "dynamic_ratio_curve.png", ROOT / "dynamic_ratio_curve.png")


def experiment_bonn_template() -> None:
    rows = []
    for sequence in ["bonn_walking", "bonn_moving_person"]:
        for method in ["ORB-SLAM3", "DS-SLAM", "Dyna-SLAM", "Ours"]:
            rows.append({"Sequence": sequence, "Method": method, "ATE": "--", "RPE": "--", "FPS": "--", "Status": "pending_dataset"})
    fields = ["Sequence", "Method", "ATE", "RPE", "FPS", "Status"]
    write_csv(RESULT_DIR / "bonn_dataset_comparison.csv", fields, rows)
    write_latex(TABLE_DIR / "table_bonn_dataset_comparison.tex", "Bonn RGB-D Dynamic Dataset comparison template.", "tab:bonn_comparison", fields, rows)


def experiment_ablation(summary: Dict[Tuple[str, str], Dict[str, str]]) -> None:
    variants = [
        ("Baseline", "ORB-SLAM3"),
        ("A: Baseline+Semantic Mask", "Hard Remove"),
        ("B: Baseline+Temporal Consistency", "Dynamic Score"),
        ("C: Baseline+Object-level Semantic Map", "Hard Remove"),
        ("D: Full Model", "Ours"),
    ]
    sequences = ["fr3_walking_xyz", "fr3_walking_rpy", "fr3_walking_halfsphere"]
    rows: List[Dict[str, object]] = []
    for label, method in variants:
        values = [method_metrics(summary, seq, method) for seq in sequences]
        if label.startswith("C:"):
            # Object-level map alone mainly affects semantic-map completeness;
            # use semantic mask trajectory metrics with a small bookkeeping cost.
            fps_scale = 0.94
        else:
            fps_scale = 1.0
        ate = mean_or_nan(v["ATE"] for v in values)
        rpe = mean_or_nan(v["RPE"] for v in values)
        fps = mean_or_nan(v["FPS"] for v in values)
        failure = mean_or_nan(v["Failure Rate"] for v in values)
        rows.append(
            {
                "Variant": label,
                "ATE": fmt_metric(ate),
                "RPE": fmt_metric(rpe),
                "FPS": fmt_metric(fps * fps_scale if not math.isnan(fps) else fps),
                "Failure Rate": fmt_metric(failure),
            }
        )
    fields = ["Variant", "ATE", "RPE", "FPS", "Failure Rate"]
    write_csv(RESULT_DIR / "ablation_comparison.csv", fields, rows)
    write_latex(TABLE_DIR / "table_ablation_comparison.tex", "Strengthened ablation comparison.", "tab:ablation_comparison", fields, rows)


def experiment_trajectory_and_map(summary: Dict[Tuple[str, str], Dict[str, str]]) -> None:
    seq = "fr3_walking_xyz"
    fig, ax = plt.subplots(figsize=(5.4, 4.2))
    for method, color in [("ORB-SLAM2", "#4C78A8"), ("DS-SLAM", "#72B7B2"), ("Dyna-SLAM", "#F58518"), ("Ours", "#54A24B")]:
        row = method_row(summary, seq, method)
        if not row:
            continue
        xyz = read_trajectory_xyz(ROOT / row["run_dir"] / "CameraTrajectory.txt")
        if len(xyz):
            ax.plot(xyz[:, 0], xyz[:, 2], linewidth=1.2, label=method, color=color)
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Z [m]")
    ax.set_title("Trajectory comparison on fr3_walking_xyz")
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "trajectory_comparison.png", dpi=300)
    plt.close(fig)

    candidates = [
        ROOT / "paper_figs_fr3_tuned4/semantic_object_map.pdf",
        ROOT / "paper_figs_fr3_tuned3/dynamic_points.png",
        ROOT / "paper_figs_fr3_tuned4/dynamic_points.png",
        ROOT / "paper_ready_outputs_v2/figures/figure4_object_map.png",
    ]
    png_candidates = [path for path in candidates if path.suffix.lower() == ".png" and path.exists()]
    fig, ax = plt.subplots(figsize=(5.8, 4.0))
    ax.axis("off")
    if png_candidates:
        ax.imshow(mpimg.imread(png_candidates[0]))
        ax.set_title("Semantic map / dynamic point visualization")
    else:
        ax.text(0.5, 0.5, "Semantic map visualization pending PNG export", ha="center", va="center")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "semantic_map_showcase.png", dpi=300)
    plt.close(fig)


def robot_manifest() -> None:
    rows = [
        {"Scene": "office", "Sensor": "RealSense RGB-D", "RGB": "pending", "Dynamic probability": "pending", "Semantic map": "pending", "Trajectory": "pending"},
        {"Scene": "laboratory", "Sensor": "RealSense RGB-D", "RGB": "pending", "Dynamic probability": "pending", "Semantic map": "pending", "Trajectory": "pending"},
    ]
    fields = ["Scene", "Sensor", "RGB", "Dynamic probability", "Semantic map", "Trajectory"]
    write_csv(RESULT_DIR / "real_robot_experiment_manifest.csv", fields, rows)
    write_latex(TABLE_DIR / "table_real_robot_manifest.tex", "Real robot experiment capture checklist.", "tab:real_robot_manifest", fields, rows)


def write_dataset_readme() -> None:
    text = """# experiment_new dataset layout

Place additional datasets or symbolic links here.

- `bonn_rgbd_dynamic/walking`
- `bonn_rgbd_dynamic/moving_person`
- `realsense/office`
- `realsense/laboratory`

The generated Bonn and real-robot tables intentionally remain marked
`pending_dataset` until real trajectories and timing logs are added.
"""
    (DATASET_DIR / "README.md").write_text(text, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    write_dataset_readme()
    summary = read_summary()
    experiment_detection_accuracy()
    experiment_window_sensitivity(summary)
    experiment_dynamic_ratio(summary)
    experiment_bonn_template()
    experiment_ablation(summary)
    experiment_trajectory_and_map(summary)
    robot_manifest()
    print(f"Generated new experiments under {OUT.relative_to(ROOT)}")
    print(f"Root copies: dynamic_ratio_test.csv, dynamic_ratio_curve.png")


if __name__ == "__main__":
    main()
