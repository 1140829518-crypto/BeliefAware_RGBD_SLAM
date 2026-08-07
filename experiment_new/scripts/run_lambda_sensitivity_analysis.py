#!/usr/bin/env python3
"""Run real lambda sensitivity experiments for semantic dynamic accumulation.

This script does not modify SLAM source code. It runs the existing RGB-D binary
through scripts/run_tum_rgbd_experiment.py with ORB_SLAM2_DYNAMIC_LAMBDA set.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


REPO = Path(__file__).resolve().parents[2]
EXP_ROOT = REPO / "experiment_new/lambda_sensitivity_analysis_v1"
RUN_ROOT = EXP_ROOT / "runs"
RESULT_DIR = EXP_ROOT / "results"
FIG_DIR = EXP_ROOT / "fig_lambda_sensitivity"

LAMBDAS = [0.70, 0.80, 0.85, 0.90, 0.95]
REPEATS = [1, 2, 3]
SEQUENCES = {
    "fr3_walking_xyz": {
        "dataset": REPO.parent.parent / "datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz",
        "association": REPO / "dataset_associations/fr3_walking_xyz_associate.txt",
    },
    "fr3_walking_halfsphere": {
        "dataset": REPO.parent.parent / "datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_halfsphere",
        "association": REPO / "dataset_associations/fr3_walking_halfsphere_associate.txt",
    },
    "fr3_walking_rpy": {
        "dataset": REPO.parent.parent / "datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_rpy",
        "association": REPO / "dataset_associations/fr3_walking_rpy_associate.txt",
    },
}

SETTINGS = REPO / "Examples/RGB-D/TUM3.yaml"
RUNNER = REPO / "scripts/run_tum_rgbd_experiment.py"

GAMMA_DEFAULT = {
    "non_person_dynamic": 1.0,
    "person": 3.0,
}
THETA_DEFAULT = {
    "non_person_dynamic": 3.0,
    "person": 1.0,
}
CODE_DEFAULT_LAMBDA = {
    "non_person_dynamic": 0.95,
    "person": 0.85,
}


def timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def count_association_frames(path: Path) -> int:
    count = 0
    with path.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                count += 1
    return count


def count_trajectory_poses(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and len(line.split()) >= 8:
                count += 1
    return count


def parse_runtime(path: Path) -> float:
    if not path.exists():
        return math.nan
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] == "fps":
            try:
                return float(parts[1])
            except ValueError:
                return math.nan
    return math.nan


def read_metrics(path: Path) -> Dict[str, float]:
    if not path.exists():
        return {"ATE": math.nan, "RPE": math.nan}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "ATE": float(data["ate"]["rmse"]),
        "RPE": float(data["rpe_trans"]["rmse"]),
    }


def switching_frequency(path: Path) -> float:
    if not path.exists():
        return math.nan
    states: List[int] = []
    with path.open(encoding="utf-8", errors="ignore") as f:
        header = f.readline().strip().split()
        try:
            idx = header.index("dynamic_objects")
        except ValueError:
            return math.nan
        for line in f:
            parts = line.strip().split()
            if len(parts) <= idx:
                continue
            try:
                states.append(1 if float(parts[idx]) > 0 else 0)
            except ValueError:
                continue
    if len(states) < 2:
        return math.nan
    switches = sum(1 for a, b in zip(states, states[1:]) if a != b)
    return switches / float(len(states) - 1)


def sample_mean(values: Iterable[float]) -> float:
    vals = [v for v in values if not math.isnan(v)]
    return statistics.mean(vals) if vals else math.nan


def sample_std(values: Iterable[float]) -> float:
    vals = [v for v in values if not math.isnan(v)]
    if len(vals) <= 1:
        return 0.0 if vals else math.nan
    return statistics.stdev(vals)


def fmt_float(value: float, digits: int = 6) -> str:
    return "nan" if math.isnan(value) else f"{value:.{digits}f}"


def ensure_inputs() -> None:
    missing = []
    for path in [RUNNER, SETTINGS, REPO / "Examples/RGB-D/rgbd_tum", REPO / "Vocabulary/ORBvoc.txt"]:
        if not path.exists():
            missing.append(path)
    for info in SEQUENCES.values():
        for path in [info["dataset"], info["association"], info["dataset"] / "groundtruth.txt"]:
            if not path.exists():
                missing.append(path)
    if missing:
        raise FileNotFoundError("Missing required input files:\n" + "\n".join(str(p) for p in missing))


def run_one(lamb: float, sequence: str, repeat_id: int, device: str, force: bool, timeout_sec: int) -> Dict[str, object]:
    info = SEQUENCES[sequence]
    run_dir = RUN_ROOT / f"lambda_{lamb:.2f}" / sequence / f"run_{repeat_id:02d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    socket_path = REPO / f".orb_lam_{int(round(lamb * 100)):03d}_{sequence.replace('fr3_walking_', '')}_{repeat_id:02d}.sock"
    metrics_path = run_dir / "eval/metrics.json"
    completed = metrics_path.exists() and (run_dir / "CameraTrajectory.txt").exists()
    if completed and not force:
        status = "skipped_existing"
    else:
        if any(run_dir.iterdir()) and force:
            raise RuntimeError(f"Refusing to overwrite non-empty run directory with --force disabled safeguards: {run_dir}")
        cmd = [
            sys.executable,
            str(RUNNER),
            "--sequence",
            sequence,
            "--method",
            "full",
            "--dataset",
            str(info["dataset"]),
            "--association",
            str(info["association"]),
            "--settings",
            str(SETTINGS),
            "--out-dir",
            str(run_dir),
            "--device",
            device,
            "--dynamic-lambda",
            f"{lamb:.2f}",
        ]
        config = {
            "experiment": "lambda_sensitivity_analysis_v1",
            "lambda_c": lamb,
            "lambda_env_var": "ORB_SLAM2_DYNAMIC_LAMBDA",
            "lambda_effect_note": (
                "Current code exposes one global ORB_SLAM2_DYNAMIC_LAMBDA; "
                "therefore non-person and person decay are both overridden in this run."
            ),
            "code_default_lambda": CODE_DEFAULT_LAMBDA,
            "actual_person_lambda": lamb,
            "gamma_c": GAMMA_DEFAULT,
            "theta_c": THETA_DEFAULT,
            "sequence": sequence,
            "repeat_id": repeat_id,
            "timestamp": timestamp(),
            "semantic_mode": 2,
            "object_map": 1,
            "method": "full",
            "dataset": str(info["dataset"]),
            "association": str(info["association"]),
            "settings": str(SETTINGS),
            "socket_path": str(socket_path),
            "command": " ".join(cmd),
        }
        (run_dir / "run_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (run_dir / "command.txt").write_text(" ".join(cmd) + "\n", encoding="utf-8")
        env = os.environ.copy()
        env["ORB_SLAM2_DYNAMIC_LAMBDA"] = f"{lamb:.2f}"
        env["ORB_SLAM2_SOCKET_PATH"] = str(socket_path)
        env["MPLCONFIGDIR"] = str(EXP_ROOT / "matplotlib_cache")
        try:
            if socket_path.exists():
                socket_path.unlink()
        except OSError:
            pass
        try:
            proc = subprocess.run(cmd, cwd=REPO, env=env, text=True, capture_output=True, timeout=timeout_sec)
            (run_dir / "batch_stdout.log").write_text(proc.stdout, encoding="utf-8")
            (run_dir / "batch_stderr.log").write_text(proc.stderr, encoding="utf-8")
            if proc.returncode != 0:
                status = f"failed:{proc.returncode}"
            else:
                status = "success"
        except subprocess.TimeoutExpired as exc:
            (run_dir / "batch_stdout.log").write_text(exc.stdout or "", encoding="utf-8")
            (run_dir / "batch_stderr.log").write_text((exc.stderr or "") + f"\nTIMEOUT after {timeout_sec} seconds\n", encoding="utf-8")
            status = f"timeout:{timeout_sec}"

    metrics = read_metrics(metrics_path)
    input_frames = count_association_frames(info["association"])
    poses = count_trajectory_poses(run_dir / "CameraTrajectory.txt")
    pose_missing = 1.0 - poses / float(input_frames) if input_frames > 0 else math.nan
    row: Dict[str, object] = {
        "Lambda": lamb,
        "Sequence": sequence,
        "Repeat": repeat_id,
        "Status": status,
        "ATE": metrics["ATE"],
        "RPE": metrics["RPE"],
        "FPS": parse_runtime(run_dir / "runtime.txt"),
        "PoseMissing": pose_missing,
        "SwitchingFrequency": switching_frequency(run_dir / "SemanticDynamicStatistics.txt"),
        "RunDir": str(run_dir),
    }
    return row


def write_csv(path: Path, rows: List[Dict[str, object]], fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def aggregate(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    for lamb in LAMBDAS:
        items = [r for r in rows if float(r["Lambda"]) == lamb and str(r["Status"]) in {"success", "skipped_existing"}]
        out.append(
            {
                "Lambda": f"{lamb:.2f}",
                "ATE_mean": fmt_float(sample_mean(float(r["ATE"]) for r in items)),
                "ATE_std": fmt_float(sample_std(float(r["ATE"]) for r in items)),
                "RPE_mean": fmt_float(sample_mean(float(r["RPE"]) for r in items)),
                "RPE_std": fmt_float(sample_std(float(r["RPE"]) for r in items)),
                "FPS_mean": fmt_float(sample_mean(float(r["FPS"]) for r in items)),
                "FPS_std": fmt_float(sample_std(float(r["FPS"]) for r in items)),
                "PoseMissing_mean": fmt_float(sample_mean(float(r["PoseMissing"]) for r in items)),
                "PoseMissing_std": fmt_float(sample_std(float(r["PoseMissing"]) for r in items)),
                "SwitchingFrequency_mean": fmt_float(sample_mean(float(r["SwitchingFrequency"]) for r in items)),
                "SwitchingFrequency_std": fmt_float(sample_std(float(r["SwitchingFrequency"]) for r in items)),
            }
        )
    return out


def write_latex(rows: List[Dict[str, object]]) -> None:
    lines = [
        "\\begin{table}[t]",
        "\\centering",
        "\\caption{Sensitivity analysis of dynamic evidence decay coefficient $\\lambda$.}",
        "\\label{tab:lambda_sensitivity}",
        "\\begin{tabular}{lccccc}",
        "\\toprule",
        "$\\lambda$ & ATE (m) & RPE (m) & FPS & Pose Missing Ratio & Switching Frequency \\\\",
        "\\midrule",
    ]
    for row in rows:
        lines.append(
            f"{row['Lambda']} & "
            f"{row['ATE_mean']} $\\pm$ {row['ATE_std']} & "
            f"{row['RPE_mean']} $\\pm$ {row['RPE_std']} & "
            f"{row['FPS_mean']} $\\pm$ {row['FPS_std']} & "
            f"{row['PoseMissing_mean']} $\\pm$ {row['PoseMissing_std']} & "
            f"{row['SwitchingFrequency_mean']} $\\pm$ {row['SwitchingFrequency_std']} \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}", ""])
    (RESULT_DIR / "table_lambda_sensitivity.tex").write_text("\n".join(lines), encoding="utf-8")


def plot_metric(rows: List[Dict[str, object]], metric: str, ylabel: str, filename: str) -> None:
    xs = [float(r["Lambda"]) for r in rows]
    means = [float(r[f"{metric}_mean"]) for r in rows]
    stds = [float(r[f"{metric}_std"]) for r in rows]
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "axes.grid": True,
            "grid.alpha": 0.24,
        }
    )
    fig, ax = plt.subplots(figsize=(4.8, 3.4))
    ax.errorbar(xs, means, yerr=stds, marker="o", capsize=4, linewidth=1.6, color="#2F6FAF")
    ax.set_xlabel("$\\lambda$")
    ax.set_ylabel(ylabel)
    ax.set_xticks(xs)
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / filename, bbox_inches="tight")
    plt.close(fig)


def write_audit(rows: List[Dict[str, object]], aggregate_rows: List[Dict[str, object]], force: bool) -> None:
    expected = len(LAMBDAS) * len(SEQUENCES) * len(REPEATS)
    success = sum(1 for r in rows if str(r["Status"]) == "success")
    skipped = sum(1 for r in rows if str(r["Status"]) == "skipped_existing")
    failed = [r for r in rows if str(r["Status"]).startswith("failed")]
    best_ate = min(aggregate_rows, key=lambda r: float(r["ATE_mean"]))
    best_rpe = min(aggregate_rows, key=lambda r: float(r["RPE_mean"]))
    best_switch = min(aggregate_rows, key=lambda r: float(r["SwitchingFrequency_mean"]))
    best_recommend = min(
        aggregate_rows,
        key=lambda r: (
            float(r["ATE_mean"]) + float(r["RPE_mean"]) + float(r["SwitchingFrequency_mean"])
        ),
    )
    lines = [
        "# Lambda Sensitivity Audit",
        "",
        f"- Generated at: {timestamp()}",
        f"- Experiment root: `{EXP_ROOT}`",
        f"- Expected runs: {expected}",
        f"- Successful newly executed runs: {success}",
        f"- Skipped existing completed runs: {skipped}",
        f"- Failed runs: {len(failed)}",
        f"- Force mode: {force}",
        "",
        "## Real Program Invocation",
        "",
        "- Real SLAM program was invoked through `scripts/run_tum_rgbd_experiment.py`.",
        "- The runner calls `Examples/RGB-D/rgbd_tum` and evaluates `CameraTrajectory.txt` against TUM ground truth.",
        "- No old metrics are copied or scaled by this script.",
        "",
        "## Lambda Source and Effect",
        "",
        "- Parameter source: environment variable `ORB_SLAM2_DYNAMIC_LAMBDA`.",
        "- Code path: `include/SemanticConfig.h::DynamicScoreDecayForClass` reads `ORB_SLAM2_DYNAMIC_LAMBDA` and returns the decay used by `src/MapPoint.cc::UpdateSemanticDynamicScore`.",
        "- Dynamic decision path: accumulated score is compared with `DynamicScoreThresholdForClass`; suppressed MapPoints are removed in `ORBmatcher` and `Tracking`.",
        "- Current code exposes one global decay override. Therefore person decay is also set to the tested lambda in these runs; this limitation is recorded in every `run_config.json`.",
        "- `gamma_c` and `theta_c` remain at code defaults: non-person gamma=1.0, theta=3.0; person gamma=3.0, theta=1.0.",
        "",
        "## Actual Lambda Values",
        "",
        ", ".join(f"{v:.2f}" for v in LAMBDAS),
        "",
        "## Outputs",
        "",
        f"- Per-run directories: `{RUN_ROOT}`",
        f"- Per-run CSV: `{RESULT_DIR / 'lambda_per_run_results.csv'}`",
        f"- Summary CSV: `{RESULT_DIR / 'lambda_results.csv'}`",
        f"- LaTeX table: `{RESULT_DIR / 'table_lambda_sensitivity.tex'}`",
        f"- Figures: `{FIG_DIR}`",
        "",
        "## Best Lambda by Mean Metric",
        "",
        f"- Lowest ATE: lambda={best_ate['Lambda']} ({best_ate['ATE_mean']})",
        f"- Lowest RPE: lambda={best_rpe['Lambda']} ({best_rpe['RPE_mean']})",
        f"- Lowest Switching Frequency: lambda={best_switch['Lambda']} ({best_switch['SwitchingFrequency_mean']})",
        f"- Recommended paper value by simple ATE+RPE+SwitchingFrequency criterion: lambda={best_recommend['Lambda']}",
        "",
        "## Failed Runs",
        "",
    ]
    if failed:
        for row in failed:
            lines.append(f"- lambda={row['Lambda']}, sequence={row['Sequence']}, repeat={row['Repeat']}, dir={row['RunDir']}, status={row['Status']}")
    else:
        lines.append("- None.")
    lines.append("")
    (EXP_ROOT / "lambda_sensitivity_audit.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run real lambda sensitivity experiments.")
    parser.add_argument("--device", default="cpu", help="YOLO device.")
    parser.add_argument("--timeout-sec", type=int, default=900, help="Timeout for each individual run.")
    parser.add_argument("--force", action="store_true", help="Reserved; currently refuses overwriting non-empty run directories.")
    args = parser.parse_args()

    ensure_inputs()
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, object]] = []
    for lamb in LAMBDAS:
        for sequence in SEQUENCES:
            for repeat_id in REPEATS:
                print(f"[lambda] running lambda={lamb:.2f} sequence={sequence} repeat={repeat_id}", flush=True)
                rows.append(run_one(lamb, sequence, repeat_id, args.device, args.force, args.timeout_sec))

    per_fields = ["Lambda", "Sequence", "Repeat", "Status", "ATE", "RPE", "FPS", "PoseMissing", "SwitchingFrequency", "RunDir"]
    write_csv(RESULT_DIR / "lambda_per_run_results.csv", rows, per_fields)
    agg = aggregate(rows)
    agg_fields = [
        "Lambda",
        "ATE_mean",
        "ATE_std",
        "RPE_mean",
        "RPE_std",
        "FPS_mean",
        "FPS_std",
        "PoseMissing_mean",
        "PoseMissing_std",
        "SwitchingFrequency_mean",
        "SwitchingFrequency_std",
    ]
    write_csv(RESULT_DIR / "lambda_results.csv", agg, agg_fields)
    write_latex(agg)
    plot_metric(agg, "ATE", "ATE RMSE (m)", "lambda_ATE.pdf")
    plot_metric(agg, "RPE", "RPE translation RMSE (m)", "lambda_RPE.pdf")
    plot_metric(agg, "FPS", "FPS (frame/s)", "lambda_FPS.pdf")
    plot_metric(agg, "SwitchingFrequency", "Switching Frequency", "lambda_SwitchingFrequency.pdf")
    write_audit(rows, agg, args.force)

    expected = len(LAMBDAS) * len(SEQUENCES) * len(REPEATS)
    ok = sum(1 for row in rows if str(row["Status"]) in {"success", "skipped_existing"})
    best = min(agg, key=lambda r: float(r["ATE_mean"]) + float(r["RPE_mean"]) + float(r["SwitchingFrequency_mean"]))
    print(f"Experiment root: {EXP_ROOT}")
    print(f"Expected runs: {expected}")
    print(f"Completed runs: {ok}")
    print(f"Summary: {RESULT_DIR / 'lambda_results.csv'}")
    print(f"Figures: {FIG_DIR}")
    print(f"Audit: {EXP_ROOT / 'lambda_sensitivity_audit.md'}")
    print(f"Recommended lambda: {best['Lambda']}")


if __name__ == "__main__":
    main()
