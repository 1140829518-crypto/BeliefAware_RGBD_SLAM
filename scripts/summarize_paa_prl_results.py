#!/usr/bin/env python3
"""Summarize PAA/PRL runs while retaining failures and coverage warnings."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List

from paa_prl_common import (CONFIGURATIONS, REPO, association_path,
                            sample_mean_std, trajectory_coverage)


def number(value: object, default: float = math.nan) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def switching_frequency(path: Path) -> tuple[int, int, float]:
    if not path.exists() or not path.stat().st_size:
        return 0, 0, math.nan
    observations: Dict[int, Dict[int, int]] = defaultdict(dict)
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            try:
                frame = int(row["frame_id"])
                point = int(row["map_point_id"])
                state = int(row.get("dynamic_state", row.get("suppressed", "0")))
            except (KeyError, TypeError, ValueError):
                continue
            observations[point][frame] = state
    switches = 0
    opportunities = 0
    for frames in observations.values():
        states = [frames[frame] for frame in sorted(frames)]
        opportunities += max(0, len(states) - 1)
        switches += sum(left != right for left, right in zip(states, states[1:]))
    return switches, opportunities, switches / opportunities if opportunities else math.nan


def runtime_values(path: Path) -> Dict[str, float]:
    values: Dict[str, float] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        fields = raw.split()
        if len(fields) == 2:
            values[fields[0]] = number(fields[1])
    return values


def runtime_breakdown(path: Path) -> Dict[str, float]:
    values: Dict[str, float] = {}
    if not path.exists() or not path.stat().st_size:
        return values
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            component = row.get("component", "")
            if not component:
                continue
            values[f"{component}_mean_seconds_steady"] = number(
                row.get("mean_seconds_steady"))
            values[f"{component}_fps_steady"] = number(row.get("fps_steady"))
            values[f"{component}_count_steady"] = number(row.get("count_steady"))
    return values


def read_attempt(attempt: Path) -> Dict[str, object]:
    config = json.loads((attempt / "run_config.json").read_text())
    status_path = attempt / "status.json"
    status = json.loads(status_path.read_text()) if status_path.exists() else {"status": "unknown"}
    sequence = str(config["sequence"])
    total, valid, gaps, tsr, pmr = trajectory_coverage(
        Path(config.get("association", association_path(sequence))),
        attempt / "CameraTrajectory.txt")
    metrics_path = attempt / "eval/metrics.json"
    metrics = json.loads(metrics_path.read_text()) if metrics_path.exists() else {}
    legal = bool(metrics and valid >= 2)
    ate = metrics.get("ate", {}) if legal else {}
    rpe_t = metrics.get("rpe_trans", {}) if legal else {}
    rpe_r = metrics.get("rpe_rot_deg", {}) if legal else {}
    if config["configuration"] == "ORB-SLAM2":
        switches, opportunities, sf = 0, 0, math.nan
    else:
        switches, opportunities, sf = switching_frequency(attempt / "mappoint_evidence_raw.csv")
    runtime = runtime_values(attempt / "runtime.txt")
    components = runtime_breakdown(attempt / "runtime_summary.csv")
    wall = number(status.get("wall_time_seconds", config.get("wall_time_seconds")))
    end_fps = total / wall if total and math.isfinite(wall) and wall > 0 else math.nan
    process_success = status.get("status") == "success"
    tracking_incomplete = (not process_success) or (math.isfinite(tsr) and tsr < 1.0)
    tracking_failure = (not process_success) or (math.isfinite(tsr) and tsr < 0.90)
    return {
        "configuration": config["configuration"], "sequence": sequence,
        "run_id": f"run_{int(config['run_id']):02d}", "attempt_id": config["attempt_id"],
        "is_primary_attempt": int(config["attempt_id"] == "attempt_01"),
        "process_status": status.get("status", "unknown"),
        "return_code": status.get("return_code", config.get("return_code", "")),
        "association_total_frames": total, "trajectory_valid_poses": valid,
        "tracking_gap_episodes": gaps, "TSR": tsr, "PMR": pmr,
        "tracking_incomplete": int(tracking_incomplete),
        "tracking_failure": int(tracking_failure),
        "coverage_warning": "short trajectory; ATE must not be interpreted alone" if tracking_failure else "",
        "ATE_RMSE": number(ate.get("rmse")),
        "RPE_translation_RMSE": number(rpe_t.get("rmse")),
        "RPE_rotation_RMSE_deg": number(rpe_r.get("rmse")),
        "MapPoint_state_switches": switches, "MapPoint_transition_opportunities": opportunities,
        "SF": sf,
        "Tracking_time_per_frame": number(
            components.get("tracking_total_mean_seconds_steady"),
            number(runtime.get("mean_tracking_time"))),
        "Semantic_detection_time_per_frame": number(
            components.get("semantic_detection_mean_seconds_steady")),
        "Temporal_evidence_update_time_per_frame": number(
            components.get("temporal_evidence_update_mean_seconds_steady")),
        "ObjectDynamic_Adapter_time_per_frame": number(
            components.get("objectdynamic_adapter_mean_seconds_steady")),
        "DynamicMapFilter_time_per_frame": number(
            components.get("dynamic_map_filter_mean_seconds_steady")),
        "Tracking_FPS": number(components.get("tracking_total_fps_steady"),
                               number(runtime.get("fps"))),
        "EndToEnd_FPS": number(components.get("end_to_end_frame_fps_steady"), end_fps),
        "runtime_steady_frame_count": number(
            components.get("end_to_end_frame_count_steady")),
        "runtime_component_reports_exist": int(bool(components)),
        "wall_time_seconds": wall, "has_legal_evaluation": int(legal),
        "git_commit": config.get("git_commit", ""), "run_dir": str(attempt),
    }


def fmt(value: object) -> object:
    if isinstance(value, float):
        return "" if not math.isfinite(value) else f"{value:.9f}"
    return value


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows({key: fmt(value) for key, value in row.items()} for row in rows)


def aggregate(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    result = []
    selected = [row for row in rows if row.get("is_selected_attempt")]
    metrics = ("ATE_RMSE", "RPE_translation_RMSE", "RPE_rotation_RMSE_deg", "TSR", "PMR",
               "tracking_gap_episodes", "SF", "Tracking_time_per_frame",
               "Semantic_detection_time_per_frame",
               "Temporal_evidence_update_time_per_frame",
               "ObjectDynamic_Adapter_time_per_frame",
               "DynamicMapFilter_time_per_frame", "Tracking_FPS", "EndToEnd_FPS")
    groups: Dict[tuple[str, str], List[Dict[str, object]]] = defaultdict(list)
    for row in selected:
        groups[(str(row["configuration"]), str(row["sequence"]))].append(row)
    for configuration in CONFIGURATIONS:
        for (group_configuration, sequence), group in sorted(groups.items()):
            if group_configuration != configuration:
                continue
            summary: Dict[str, object] = {
                "configuration": configuration, "sequence": sequence,
                "n_fixed_runs": len(group),
                "n_process_success": sum(row["process_status"] == "success" for row in group),
                "n_legal_evaluation": sum(int(row["has_legal_evaluation"]) for row in group),
                "n_tracking_incomplete": sum(int(row["tracking_incomplete"]) for row in group),
                "n_tracking_failure": sum(int(row["tracking_failure"]) for row in group),
            }
            for metric in metrics:
                source = ([row for row in group if row["has_legal_evaluation"]]
                          if metric.startswith("ATE") or metric.startswith("RPE") else group)
                mean, std = sample_mean_std(number(row[metric]) for row in source)
                summary[f"{metric}_mean"] = mean
                summary[f"{metric}_std"] = std
            result.append(summary)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=REPO / "results/paa_prl")
    args = parser.parse_args()
    root = args.root.resolve()
    attempts = sorted(path.parent for path in root.glob("*/*/run_*/attempt_*/run_config.json"))
    rows = [read_attempt(attempt) for attempt in attempts]
    run_groups: Dict[tuple[str, str, str], List[Dict[str, object]]] = defaultdict(list)
    for row in rows:
        run_groups[(str(row["configuration"]), str(row["sequence"]), str(row["run_id"]))].append(row)
    for group in run_groups.values():
        successful = [row for row in group if row["process_status"] == "success"]
        chosen = successful[-1] if successful else group[-1]
        for row in group:
            row["is_selected_attempt"] = int(row is chosen)
    summaries = aggregate(rows)
    write_csv(root / "summary/all_attempts.csv", rows)
    write_csv(root / "summary/configuration_sequence_summary.csv", summaries)
    print(f"attempts: {len(rows)}; summary groups: {len(summaries)}")
    print(root / "summary/all_attempts.csv")
    print(root / "summary/configuration_sequence_summary.csv")


if __name__ == "__main__":
    main()
