#!/usr/bin/env python3
"""Evaluate TUM-format trajectories and generate trajectory/error plots."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial.transform import Rotation


def load_tum(path: Path) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    stamps: List[float] = []
    xyz: List[List[float]] = []
    quat: List[List[float]] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            vals = line.split()
            if len(vals) < 8:
                continue
            stamps.append(float(vals[0]))
            xyz.append([float(vals[1]), float(vals[2]), float(vals[3])])
            quat.append([float(vals[4]), float(vals[5]), float(vals[6]), float(vals[7])])
    return np.asarray(stamps), np.asarray(xyz), np.asarray(quat)


def associate(stamps_a: np.ndarray, stamps_b: np.ndarray, max_diff: float) -> List[Tuple[int, int]]:
    matches: List[Tuple[int, int]] = []
    j = 0
    for i, ta in enumerate(stamps_a):
        while j + 1 < len(stamps_b) and abs(stamps_b[j + 1] - ta) < abs(stamps_b[j] - ta):
            j += 1
        if abs(stamps_b[j] - ta) <= max_diff:
            matches.append((i, j))
    return matches


def align_se3(src: np.ndarray, dst: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    mu_src = src.mean(axis=0)
    mu_dst = dst.mean(axis=0)
    src_c = src - mu_src
    dst_c = dst - mu_dst
    cov = src_c.T @ dst_c / src.shape[0]
    u, _, vt = np.linalg.svd(cov)
    r = vt.T @ u.T
    if np.linalg.det(r) < 0:
        vt[-1, :] *= -1
        r = vt.T @ u.T
    t = mu_dst - r @ mu_src
    return r, t


def make_poses(xyz: np.ndarray, quat: np.ndarray) -> np.ndarray:
    poses = np.tile(np.eye(4), (len(xyz), 1, 1))
    poses[:, :3, :3] = Rotation.from_quat(quat).as_matrix()
    poses[:, :3, 3] = xyz
    return poses


def summarize(values: np.ndarray) -> Dict[str, float]:
    return {
        "rmse": float(np.sqrt(np.mean(values**2))),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "std": float(np.std(values)),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
    }


def save_metrics(path: Path, metrics: Dict[str, object]) -> None:
    path.write_text(json.dumps(metrics, indent=2) + "\n")
    txt = path.with_suffix(".txt")
    lines = [
        f"matches: {metrics['matches']}",
        f"ATE RMSE [m]: {metrics['ate']['rmse']:.6f}",
        f"ATE mean [m]: {metrics['ate']['mean']:.6f}",
        f"ATE median [m]: {metrics['ate']['median']:.6f}",
        f"RPE trans RMSE [m]: {metrics['rpe_trans']['rmse']:.6f}",
        f"RPE trans mean [m]: {metrics['rpe_trans']['mean']:.6f}",
        f"RPE rot RMSE [deg]: {metrics['rpe_rot_deg']['rmse']:.6f}",
        f"RPE rot mean [deg]: {metrics['rpe_rot_deg']['mean']:.6f}",
    ]
    txt.write_text("\n".join(lines) + "\n")


def save_trajectory_plot(gt: np.ndarray, est_aligned: np.ndarray, out_base: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(6.2, 4.8))
    ax.plot(gt[:, 0], gt[:, 2], "k--", linewidth=1.4, label="Ground truth")
    ax.plot(est_aligned[:, 0], est_aligned[:, 2], color="#d62728", linewidth=1.5, label="DS-SLAM")
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Z [m]")
    ax.set_title(title)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out_base.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(out_base.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def save_error_plot(times: np.ndarray, ate: np.ndarray, rpe_t: np.ndarray, rpe_r_deg: np.ndarray, out_base: Path) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(7.0, 7.2), sharex=False)
    t0 = times[0]
    axes[0].plot(times - t0, ate, color="#1f77b4", linewidth=1.2)
    axes[0].set_ylabel("ATE [m]")
    axes[0].grid(True, alpha=0.25)
    axes[1].plot(times[1:] - t0, rpe_t, color="#2ca02c", linewidth=1.2)
    axes[1].set_ylabel("RPE trans [m]")
    axes[1].grid(True, alpha=0.25)
    axes[2].plot(times[1:] - t0, rpe_r_deg, color="#d62728", linewidth=1.2)
    axes[2].set_ylabel("RPE rot [deg]")
    axes[2].set_xlabel("Time [s]")
    axes[2].grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_base.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(out_base.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate TUM trajectories with ATE and frame-to-frame RPE.")
    parser.add_argument("--gt", type=Path, required=True)
    parser.add_argument("--est", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--max-diff", type=float, default=0.02)
    parser.add_argument("--title", default="Trajectory comparison")
    args = parser.parse_args()

    gt_stamps, gt_xyz, gt_quat = load_tum(args.gt)
    est_stamps, est_xyz, est_quat = load_tum(args.est)
    matches = associate(est_stamps, gt_stamps, args.max_diff)
    if len(matches) < 2:
        raise RuntimeError(f"Need at least 2 timestamp matches, got {len(matches)}.")

    est_idx = np.asarray([i for i, _ in matches])
    gt_idx = np.asarray([j for _, j in matches])
    times = est_stamps[est_idx]
    est_sel = est_xyz[est_idx]
    gt_sel = gt_xyz[gt_idx]

    r_align, t_align = align_se3(est_sel, gt_sel)
    est_aligned = (r_align @ est_sel.T).T + t_align
    ate_errors = np.linalg.norm(est_aligned - gt_sel, axis=1)

    est_poses = make_poses(est_sel, est_quat[est_idx])
    gt_poses = make_poses(gt_sel, gt_quat[gt_idx])
    rpe_t: List[float] = []
    rpe_r_deg: List[float] = []
    for i in range(len(matches) - 1):
        gt_rel = np.linalg.inv(gt_poses[i]) @ gt_poses[i + 1]
        est_rel = np.linalg.inv(est_poses[i]) @ est_poses[i + 1]
        err = np.linalg.inv(gt_rel) @ est_rel
        rpe_t.append(float(np.linalg.norm(err[:3, 3])))
        rpe_r_deg.append(float(np.degrees(Rotation.from_matrix(err[:3, :3]).magnitude())))
    rpe_t_arr = np.asarray(rpe_t)
    rpe_r_arr = np.asarray(rpe_r_deg)

    metrics: Dict[str, object] = {
        "gt": str(args.gt),
        "est": str(args.est),
        "matches": int(len(matches)),
        "max_timestamp_diff": args.max_diff,
        "ate": summarize(ate_errors),
        "rpe_trans": summarize(rpe_t_arr),
        "rpe_rot_deg": summarize(rpe_r_arr),
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    save_metrics(args.out_dir / "metrics.json", metrics)
    save_trajectory_plot(gt_sel, est_aligned, args.out_dir / "trajectory_compare", args.title)
    save_error_plot(times, ate_errors, rpe_t_arr, rpe_r_arr, args.out_dir / "ate_rpe_errors")

    print((args.out_dir / "metrics.txt").read_text(), end="")
    print(f"Saved plots to: {args.out_dir}")


if __name__ == "__main__":
    main()
