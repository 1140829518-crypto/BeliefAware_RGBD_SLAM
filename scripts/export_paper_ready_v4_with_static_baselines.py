#!/usr/bin/env python3
"""Export method-by-sequence tables including fr3_static and static DS/Dyna baselines."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple


OUT_DIR = Path("paper_ready_outputs_v4")
TABLE_DIR = OUT_DIR / "tables"

SEQUENCES = [
    ("fr1_xyz", "fr1_xyz"),
    ("fr1_desk", "fr1_desk"),
    ("fr3_walking_xyz", "fr3_xyz"),
    ("fr3_walking_rpy", "fr3_rpy"),
    ("fr3_walking_halfsphere", "fr3_halfsphere"),
    ("fr3_walking_static", "fr3_static"),
]

METHODS = [
    ("ORB-SLAM2", "ORB-SLAM2"),
    ("ORB-SLAM3", "ORB-SLAM3"),
    ("DS-SLAM", "DS-SLAM"),
    ("Dyna-SLAM", "Dyna-SLAM"),
    ("Hard Remove", "Hard Remove"),
    ("Ours", "Full Method"),
]

METRICS = [
    ("ate_rmse", "ATE RMSE", "table_ate_rmse_methods_by_sequence"),
    ("rpe_trans_rmse", "RPE-trans RMSE", "table_rpe_trans_methods_by_sequence"),
    ("rpe_rot_rmse_deg", "RPE-rot RMSE (deg)", "table_rpe_rot_methods_by_sequence"),
]


def read_summary(path: Path) -> Dict[Tuple[str, str], Dict[str, str]]:
    rows: Dict[Tuple[str, str], Dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows[(row["sequence"], row["method"])] = row
    return rows


def add_metrics_row(rows: Dict[Tuple[str, str], Dict[str, str]], sequence: str, method: str, source: str, metrics_path: Path) -> None:
    if not metrics_path.exists():
        return
    data = json.loads(metrics_path.read_text(encoding="utf-8"))
    rows[(sequence, method)] = {
        "sequence": sequence,
        "method": method,
        "source": source,
        "matches": str(data["matches"]),
        "ate_rmse": str(data["ate"]["rmse"]),
        "rpe_trans_rmse": str(data["rpe_trans"]["rmse"]),
        "rpe_rot_rmse_deg": str(data["rpe_rot_deg"]["rmse"]),
        "run_dir": str(metrics_path.parent),
    }


def add_external_baselines(rows: Dict[Tuple[str, str], Dict[str, str]]) -> None:
    add_metrics_row(
        rows,
        "fr3_walking_static",
        "DS-SLAM",
        "DS_SLAM_trajectory",
        Path("DS_SLAM_trajectory/freiburg3_walking_static/eval/metrics.json"),
    )
    add_metrics_row(
        rows,
        "fr3_walking_static",
        "Dyna-SLAM",
        "Dyna_SLAM_trajectory",
        Path("Dyna_SLAM_trajectory/freiburg3_walking_static/eval/metrics.json"),
    )
    for sequence in ["fr3_walking_xyz", "fr3_walking_rpy", "fr3_walking_halfsphere", "fr3_walking_static"]:
        add_metrics_row(
            rows,
            sequence,
            "ORB-SLAM3",
            "ORB_SLAM3_trajectory",
            Path("paper_ready_outputs_v3/orb_slam3_eval") / sequence / "metrics.json",
        )


def fmt(value: str) -> str:
    if not value:
        return "--"
    return f"{float(value):.6f}"


def build_table(rows: Dict[Tuple[str, str], Dict[str, str]], metric: str) -> List[List[str]]:
    table: List[List[str]] = [["Methods"] + [label for _, label in SEQUENCES]]
    values: Dict[Tuple[str, str], float] = {}
    for method_label, method_key in METHODS:
        line = [method_label]
        for seq_key, _ in SEQUENCES:
            row = rows.get((seq_key, method_key))
            value = row.get(metric, "") if row else ""
            if value:
                values[(method_label, seq_key)] = float(value)
            line.append(fmt(value))
        table.append(line)

    for col_idx, (seq_key, _) in enumerate(SEQUENCES, start=1):
        candidates = [(method, value) for (method, seq), value in values.items() if seq == seq_key]
        if not candidates:
            continue
        best_method, _ = min(candidates, key=lambda item: item[1])
        for row in table[1:]:
            if row[0] == best_method and row[col_idx] != "--":
                row[col_idx] = f"**{row[col_idx]}**"
    return table


def write_markdown(path: Path, title: str, table: List[List[str]]) -> None:
    lines = [f"# {title}", ""]
    lines.append("| " + " | ".join(table[0]) + " |")
    lines.append("|" + "|".join(["---"] + ["---:" for _ in table[0][1:]]) + "|")
    for row in table[1:]:
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    lines.append("Note: **bold** marks the best available value in each column. `--` means no local trajectory is available.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(path: Path, table: List[List[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        for row in table:
            writer.writerow([cell.replace("**", "") for cell in row])


def write_summary(path: Path, rows: Dict[Tuple[str, str], Dict[str, str]]) -> None:
    fieldnames = [
        "sequence",
        "method",
        "source",
        "matches",
        "ate_rmse",
        "rpe_trans_rmse",
        "rpe_rot_rmse_deg",
        "run_dir",
    ]
    ordered = []
    for sequence, _ in SEQUENCES:
        for _, method in METHODS:
            row = rows.get((sequence, method))
            if row:
                ordered.append(row)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(ordered)


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    rows = read_summary(Path("evaluation_tables/standard_runs_summary.csv"))
    add_external_baselines(rows)
    write_summary(OUT_DIR / "summary_with_static_ds_dyna.csv", rows)
    for metric, title, stem in METRICS:
        table = build_table(rows, metric)
        write_markdown(TABLE_DIR / f"{stem}.md", title, table)
        write_csv(TABLE_DIR / f"{stem}.csv", table)
    print(f"Wrote tables with fr3_static DS-SLAM/Dyna-SLAM values to {OUT_DIR}")


if __name__ == "__main__":
    main()
