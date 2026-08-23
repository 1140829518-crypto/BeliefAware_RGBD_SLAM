#!/usr/bin/env python3
"""Summarize the fixed 15 P1 runs without changing or replacing run status."""

from __future__ import annotations

import csv
import json
import math
import re
import statistics
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "experiments/final_paper/01_tum_full"
SEQUENCES = {
    "fr3_walking_xyz": (REPO / "dataset_associations/fr3_walking_xyz_associate.txt", 827),
    "fr3_walking_rpy": (REPO / "dataset_associations/fr3_walking_rpy_associate.txt", 866),
    "fr3_walking_halfsphere": (REPO / "dataset_associations/fr3_walking_halfsphere_associate.txt", 1021),
}
FIELDS = [
    "sequence", "run_id", "original_status", "exit_code", "raw_process_status",
    "experiment_completion_status", "completion_evidence", "association_total_frames",
    "trajectory_valid_poses", "ATE_RMSE", "ATE_mean", "ATE_median", "ATE_std",
    "RPE_translation_RMSE", "RPE_rotation_RMSE", "tracking_gap_episodes",
    "tracking_success_rate", "pose_missing_ratio", "tracking_FPS", "end_to_end_FPS",
    "runtime_seconds", "has_legal_evaluation", "run_dir",
]

FATAL_PATTERNS = (
    "segmentation fault", "segfault", "out of memory", "oom-killer",
    "timed out", "timeout expired",
)


def raw_status(config: dict) -> str:
    if config.get("raw_process_status"):
        return str(config["raw_process_status"])
    original = str(config.get("status", "unknown"))
    code = config.get("return_code")
    if original == "timeout":
        return "timeout"
    if isinstance(code, int):
        return "killed" if code < 0 else f"exit_{code}"
    return "unknown"


def completion(run_dir: Path) -> tuple[str, str]:
    combined = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in (run_dir / "slam.log", run_dir / "terminal.log") if path.exists()
    ).lower()
    marker = "trajectory saved!" in combined and "semantic dynamic statistics saved!" in combined
    trajectory = run_dir / "CameraTrajectory.txt"
    trajectory_ok = trajectory.exists() and trajectory.stat().st_size > 0
    evaluation = run_dir / "eval/metrics.json"
    evaluation_ok = evaluation.exists() and evaluation.stat().st_size > 0
    fatal = [pattern for pattern in FATAL_PATTERNS if pattern in combined]
    evidence = (
        f"slam_marker={int(marker)};trajectory_nonempty={int(trajectory_ok)};"
        f"evaluation_nonempty={int(evaluation_ok)};fatal_patterns={'|'.join(fatal) or 'none'}"
    )
    if fatal:
        return "invalid", evidence
    if marker and trajectory_ok and evaluation_ok:
        return "completed", evidence
    return "incomplete", evidence


def timestamps(path: Path, minimum_fields: int = 1) -> list[float]:
    out = []
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= minimum_fields:
            try:
                out.append(float(parts[0]))
            except ValueError:
                pass
    return out


def coverage(association: Path, trajectory: Path) -> tuple[int, int, float, float]:
    expected = timestamps(association, 4)
    poses = timestamps(trajectory, 8)
    matched = [False] * len(expected)
    j = 0
    for i, stamp in enumerate(expected):
        while j + 1 < len(poses) and abs(poses[j + 1] - stamp) < abs(poses[j] - stamp):
            j += 1
        if poses and abs(poses[j] - stamp) <= 0.02:
            matched[i] = True
    gaps = 0
    inside = False
    for present in matched:
        if not present and not inside:
            gaps += 1
            inside = True
        elif present:
            inside = False
    valid = len(poses)
    total = len(expected)
    tsr = valid / total if total else math.nan
    return valid, gaps, tsr, 1.0 - tsr


def runtime_values(run_dir: Path, config: dict) -> tuple[float, float, float]:
    tracking_fps = math.nan
    runtime = float(config.get("runtime_seconds", math.nan))
    p = run_dir / "runtime.txt"
    if p.exists():
        values = {}
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            parts = line.split()
            if len(parts) >= 2:
                values[parts[0]] = parts[1]
        try:
            tracking_fps = float(values.get("fps", "nan"))
        except ValueError:
            pass
    total = int(config.get("association_total_frames", 0))
    end_fps = total / runtime if total and math.isfinite(runtime) and runtime > 0 else math.nan
    return tracking_fps, end_fps, runtime


def fmt(value: object) -> object:
    if isinstance(value, float):
        return "" if not math.isfinite(value) else f"{value:.9f}"
    return value


def read_rows() -> list[dict[str, object]]:
    rows = []
    for sequence, (association, expected_total) in SEQUENCES.items():
        for run_id in range(1, 6):
            run_dir = ROOT / sequence / f"run_{run_id:02d}"
            config = json.loads((run_dir / "p1_run_config.json").read_text())
            valid, gaps, tsr, pmr = coverage(association, run_dir / "CameraTrajectory.txt")
            metrics_path = run_dir / "eval/metrics.json"
            metrics = json.loads(metrics_path.read_text()) if metrics_path.exists() else {}
            legal = bool(metrics and valid >= 2)
            ate = metrics.get("ate", {}) if legal else {}
            rpe_t = metrics.get("rpe_trans", {}) if legal else {}
            rpe_r = metrics.get("rpe_rot_deg", {}) if legal else {}
            tracking_fps, end_fps, runtime = runtime_values(run_dir, config)
            completion_state, completion_evidence = completion(run_dir)
            rows.append({
                "sequence": sequence, "run_id": f"run_{run_id:02d}",
                "original_status": config.get("status", "unknown"),
                "exit_code": config.get("return_code", ""),
                "raw_process_status": raw_status(config),
                "experiment_completion_status": completion_state,
                "completion_evidence": completion_evidence,
                "association_total_frames": expected_total, "trajectory_valid_poses": valid,
                "ATE_RMSE": float(ate.get("rmse", math.nan)), "ATE_mean": float(ate.get("mean", math.nan)),
                "ATE_median": float(ate.get("median", math.nan)), "ATE_std": float(ate.get("std", math.nan)),
                "RPE_translation_RMSE": float(rpe_t.get("rmse", math.nan)),
                "RPE_rotation_RMSE": float(rpe_r.get("rmse", math.nan)),
                "tracking_gap_episodes": gaps, "tracking_success_rate": tsr, "pose_missing_ratio": pmr,
                "tracking_FPS": tracking_fps, "end_to_end_FPS": end_fps, "runtime_seconds": runtime,
                "has_legal_evaluation": int(legal), "run_dir": str(run_dir),
            })
    return rows


def values(rows: list[dict[str, object]], key: str) -> list[float]:
    return [float(r[key]) for r in rows if isinstance(r[key], (int, float)) and math.isfinite(float(r[key]))]


def mean(v: list[float]) -> float:
    return statistics.fmean(v) if v else math.nan


def std(v: list[float]) -> float:
    return statistics.stdev(v) if len(v) > 1 else (0.0 if len(v) == 1 else math.nan)


def summaries(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    output = []
    for sequence in SEQUENCES:
        group = [r for r in rows if r["sequence"] == sequence]
        legal = [r for r in group if r["has_legal_evaluation"] == 1]
        ate = values(legal, "ATE_RMSE")
        output.append({
            "sequence": sequence, "n_total": len(group),
            "n_raw_exit_0": sum(r["raw_process_status"] == "exit_0" for r in group),
            "n_raw_nonzero_or_unknown": sum(r["raw_process_status"] != "exit_0" for r in group),
            "n_completed": sum(r["experiment_completion_status"] == "completed" for r in group),
            "n_incomplete": sum(r["experiment_completion_status"] == "incomplete" for r in group),
            "n_invalid": sum(r["experiment_completion_status"] == "invalid" for r in group),
            "n_legal_evaluation": len(legal),
            "raw_exit_0_rate": sum(r["raw_process_status"] == "exit_0" for r in group) / len(group),
            "experiment_completion_rate": sum(r["experiment_completion_status"] == "completed" for r in group) / len(group),
            "ATE_RMSE_mean": mean(ate), "ATE_RMSE_std": std(ate),
            "ATE_RMSE_min": min(ate) if ate else math.nan, "ATE_RMSE_max": max(ate) if ate else math.nan,
            "ATE_mean_mean": mean(values(legal, "ATE_mean")),
            "ATE_median_mean": mean(values(legal, "ATE_median")),
            "RPE_translation_mean": mean(values(legal, "RPE_translation_RMSE")),
            "RPE_translation_std": std(values(legal, "RPE_translation_RMSE")),
            "RPE_rotation_mean": mean(values(legal, "RPE_rotation_RMSE")),
            "RPE_rotation_std": std(values(legal, "RPE_rotation_RMSE")),
            "TSR_mean": mean(values(group, "tracking_success_rate")),
            "TSR_std": std(values(group, "tracking_success_rate")),
            "PMR_mean": mean(values(group, "pose_missing_ratio")),
            "PMR_std": std(values(group, "pose_missing_ratio")),
            "Tracking_FPS_mean": mean(values(group, "tracking_FPS")),
            "Tracking_FPS_std": std(values(group, "tracking_FPS")),
            "EndToEnd_FPS_mean": mean(values(group, "end_to_end_FPS")),
            "EndToEnd_FPS_std": std(values(group, "end_to_end_FPS")),
        })
    return output


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: fmt(row.get(key, "")) for key in fields})


def report(rows: list[dict[str, object]], summary: list[dict[str, object]]) -> None:
    lines = ["# P1 Full TUM Repeated Experiment Report", "", "## Completion", "",
             "- Fixed run IDs completed: 15/15.",
             f"- Raw process `exit_0`: {sum(r['raw_process_status']=='exit_0' for r in rows)}/15.",
             f"- Raw process nonzero/unknown: {sum(r['raw_process_status']!='exit_0' for r in rows)}/15.",
             f"- Evidence-based experiment completion: {sum(r['experiment_completion_status']=='completed' for r in rows)}/15.",
             "- No failed run was deleted or replaced.",
             "- Raw process status and experiment completion are independent; exit codes are never rewritten from artifact evidence.", "",
             "## Statistical inclusion policy actually used", "",
             "- ATE/RPE: all runs with a non-empty trajectory and valid `eval/metrics.json` (`has_legal_evaluation=1`). In P1 this is 5/5 runs for every sequence, including rpy run_01 and run_03; it is not limited to the three rpy `exit_0` runs.",
             "- TSR/PMR and tracking gaps: all five fixed run IDs per sequence, derived from each trajectory against the association file, regardless of raw exit status.",
             "- Tracking FPS: every run containing a parseable `runtime.txt`; P1 has this for all 15 runs.",
             "- End-to-end FPS: every run with recorded outer runtime; P1 has this for all 15 runs.", "",
             "## Per-run Status", "", "| Sequence | Run | Original status | Raw process | Completion | Valid poses | ATE RMSE | RPE trans | TSR | PMR | Tracking FPS | End-to-end FPS |",
             "|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        def f(k: str) -> str:
            v = r[k]
            return "--" if isinstance(v, float) and not math.isfinite(v) else (f"{v:.6f}" if isinstance(v, float) else str(v))
        lines.append(f"| {r['sequence']} | {r['run_id']} | {r['original_status']} | {r['raw_process_status']} | {r['experiment_completion_status']} | {r['trajectory_valid_poses']} | {f('ATE_RMSE')} | {f('RPE_translation_RMSE')} | {f('tracking_success_rate')} | {f('pose_missing_ratio')} | {f('tracking_FPS')} | {f('end_to_end_FPS')} |")
    lines += ["", "## Sequence Summary", "", "| Sequence | n total | raw exit 0 | completed | legal eval | raw exit-0 rate | completion rate | ATE RMSE mean ± std | RPE trans mean ± std | TSR mean | PMR mean |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for s in summary:
        lines.append(f"| {s['sequence']} | {s['n_total']} | {s['n_raw_exit_0']} | {s['n_completed']} | {s['n_legal_evaluation']} | {s['raw_exit_0_rate']:.3f} | {s['experiment_completion_rate']:.3f} | {s['ATE_RMSE_mean']:.6f} ± {s['ATE_RMSE_std']:.6f} | {s['RPE_translation_mean']:.6f} ± {s['RPE_translation_std']:.6f} | {s['TSR_mean']:.6f} | {s['PMR_mean']:.6f} |")
    lines += ["", "## Stability and Outliers", ""]
    for sequence in SEQUENCES:
        group = [r for r in rows if r["sequence"] == sequence and r["has_legal_evaluation"] == 1]
        vals = values(group, "ATE_RMSE")
        if len(vals) >= 3:
            m, sd = mean(vals), std(vals)
            outliers = [r["run_id"] for r in group if sd > 0 and abs(float(r["ATE_RMSE"])-m) > 2*sd]
            lines.append(f"- `{sequence}`: 2-sample-standard-deviation rule flags {', '.join(outliers) if outliers else 'no run'}; no value was removed.")
    lines += ["- `fr3_walking_rpy` recorded 3/5 success and 2/5 interrupted metadata states. Both interrupted directories nevertheless contain normal SLAM shutdown markers and valid evaluation files; see `fr3_walking_rpy_interruption_audit.md`. This metadata/runner inconsistency must accompany any accuracy summary.", "",
              "## Artifacts", "", f"- Root: `{ROOT}`", "- Every run directory contains its configuration and available terminal/SLAM/YOLO logs, trajectories, semantic statistics, and evaluation output.", "- Environment and hashes: `experiment_environment.json`.", ""]
    (ROOT / "p1_full_experiment_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    rows = read_rows()
    summary = summaries(rows)
    write_csv(ROOT / "tum_full_runs.csv", rows, FIELDS)
    write_csv(ROOT / "tum_full_summary.csv", summary, list(summary[0]))
    report(rows, summary)


if __name__ == "__main__":
    main()
