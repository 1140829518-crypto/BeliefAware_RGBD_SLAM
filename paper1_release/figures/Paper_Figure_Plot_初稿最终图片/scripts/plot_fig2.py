#!/usr/bin/env python3
"""Fig2 Bonn trajectory comparison."""

from __future__ import annotations

import argparse

import numpy as np

from plot_style import DATA_ROOT, FONT_NAME, apply_style, add_panel_label, load_tum_trajectory, save_figure
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


SEQUENCES = [("walking", "(a) walking"), ("sitting", "(b) sitting"), ("crowd", "(c) crowd")]
METHODS = [
    ("ORB-SLAM3", "orbslam3.txt", "red", "--", 1.8, 2),
    ("DS-SLAM", "dsslam.txt", "blue", "-.", 1.8, 2),
    ("DynaSLAM", "dynaslam.txt", "green", ":", 1.8, 2),
    ("Ours", "ours.txt", "orange", "-", 2.0, 5),
]
GT_STYLE = ("Ground Truth", "black", "-", 2.5)


def associate(a: np.ndarray, b: np.ndarray, max_diff: float = 0.04) -> list[tuple[int, int]]:
    if len(a) == 0 or len(b) == 0:
        return []
    pairs: list[tuple[int, int]] = []
    j = 0
    for i, ta in enumerate(a[:, 0]):
        while j + 1 < len(b) and abs(b[j + 1, 0] - ta) < abs(b[j, 0] - ta):
            j += 1
        if abs(b[j, 0] - ta) <= max_diff:
            pairs.append((i, j))
    return pairs


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


def aligned_to_gt(est: np.ndarray, gt: np.ndarray) -> np.ndarray:
    pairs = associate(est, gt)
    if not pairs:
        return np.empty((0, 4))
    est_xyz = np.asarray([est[i, 1:4] for i, _ in pairs])
    gt_xyz = np.asarray([gt[j, 1:4] for _, j in pairs])
    aligned = align_umeyama(est_xyz, gt_xyz)
    stamps = np.asarray([gt[j, 0] for _, j in pairs])[:, None]
    return np.hstack([stamps, aligned])


def limits(curves: list[np.ndarray]) -> tuple[tuple[float, float], tuple[float, float]]:
    pts = [c[:, [1, 3]] for c in curves if len(c)]
    if not pts:
        return (-1, 1), (-1, 1)
    all_pts = np.vstack(pts)
    lo = all_pts.min(axis=0)
    hi = all_pts.max(axis=0)
    pad = np.maximum((hi - lo) * 0.08, 0.05)
    return (lo[0] - pad[0], hi[0] + pad[0]), (lo[1] - pad[1], hi[1] + pad[1])


def groundtruth_path(seq_dir):
    return seq_dir / "gt.txt"


def range_text(traj: np.ndarray, col: int) -> str:
    if len(traj) == 0:
        return "NA"
    return f"{float(np.min(traj[:, col])):.6f} to {float(np.max(traj[:, col])):.6f}"


def load_sequence_debug(seq: str) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    base = DATA_ROOT / "Fig2_Trajectory"
    seq_dir = base / seq
    gt_path = groundtruth_path(seq_dir)
    gt_traj = load_tum_trajectory(gt_path) if gt_path.exists() else np.empty((0, 4))
    if len(gt_traj) == 0:
        raise RuntimeError(f"{seq}: GT trajectory is empty or missing: {gt_path}")
    method_trajs: dict[str, np.ndarray] = {}
    print(f"{seq}:")
    print(f"  GT file path: {gt_path}")
    print(f"  GT trajectory points: {len(gt_traj)}")
    print(f"  GT X range: {range_text(gt_traj, 1)}")
    print(f"  GT Z range: {range_text(gt_traj, 3)}")
    print("  Drawing alignment: Umeyama SE(3) alignment to GT before plotting")
    for method, file_name, *_ in METHODS:
        est_path = seq_dir / file_name
        est_traj = load_tum_trajectory(est_path) if est_path.exists() else np.empty((0, 4))
        if len(est_traj) == 0:
            raise RuntimeError(f"{seq}: {method} trajectory is empty or missing: {est_path}")
        matches = len(associate(est_traj, gt_traj))
        method_trajs[method] = est_traj
        print(f"  {method} points: {len(est_traj)}")
        print(f"    file path: {est_path}")
        print(f"    aligned before plotting: True")
        print(f"    matched pairs: {matches}")
    return gt_traj, method_trajs


def debug_sequences() -> None:
    for seq, _ in SEQUENCES:
        load_sequence_debug(seq)


def main(debug: bool = False) -> None:
    if debug:
        debug_sequences()
        return
    apply_style()
    plt.rcParams.update(
        {
            "font.family": FONT_NAME,
            "axes.labelsize": 10.5,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
        }
    )
    base = DATA_ROOT / "Fig2_Trajectory"
    sequence_data = {seq: load_sequence_debug(seq) for seq, _ in SEQUENCES}
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.65))
    for ax, (seq, label) in zip(axes, SEQUENCES):
        ax.grid(False)
        seq_dir = base / seq
        curves: list[np.ndarray] = []
        gt_traj, method_trajs = sequence_data[seq]
        for method, file_name, color, linestyle, linewidth, zorder in METHODS:
            traj = method_trajs[method]
            traj = aligned_to_gt(traj, gt_traj)
            curves.append(traj)
            if len(traj):
                ax.plot(traj[:, 1], traj[:, 3], color=color, linestyle=linestyle, linewidth=linewidth, label=method, zorder=zorder)
        gt_label, gt_color, gt_linestyle, gt_linewidth = GT_STYLE
        curves.append(gt_traj)
        ax.plot(
            gt_traj[:, 1],
            gt_traj[:, 3],
            color=gt_color,
            linestyle=gt_linestyle,
            linewidth=gt_linewidth,
            label=gt_label,
            zorder=10,
            solid_capstyle="round",
        )
        xlim, zlim = limits(curves)
        ax.set_xlim(*xlim)
        ax.set_ylim(*zlim)
        ax.set_title(label, fontsize=10, fontweight="bold", pad=4)
        ax.set_xlabel("X (m)")
        ax.set_ylabel("Z (m)")
        ax.xaxis.label.set_size(10.5)
        ax.yaxis.label.set_size(10.5)
        ax.tick_params(axis="both", labelsize=9)
    gt_label, gt_color, gt_linestyle, gt_linewidth = GT_STYLE
    handles = [Line2D([0], [0], color=gt_color, linestyle=gt_linestyle, linewidth=gt_linewidth)]
    handles += [Line2D([0], [0], color=c, linestyle=ls, linewidth=lw) for _, _, c, ls, lw, _ in METHODS]
    labels = [gt_label] + [m for m, *_ in METHODS]
    fig.legend(
        handles,
        labels,
        ncol=5,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.015),
        frameon=False,
        handlelength=1.8,
        columnspacing=0.6,
        handletextpad=0.45,
        borderaxespad=0.15,
        fontsize=9,
    )
    fig.subplots_adjust(left=0.075, right=0.99, bottom=0.18, top=0.80, wspace=0.35)
    save_figure(fig, "Fig2")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot or debug Fig2 Bonn trajectory comparison.")
    parser.add_argument("--debug", action="store_true", help="Print GT path/range and alignment checks without drawing.")
    args = parser.parse_args()
    main(debug=args.debug)
