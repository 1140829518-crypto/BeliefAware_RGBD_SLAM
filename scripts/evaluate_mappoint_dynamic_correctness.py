#!/usr/bin/env python3
"""Auditable offline MapPoint-observation dynamic-state correctness evaluation.

This script never runs SLAM and never constructs ground truth from predictions.
It joins existing projection observations to independently annotated binary masks.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

import cv2
import numpy as np


REPO = Path(__file__).resolve().parents[1]
METHODS = ("Semantic", "Temporal")
SEQUENCES = (
    "fr3_walking_xyz",
    "fr3_walking_rpy",
    "fr3_walking_halfsphere",
)
RATIO_THRESHOLDS = (0.1, 0.2, 0.3)

DEFAULT_GT_ROOT = (
    REPO / "experiments/final_paper/04_appendix_logs/annotation/annotation_v2"
)
DEFAULT_PROGRESS = (
    REPO / "experiments/final_paper/04_appendix_logs/annotation/annotation_progress.csv"
)
DEFAULT_SELECTED = (
    REPO / "experiments/final_paper/04_appendix_logs/annotation/selected_frames_v2.csv"
)
DEFAULT_OBSERVATIONS = (
    REPO / "experiments/final_paper/03_mappoint_temporal_analysis/mappoint_observations_v2.csv"
)
DEFAULT_SF = REPO / "results/paa_prl/summary/configuration_sequence_summary.csv"
DEFAULT_OUTPUT = REPO / "results/paa_prl_limitation2/correctness"


def timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else math.nan


def metrics(tp: int, fp: int, tn: int, fn: int) -> Dict[str, float]:
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    specificity = safe_div(tn, tn + fp)
    f1 = safe_div(2 * tp, 2 * tp + fp + fn)
    balanced = (recall + specificity) / 2 if math.isfinite(recall) and math.isfinite(specificity) else math.nan
    return {
        "Precision": precision,
        "Recall_TPR": recall,
        "F1": f1,
        "Specificity_TNR": specificity,
        "Balanced_Accuracy": balanced,
        "FPR": safe_div(fp, fp + tn),
        "FNR": safe_div(fn, fn + tp),
        "Accuracy": safe_div(tp + tn, tp + fp + tn + fn),
    }


def fmt(value: object) -> object:
    if isinstance(value, float):
        return "" if not math.isfinite(value) else f"{value:.9f}"
    return value


def write_csv(path: Path, rows: Iterable[Mapping[str, object]], fields: Sequence[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: fmt(row.get(field, "")) for field in fields})


def load_completed_frames(progress_path: Path) -> Dict[str, set[int]]:
    completed = {sequence: set() for sequence in SEQUENCES}
    with progress_path.open(encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            sequence = row["sequence"]
            if sequence in completed and int(row["completed"]) == 1:
                completed[sequence].add(int(row["frame_id"]))
    return completed


def load_selected_timestamps(path: Path) -> Dict[Tuple[str, int], float]:
    result: Dict[Tuple[str, int], float] = {}
    with path.open(encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            sequence = row["sequence"]
            if sequence in SEQUENCES:
                result[(sequence, int(row["frame_id"]))] = float(row["timestamp"])
    return result


def load_sf(path: Path) -> Dict[Tuple[str, str], float]:
    result: Dict[Tuple[str, str], float] = {}
    with path.open(encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            method = row["configuration"]
            sequence = row["sequence"]
            if method in METHODS and sequence in SEQUENCES:
                value = row.get("SF_mean", "")
                if value:
                    result[(method, sequence)] = float(value)
    return result


def boundary_band(gt: np.ndarray, radius: int = 2) -> np.ndarray:
    """Return a Chebyshev-radius boundary band on both sides of GT edges.

    A 5x5 square structuring element for radius=2 dilates two pixels outward and
    erodes two pixels inward. Pixels where these results differ are excluded.
    """
    binary = (gt == 255).astype(np.uint8)
    kernel = np.ones((2 * radius + 1, 2 * radius + 1), dtype=np.uint8)
    dilated = cv2.dilate(binary, kernel, iterations=1)
    eroded = cv2.erode(binary, kernel, iterations=1)
    return dilated != eroded


def confusion_update(counts: Dict[str, int], truth: bool, prediction: bool) -> None:
    if truth and prediction:
        counts["TP"] += 1
    elif not truth and prediction:
        counts["FP"] += 1
    elif not truth and not prediction:
        counts["TN"] += 1
    else:
        counts["FN"] += 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gt-root", type=Path, default=DEFAULT_GT_ROOT)
    parser.add_argument("--progress", type=Path, default=DEFAULT_PROGRESS)
    parser.add_argument("--selected-frames", type=Path, default=DEFAULT_SELECTED)
    parser.add_argument("--observations", type=Path, default=DEFAULT_OBSERVATIONS)
    parser.add_argument("--sf-summary", type=Path, default=DEFAULT_SF)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    inputs = [args.gt_root, args.progress, args.selected_frames, args.observations, args.sf_summary]
    missing_inputs = [str(path) for path in inputs if not path.exists()]
    if missing_inputs:
        raise FileNotFoundError("Missing required inputs: " + ", ".join(missing_inputs))
    if args.output.exists() and any(args.output.iterdir()):
        raise RuntimeError(f"Refusing to overwrite non-empty output directory: {args.output}")
    args.output.mkdir(parents=True, exist_ok=True)

    completed = load_completed_frames(args.progress)
    selected_timestamps = load_selected_timestamps(args.selected_frames)
    sf = load_sf(args.sf_summary)

    expected_frames = {(sequence, frame_id) for sequence, frames in completed.items() for frame_id in frames}
    mask_cache: Dict[Tuple[str, int], Tuple[np.ndarray, np.ndarray, np.ndarray] | None] = {}
    missing_gt: List[str] = []
    missing_ignore: List[str] = []
    invalid_masks: List[str] = []
    for sequence, frame_id in sorted(expected_frames):
        gt_path = args.gt_root / sequence / f"frame_{frame_id:04d}_gt.png"
        ignore_path = args.gt_root / sequence / f"frame_{frame_id:04d}_ignore.png"
        if not gt_path.exists():
            missing_gt.append(str(gt_path)); mask_cache[(sequence, frame_id)] = None; continue
        if not ignore_path.exists():
            missing_ignore.append(str(ignore_path)); mask_cache[(sequence, frame_id)] = None; continue
        gt = cv2.imread(str(gt_path), cv2.IMREAD_UNCHANGED)
        ignore = cv2.imread(str(ignore_path), cv2.IMREAD_UNCHANGED)
        if gt is None or ignore is None or gt.ndim != 2 or ignore.ndim != 2 or gt.shape != ignore.shape:
            invalid_masks.append(f"{sequence}/{frame_id}: unreadable/non-grayscale/shape mismatch")
            mask_cache[(sequence, frame_id)] = None; continue
        if not set(np.unique(gt)).issubset({0, 255}) or not set(np.unique(ignore)).issubset({0, 255}):
            invalid_masks.append(f"{sequence}/{frame_id}: masks are not binary 0/255")
            mask_cache[(sequence, frame_id)] = None; continue
        mask_cache[(sequence, frame_id)] = (gt, ignore, boundary_band(gt, 2))

    # Last record wins for duplicate matcher-path updates in one frame.
    dedup: Dict[Tuple[str, str, str, int, int], Dict[str, str]] = {}
    raw_relevant = defaultdict(int)
    raw_all = 0
    duplicate_count = defaultdict(int)
    timestamp_mismatches: List[str] = []
    with args.observations.open(encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            raw_all += 1
            method, sequence = row["method"], row["sequence"]
            if method not in METHODS or sequence not in SEQUENCES:
                continue
            frame_id = int(row["frame_id"])
            if (sequence, frame_id) not in expected_frames:
                continue
            raw_relevant[(method, sequence)] += 1
            expected_stamp = selected_timestamps.get((sequence, frame_id))
            if expected_stamp is None or abs(float(row["timestamp"]) - expected_stamp) > 1e-6:
                if len(timestamp_mismatches) < 100:
                    timestamp_mismatches.append(
                        f"{method}/{sequence}/{row['run_id']}/frame={frame_id}: "
                        f"observation={row['timestamp']} selected={expected_stamp}"
                    )
            key = (method, sequence, row["run_id"], frame_id, int(row["map_point_id"]))
            if key in dedup:
                duplicate_count[(method, sequence)] += 1
            dedup[key] = row

    audit_counts: Dict[Tuple[str, str], Dict[str, int]] = {
        (method, sequence): defaultdict(int) for method in METHODS for sequence in SEQUENCES
    }
    observation_rows: List[Dict[str, object]] = []
    used_frames: Dict[Tuple[str, str], set[int]] = defaultdict(set)
    mp_observations: Dict[Tuple[str, str, str, int], List[Tuple[bool, bool]]] = defaultdict(list)
    sequence_counts: Dict[Tuple[str, str], Dict[str, int]] = {
        (method, sequence): {"TP": 0, "FP": 0, "TN": 0, "FN": 0}
        for method in METHODS for sequence in SEQUENCES
    }

    for key, row in dedup.items():
        method, sequence, run_id, frame_id, map_point_id = key
        counts = audit_counts[(method, sequence)]
        counts["deduplicated_observations"] += 1
        masks = mask_cache.get((sequence, frame_id))
        if masks is None:
            counts["missing_or_invalid_mask"] += 1
            continue
        gt, ignore, boundary = masks
        u_float, v_float = float(row["u"]), float(row["v"])
        u, v = int(round(u_float)), int(round(v_float))
        if not (0 <= u < gt.shape[1] and 0 <= v < gt.shape[0]):
            counts["out_of_bounds"] += 1
            continue
        if ignore[v, u] == 255:
            counts["manual_ignore_excluded"] += 1
            continue
        if boundary[v, u]:
            counts["boundary_ignore_excluded"] += 1
            continue
        truth = bool(gt[v, u] == 255)
        prediction = bool(int(row["semantic_state"])) if method == "Semantic" else bool(int(row["temporal_state"]))
        confusion_update(sequence_counts[(method, sequence)], truth, prediction)
        counts["evaluated_observations"] += 1
        used_frames[(method, sequence)].add(frame_id)
        mp_observations[(method, sequence, run_id, map_point_id)].append((truth, prediction))
        observation_rows.append({
            "method": method, "sequence": sequence, "run_id": run_id,
            "frame_id": frame_id, "map_point_id": map_point_id,
            "u": u_float, "v": v_float, "class_id": int(row["class_id"]),
            "gt_dynamic": int(truth), "pred_dynamic": int(prediction),
            "semantic_state": int(row["semantic_state"]),
            "temporal_state": int(row["temporal_state"]),
            "temporal_score": float(row["temporal_score"]),
            "threshold": float(row["threshold"]),
        })

    sequence_rows: List[Dict[str, object]] = []
    confusion_rows: List[Dict[str, object]] = []
    for sequence in SEQUENCES:
        for method in METHODS:
            c = sequence_counts[(method, sequence)]
            total = sum(c.values())
            rate = metrics(c["TP"], c["FP"], c["TN"], c["FN"])
            row: Dict[str, object] = {
                "Sequence": sequence, "Configuration": method,
                "Evaluated_observations": total,
                "Annotated_frames_used": len(used_frames[(method, sequence)]),
                "Dynamic_prevalence": safe_div(c["TP"] + c["FN"], total),
                **c, **rate, "SF": sf.get((method, sequence), math.nan),
            }
            sequence_rows.append(row)
            confusion_rows.append({
                "Sequence": sequence, "Configuration": method, **c,
                "Evaluated_observations": total,
            })

    rate_fields = ("Dynamic_prevalence", "Precision", "Recall_TPR", "F1", "Specificity_TNR",
                   "Balanced_Accuracy", "FPR", "FNR", "Accuracy", "SF")
    macro_rows: List[Dict[str, object]] = []
    pooled_rows: List[Dict[str, object]] = []
    for method in METHODS:
        members = [row for row in sequence_rows if row["Configuration"] == method]
        macro = {"Sequence": "Macro average", "Configuration": method,
                 "Evaluated_observations": sum(int(row["Evaluated_observations"]) for row in members),
                 "Annotated_frames_used": sum(int(row["Annotated_frames_used"]) for row in members)}
        for field in rate_fields:
            values = [float(row[field]) for row in members if math.isfinite(float(row[field]))]
            macro[field] = sum(values) / len(values) if values else math.nan
        for field in ("TP", "FP", "TN", "FN"):
            macro[field] = ""
        macro_rows.append(macro)

        pooled_counts = {field: sum(int(row[field]) for row in members) for field in ("TP", "FP", "TN", "FN")}
        total = sum(pooled_counts.values())
        pooled = {"Sequence": "Pooled/micro", "Configuration": method,
                  "Evaluated_observations": total,
                  "Annotated_frames_used": sum(int(row["Annotated_frames_used"]) for row in members),
                  "Dynamic_prevalence": safe_div(pooled_counts["TP"] + pooled_counts["FN"], total),
                  **pooled_counts, **metrics(**{k.lower(): v for k, v in pooled_counts.items()}), "SF": math.nan}
        pooled_rows.append(pooled)

    all_summary_rows = sequence_rows + macro_rows + pooled_rows

    # Secondary persistent MapPoint aggregation, never used as the primary result.
    mp_detail_rows: List[Dict[str, object]] = []
    ratio_counts: Dict[Tuple[float, str, str], Dict[str, int]] = defaultdict(
        lambda: {"TP": 0, "FP": 0, "TN": 0, "FN": 0}
    )
    for (method, sequence, run_id, map_point_id), observations in mp_observations.items():
        gt_ratio = sum(truth for truth, _ in observations) / len(observations)
        pred_ratio = sum(pred for _, pred in observations) / len(observations)
        detail: Dict[str, object] = {
            "method": method, "sequence": sequence, "run_id": run_id,
            "map_point_id": map_point_id, "evaluated_observations": len(observations),
            "gt_dynamic_ratio": gt_ratio, "pred_dynamic_ratio": pred_ratio,
        }
        for ratio in RATIO_THRESHOLDS:
            truth, prediction = gt_ratio >= ratio, pred_ratio >= ratio
            confusion_update(ratio_counts[(ratio, method, sequence)], truth, prediction)
            detail[f"gt_state_at_{ratio:g}"] = int(truth)
            detail[f"pred_state_at_{ratio:g}"] = int(prediction)
        mp_detail_rows.append(detail)

    ratio_rows: List[Dict[str, object]] = []
    for ratio in RATIO_THRESHOLDS:
        for sequence in SEQUENCES:
            for method in METHODS:
                c = ratio_counts[(ratio, method, sequence)]
                ratio_rows.append({"ratio_threshold": ratio, "Sequence": sequence,
                                   "Configuration": method, "MapPoints": sum(c.values()),
                                   **c, **metrics(c["TP"], c["FP"], c["TN"], c["FN"])})
        for method in METHODS:
            members = [row for row in ratio_rows if row["ratio_threshold"] == ratio
                       and row["Configuration"] == method and row["Sequence"] in SEQUENCES]
            row = {"ratio_threshold": ratio, "Sequence": "Macro average", "Configuration": method,
                   "MapPoints": sum(int(member["MapPoints"]) for member in members)}
            for field in ("Precision", "Recall_TPR", "F1", "Specificity_TNR", "Balanced_Accuracy",
                          "FPR", "FNR", "Accuracy"):
                values = [float(member[field]) for member in members if math.isfinite(float(member[field]))]
                row[field] = sum(values) / len(values) if values else math.nan
            for field in ("TP", "FP", "TN", "FN"):
                row[field] = ""
            ratio_rows.append(row)

    observation_fields = ("method", "sequence", "run_id", "frame_id", "map_point_id", "u", "v",
                          "class_id", "gt_dynamic", "pred_dynamic", "semantic_state", "temporal_state",
                          "temporal_score", "threshold")
    summary_fields = ("Sequence", "Configuration", "Evaluated_observations", "Annotated_frames_used",
                      "Dynamic_prevalence", "TP", "FP", "TN", "FN", "Precision", "Recall_TPR", "F1",
                      "Specificity_TNR", "Balanced_Accuracy", "FPR", "FNR", "Accuracy", "SF")
    write_csv(args.output / "correctness_observation_level.csv", observation_rows, observation_fields)
    write_csv(args.output / "correctness_confusion_counts.csv", confusion_rows,
              ("Sequence", "Configuration", "Evaluated_observations", "TP", "FP", "TN", "FN"))
    write_csv(args.output / "correctness_sequence_summary.csv", all_summary_rows, summary_fields)
    mp_fields = ("method", "sequence", "run_id", "map_point_id", "evaluated_observations",
                 "gt_dynamic_ratio", "pred_dynamic_ratio") + tuple(
        item for ratio in RATIO_THRESHOLDS for item in (f"gt_state_at_{ratio:g}", f"pred_state_at_{ratio:g}")
    )
    write_csv(args.output / "correctness_mappoint_level_secondary.csv", mp_detail_rows, mp_fields)
    ratio_fields = ("ratio_threshold", "Sequence", "Configuration", "MapPoints", "TP", "FP", "TN", "FN",
                    "Precision", "Recall_TPR", "F1", "Specificity_TNR", "Balanced_Accuracy", "FPR", "FNR", "Accuracy")
    write_csv(args.output / "correctness_ratio_sensitivity.csv", ratio_rows, ratio_fields)

    input_files = [args.progress, args.selected_frames, args.observations, args.sf_summary]
    mask_files = sorted(args.gt_root.glob("*/*_gt.png")) + sorted(args.gt_root.glob("*/*_ignore.png"))
    protocol = {
        "created_at": timestamp(),
        "gt_annotation_path": str(args.gt_root.resolve()),
        "gt_annotation_version": "annotation_v2; completed human masks with five-frame context",
        "evaluated_sequences": list(SEQUENCES),
        "annotated_frame_count": {sequence: len(completed[sequence]) for sequence in SEQUENCES},
        "evaluation_unit": "(method, sequence, run_id, frame_id, map_point_id) MapPoint observation",
        "deduplication_policy": "last CSV record wins within each evaluation-unit key; IDs are never joined across runs",
        "boundary_ignore": "2-pixel Chebyshev-radius band on both sides of GT boundary, implemented as 5x5-square dilation != erosion",
        "mask_interpretation": "GT 255=dynamic; GT 0=static unless manual-ignore or boundary-ignore; ignore 255=excluded",
        "ground_truth_independence": "Human GT only; no YOLO/Semantic/Temporal output is used to construct GT",
        "metrics": {
            "Precision": "TP/(TP+FP)", "Recall_TPR": "TP/(TP+FN)", "F1": "2TP/(2TP+FP+FN)",
            "Specificity_TNR": "TN/(TN+FP)", "Balanced_Accuracy": "(TPR+TNR)/2",
            "FPR": "FP/(FP+TN)", "FNR": "FN/(FN+TP)", "Accuracy": "(TP+TN)/all",
        },
        "macro_average": "unweighted arithmetic mean of the three sequence-level rates; never a pooled observation rate",
        "pooled_result": "reported separately as Pooled/micro",
        "secondary_mappoint_ratio_thresholds": list(RATIO_THRESHOLDS),
        "script_path": str(Path(__file__).resolve()),
        "script_sha256": sha256(Path(__file__).resolve()),
        "input_files": {str(path.resolve()): sha256(path) for path in input_files},
        "mask_manifest": {"file_count": len(mask_files),
                          "combined_sha256": hashlib.sha256("".join(sha256(path) for path in mask_files).encode()).hexdigest()},
    }
    (args.output / "correctness_protocol.json").write_text(
        json.dumps(protocol, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    audit_lines = [
        "# Dynamic-State Correctness Audit", "", f"- Executed: `{protocol['created_at']}`",
        f"- Script: `{protocol['script_path']}`", f"- Script SHA-256: `{protocol['script_sha256']}`",
        "- Ground truth: the same independently annotated `annotation_v2` masks are used for Semantic and Temporal.",
        "- Prediction leakage: none in GT construction; predictions are read only after GT masks are fixed.",
        "- Boundary ignore: executed as a fixed 2-pixel Chebyshev-radius band (`5x5 dilation != erosion`).", "",
        "## Input integrity", "",
        f"- Raw CSV records (all): {raw_all}",
        f"- Missing GT masks: {len(missing_gt)}", f"- Missing ignore masks: {len(missing_ignore)}",
        f"- Invalid masks: {len(invalid_masks)}", f"- Timestamp mismatches (>1e-6 s): {len(timestamp_mismatches)}", "",
        "## Observation accounting", "",
        "| Configuration | Sequence | Raw relevant | Duplicate records | Deduplicated | Manual ignore | Boundary ignore | Out of bounds | Missing/invalid mask | Evaluated | Frames used |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for method in METHODS:
        for sequence in SEQUENCES:
            a = audit_counts[(method, sequence)]
            audit_lines.append(
                f"| {method} | {sequence} | {raw_relevant[(method, sequence)]} | {duplicate_count[(method, sequence)]} | "
                f"{a['deduplicated_observations']} | {a['manual_ignore_excluded']} | {a['boundary_ignore_excluded']} | "
                f"{a['out_of_bounds']} | {a['missing_or_invalid_mask']} | {a['evaluated_observations']} | "
                f"{len(used_frames[(method, sequence)])} |"
            )
    audit_lines += ["", "## Stream comparability", ""]
    for sequence in SEQUENCES:
        sem = audit_counts[("Semantic", sequence)]["evaluated_observations"]
        tmp = audit_counts[("Temporal", sequence)]["evaluated_observations"]
        change = safe_div(tmp - sem, sem)
        audit_lines.append(f"- `{sequence}`: Semantic={sem}, Temporal={tmp}, relative change={change:.2%}.")
    audit_lines += [
        "", "The realized streams are not paired: Semantic and Temporal are independent SLAM runs, and MapPoint IDs are stable only within a run.",
        "A lower observation count can reflect divergent tracking or suppression, so counts and frames used accompany every rate.",
        "", "## Exceptions", "",
        f"- Missing GT: `{missing_gt}`", f"- Missing ignore: `{missing_ignore}`",
        f"- Invalid masks: `{invalid_masks}`", f"- Timestamp mismatch examples: `{timestamp_mismatches}`",
        "", "## Secondary analysis", "",
        "MapPoint-level aggregation is secondary and is reported at fixed ratio thresholds 0.1, 0.2, and 0.3 without selecting a best threshold.",
    ]
    (args.output / "correctness_audit.md").write_text("\n".join(audit_lines) + "\n", encoding="utf-8")
    print(f"Wrote correctness evaluation to {args.output}")


if __name__ == "__main__":
    main()
