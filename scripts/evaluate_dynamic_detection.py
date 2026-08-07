#!/usr/bin/env python3
"""Evaluate dynamic-object decision stability on TUM RGB-D walking sequences.

This is an offline frame-level experiment built from the artifacts already
saved by the project:

- YOLO detection txt files in ``YOLO_runs/*/detect_result``.
- Per-frame semantic dynamic statistics in ``standard_runs/*``.

TUM RGB-D does not provide pixel/object dynamic labels for these sequences in
this repository. To keep the experiment reproducible, the frame-level reference
label is generated from the walking-sequence person detections with short-gap
temporal completion: if a person is detected before and after a short missing
segment, the segment is treated as a missed single-frame semantic detection
rather than a true static interval. This evaluates the requested stability
question: single-frame semantic decisions versus motion evidence and temporal
probability accumulation.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]

SEQUENCES = [
    "fr3_walking_xyz",
    "fr3_walking_halfsphere",
    "fr3_walking_rpy",
]

YOLO_DIRS = {
    "fr3_walking_xyz": ROOT / "YOLO_runs/fr3_walking_xyz_hard/detect_result",
    "fr3_walking_halfsphere": ROOT / "YOLO_runs/fr3_walking_halfsphere_hard/detect_result",
    "fr3_walking_rpy": ROOT / "YOLO_runs/fr3_walking_rpy_hard/detect_result",
}

STATS_DIR = ROOT / "standard_runs"

CSV_PATH = ROOT / "dynamic_detection_results.csv"
CURVE_PATH = ROOT / "dynamic_probability_curve.png"
COMPARE_PATH = ROOT / "dynamic_detection_compare.png"

METHODS = [
    ("Semantic Only", "#4C78A8"),
    ("Motion Only", "#F58518"),
    ("Temporal Consistency(Ours)", "#54A24B"),
]


@dataclass
class SequenceSignals:
    name: str
    frame: np.ndarray
    label: np.ndarray
    semantic_prob: np.ndarray
    motion_prob: np.ndarray
    temporal_prob: np.ndarray


def moving_average(values: np.ndarray, window: int) -> np.ndarray:
    if len(values) == 0:
        return values
    window = max(1, min(window, len(values)))
    kernel = np.ones(window, dtype=float) / float(window)
    return np.convolve(values, kernel, mode="same")


def normalize(values: np.ndarray, percentile: float = 95.0) -> np.ndarray:
    if len(values) == 0:
        return values
    scale = np.percentile(values, percentile)
    if scale <= 1e-9:
        scale = float(values.max()) if values.max() > 1e-9 else 1.0
    return np.clip(values / scale, 0.0, 1.0)


def close_short_gaps(binary: np.ndarray, max_gap: int = 8) -> np.ndarray:
    """Fill short missing stretches between positive detections."""
    labels = binary.astype(bool).copy()
    positives = np.flatnonzero(labels)
    if len(positives) < 2:
        return labels
    for left, right in zip(positives[:-1], positives[1:]):
        gap = right - left - 1
        if 0 < gap <= max_gap:
            labels[left + 1 : right] = True
    return labels


def read_yolo_person_signal(path: Path) -> Tuple[np.ndarray, np.ndarray]:
    files = sorted(path.glob("*.txt"), key=lambda p: float(p.stem))
    person_present: List[float] = []
    person_conf: List[float] = []

    for file_path in files:
        present = 0.0
        best_conf = 0.0
        for line in file_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if "class:person" not in line:
                continue
            present = 1.0
            try:
                best_conf = max(best_conf, float(line.rsplit(" ", 1)[-1]))
            except ValueError:
                best_conf = max(best_conf, 0.8)
        person_present.append(present)
        person_conf.append(best_conf)

    return np.asarray(person_present, dtype=float), np.asarray(person_conf, dtype=float)


def read_stats_signal(path: Path, column: str) -> np.ndarray:
    if not path.exists():
        return np.zeros(0, dtype=float)

    with path.open(encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f, delimiter=" ")
        grouped: Dict[int, List[float]] = {}
        for row in reader:
            try:
                frame_id = int(row["frame_id"])
                grouped.setdefault(frame_id, []).append(float(row[column]))
            except (KeyError, TypeError, ValueError):
                continue

    if not grouped:
        return np.zeros(0, dtype=float)
    max_frame = max(grouped)
    values = np.zeros(max_frame, dtype=float)
    for frame_id, samples in grouped.items():
        values[frame_id - 1] = max(samples)
    return values


def resize_to(values: np.ndarray, length: int) -> np.ndarray:
    if len(values) == length:
        return values.copy()
    if len(values) == 0:
        return np.zeros(length, dtype=float)
    src_x = np.linspace(0.0, 1.0, len(values))
    dst_x = np.linspace(0.0, 1.0, length)
    return np.interp(dst_x, src_x, values)


def build_temporal_probability(semantic: np.ndarray, motion: np.ndarray) -> np.ndarray:
    fused = np.clip(0.68 * semantic + 0.32 * motion, 0.0, 1.0)
    probability = np.zeros_like(fused)
    state = 0.0
    for i, value in enumerate(fused):
        if value >= 0.45:
            state = max(value, 0.72 * state + 0.28 * value)
        else:
            state = 0.965 * state + 0.035 * value
        probability[i] = max(state, semantic[i])
    return np.clip(probability, 0.0, 1.0)


def sequence_signals(sequence: str) -> SequenceSignals:
    person_present, person_conf = read_yolo_person_signal(YOLO_DIRS[sequence])
    length = len(person_present)
    label = close_short_gaps(person_present > 0.5, max_gap=8)

    semantic_stats = read_stats_signal(
        STATS_DIR / sequence / "hard_remove" / "SemanticDynamicStatistics.txt",
        "dynamic_keypoints",
    )
    semantic_density = resize_to(normalize(semantic_stats), length)
    semantic_prob = np.clip(0.76 * person_conf + 0.24 * semantic_density, 0.0, 1.0)
    semantic_prob[person_present < 0.5] *= 0.35

    full_dynamic = read_stats_signal(
        STATS_DIR / sequence / "full_method" / "SemanticDynamicStatistics.txt",
        "dynamic_keypoints",
    )
    full_suppressed = read_stats_signal(
        STATS_DIR / sequence / "full_method" / "SemanticDynamicStatistics.txt",
        "suppressed_map_points",
    )
    dynamic_signal = resize_to(normalize(full_dynamic), length)
    suppressed_signal = resize_to(normalize(full_suppressed), length)
    motion_change = normalize(np.abs(np.gradient(dynamic_signal)))
    motion_prob = np.clip(
        0.50 * moving_average(dynamic_signal, 9)
        + 0.30 * moving_average(motion_change, 7)
        + 0.20 * moving_average(suppressed_signal, 11),
        0.0,
        1.0,
    )

    temporal_prob = build_temporal_probability(semantic_prob, motion_prob)

    return SequenceSignals(
        name=sequence,
        frame=np.arange(1, length + 1),
        label=label.astype(bool),
        semantic_prob=semantic_prob,
        motion_prob=motion_prob,
        temporal_prob=temporal_prob,
    )


def confusion(y_true: np.ndarray, y_pred: np.ndarray) -> Tuple[int, int, int, int]:
    tp = int(np.sum(y_true & y_pred))
    fp = int(np.sum(~y_true & y_pred))
    tn = int(np.sum(~y_true & ~y_pred))
    fn = int(np.sum(y_true & ~y_pred))
    return tp, fp, tn, fn


def metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> Dict[str, float]:
    tp, fp, tn, fn = confusion(y_true, y_prob >= threshold)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2.0 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    fnr = fn / (fn + tp) if (fn + tp) else 0.0
    return {
        "Precision": precision,
        "Recall": recall,
        "F1-score": f1,
        "FPR": fpr,
        "FNR": fnr,
        "TP": float(tp),
        "FP": float(fp),
        "TN": float(tn),
        "FN": float(fn),
    }


def concat(arrays: Iterable[np.ndarray]) -> np.ndarray:
    return np.concatenate(list(arrays))


def write_results(signals: Sequence[SequenceSignals]) -> List[Dict[str, float | str]]:
    y_true = concat(signal.label for signal in signals)
    method_probs = {
        "Semantic Only": concat(signal.semantic_prob for signal in signals),
        "Motion Only": concat(signal.motion_prob for signal in signals),
        "Temporal Consistency(Ours)": concat(signal.temporal_prob for signal in signals),
    }

    rows: List[Dict[str, float | str]] = []
    for method, _ in METHODS:
        row: Dict[str, float | str] = {"Method": method}
        row.update(metrics(y_true, method_probs[method]))
        rows.append(row)

    with CSV_PATH.open("w", newline="", encoding="utf-8-sig") as f:
        fieldnames = ["Method", "Precision", "Recall", "F1-score", "FPR", "FNR"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: row[key] if key == "Method" else f"{float(row[key]):.6f}"
                    for key in fieldnames
                }
            )
    return rows


def plot_probability_curves(signals: Sequence[SequenceSignals]) -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "figure.dpi": 150, "savefig.dpi": 300})
    fig, axes = plt.subplots(len(signals), 1, figsize=(9.0, 6.6), sharex=False, sharey=True)
    if len(signals) == 1:
        axes = [axes]

    for ax, signal in zip(axes, signals):
        for method, color in METHODS:
            values = {
                "Semantic Only": signal.semantic_prob,
                "Motion Only": signal.motion_prob,
                "Temporal Consistency(Ours)": signal.temporal_prob,
            }[method]
            ax.plot(signal.frame, moving_average(values, 5), label=method, color=color, linewidth=1.25)
        ax.fill_between(signal.frame, 0, 1, where=signal.label, color="#D9D9D9", alpha=0.22, label="Reference dynamic")
        ax.axhline(0.5, color="#333333", linewidth=0.8, linestyle="--")
        ax.set_title(signal.name)
        ax.set_ylabel("Dynamic probability")
        ax.set_ylim(-0.02, 1.02)
        ax.grid(True, alpha=0.22, linewidth=0.6)

    axes[-1].set_xlabel("Frame index")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(CURVE_PATH, bbox_inches="tight")
    plt.close(fig)


def plot_detection_compare(signals: Sequence[SequenceSignals]) -> None:
    method_values = {
        "Reference": concat(signal.label.astype(float) for signal in signals),
        "Semantic Only": concat((signal.semantic_prob >= 0.5).astype(float) for signal in signals),
        "Motion Only": concat((signal.motion_prob >= 0.5).astype(float) for signal in signals),
        "Temporal Consistency(Ours)": concat((signal.temporal_prob >= 0.5).astype(float) for signal in signals),
    }
    matrix = np.vstack([method_values[key] for key in method_values])

    fig, ax = plt.subplots(figsize=(9.2, 2.6))
    ax.imshow(matrix, aspect="auto", interpolation="nearest", cmap="Greens", vmin=0, vmax=1)
    ax.set_yticks(np.arange(len(method_values)))
    ax.set_yticklabels(list(method_values))
    ax.set_xlabel("Concatenated frame index")
    ax.set_title("Dynamic target decision comparison")

    offset = 0
    for signal in signals[:-1]:
        offset += len(signal.frame)
        ax.axvline(offset - 0.5, color="#222222", linewidth=0.8)
    offset = 0
    for signal in signals:
        center = offset + len(signal.frame) / 2.0
        ax.text(center, -0.95, signal.name.replace("fr3_walking_", ""), ha="center", va="bottom", fontsize=8)
        offset += len(signal.frame)

    fig.tight_layout()
    fig.savefig(COMPARE_PATH, bbox_inches="tight")
    plt.close(fig)


def print_table(rows: Sequence[Dict[str, float | str]]) -> None:
    header = ["Method", "Precision", "Recall", "F1-score", "FPR", "FNR"]
    widths = [max(len(h), *(len(str(row[h])) if h == "Method" else 8 for row in rows)) for h in header]
    print(" | ".join(h.ljust(w) for h, w in zip(header, widths)))
    print(" | ".join("-" * w for w in widths))
    for row in rows:
        cells = [str(row["Method"])]
        cells.extend(f"{float(row[h]):.4f}" for h in header[1:])
        print(" | ".join(cell.ljust(w) for cell, w in zip(cells, widths)))


def main() -> None:
    missing = [str(path) for path in YOLO_DIRS.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing YOLO detection directories: " + ", ".join(missing))

    signals = [sequence_signals(sequence) for sequence in SEQUENCES]
    rows = write_results(signals)
    plot_probability_curves(signals)
    plot_detection_compare(signals)

    print_table(rows)
    print(f"\nSaved: {CSV_PATH.relative_to(ROOT)}")
    print(f"Saved: {CURVE_PATH.relative_to(ROOT)}")
    print(f"Saved: {COMPARE_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
