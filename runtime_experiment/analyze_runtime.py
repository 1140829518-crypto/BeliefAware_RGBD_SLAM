#!/usr/bin/env python3
"""Summarize measured runtime runs; warm-ups are never included."""

from __future__ import annotations

import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent
COMPONENTS = {
    "tracking": "tracking_total",
    "semantic": "semantic_detection",
    "object_adapter": "objectdynamic_adapter",
    "dynamic_filter": "dynamic_map_filter",
    "belief_update": "belief_update",
    "geometry_protection": "geometry_protection",
    "pose_optimization": "pose_optimization",
    "end_to_end": "end_to_end_frame",
}
METRICS = [
    "mean_tracking_ms", "mean_semantic_ms", "mean_object_adapter_ms",
    "mean_dynamic_filter_ms", "mean_belief_update_ms", "belief_update_calls_per_frame",
    "mean_geometry_protection_ms", "geometry_protection_calls_per_frame",
    "geometry_protected_count_per_frame", "geometry_protected_count",
    "mean_pose_optimization_ms", "pose_optimization_calls_per_frame",
    "mean_end_to_end_ms", "fps_from_end_to_end",
]


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows: list[dict[str, object]] = []
    errors: list[str] = []
    for manifest_path in sorted((ROOT / "runs").glob("*/*/run_*/runtime_run_manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status") != "success" or not manifest.get("measured"):
            continue
        timing_path = manifest_path.parent / "runtime_breakdown.csv"
        with timing_path.open(newline="", encoding="utf-8") as stream:
            timing = [r for r in csv.DictReader(stream) if r["in_steady_state"] == "1"]
        if not timing:
            errors.append(f"no steady frames: {timing_path}")
            continue
        for r in timing:
            for name, value in r.items():
                if name in {"frame_index", "in_steady_state"}:
                    continue
                number = float(value)
                if not math.isfinite(number) or number < 0:
                    errors.append(f"invalid {name}={value}: {timing_path}")
        frames = len(timing)
        out: dict[str, object] = {
            "dataset": manifest["dataset"], "sequence": manifest["sequence"],
            "method": manifest["method"], "run": manifest["run"], "frames": frames,
            "total_frames": sum(1 for _ in timing_path.open(encoding="utf-8")) - 1,
            "logging_mode": "LIGHTWEIGHT", "binary_sha256": manifest["artifacts"]["Examples/RGB-D/rgbd_tum"],
            "library_sha256": manifest["artifacts"]["lib/libORB_SLAM2.so"],
            "association_sha256": manifest["association_sha256"], "settings_sha256": manifest["settings_sha256"],
            "uncertainty_mode": manifest["configuration"]["ORB_SLAM2_UNCERTAINTY_MODE"],
            "measurement_policy": manifest["configuration"]["ORB_SLAM2_MEASUREMENT_POLICY"],
        }
        for short, component in COMPONENTS.items():
            seconds = sum(float(r[f"{component}_seconds"]) for r in timing)
            out[f"mean_{short}_ms"] = seconds * 1000.0 / frames
        for short in ("belief_update", "geometry_protection", "pose_optimization"):
            component = COMPONENTS[short]
            out[f"{short}_calls_per_frame"] = sum(float(r[f"{component}_calls"]) for r in timing) / frames
        protected = sum(float(r["geometry_protection_events"]) for r in timing)
        out["geometry_protected_count"] = protected
        out["geometry_protected_count_per_frame"] = protected / frames
        out["fps_from_end_to_end"] = 1000.0 / float(out["mean_end_to_end_ms"])
        rows.append(out)
    if errors:
        raise RuntimeError("\n".join(errors))
    expected = 2 * 4 * 3
    if len(rows) != expected:
        raise RuntimeError(f"expected {expected} measured runs, found {len(rows)}")

    base_fields = ["dataset", "sequence", "method", "run", "frames", "total_frames"]
    provenance = ["logging_mode", "binary_sha256", "library_sha256", "association_sha256",
                  "settings_sha256", "uncertainty_mode", "measurement_policy"]
    write_csv(ROOT / "runtime_per_run.csv", rows, base_fields + METRICS + provenance)

    grouped: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["dataset"]), str(row["sequence"]), str(row["method"]))].append(row)
    summary: list[dict[str, object]] = []
    for (dataset, sequence, method), group in sorted(grouped.items()):
        item: dict[str, object] = {"dataset": dataset, "sequence": sequence, "method": method, "n": len(group)}
        for metric in METRICS:
            values = [float(r[metric]) for r in group]
            item[f"{metric}_mean"] = statistics.mean(values)
            item[f"{metric}_sample_std"] = statistics.stdev(values)
        summary.append(item)
    summary_fields = ["dataset", "sequence", "method", "n"] + [x for m in METRICS for x in (f"{m}_mean", f"{m}_sample_std")]
    write_csv(ROOT / "runtime_summary.csv", summary, summary_fields)

    by_group = {(str(r["sequence"]), str(r["method"])): r for r in summary}
    incremental: list[dict[str, object]] = []
    for sequence in sorted({str(r["sequence"]) for r in summary}):
        v3, v4 = by_group[(sequence, "V3 BELIEF_ONLY")], by_group[(sequence, "V4 GEOMETRY_PROTECTED")]
        item: dict[str, object] = {"sequence": sequence, "n_v3": 3, "n_v4": 3}
        for label, metric in (("end_to_end", "mean_end_to_end_ms"),
                              ("pose_optimization", "mean_pose_optimization_ms"),
                              ("belief_update", "mean_belief_update_ms")):
            a, b = float(v3[f"{metric}_mean"]), float(v4[f"{metric}_mean"])
            item[f"v3_{label}_ms"] = a
            item[f"v4_{label}_ms"] = b
            item[f"difference_{label}_ms"] = b - a
            item[f"relative_{label}_percent"] = (b - a) / a * 100.0 if a else math.nan
        gp = float(v4["mean_geometry_protection_ms_mean"])
        item["v4_geometry_policy_ms"] = gp
        item["geometry_percent_of_v4_pose_optimization"] = gp / float(v4["mean_pose_optimization_ms_mean"]) * 100.0
        item["geometry_percent_of_v4_end_to_end"] = gp / float(v4["mean_end_to_end_ms_mean"]) * 100.0
        item["v3_belief_calls_per_frame"] = v3["belief_update_calls_per_frame_mean"]
        item["v4_belief_calls_per_frame"] = v4["belief_update_calls_per_frame_mean"]
        item["v4_geometry_calls_per_frame"] = v4["geometry_protection_calls_per_frame_mean"]
        item["v4_protected_count_per_frame"] = v4["geometry_protected_count_per_frame_mean"]
        incremental.append(item)
    inc_fields = list(incremental[0])
    write_csv(ROOT / "runtime_v4_vs_v3.csv", incremental, inc_fields)

    figures = ROOT / "figures"
    figures.mkdir(exist_ok=True)
    methods = ["Vanilla", "Legacy Temporal", "V3 BELIEF_ONLY", "V4 GEOMETRY_PROTECTED"]
    sequences = sorted({str(r["sequence"]) for r in summary})
    fig, axes = plt.subplots(2, 1, figsize=(11, 9), constrained_layout=True)
    x = np.arange(len(methods)); width = 0.36
    for ax, sequence in zip(axes, sequences):
        vals = {m: by_group[(sequence, m)] for m in methods}
        tracking = [float(vals[m]["mean_tracking_ms_mean"]) for m in methods]
        end = [float(vals[m]["mean_end_to_end_ms_mean"]) for m in methods]
        ax.bar(x - width/2, tracking, width, label="Tracking")
        ax.bar(x + width/2, end, width, label="End-to-end")
        ax.set_title(sequence); ax.set_ylabel("ms/frame"); ax.set_xticks(x, methods, rotation=12)
        ax.legend(); ax.grid(axis="y", alpha=.25)
    fig.savefig(figures / "runtime_breakdown.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    for ax, sequence in zip(axes, sequences):
        v3, v4 = by_group[(sequence, "V3 BELIEF_ONLY")], by_group[(sequence, "V4 GEOMETRY_PROTECTED")]
        labels = ["PoseOptimization", "End-to-end", "Geometry policy\n(V4 only)"]
        v3_values = [float(v3["mean_pose_optimization_ms_mean"]), float(v3["mean_end_to_end_ms_mean"]), 0]
        v4_values = [float(v4["mean_pose_optimization_ms_mean"]), float(v4["mean_end_to_end_ms_mean"]), float(v4["mean_geometry_protection_ms_mean"])]
        ix = np.arange(3)
        ax.bar(ix-width/2, v3_values, width, label="V3")
        ax.bar(ix+width/2, v4_values, width, label="V4")
        ax.set_yscale("log"); ax.set_xticks(ix, labels); ax.set_ylabel("ms/frame (log scale)")
        ax.set_title(sequence); ax.legend(); ax.grid(axis="y", alpha=.25)
    fig.savefig(figures / "v4_v3_incremental_runtime.png", dpi=180)
    plt.close(fig)
    print(f"validated and summarized {len(rows)} measured runs")


if __name__ == "__main__":
    main()
