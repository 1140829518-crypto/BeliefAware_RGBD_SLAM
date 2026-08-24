#!/usr/bin/env python3
"""Shared, dependency-free helpers for the PAA/PRL experiment pipeline."""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


REPO = Path(__file__).resolve().parents[1]
SETTINGS = REPO / "Examples/RGB-D/TUM3.yaml"
DATASET_ROOT = Path("/home/djn/datasets/TUMRGBD")
SEQUENCE_NAMES = (
    "fr3_walking_xyz",
    "fr3_walking_rpy",
    "fr3_walking_halfsphere",
    "fr3_sitting_xyz",
    "fr3_sitting_rpy",
    "fr3_sitting_halfsphere",
)
CONFIGURATIONS = ("ORB-SLAM2", "Semantic", "Temporal", "Full")
CONFIGURATION_SPECS = {
    "ORB-SLAM2": {"runner_method": "orb", "semantic_mode": 0, "object_map": 0,
                  "shadow": 0, "active": 0, "build_variant": "no_object"},
    "Semantic": {"runner_method": "hard", "semantic_mode": 1, "object_map": 0,
                 "shadow": 0, "active": 0, "build_variant": "no_object"},
    "Temporal": {"runner_method": "dynamic", "semantic_mode": 2, "object_map": 0,
                 "shadow": 0, "active": 0, "build_variant": "no_object"},
    "Full": {"runner_method": "full", "semantic_mode": 2, "object_map": 1,
             "shadow": 1, "active": 1, "build_variant": "full"},
}
BUILD_VARIANTS = {"no_object": (0, 0), "full": (1, 1)}


def dataset_path(sequence: str, dataset_root: Path = DATASET_ROOT) -> Path:
    if not sequence.startswith("fr3_"):
        raise ValueError(f"Unsupported TUM sequence name: {sequence}")
    return dataset_root / f"rgbd_dataset_freiburg3_{sequence[4:]}"


def association_path(sequence: str) -> Path:
    return REPO / "dataset_associations" / f"{sequence}_associate.txt"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_output(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def parse_semantic_defaults(path: Path | None = None) -> Dict[str, Dict[str, float]]:
    """Read actual compiled fallback values from SemanticConfig.h.

    This deliberately parses the checked-out source on every invocation. No
    sensitivity default is duplicated in Python.
    """
    source = path or REPO / "include/SemanticConfig.h"
    text = source.read_text(encoding="utf-8")
    names = {
        "threshold": ("kDynamicScoreThreshold", "kPersonDynamicScoreThreshold"),
        "increment": ("kDynamicScoreIncrement", "kPersonDynamicScoreIncrement"),
        "decay": ("kDynamicScoreDecay", "kPersonDynamicScoreDecay"),
    }
    parsed: Dict[str, Dict[str, float]] = {}
    for metric, (normal_name, person_name) in names.items():
        values: List[float] = []
        for name in (normal_name, person_name):
            match = re.search(rf"\b{name}\s*=\s*([0-9]+(?:\.[0-9]*)?)f\s*;", text)
            if not match:
                raise RuntimeError(f"Cannot parse {name} from {source}")
            values.append(float(match.group(1)))
        parsed[metric] = {"normal_dynamic_class": values[0], "person": values[1]}
    return parsed


def data_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()
               if line.strip() and not line.lstrip().startswith("#"))


def load_timestamps(path: Path, minimum_fields: int) -> List[float]:
    result: List[float] = []
    if not path.exists():
        return result
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        fields = raw.strip().split()
        if not fields or raw.lstrip().startswith("#") or len(fields) < minimum_fields:
            continue
        try:
            stamp = float(fields[0])
        except ValueError:
            continue
        if math.isfinite(stamp):
            result.append(stamp)
    return result


def trajectory_coverage(association: Path, trajectory: Path,
                        max_diff: float = 0.02) -> Tuple[int, int, int, float, float]:
    association_stamps = load_timestamps(association, 4)
    trajectory_stamps = load_timestamps(trajectory, 8)
    hits = [False] * len(association_stamps)
    j = 0
    for index, stamp in enumerate(association_stamps):
        while j + 1 < len(trajectory_stamps) and abs(trajectory_stamps[j + 1] - stamp) < abs(trajectory_stamps[j] - stamp):
            j += 1
        if trajectory_stamps and abs(trajectory_stamps[j] - stamp) <= max_diff:
            hits[index] = True
    gaps = 0
    in_gap = False
    for hit in hits:
        if not hit and not in_gap:
            gaps += 1
            in_gap = True
        elif hit:
            in_gap = False
    matched = sum(hits)
    total = len(hits)
    tsr = matched / total if total else math.nan
    return total, len(trajectory_stamps), gaps, tsr, 1.0 - tsr if total else math.nan


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sample_mean_std(values: Iterable[float]) -> Tuple[float, float]:
    clean = [float(value) for value in values if math.isfinite(float(value))]
    if not clean:
        return math.nan, math.nan
    mean = sum(clean) / len(clean)
    if len(clean) == 1:
        return mean, 0.0
    variance = sum((value - mean) ** 2 for value in clean) / (len(clean) - 1)
    return mean, math.sqrt(variance)
