#!/usr/bin/env python3
"""Validate the six PAA/PRL TUM sequences and create missing associations."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Tuple

from paa_prl_common import (DATASET_ROOT, REPO, SEQUENCE_NAMES, association_path,
                            data_lines, dataset_path, sha256, write_json)


def load_list(path: Path) -> List[Tuple[float, str]]:
    rows: List[Tuple[float, str]] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        fields = raw.strip().split()
        if not fields or raw.lstrip().startswith("#") or len(fields) < 2:
            continue
        rows.append((float(fields[0]), fields[1]))
    return rows


def associate(rgb: List[Tuple[float, str]], depth: List[Tuple[float, str]],
              max_diff: float) -> List[Tuple[float, str, float, str]]:
    candidates = sorted(
        (abs(rgb_stamp - depth_stamp), rgb_index, depth_index)
        for rgb_index, (rgb_stamp, _) in enumerate(rgb)
        for depth_index, (depth_stamp, _) in enumerate(depth)
        if abs(rgb_stamp - depth_stamp) <= max_diff
    )
    used_rgb = set()
    used_depth = set()
    matches = []
    for _, rgb_index, depth_index in candidates:
        if rgb_index in used_rgb or depth_index in used_depth:
            continue
        used_rgb.add(rgb_index)
        used_depth.add(depth_index)
        matches.append((*rgb[rgb_index], *depth[depth_index]))
    return sorted(matches)


def write_association(path: Path, matches: List[Tuple[float, str, float, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(
        f"{rgb_stamp:.6f} {rgb_path} {depth_stamp:.6f} {depth_path}\n"
        for rgb_stamp, rgb_path, depth_stamp, depth_path in matches
    ), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, default=DATASET_ROOT)
    parser.add_argument("--manifest", type=Path,
                        default=REPO / "results/paa_prl/metadata/dataset_manifest.json")
    parser.add_argument("--write-missing-associations", action="store_true")
    parser.add_argument("--max-diff", type=float, default=0.02)
    parser.add_argument("--allow-missing", action="store_true")
    args = parser.parse_args()

    rows = []
    all_ready = True
    for sequence in SEQUENCE_NAMES:
        dataset = dataset_path(sequence, args.dataset_root)
        association = association_path(sequence)
        required = [dataset / name for name in ("rgb.txt", "depth.txt", "groundtruth.txt")]
        dataset_ready = (
            dataset.is_dir()
            and all(path.is_file() and path.stat().st_size for path in required)
            and (dataset / "rgb").is_dir()
            and (dataset / "depth").is_dir()
            and any((dataset / "rgb").glob("*.png"))
            and any((dataset / "depth").glob("*.png"))
        )
        generated = False
        if dataset_ready and not association.exists() and args.write_missing_associations:
            write_association(association, associate(load_list(dataset / "rgb.txt"),
                                                     load_list(dataset / "depth.txt"),
                                                     args.max_diff))
            generated = True
        association_ready = association.is_file() and association.stat().st_size > 0
        ready = dataset_ready and association_ready
        all_ready = all_ready and ready
        row = {
            "sequence": sequence,
            "dataset": str(dataset),
            "dataset_ready": dataset_ready,
            "rgb_images": len(list((dataset / "rgb").glob("*.png"))) if dataset.is_dir() else 0,
            "depth_images": len(list((dataset / "depth").glob("*.png"))) if dataset.is_dir() else 0,
            "association": str(association),
            "association_ready": association_ready,
            "association_generated": generated,
            "association_rows": data_lines(association),
            "association_sha256": sha256(association) if association_ready else None,
            "groundtruth_sha256": sha256(dataset / "groundtruth.txt") if dataset_ready else None,
            "ready": ready,
        }
        rows.append(row)
        print(f"{sequence}: {'READY' if ready else 'MISSING'} "
              f"dataset={dataset_ready} association={association_ready} rows={row['association_rows']}")
    write_json(args.manifest, {"dataset_root": str(args.dataset_root), "max_rgb_depth_diff": args.max_diff,
                               "all_ready": all_ready, "sequences": rows})
    print(f"manifest: {args.manifest}")
    if not all_ready and not args.allow_missing:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
