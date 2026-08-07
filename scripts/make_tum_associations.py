#!/usr/bin/env python3
"""Create TUM RGB-D association files from rgb.txt and depth.txt."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Tuple


def load_list(path: Path) -> List[Tuple[float, str]]:
    rows: List[Tuple[float, str]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            vals = line.split()
            if len(vals) < 2:
                continue
            rows.append((float(vals[0]), vals[1]))
    return rows


def associate(a: List[Tuple[float, str]], b: List[Tuple[float, str]], max_diff: float) -> List[Tuple[float, str, float, str]]:
    matches: List[Tuple[float, str, float, str]] = []
    used = set()
    for ta, pa in a:
        best_j = None
        best_dt = max_diff
        for j, (tb, _) in enumerate(b):
            if j in used:
                continue
            dt = abs(ta - tb)
            if dt < best_dt:
                best_dt = dt
                best_j = j
        if best_j is None:
            continue
        used.add(best_j)
        tb, pb = b[best_j]
        matches.append((ta, pa, tb, pb))
    return matches


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a TUM RGB-D associate.txt file.")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-diff", type=float, default=0.02)
    args = parser.parse_args()

    rgb = load_list(args.dataset / "rgb.txt")
    depth = load_list(args.dataset / "depth.txt")
    matches = associate(rgb, depth, args.max_diff)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for ta, pa, tb, pb in matches:
            f.write(f"{ta:.6f} {pa} {tb:.6f} {pb}\n")
    print(f"wrote {len(matches)} associations to {args.out}")


if __name__ == "__main__":
    main()
