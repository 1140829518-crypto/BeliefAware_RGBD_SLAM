#!/usr/bin/env python3
"""Run theta sensitivity experiments for semantic dynamic evidence.

The algorithmic rule is unchanged:

    s_i^t >= theta_c

Only the threshold parameter is exposed through environment variables and
changed per run.
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


REPO = Path(__file__).resolve().parents[1]
OUT_ROOT = REPO / "results/theta_sensitivity"
RUN_ROOT = OUT_ROOT / "runs"
FIG_PATH = OUT_ROOT / "Fig_theta_sensitivity.pdf"
RUNNER = REPO / "scripts/run_tum_rgbd_experiment.py"
SETTINGS = REPO / "Examples/RGB-D/TUM3.yaml"

THETAS = [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0]
REPEATS = [1, 2, 3]
SEQUENCES = {
    "fr3_walking_xyz": {
        "dataset": REPO.parent.parent / "datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz",
        "association": REPO / "dataset_associations/fr3_walking_xyz_associate.txt",
    },
    "fr3_walking_rpy": {
        "dataset": REPO.parent.parent / "datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_rpy",
        "association": REPO / "dataset_associations/fr3_walking_rpy_associate.txt",
    },
    "fr3_walking_halfsphere": {
        "dataset": REPO.parent.parent / "datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_halfsphere",
        "association": REPO / "dataset_associations/fr3_walking_halfsphere_associate.txt",
    },
}

DEFAULT_THETA = {"normal_dynamic_class": 3.0, "person": 1.0}
DEFAULT_GAMMA = {"normal_dynamic_class": 1.0, "person": 3.0}
DEFAULT_LAMBDA = {"normal_dynamic_class": 0.95, "person": 0.85}


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def count_non_comment_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip() and not line.lstrip().startswith("#"))


def count_valid_poses(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 8:
            continue
        try:
            vals = [float(v) for v in parts[:8]]
        except ValueError:
            continue
        if all(math.isfinite(v) for v in vals):
            count += 1
    return count


def read_metrics(path: Path) -> Dict[str, float]:
    if not path.exists():
        return {"ATE": math.nan, "RPE": math.nan}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {"ATE": float(data["ate"]["rmse"]), "RPE": float(data["rpe_trans"]["rmse"])}


def read_fps(path: Path) -> float:
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


def switching_frequency(path: Path) -> float:
    if not path.exists():
        return math.nan
    states: List[int] = []
    with path.open(encoding="utf-8", errors="ignore") as f:
        header = f.readline().strip().replace(",", " ").split()
        try:
            idx = header.index("dynamic_objects")
        except ValueError:
            return math.nan
        for line in f:
            parts = line.strip().replace(",", " ").split()
            if len(parts) <= idx:
                continue
            try:
                states.append(1 if float(parts[idx]) > 0 else 0)
            except ValueError:
                continue
    if len(states) < 2:
        return math.nan
    return sum(1 for a, b in zip(states, states[1:]) if a != b) / float(len(states) - 1)


def sample_mean(values: Iterable[float]) -> float:
    vals = [v for v in values if math.isfinite(v)]
    return statistics.mean(vals) if vals else math.nan


def sample_std(values: Iterable[float]) -> float:
    vals = [v for v in values if math.isfinite(v)]
    if not vals:
        return math.nan
    return statistics.stdev(vals) if len(vals) > 1 else 0.0


def fmt(value: float, digits: int = 6) -> str:
    return "nan" if not math.isfinite(value) else f"{value:.{digits}f}"


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


def run_one(theta: float, theta_class: str, sequence: str, repeat: int, device: str, timeout: int) -> Dict[str, object]:
    info = SEQUENCES[sequence]
    run_dir = RUN_ROOT / theta_class / f"theta_{theta:.1f}" / sequence / f"run_{repeat:02d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = run_dir / "eval/metrics.json"
    trajectory = run_dir / "CameraTrajectory.txt"
    completed = metrics_path.exists() and trajectory.exists()
    if completed:
        status = "success"
    else:
        socket_path = REPO / f".orb_theta_{theta_class}_{int(theta * 10):02d}_{sequence.replace('fr3_walking_', '')}_{repeat:02d}.sock"
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
        ]
        if theta_class == "person":
            cmd += ["--person-dynamic-theta", f"{theta:.1f}", "--dynamic-theta", f"{DEFAULT_THETA['normal_dynamic_class']:.1f}"]
            person_theta = theta
            normal_theta = DEFAULT_THETA["normal_dynamic_class"]
        elif theta_class == "normal":
            cmd += ["--dynamic-theta", f"{theta:.1f}", "--person-dynamic-theta", f"{DEFAULT_THETA['person']:.1f}"]
            person_theta = DEFAULT_THETA["person"]
            normal_theta = theta
        else:
            raise ValueError(f"Unsupported theta class: {theta_class}")

        config = {
            "experiment": "theta_sensitivity",
            "theta_class": theta_class,
            "theta": theta,
            "person_theta": person_theta,
            "normal_dynamic_class_theta": normal_theta,
            "lambda_c": DEFAULT_LAMBDA,
            "gamma_c": DEFAULT_GAMMA,
            "sequence": sequence,
            "repeat_id": repeat,
            "timestamp": now(),
            "method": "full",
            "semantic_mode": 2,
            "object_map": 1,
            "dataset": str(info["dataset"]),
            "association": str(info["association"]),
            "settings": str(SETTINGS),
            "command": " ".join(cmd),
            "env_vars": {
                "ORB_SLAM2_PERSON_DYNAMIC_THETA": f"{person_theta:.1f}",
                "ORB_SLAM2_DYNAMIC_THETA": f"{normal_theta:.1f}",
            },
        }
        (run_dir / "run_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (run_dir / "command.txt").write_text(" ".join(cmd) + "\n", encoding="utf-8")
        env = os.environ.copy()
        env["ORB_SLAM2_SOCKET_PATH"] = str(socket_path)
        env["MPLCONFIGDIR"] = str(OUT_ROOT / "matplotlib_cache")
        env["ORB_SLAM2_PERSON_DYNAMIC_THETA"] = f"{person_theta:.1f}"
        env["ORB_SLAM2_DYNAMIC_THETA"] = f"{normal_theta:.1f}"
        if socket_path.exists():
            socket_path.unlink()
        try:
            proc = subprocess.run(cmd, cwd=REPO, env=env, text=True, capture_output=True, timeout=timeout)
            (run_dir / "batch_stdout.log").write_text(proc.stdout, encoding="utf-8")
            (run_dir / "batch_stderr.log").write_text(proc.stderr, encoding="utf-8")
            status = "success" if proc.returncode == 0 else f"failed:{proc.returncode}"
        except subprocess.TimeoutExpired as exc:
            (run_dir / "batch_stdout.log").write_text(exc.stdout or "", encoding="utf-8")
            (run_dir / "batch_stderr.log").write_text((exc.stderr or "") + f"\nTIMEOUT after {timeout} seconds\n", encoding="utf-8")
            status = f"timeout:{timeout}"

    metrics = read_metrics(metrics_path)
    total = count_non_comment_lines(info["association"])
    valid = count_valid_poses(trajectory)
    pose_missing = 1.0 - valid / float(total) if total else math.nan
    tsr = valid / float(total) if total else math.nan
    switch = switching_frequency(run_dir / "SemanticDynamicStatistics.txt")
    return {
        "ThetaClass": theta_class,
        "theta": theta,
        "Sequence": sequence,
        "Repeat": repeat,
        "Status": status,
        "ATE": metrics["ATE"],
        "RPE": metrics["RPE"],
        "FPS": read_fps(run_dir / "runtime.txt"),
        "PoseMissingRatio": pose_missing,
        "TSR": tsr,
        "SwitchingFrequency": switch,
        "InputFrames": total,
        "ValidPoses": valid,
        "RunDir": str(run_dir),
    }


def write_csv(path: Path, rows: List[Dict[str, object]], fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def aggregate(rows: List[Dict[str, object]], theta_class: str) -> List[Dict[str, object]]:
    out = []
    for theta in THETAS:
        items = [r for r in rows if r["ThetaClass"] == theta_class and float(r["theta"]) == theta and str(r["Status"]) == "success"]
        out.append(
            {
                "theta": f"{theta:.1f}",
                "ATE_mean": fmt(sample_mean(float(r["ATE"]) for r in items)),
                "ATE_std": fmt(sample_std(float(r["ATE"]) for r in items)),
                "RPE_mean": fmt(sample_mean(float(r["RPE"]) for r in items)),
                "RPE_std": fmt(sample_std(float(r["RPE"]) for r in items)),
                "FPS_mean": fmt(sample_mean(float(r["FPS"]) for r in items)),
                "FPS_std": fmt(sample_std(float(r["FPS"]) for r in items)),
                "PoseMissingRatio_mean": fmt(sample_mean(float(r["PoseMissingRatio"]) for r in items)),
                "PoseMissingRatio_std": fmt(sample_std(float(r["PoseMissingRatio"]) for r in items)),
                "TSR_mean": fmt(sample_mean(float(r["TSR"]) for r in items)),
                "TSR_std": fmt(sample_std(float(r["TSR"]) for r in items)),
                "SwitchingFrequency_mean": fmt(sample_mean(float(r["SwitchingFrequency"]) for r in items)),
                "SwitchingFrequency_std": fmt(sample_std(float(r["SwitchingFrequency"]) for r in items)),
            }
        )
    return out


def write_latex(rows: List[Dict[str, object]]) -> None:
    lines = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{Sensitivity analysis of dynamic evidence decision threshold $\theta$.}",
        r"\label{tab:theta_sensitivity}",
        r"\begin{tabular}{lcccccc}",
        r"\toprule",
        r"$\theta$ & ATE (m) & RPE (m) & FPS & Pose Missing Ratio & TSR & Switching Frequency \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            f"{row['theta']} & "
            f"{row['ATE_mean']} $\\pm$ {row['ATE_std']} & "
            f"{row['RPE_mean']} $\\pm$ {row['RPE_std']} & "
            f"{row['FPS_mean']} $\\pm$ {row['FPS_std']} & "
            f"{row['PoseMissingRatio_mean']} $\\pm$ {row['PoseMissingRatio_std']} & "
            f"{row['TSR_mean']} $\\pm$ {row['TSR_std']} & "
            f"{row['SwitchingFrequency_mean']} $\\pm$ {row['SwitchingFrequency_std']} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""])
    (OUT_ROOT / "theta_sensitivity_results.tex").write_text("\n".join(lines), encoding="utf-8")


def plot(rows: List[Dict[str, object]]) -> None:
    xs = [float(r["theta"]) for r in rows]
    specs = [
        ("ATE", "ATE RMSE (m)", "(a) theta-ATE"),
        ("RPE", "RPE translation RMSE (m)", "(b) theta-RPE"),
        ("PoseMissingRatio", "Pose Missing Ratio", "(c) theta-Pose Missing Ratio"),
        ("SwitchingFrequency", "Switching Frequency", "(d) theta-Switching Frequency"),
    ]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.grid": False, "savefig.dpi": 600})
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.8))
    for ax, (metric, ylabel, title) in zip(axes.ravel(), specs):
        means = [float(r[f"{metric}_mean"]) for r in rows]
        stds = [float(r[f"{metric}_std"]) for r in rows]
        ax.errorbar(xs, means, yerr=stds, marker="o", capsize=3, linewidth=1.5, color="#1f77b4")
        ax.set_xlabel(r"$\theta$")
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontweight="bold")
        ax.set_xticks(xs)
        ax.set_ylim(bottom=0)
        ax.grid(False)
    fig.tight_layout()
    fig.savefig(FIG_PATH, bbox_inches="tight")
    plt.close(fig)


def write_analysis(rows: List[Dict[str, object]], per_rows: List[Dict[str, object]], theta_class: str, normal_requested: bool) -> None:
    best_ate = min(rows, key=lambda r: float(r["ATE_mean"]))
    best_rpe = min(rows, key=lambda r: float(r["RPE_mean"]))
    best_fps = max(rows, key=lambda r: float(r["FPS_mean"]))
    best_missing = min(rows, key=lambda r: float(r["PoseMissingRatio_mean"]))
    best_tsr = max(rows, key=lambda r: float(r["TSR_mean"]))
    best_switch = min(rows, key=lambda r: float(r["SwitchingFrequency_mean"]))
    completed = sum(1 for r in per_rows if str(r["Status"]) == "success")
    expected = len(THETAS) * len(SEQUENCES) * len(REPEATS)
    failed = [r for r in per_rows if str(r["Status"]) != "success"]
    lines = [
        "# Theta Sensitivity Analysis",
        "",
        f"- Generated at: {now()}",
        f"- Output root: `{OUT_ROOT}`",
        f"- Main scanned threshold: `{theta_class}`",
        f"- Expected main-scan runs: {expected}",
        f"- Completed main-scan runs: {completed}",
        f"- Failed main-scan runs: {len(failed)}",
        "",
        "## Parameter Path",
        "",
        "- Decision formula remains `s_i^t >= theta_c`.",
        "- Code path: `include/SemanticConfig.h::DynamicScoreThresholdForClass` reads `ORB_SLAM2_PERSON_DYNAMIC_THETA` for person and `ORB_SLAM2_DYNAMIC_THETA` for non-person dynamic classes.",
        "- `src/MapPoint.cc::ShouldSuppressSemanticDynamic` and `src/ORBmatcher.cc` use the same threshold comparison as before.",
        "- `lambda_c` and `gamma_c` remain at code defaults: person lambda=0.85, gamma=3.0; normal lambda=0.95, gamma=1.0.",
        "",
        "## Dataset Note",
        "",
        "- Current active dynamic object class set is `{person}` in `SemanticConfig::DynamicObjectClasses()`.",
        "- Therefore the TUM walking sequences mainly evaluate person theta. Non-person dynamic theta is retained in run configs but is not an effective variable for these sequences.",
    ]
    if normal_requested:
        lines.append("- A normal-class scan was requested, but its interpretation must be limited because no non-person dynamic class is active in the current TUM walking setup.")
    lines.extend(
        [
            "",
            "## Paper-ready Analysis",
            "",
            f"动态证据判定阈值敏感性实验表明，阈值 $\\theta$ 会影响动态点抑制强度与轨迹输出完整性之间的平衡。当前采样点中，ATE 最低出现在 $\\theta={best_ate['theta']}$，RPE 最低出现在 $\\theta={best_rpe['theta']}$，动态状态切换频率最低出现在 $\\theta={best_switch['theta']}$；FPS 最高出现在 $\\theta={best_fps['theta']}$，Pose Missing Ratio 最低和 TSR 最高均出现在 $\\theta={best_missing['theta']}$。因此，不存在一个在所有指标上同时最优的阈值。",
            "",
            "从机理上看，较低的 $\\theta$ 使动态证据更容易达到抑制条件，动态点可能被更早剔除；该设置有助于减少动态误匹配，但在快速运动或旋转场景中也可能减少可用于跟踪的有效静态特征，从而影响位姿输出连续性。较高的 $\\theta$ 则需要更长时间积累动态证据，动态点残留时间增加，可能引入更多动态误匹配并影响 ATE/RPE。综合 ATE、RPE、Pose Missing Ratio、TSR 和 Switching Frequency，论文中不宜将某一阈值表述为绝对最优，而应强调阈值选择体现动态抑制强度与轨迹完整性之间的权衡。",
            "",
            "该实验作为 $\\lambda$ 敏感性分析的补充，说明时间一致性模型不仅受证据衰减速度影响，也受最终动态判定阈值影响。论文中应将 ATE/RPE 与 Pose Missing Ratio、TSR 联合解释，避免在轨迹覆盖率较低时仅依据局部误差得出过强结论。",
            "",
            "## Failed Runs",
            "",
        ]
    )
    lines.extend([f"- theta={r['theta']} sequence={r['Sequence']} repeat={r['Repeat']} status={r['Status']} dir={r['RunDir']}" for r in failed] or ["- None."])
    (OUT_ROOT / "theta_sensitivity_analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run theta sensitivity experiments.")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--timeout-sec", type=int, default=900)
    parser.add_argument("--theta-class", choices=["person", "normal"], default="person")
    parser.add_argument("--include-normal-scan", action="store_true", help="Also run normal dynamic class theta scan; not effective for current person-only dynamic class setup.")
    args = parser.parse_args()

    ensure_inputs()
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    classes = [args.theta_class]
    if args.include_normal_scan and "normal" not in classes:
        classes.append("normal")

    rows: List[Dict[str, object]] = []
    for theta_class in classes:
        for theta in THETAS:
            for sequence in SEQUENCES:
                for repeat in REPEATS:
                    print(f"[theta] class={theta_class} theta={theta:.1f} sequence={sequence} repeat={repeat}", flush=True)
                    rows.append(run_one(theta, theta_class, sequence, repeat, args.device, args.timeout_sec))

    per_fields = [
        "ThetaClass",
        "theta",
        "Sequence",
        "Repeat",
        "Status",
        "ATE",
        "RPE",
        "FPS",
        "PoseMissingRatio",
        "TSR",
        "SwitchingFrequency",
        "InputFrames",
        "ValidPoses",
        "RunDir",
    ]
    write_csv(OUT_ROOT / "theta_sensitivity_per_run_results.csv", rows, per_fields)
    main_rows = [r for r in rows if r["ThetaClass"] == args.theta_class]
    agg = aggregate(main_rows, args.theta_class)
    agg_fields = [
        "theta",
        "ATE_mean",
        "ATE_std",
        "RPE_mean",
        "RPE_std",
        "FPS_mean",
        "FPS_std",
        "PoseMissingRatio_mean",
        "PoseMissingRatio_std",
        "TSR_mean",
        "TSR_std",
        "SwitchingFrequency_mean",
        "SwitchingFrequency_std",
    ]
    write_csv(OUT_ROOT / "theta_sensitivity_results.csv", agg, agg_fields)
    write_latex(agg)
    plot(agg)
    write_analysis(agg, main_rows, args.theta_class, args.include_normal_scan)
    print(f"Results: {OUT_ROOT / 'theta_sensitivity_results.csv'}")
    print(f"LaTeX: {OUT_ROOT / 'theta_sensitivity_results.tex'}")
    print(f"Figure: {FIG_PATH}")
    print(f"Analysis: {OUT_ROOT / 'theta_sensitivity_analysis.md'}")


if __name__ == "__main__":
    main()
