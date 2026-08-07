#!/usr/bin/env python3
"""Export paper-ready tables and figure index without overwriting prior outputs."""

from __future__ import annotations

import csv
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


OUT_DIR = Path("paper_ready_outputs_v2")
TABLE_DIR = OUT_DIR / "tables"
FIG_DIR = OUT_DIR / "figures"

SEQUENCES = [
    ("fr1_xyz", "fr1_xyz"),
    ("fr1_desk", "fr1_desk"),
    ("fr3_walking_xyz", "fr3_xyz"),
    ("fr3_walking_rpy", "fr3_rpy"),
    ("fr3_walking_halfsphere", "fr3_halfsphere"),
]

METHODS = [
    ("ORB-SLAM2", "ORB-SLAM2"),
    ("DS-SLAM", "DS-SLAM"),
    ("Dyna-SLAM", "Dyna-SLAM"),
    ("Hard Remove", "Hard Remove"),
    ("Ours", "Full Method"),
]

METRICS = [
    ("ate_rmse", "ATE RMSE", "table_ate_rmse_methods_by_sequence"),
    ("rpe_trans_rmse", "RPE-trans RMSE", "table_rpe_trans_methods_by_sequence"),
    ("rpe_rot_rmse_deg", "RPE-rot RMSE (deg)", "table_rpe_rot_methods_by_sequence"),
    ("fps", "FPS", "table_fps_methods_by_sequence"),
]


def read_summary(path: Path) -> Dict[Tuple[str, str], Dict[str, str]]:
    rows: Dict[Tuple[str, str], Dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows[(row["sequence"], row["method"])] = row
    return rows


def fmt(value: str, metric: str) -> str:
    if not value:
        return "--"
    number = float(value)
    if metric == "fps":
        return f"{number:.2f}"
    return f"{number:.6f}"


def build_table(rows: Dict[Tuple[str, str], Dict[str, str]], metric: str) -> List[List[str]]:
    table: List[List[str]] = [["Methods"] + [label for _, label in SEQUENCES]]
    raw_values: Dict[Tuple[str, str], float] = {}
    for method_label, method_key in METHODS:
        line = [method_label]
        for seq_key, _ in SEQUENCES:
            row = rows.get((seq_key, method_key))
            value = row.get(metric, "") if row else ""
            if value:
                raw_values[(method_label, seq_key)] = float(value)
            line.append(fmt(value, metric))
        table.append(line)

    for col_idx, (seq_key, _) in enumerate(SEQUENCES, start=1):
        candidates = [(method, value) for (method, seq), value in raw_values.items() if seq == seq_key]
        if not candidates:
            continue
        best_method, _ = (max(candidates, key=lambda item: item[1]) if metric == "fps" else min(candidates, key=lambda item: item[1]))
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
    lines.append("Note: **bold** marks the best available value in each column. DS-SLAM and Dyna-SLAM are left as `--` where no local run is available.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(path: Path, table: List[List[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        for row in table:
            writer.writerow([cell.replace("**", "") for cell in row])


def draw_pipeline(path_prefix: Path) -> None:
    steps = [
        ("RGB-D Input", "color + depth frames"),
        ("ORB Front-end", "feature extraction\ntracking"),
        ("YOLO Detection", "semantic boxes"),
        ("Dynamic Score", "temporal dynamic\nprobability"),
        ("Object Map", "object-level\nsemantic landmarks"),
        ("Pose / Map Output", "trajectory + figures"),
    ]

    fig, ax = plt.subplots(figsize=(11.5, 3.1))
    ax.set_axis_off()
    x0, y0, w, h, gap = 0.03, 0.32, 0.135, 0.36, 0.028
    colors = ["#d9e8fb", "#e5e7eb", "#fde2cf", "#fff3bf", "#d8f3dc", "#e9d8fd"]

    for i, ((title, subtitle), color) in enumerate(zip(steps, colors)):
        x = x0 + i * (w + gap)
        box = FancyBboxPatch(
            (x, y0),
            w,
            h,
            boxstyle="round,pad=0.018,rounding_size=0.018",
            linewidth=1.1,
            edgecolor="#333333",
            facecolor=color,
        )
        ax.add_patch(box)
        ax.text(x + w / 2, y0 + h * 0.63, title, ha="center", va="center", fontsize=10, fontweight="bold")
        ax.text(x + w / 2, y0 + h * 0.34, subtitle, ha="center", va="center", fontsize=8)
        if i < len(steps) - 1:
            ax.add_patch(
                FancyArrowPatch(
                    (x + w + 0.004, y0 + h / 2),
                    (x + w + gap - 0.006, y0 + h / 2),
                    arrowstyle="-|>",
                    mutation_scale=12,
                    linewidth=1.1,
                    color="#333333",
                )
            )

    ax.text(0.5, 0.12, "Full Method = YOLO-assisted dynamic scoring + object-level semantic map", ha="center", va="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(path_prefix.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(path_prefix.with_suffix(".png"), bbox_inches="tight", dpi=300)
    plt.close(fig)


def copy_if_exists(src: Path, dst: Path) -> str:
    if not src.exists():
        return "--"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return str(dst)


def export_figures() -> None:
    draw_pipeline(FIG_DIR / "figure1_system_pipeline")

    selected = "fr3_walking_xyz"
    src_root = Path("standard_runs") / selected / "full_method" / "eval"
    copy_if_exists(src_root / "trajectory_compare.png", FIG_DIR / "figure2_trajectory_compare.png")
    copy_if_exists(src_root / "trajectory_compare.pdf", FIG_DIR / "figure2_trajectory_compare.pdf")
    copy_if_exists(src_root / "ate_rpe_errors.png", FIG_DIR / "figure3_error_curve_ate_rpe.png")
    copy_if_exists(src_root / "ate_rpe_errors.pdf", FIG_DIR / "figure3_error_curve_ate_rpe.pdf")

    obj_root = Path("paper_figs_standard") / f"{selected}_full"
    copy_if_exists(obj_root / "semantic_object_map.png", FIG_DIR / "figure4_object_map.png")
    copy_if_exists(obj_root / "semantic_object_map.pdf", FIG_DIR / "figure4_object_map.pdf")

    lines = [
        "# Paper Figure Index",
        "",
        "| Figure | File | Description |",
        "|---|---|---|",
        "| Figure 1 | `figures/figure1_system_pipeline.pdf` | System pipeline. |",
        "| Figure 2 | `figures/figure2_trajectory_compare.pdf` | Trajectory comparison on fr3_walking_xyz / Full Method. |",
        "| Figure 3 | `figures/figure3_error_curve_ate_rpe.pdf` | ATE/RPE error curves on fr3_walking_xyz / Full Method. |",
        "| Figure 4 | `figures/figure4_object_map.pdf` | Object-level semantic map on fr3_walking_xyz / Full Method. |",
    ]
    (OUT_DIR / "figure_index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    rows = read_summary(Path("evaluation_tables/standard_runs_summary.csv"))
    for metric, title, stem in METRICS:
        table = build_table(rows, metric)
        write_markdown(TABLE_DIR / f"{stem}.md", title, table)
        write_csv(TABLE_DIR / f"{stem}.csv", table)
    export_figures()
    print(f"Wrote paper-ready outputs to {OUT_DIR}")


if __name__ == "__main__":
    main()
