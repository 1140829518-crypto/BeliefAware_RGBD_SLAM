#!/usr/bin/env python3
"""Summarize object-map and dynamic-point statistics for Full Method runs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, Iterable, List


def read_dynamic_stats(path: Path) -> Dict[str, float]:
    rows: List[Dict[str, int]] = []
    with path.open(encoding="utf-8") as f:
        header = f.readline().split()
        for line in f:
            if not line.strip():
                continue
            vals = line.split()
            if len(vals) != len(header):
                continue
            rows.append({k: int(v) for k, v in zip(header, vals)})
    if not rows:
        return {}
    return {
        "frames": len(rows),
        "avg_dynamic_keypoints": sum(r["dynamic_keypoints"] for r in rows) / len(rows),
        "max_dynamic_keypoints": max(r["dynamic_keypoints"] for r in rows),
        "avg_dynamic_map_points": sum(r["dynamic_map_points"] for r in rows) / len(rows),
        "max_dynamic_map_points": max(r["dynamic_map_points"] for r in rows),
        "avg_suppressed_map_points": sum(r["suppressed_map_points"] for r in rows) / len(rows),
        "max_suppressed_map_points": max(r["suppressed_map_points"] for r in rows),
        "avg_dynamic_objects": sum(r["dynamic_objects"] for r in rows) / len(rows),
        "max_dynamic_objects": max(r["dynamic_objects"] for r in rows),
        "avg_static_objects": sum(r["static_objects"] for r in rows) / len(rows),
        "max_static_objects": max(r["static_objects"] for r in rows),
    }


def read_object_stats(path: Path) -> Dict[str, float]:
    objects = []
    class_counts: Dict[str, int] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.startswith("#"):
                continue
            vals = line.split()
            if len(vals) < 12:
                continue
            class_name = vals[2]
            observations = int(vals[5] if len(vals) >= 13 else vals[4])
            objects.append(observations)
            class_counts[class_name] = class_counts.get(class_name, 0) + 1
    if not objects:
        return {}
    return {
        "semantic_objects": len(objects),
        "avg_object_observations": sum(objects) / len(objects),
        "max_object_observations": max(objects),
        "static_group_objects": class_counts.get("static_group", 0),
        "low_dynamic_group_objects": class_counts.get("low_dynamic_group", 0),
        "person_objects": class_counts.get("person", 0),
    }


def summarize_run(sequence: str, objects: Path, dynamic_stats: Path) -> Dict[str, object]:
    summary: Dict[str, object] = {"sequence": sequence}
    if objects.exists():
        summary.update(read_object_stats(objects))
    if dynamic_stats.exists():
        summary.update(read_dynamic_stats(dynamic_stats))
    return summary


def discover_full_method_runs(runs_root: Path) -> Iterable[Dict[str, object]]:
    if not runs_root.exists():
        return []
    rows: List[Dict[str, object]] = []
    for sequence_dir in sorted(p for p in runs_root.iterdir() if p.is_dir()):
        run_dir = sequence_dir / "full_method"
        objects = run_dir / "SemanticObjects.txt"
        dynamic_stats = run_dir / "SemanticDynamicStatistics.txt"
        if objects.exists() or dynamic_stats.exists():
            rows.append(summarize_run(sequence_dir.name, objects, dynamic_stats))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize semantic object map statistics.")
    parser.add_argument("--sequence", default="fr3_walking_static")
    parser.add_argument("--objects", type=Path, default=Path("TUM_trajectory_results/SemanticObjects.txt"))
    parser.add_argument("--dynamic-stats", type=Path, default=Path("TUM_trajectory_results/SemanticDynamicStatistics.txt"))
    parser.add_argument("--runs-root", type=Path, default=Path("standard_runs"))
    parser.add_argument("--single", action="store_true", help="Summarize only --objects/--dynamic-stats instead of scanning standard_runs.")
    parser.add_argument("--out", type=Path, default=Path("evaluation_tables/standard_object_map_stats.csv"))
    args = parser.parse_args()

    if args.single:
        summaries = [summarize_run(args.sequence, args.objects, args.dynamic_stats)]
    else:
        summaries = list(discover_full_method_runs(args.runs_root))
        if not summaries:
            summaries = [summarize_run(args.sequence, args.objects, args.dynamic_stats)]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "sequence",
        "semantic_objects",
        "static_group_objects",
        "low_dynamic_group_objects",
        "person_objects",
        "avg_object_observations",
        "max_object_observations",
        "frames",
        "avg_dynamic_keypoints",
        "max_dynamic_keypoints",
        "avg_dynamic_map_points",
        "max_dynamic_map_points",
        "avg_suppressed_map_points",
        "max_suppressed_map_points",
        "avg_dynamic_objects",
        "max_dynamic_objects",
        "avg_static_objects",
        "max_static_objects",
    ]
    with args.out.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(summaries)
    print(f"Wrote object-map stats: {args.out}")


if __name__ == "__main__":
    main()
