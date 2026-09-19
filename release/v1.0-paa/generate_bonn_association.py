#!/usr/bin/env python3
"""Generate the Bonn RGB-depth association used by the frozen PAA protocol."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Tuple


def read_timestamps(path: Path) -> List[Tuple[float, str]]:
    rows: List[Tuple[float, str]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            rows.append((float(parts[0]), parts[1]))
    return rows


def generate(sequence: Path) -> List[str]:
    rgb = read_timestamps(sequence / "rgb.txt")
    depth = read_timestamps(sequence / "depth.txt")
    if not depth:
        raise RuntimeError(f"No depth timestamps in {sequence / 'depth.txt'}")
    lines: List[str] = []
    j = 0
    for tr, rgb_file in rgb:
        while j + 1 < len(depth) and abs(depth[j + 1][0] - tr) < abs(depth[j][0] - tr):
            j += 1
        if abs(depth[j][0] - tr) <= 0.04:
            lines.append(f"{tr:.6f} {rgb_file} {depth[j][0]:.6f} {depth[j][1]}")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sequence", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    lines = generate(args.sequence)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(lines)} associations to {args.out}")


if __name__ == "__main__":
    main()
