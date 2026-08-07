#!/usr/bin/env python3
"""Plot Bonn trajectory comparison and TUM trajectory stability figures."""

from __future__ import annotations

import argparse
import csv
import math
import os
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiment_new"
os.environ.setdefault("MPLCONFIGDIR", str(EXP / ".matplotlib_cache"))

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D


RESULT_DIR = EXP / "results"
FIG_DIR = EXP / "figures"
RUN_ROOT = RESULT_DIR / "bonn_runs"

METHODS = [
    ("Ground Truth", "#111111", "--"),
    ("ORB-SLAM3", "#4C78A8", "-"),
    ("DS-SLAM", "#72B7B2", "-"),
    ("Dyna-SLAM", "#F58518", "-"),
    ("Ours", "#54A24B", "-"),
]

TUM_TRAJ = {
    "Ground Truth": ROOT.parent.parent / "datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz/groundtruth.txt",
    "ORB-SLAM3": ROOT / "ORB_SLAM3_trajectory/freiburg3_walking_xyz/CameraTrajectory.txt",
    "DS-SLAM": ROOT / "baseline_runs_missing/ds_slam/fr3_walking_xyz/CameraTrajectory.txt",
    "Dyna-SLAM": ROOT / "baseline_runs_retry/dyna_slam/fr3_walking_xyz/CameraTrajectory.txt",
    "Ours": ROOT / "standard_runs/fr3_walking_xyz/full_method/CameraTrajectory.txt",
}


def method_slug(method: str) -> str:
    return method.lower().replace("-", "_").replace(" ", "_")


def read_manifest(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_tum(path: Path) -> Tuple[np.ndarray, np.ndarray]:
    stamps: List[float] = []
    xyz: List[List[float]] = []
    if not path.exists():
        return np.empty((0,)), np.empty((0, 3))
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        try:
            stamps.append(float(parts[0]))
            xyz.append([float(parts[1]), float(parts[2]), float(parts[3])])
        except ValueError:
            continue
    return np.asarray(stamps), np.asarray(xyz)


def associate(a: np.ndarray, b: np.ndarray, max_diff: float = 0.04) -> List[Tuple[int, int]]:
    if len(a) == 0 or len(b) == 0:
        return []
    out: List[Tuple[int, int]] = []
    j = 0
    for i, ta in enumerate(a):
        while j + 1 < len(b) and abs(b[j + 1] - ta) < abs(b[j] - ta):
            j += 1
        if abs(b[j] - ta) <= max_diff:
            out.append((i, j))
    return out


def align_umeyama(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    if len(src) < 3 or len(dst) < 3:
        return src
    mu_src = src.mean(axis=0)
    mu_dst = dst.mean(axis=0)
    src_c = src - mu_src
    dst_c = dst - mu_dst
    cov = src_c.T @ dst_c / len(src)
    u, _, vt = np.linalg.svd(cov)
    r = vt.T @ u.T
    if np.linalg.det(r) < 0:
        vt[-1, :] *= -1
        r = vt.T @ u.T
    t = mu_dst - r @ mu_src
    return (r @ src.T).T + t


def aligned_to_gt(est_path: Path, gt_path: Path) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    est_t, est_xyz = load_tum(est_path)
    gt_t, gt_xyz = load_tum(gt_path)
    matches = associate(est_t, gt_t)
    if not matches:
        return np.empty((0, 3)), np.empty((0, 3)), np.empty((0,))
    est_sel = np.asarray([est_xyz[i] for i, _ in matches])
    gt_sel = np.asarray([gt_xyz[j] for _, j in matches])
    times = np.asarray([gt_t[j] for _, j in matches])
    return align_umeyama(est_sel, gt_sel), gt_sel, times


def plot_bonn(manifest: Sequence[Dict[str, str]], run_root: Path) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    if not manifest:
        fig, ax = plt.subplots(figsize=(7.2, 4.2))
        ax.axis("off")
        ax.text(0.5, 0.5, "Bonn dataset not configured yet", ha="center", va="center")
        fig.savefig(FIG_DIR / "bonn_trajectory_comparison.png", dpi=300, bbox_inches="tight")
        plt.close(fig)
        return

    fig, axes = plt.subplots(1, len(manifest), figsize=(5.0 * len(manifest), 4.2), squeeze=False)
    for ax, item in zip(axes[0], manifest):
        dataset = item["Dataset"]
        sequence_dir = Path(item["Path"])
        gt_path = sequence_dir / "groundtruth.txt"
        gt_t, gt_xyz = load_tum(gt_path)
        if len(gt_xyz):
            ax.plot(gt_xyz[:, 0], gt_xyz[:, 2], color=METHODS[0][1], linestyle=METHODS[0][2], linewidth=1.4, label="Ground Truth")
        for method, color, linestyle in METHODS[1:]:
            est_path = run_root / dataset / method_slug(method) / "CameraTrajectory.txt"
            est, _, _ = aligned_to_gt(est_path, gt_path)
            if len(est):
                ax.plot(est[:, 0], est[:, 2], color=color, linestyle=linestyle, linewidth=1.25, label=method)
        missing = [
            method
            for method, _, _ in METHODS[1:]
            if not (run_root / dataset / method_slug(method) / "CameraTrajectory.txt").exists()
        ]
        if missing:
            ax.text(
                0.02,
                0.02,
                "trajectory pending: " + ", ".join(missing),
                transform=ax.transAxes,
                fontsize=7,
                color="#666666",
                va="bottom",
            )
        ax.set_title(dataset)
        ax.set_xlabel("X [m]")
        ax.set_ylabel("Z [m]")
        ax.set_aspect("equal", adjustable="box")
        ax.grid(True, alpha=0.25)
    handles = [Line2D([0], [0], color=color, linestyle=linestyle, linewidth=1.4) for _, color, linestyle in METHODS]
    labels = [method for method, _, _ in METHODS]
    fig.legend(handles, labels, loc="upper center", ncol=5, frameon=False)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    fig.savefig(FIG_DIR / "bonn_trajectory_comparison.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def moving_std(values: np.ndarray, window: int = 15) -> np.ndarray:
    if len(values) == 0:
        return values
    out = np.zeros_like(values)
    half = max(1, window // 2)
    for i in range(len(values)):
        lo = max(0, i - half)
        hi = min(len(values), i + half + 1)
        out[i] = float(np.std(values[lo:hi]))
    return out


def plot_tum_stability() -> None:
    gt_path = TUM_TRAJ["Ground Truth"]
    gt_t, gt_xyz = load_tum(gt_path)
    fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.1))
    axes[0].plot(gt_xyz[:, 0], gt_xyz[:, 2], color="#111111", linestyle="--", linewidth=1.3, label="Ground Truth")

    deviation_rows: List[Dict[str, str]] = []
    for method, color, linestyle in METHODS[1:]:
        est, gt, times = aligned_to_gt(TUM_TRAJ[method], gt_path)
        if len(est) == 0:
            continue
        axes[0].plot(est[:, 0], est[:, 2], color=color, linestyle=linestyle, linewidth=1.15, label=method)
        dev = np.linalg.norm(est - gt, axis=1)
        t = times - times[0]
        axes[1].plot(t, moving_std(dev, 21), color=color, linewidth=1.15, label=method)
        for ti, di in zip(t[:: max(1, len(t) // 80)], dev[:: max(1, len(dev) // 80)]):
            deviation_rows.append({"method": method, "time_s": f"{ti:.6f}", "deviation_m": f"{di:.6f}"})

    axes[0].set_title("Trajectory stability comparison")
    axes[0].set_xlabel("X [m]")
    axes[0].set_ylabel("Z [m]")
    axes[0].set_aspect("equal", adjustable="box")
    axes[1].set_title("Trajectory deviation stability")
    axes[1].set_xlabel("Time [s]")
    axes[1].set_ylabel("Moving std. of deviation [m]")
    for ax in axes:
        ax.grid(True, alpha=0.25)
    axes[0].legend(frameon=False, fontsize=8)
    axes[1].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "trajectory_stability_comparison.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    with (RESULT_DIR / "trajectory_deviation_samples.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["method", "time_s", "deviation_m"])
        writer.writeheader()
        writer.writerows(deviation_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot Bonn and trajectory-stability results.")
    parser.add_argument("--manifest", type=Path, default=RESULT_DIR / "bonn_selected_sequences.csv")
    parser.add_argument("--run-root", type=Path, default=RUN_ROOT)
    args = parser.parse_args()

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    manifest = read_manifest(args.manifest)
    plot_bonn(manifest, args.run_root)
    plot_tum_stability()
    print(f"Saved {FIG_DIR / 'bonn_trajectory_comparison.png'}")
    print(f"Saved {FIG_DIR / 'trajectory_stability_comparison.png'}")


if __name__ == "__main__":
    main()
