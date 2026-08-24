#!/usr/bin/env python3
"""Create a non-running, auditable DynaSLAM/DS-SLAM readiness report."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

from paa_prl_common import REPO, sha256, write_json


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    excluded = {"build", "devel", ".git"}
    for path in sorted(p for p in root.rglob("*") if p.is_file()
                       and not any(part in excluded for part in p.relative_to(root).parts)):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(bytes.fromhex(sha256(path)))
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path,
                        default=REPO / "results/paa_prl_baselines/readiness.json")
    args = parser.parse_args()
    dyna = REPO / "baselines/DynaSLAM-master"
    ds = REPO / "baselines/DS-SLAM-master"
    dyna_weights = list(dyna.rglob("mask_rcnn_coco.h5")) if dyna.exists() else []
    ds_models = sorted(ds.rglob("*.caffemodel")) if ds.exists() else []
    report = {
        "checked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "policy": "readiness only; no baseline experiment was started",
        "DynaSLAM": {
            "source_path": str(dyna), "source_exists": dyna.exists(),
            "source_tree_sha256_excluding_build": tree_hash(dyna) if dyna.exists() else None,
            "mask_rcnn_coco_h5": [str(path) for path in dyna_weights],
            "status": "available" if dyna_weights else "unavailable",
            "paper_result_allowed": bool(dyna_weights),
            "reason": ("complete Mask R-CNN weight found" if dyna_weights else
                       "mask_rcnn_coco.h5 missing; geometry-only output is not full DynaSLAM"),
        },
        "DS-SLAM": {
            "source_path": str(ds), "source_exists": ds.exists(),
            "source_tree_sha256_excluding_build": tree_hash(ds) if ds.exists() else None,
            "models": [{"path": str(path), "sha256": sha256(path),
                        "size_bytes": path.stat().st_size} for path in ds_models],
            "build_cache_exists": (ds / "build/CMakeCache.txt").exists(),
            "rgbd_entrypoint": str(ds / "Examples/RGB-D/rgbd_tum_ds.cc"),
            "status": "source_and_model_present" if ds.exists() and ds_models else "unavailable",
            "provenance_note": "local imported source; no nested .git metadata present",
        },
    }
    write_json(args.out.resolve(), report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
