#!/usr/bin/env python3
"""
Generate publication-style figures from saved ORB-SLAM2 semantic outputs.

Figures:
1) trajectory comparison in top-down view
2) semantic object map top-down scatter
3) dynamic point visualization copy/export
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401


plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.labelsize": 10,
        "axes.titlesize": 10,
        "legend.fontsize": 8,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linewidth": 0.6,
    }
)


def load_tum_trajectory(path: Path) -> Tuple[np.ndarray, np.ndarray]:
    stamps: List[float] = []
    xyz: List[List[float]] = []
    with path.open() as f:
        for line in f:
            if not line.strip() or line.startswith("#"):
                continue
            vals = line.split()
            if len(vals) < 8:
                continue
            stamps.append(float(vals[0]))
            xyz.append([float(vals[1]), float(vals[2]), float(vals[3])])
    return np.asarray(stamps), np.asarray(xyz)


def associate(stamps_a: np.ndarray, stamps_b: np.ndarray, max_diff: float = 0.02) -> List[Tuple[int, int]]:
    matches: List[Tuple[int, int]] = []
    j = 0
    for i, ta in enumerate(stamps_a):
        while j + 1 < len(stamps_b) and abs(stamps_b[j + 1] - ta) < abs(stamps_b[j] - ta):
            j += 1
        if abs(stamps_b[j] - ta) <= max_diff:
            matches.append((i, j))
    return matches


def umeyama_align(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
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
    return (r @ src.T).T + t


def plot_trajectory(est_file: Path, gt_file: Path, out_file: Path) -> None:
    est_stamps, est_xyz = load_tum_trajectory(est_file)
    gt_stamps, gt_xyz = load_tum_trajectory(gt_file)
    matches = associate(est_stamps, gt_stamps, max_diff=0.02)
    if not matches:
        raise RuntimeError("No timestamp matches between estimated and groundtruth trajectories.")
    est_sel = np.asarray([est_xyz[i] for i, _ in matches])
    gt_sel = np.asarray([gt_xyz[j] for _, j in matches])
    est_aligned = umeyama_align(est_sel, gt_sel)

    fig, ax = plt.subplots(figsize=(5.4, 4.4))
    # Use the X-Z plane, which is more readable for TUM walking sequences than X-Y.
    ax.plot(gt_sel[:, 0], gt_sel[:, 2], color="black", linestyle="--", linewidth=1.3, label="Ground truth")
    ax.plot(est_aligned[:, 0], est_aligned[:, 2], color="#d62728", linewidth=1.6, label="Estimated")
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Z [m]")
    ax.set_title("Trajectory comparison (X-Z)")
    ax.legend(frameon=False, loc="best")
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()
    fig.savefig(out_file, bbox_inches="tight")
    plt.close(fig)


def plot_trajectory_3d(est_file: Path, gt_file: Path, out_file: Path) -> None:
    est_stamps, est_xyz = load_tum_trajectory(est_file)
    gt_stamps, gt_xyz = load_tum_trajectory(gt_file)
    matches = associate(est_stamps, gt_stamps, max_diff=0.02)
    if not matches:
        raise RuntimeError("No timestamp matches between estimated and groundtruth trajectories.")
    est_sel = np.asarray([est_xyz[i] for i, _ in matches])
    gt_sel = np.asarray([gt_xyz[j] for _, j in matches])
    est_aligned = umeyama_align(est_sel, gt_sel)

    fig = plt.figure(figsize=(5.8, 4.8))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot(gt_sel[:, 0], gt_sel[:, 1], gt_sel[:, 2], color="black", linestyle="--", linewidth=1.2, label="Ground truth")
    ax.plot(est_aligned[:, 0], est_aligned[:, 1], est_aligned[:, 2], color="#d62728", linewidth=1.5, label="Estimated")
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Y [m]")
    ax.set_zlabel("Z [m]")
    ax.set_title("Trajectory comparison (3D)")
    ax.legend(frameon=False, loc="best")
    ax.view_init(elev=22, azim=-62)
    fig.tight_layout()
    fig.savefig(out_file, bbox_inches="tight")
    plt.close(fig)


def parse_semantic_objects(path: Path):
    class_points: Dict[str, List[Tuple[float, float, float]]] = {}
    with path.open() as f:
        for line in f:
            if not line.strip() or line.startswith("#"):
                continue
            vals = line.split()
            if len(vals) < 12:
                continue
            class_name = vals[2]
            x, y, z = map(float, vals[-3:])
            class_points.setdefault(class_name, []).append((x, y, z))
    return class_points


def plot_semantic_objects(obj_file: Path, out_file: Path) -> None:
    class_points = parse_semantic_objects(obj_file)
    if not class_points:
        raise RuntimeError("No semantic objects found.")

    palette = {
        "static_group": "#2ca02c",
        "low_dynamic_group": "#ff7f0e",
        "person": "#d62728",
        "unknown": "#7f7f7f",
    }

    fig, ax = plt.subplots(figsize=(5.4, 4.4))
    for class_name, pts in sorted(class_points.items()):
        arr = np.asarray(pts)
        color = palette.get(class_name, "#1f77b4")
        ax.scatter(arr[:, 0], arr[:, 2], s=28, c=color, alpha=0.9, edgecolors="white", linewidths=0.4, label=f"{class_name} ({len(arr)})")

    ax.set_xlabel("X [m]")
    ax.set_ylabel("Z [m]")
    ax.set_title("Semantic object map")
    ax.legend(frameon=False, loc="best", markerscale=1.0)
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()
    fig.savefig(out_file, bbox_inches="tight")
    if out_file.suffix.lower() != ".png":
        fig.savefig(out_file.with_suffix(".png"), bbox_inches="tight")
    plt.close(fig)


def export_dynamic_image(src_file: Path, out_file: Path) -> None:
    # Keep it simple: copy the saved dynamic visualization to a paper-friendly filename.
    out_file.write_bytes(src_file.read_bytes())


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate publication-style figures for semantic ORB-SLAM2.")
    parser.add_argument("--results-dir", type=Path, default=Path("TUM_trajectory_results"))
    parser.add_argument("--gt", type=Path, required=True, help="Ground truth trajectory in TUM format.")
    parser.add_argument("--est", type=Path, default=None, help="Estimated trajectory in TUM format.")
    parser.add_argument("--out-dir", type=Path, default=Path("paper_figs"))
    parser.add_argument("--dynamic-image", type=Path, default=None, help="Saved filtered frame image.")
    args = parser.parse_args()

    est_file = args.est or (args.results_dir / "CameraTrajectory.txt")
    obj_file = args.results_dir / "SemanticObjects.txt"
    dyn_file = args.dynamic_image or (args.results_dir / "Frame_YDOF_filtered.png")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    plot_trajectory(est_file, args.gt, args.out_dir / "trajectory_compare.pdf")
    plot_trajectory_3d(est_file, args.gt, args.out_dir / "trajectory_compare_3d.pdf")
    plot_semantic_objects(obj_file, args.out_dir / "semantic_object_map.pdf")
    if dyn_file.exists():
        export_dynamic_image(dyn_file, args.out_dir / "dynamic_points.png")

    print(f"Saved figures to: {args.out_dir}")


if __name__ == "__main__":
    main()
