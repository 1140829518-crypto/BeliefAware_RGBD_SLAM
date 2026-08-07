#!/usr/bin/env python3
"""Evaluate tracking success rate from existing ablation trajectories.

This script is read-only with respect to SLAM outputs. It counts input RGB-D
frames from the association file used by each run and valid poses from
CameraTrajectory.txt, then computes:

    TSR = N_success / N_total

It also cross-checks the existing Pose Missing Ratio in sequence_results.csv.
"""

from __future__ import annotations

import csv
import json
import math
import shlex
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "experiment_new" / "independent_ablation_v3"
RUNS_ROOT = SOURCE_ROOT / "runs"
AGGREGATED = SOURCE_ROOT / "aggregated_results"
SEQUENCE_RESULTS = AGGREGATED / "sequence_results.csv"
OUTPUT_ROOT = ROOT / "results" / "tracking_success_rate"

SEQUENCES = [
    "fr3_walking_xyz",
    "fr3_walking_rpy",
    "fr3_walking_halfsphere",
]

VARIANT_ORDER = [
    ("baseline", "Baseline"),
    ("semantic_mask", "Semantic Mask"),
    ("temporal_consistency", "Temporal Consistency"),
    ("object_level_map", "Object Map"),
    ("full_model", "Full Model"),
]


def non_comment_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    rows = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            rows.append(line)
    return rows


def count_valid_poses(path: Path) -> int:
    count = 0
    for line in non_comment_lines(path):
        parts = line.split()
        if len(parts) < 8:
            continue
        try:
            values = [float(v) for v in parts[:8]]
        except ValueError:
            continue
        if all(math.isfinite(v) for v in values):
            count += 1
    return count


def count_association_frames(path: Path) -> int:
    return len(non_comment_lines(path))


def association_from_command(command: str) -> Path | None:
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = command.split()
    for token in reversed(parts):
        candidate = Path(token)
        if candidate.name in {"associate.txt", "associations.txt"} or "associate" in candidate.name:
            return candidate
    return None


def resolve_input_frame_source(config: dict) -> tuple[Path | None, str]:
    command_assoc = association_from_command(str(config.get("command", "")))
    if command_assoc and command_assoc.exists():
        return command_assoc, "command association file"

    dataset = Path(str(config.get("dataset", "")))
    for name in ("associate.txt", "associations.txt"):
        candidate = dataset / name
        if candidate.exists():
            return candidate, f"dataset {name}"

    for name in ("rgb.txt", "depth.txt"):
        candidate = dataset / name
        if candidate.exists():
            return candidate, f"dataset {name} fallback"

    seq = str(config.get("sequence", ""))
    candidate = ROOT / "dataset_associations" / f"{seq}_associate.txt"
    if candidate.exists():
        return candidate, "repository association fallback"

    return None, "missing"


def read_sequence_results() -> dict[tuple[str, str, str], dict[str, str]]:
    rows: dict[tuple[str, str, str], dict[str, str]] = {}
    if not SEQUENCE_RESULTS.exists():
        return rows
    with SEQUENCE_RESULTS.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            key = (row.get("variant_key", ""), row.get("sequence", ""), row.get("run_id", ""))
            rows[key] = row
    return rows


def fmt_mean_std(values: Iterable[float], scale: float = 1.0, digits: int = 2) -> str:
    vals = [v * scale for v in values]
    if not vals:
        return "NA"
    sigma = stdev(vals) if len(vals) > 1 else 0.0
    return f"{mean(vals):.{digits}f} ± {sigma:.{digits}f}"


def safe_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except ValueError:
        return None
    return out if math.isfinite(out) else None


def discover_run_dirs() -> list[tuple[str, str, Path]]:
    discovered: list[tuple[str, str, Path]] = []
    for variant_key, _ in VARIANT_ORDER:
        for sequence in SEQUENCES:
            seq_dir = RUNS_ROOT / variant_key / sequence
            for run_dir in sorted(seq_dir.glob("run_*")):
                if run_dir.is_dir():
                    discovered.append((variant_key, sequence, run_dir))
    return discovered


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def latex_escape(text: str) -> str:
    return text.replace("_", r"\_").replace("%", r"\%")


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    sequence_rows = read_sequence_results()
    variant_name = dict(VARIANT_ORDER)
    run_rows: list[dict[str, object]] = []
    warnings: list[str] = []

    for variant_key, sequence, run_dir in discover_run_dirs():
        run_id = run_dir.name
        config_path = run_dir / "run_config.json"
        trajectory_path = run_dir / "CameraTrajectory.txt"
        if not config_path.exists():
            warnings.append(f"Missing run_config.json: {config_path}")
            continue
        if not trajectory_path.exists():
            warnings.append(f"Missing CameraTrajectory.txt: {trajectory_path}")
            continue

        config = json.loads(config_path.read_text(encoding="utf-8"))
        method = str(config.get("variant") or variant_name.get(variant_key, variant_key))
        if method == "Object-level Semantic Map":
            method = "Object Map"
        frame_source, frame_source_type = resolve_input_frame_source(config)
        total_frames = count_association_frames(frame_source) if frame_source else 0
        valid_poses = count_valid_poses(trajectory_path)
        missing_frames = max(total_frames - valid_poses, 0) if total_frames else 0
        tsr = valid_poses / total_frames if total_frames else float("nan")
        pose_missing_ratio = missing_frames / total_frames if total_frames else float("nan")

        seq_key = (variant_key, sequence, run_id)
        existing = sequence_rows.get(seq_key, {})
        existing_total = safe_float(existing.get("Input_Frames"))
        existing_valid = safe_float(existing.get("Valid_Poses"))
        existing_pmr = safe_float(existing.get("Pose_Missing_Ratio"))
        pmr_diff = abs(pose_missing_ratio - existing_pmr) if existing_pmr is not None and math.isfinite(pose_missing_ratio) else float("nan")
        count_match = (
            existing_total is not None
            and existing_valid is not None
            and int(existing_total) == total_frames
            and int(existing_valid) == valid_poses
        )

        if total_frames <= 0:
            warnings.append(f"Could not count input frames for {run_dir}")
        if existing_pmr is not None and math.isfinite(pmr_diff) and pmr_diff > 1e-9:
            warnings.append(
                f"Pose Missing Ratio mismatch for {run_dir}: computed={pose_missing_ratio:.12f}, existing={existing_pmr:.12f}"
            )
        if existing_total is not None and existing_valid is not None and not count_match:
            warnings.append(
                f"Frame/pose count mismatch for {run_dir}: computed {total_frames}/{valid_poses}, "
                f"existing {int(existing_total)}/{int(existing_valid)}"
            )

        run_rows.append(
            {
                "Method": method,
                "Variant_Key": variant_key,
                "Dataset": "TUM RGB-D",
                "Sequence": sequence,
                "Repeat": run_id,
                "N_total": total_frames,
                "N_success": valid_poses,
                "Missing_Frames": missing_frames,
                "TSR": f"{tsr:.8f}" if math.isfinite(tsr) else "NA",
                "TSR(%)": f"{tsr * 100:.4f}" if math.isfinite(tsr) else "NA",
                "Pose_Missing_Ratio_Computed": f"{pose_missing_ratio:.8f}" if math.isfinite(pose_missing_ratio) else "NA",
                "Pose_Missing_Ratio_Existing": f"{existing_pmr:.8f}" if existing_pmr is not None else "NA",
                "PMR_Check": "OK" if existing_pmr is not None and math.isfinite(pmr_diff) and pmr_diff <= 1e-9 else "CHECK",
                "Input_Frame_Source": str(frame_source) if frame_source else "NA",
                "Input_Frame_Source_Type": frame_source_type,
                "Trajectory_File": str(trajectory_path),
            }
        )

    if not run_rows:
        raise RuntimeError(f"No run rows found under {RUNS_ROOT}")

    write_csv(
        OUTPUT_ROOT / "tracking_success_rate_runs.csv",
        run_rows,
        [
            "Method",
            "Variant_Key",
            "Dataset",
            "Sequence",
            "Repeat",
            "N_total",
            "N_success",
            "Missing_Frames",
            "TSR",
            "TSR(%)",
            "Pose_Missing_Ratio_Computed",
            "Pose_Missing_Ratio_Existing",
            "PMR_Check",
            "Input_Frame_Source",
            "Input_Frame_Source_Type",
            "Trajectory_File",
        ],
    )

    by_method_sequence: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    by_method: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in run_rows:
        by_method_sequence[(str(row["Method"]), str(row["Sequence"]))].append(row)
        by_method[str(row["Method"])].append(row)

    sequence_summary: list[dict[str, object]] = []
    for method in [name if name != "Object-level Semantic Map" else "Object Map" for _, name in VARIANT_ORDER]:
        for sequence in SEQUENCES:
            rows = by_method_sequence.get((method, sequence), [])
            tsr_values = [float(r["TSR"]) for r in rows if r["TSR"] != "NA"]
            sequence_summary.append(
                {
                    "Method": method,
                    "Dataset": "TUM RGB-D",
                    "Sequence": sequence,
                    "Runs": len(rows),
                    "Total_Frames_mean": fmt_mean_std([float(r["N_total"]) for r in rows], digits=1),
                    "Valid_Poses_mean": fmt_mean_std([float(r["N_success"]) for r in rows], digits=1),
                    "Missing_Frames_mean": fmt_mean_std([float(r["Missing_Frames"]) for r in rows], digits=1),
                    "TSR_mean": f"{mean(tsr_values):.8f}" if tsr_values else "NA",
                    "TSR_std": f"{stdev(tsr_values):.8f}" if len(tsr_values) > 1 else "0.00000000",
                    "TSR(%)": fmt_mean_std(tsr_values, scale=100.0, digits=2),
                }
            )

    write_csv(
        OUTPUT_ROOT / "tracking_success_rate_by_sequence.csv",
        sequence_summary,
        [
            "Method",
            "Dataset",
            "Sequence",
            "Runs",
            "Total_Frames_mean",
            "Valid_Poses_mean",
            "Missing_Frames_mean",
            "TSR_mean",
            "TSR_std",
            "TSR(%)",
        ],
    )

    table_rows: list[dict[str, object]] = []
    for _, configured_name in VARIANT_ORDER:
        method = "Object Map" if configured_name == "Object-level Semantic Map" else configured_name
        rows = by_method.get(method, [])
        tsr_values = [float(r["TSR"]) for r in rows if r["TSR"] != "NA"]
        total_missing = sum(int(r["Missing_Frames"]) for r in rows)
        total_frames = sum(int(r["N_total"]) for r in rows)
        table_rows.append(
            {
                "Method": method,
                "TSR(%)": fmt_mean_std(tsr_values, scale=100.0, digits=2),
                "Runs": len(rows),
                "Total_Frames": total_frames,
                "Valid_Poses": sum(int(r["N_success"]) for r in rows),
                "Missing_Frames": total_missing,
                "Pose_Missing_Ratio(%)": f"{(total_missing / total_frames * 100):.2f}" if total_frames else "NA",
            }
        )

    write_csv(
        OUTPUT_ROOT / "tracking_success_rate_method_summary.csv",
        table_rows,
        [
            "Method",
            "TSR(%)",
            "Runs",
            "Total_Frames",
            "Valid_Poses",
            "Missing_Frames",
            "Pose_Missing_Ratio(%)",
        ],
    )
    write_csv(
        OUTPUT_ROOT / "Table8_tracking_success_rate.csv",
        [{"Method": row["Method"], "TSR(%)": row["TSR(%)"]} for row in table_rows],
        ["Method", "TSR(%)"],
    )

    tex_lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Tracking Success Rate comparison}",
        r"\label{tab:tracking_success_rate}",
        r"\begin{tabular}{lc}",
        r"\toprule",
        r"Method & TSR(\%) \\",
        r"\midrule",
    ]
    for row in table_rows:
        tsr_text = latex_escape(str(row["TSR(%)"])).replace("±", r"$\pm$")
        tex_lines.append(f"{latex_escape(str(row['Method']))} & {tsr_text} " + r"\\")
    tex_lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
            "",
        ]
    )
    (OUTPUT_ROOT / "table8_tsr.tex").write_text("\n".join(tex_lines), encoding="utf-8")

    pmr_ok = all(str(row["PMR_Check"]) == "OK" for row in run_rows)
    audit = [
        "# Tracking Success Rate Audit",
        "",
        f"- Source run root: `{RUNS_ROOT}`",
        f"- Sequence results cross-check: `{SEQUENCE_RESULTS}`",
        f"- Output directory: `{OUTPUT_ROOT}`",
        f"- Runs discovered: {len(run_rows)}",
        f"- Expected runs: {len(VARIANT_ORDER) * len(SEQUENCES) * 3}",
        f"- Pose Missing Ratio check: {'OK' if pmr_ok else 'CHECK'}",
        "",
        "## Definition",
        "",
        "- `N_total`: number of non-comment lines in the RGB-D association file used by the run.",
        "- `N_success`: number of valid 8-field TUM poses in `CameraTrajectory.txt`.",
        "- `TSR = N_success / N_total`.",
        "- `Missing_Frames = N_total - N_success`.",
        "- `Pose Missing Ratio = Missing_Frames / N_total = 1 - TSR`.",
        "",
        "This statistic does not use timestamp association with ground truth. It directly measures whether the SLAM run output a valid camera pose for an input RGB-D frame, avoiding artificial missing counts caused by evaluation timestamp matching.",
        "",
        "## Files Written",
        "",
        "- `tracking_success_rate_runs.csv`: per-run details including total frames, valid poses and missing frames.",
        "- `tracking_success_rate_by_sequence.csv`: mean/std grouped by method and sequence.",
        "- `Table8_tracking_success_rate.csv`: paper table summary with `Method, TSR(%)` columns.",
        "- `tracking_success_rate_method_summary.csv`: method-level summary with frame/pose/missing counts.",
        "- `table8_tsr.tex`: LaTeX table.",
        "",
        "## Pose Missing Ratio Cross-check",
        "",
    ]
    if pmr_ok:
        audit.append("All computed Pose Missing Ratio values match `aggregated_results/sequence_results.csv` within numerical tolerance.")
    else:
        audit.append("Some computed Pose Missing Ratio values differ from `aggregated_results/sequence_results.csv`; see warnings below.")
    audit.extend(["", "## Warnings", ""])
    audit.extend([f"- {w}" for w in warnings] or ["- None."])
    (OUTPUT_ROOT / "tracking_success_rate_audit.md").write_text("\n".join(audit) + "\n", encoding="utf-8")

    print(f"Output directory: {OUTPUT_ROOT}")
    print(f"Runs discovered: {len(run_rows)}")
    print(f"Pose Missing Ratio check: {'OK' if pmr_ok else 'CHECK'}")
    print(f"Table CSV: {OUTPUT_ROOT / 'Table8_tracking_success_rate.csv'}")
    print(f"LaTeX table: {OUTPUT_ROOT / 'table8_tsr.tex'}")


if __name__ == "__main__":
    main()
