#!/usr/bin/env python3
"""Redraw Fig. 2 Bonn RGB-D Dynamic Dataset trajectory comparison.

This script only reads existing experiment trajectories and ground-truth files.
It does not modify, rerun, or synthesize any experiment result.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiment_new"
RESULT_DIR = EXP / "results"
RUN_ROOT = RESULT_DIR / "bonn_runs"
MANIFEST = RESULT_DIR / "bonn_selected_sequences.csv"
OUT_DIR = ROOT / "robot_submission_revision" / "figures" / "bonn_trajectory_figure2"

os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "experiment_new" / ".matplotlib_cache"))

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D


SEQUENCE_ORDER = ["walking", "sitting", "crowd"]
SEQUENCE_TITLES = {
    "walking": "(a) walking",
    "sitting": "(b) sitting",
    "crowd": "(c) crowd",
}

METHODS = [
    ("Ground Truth", "ground_truth", "#111111", "-", 2.4),
    ("ORB-SLAM3", "orb_slam3", "#1f77b4", "--", 2.1),
    ("DS-SLAM", "ds_slam", "#2ca02c", "-.", 2.1),
    ("DynaSLAM", "dyna_slam", "#d62728", (0, (1.2, 1.2)), 2.1),
    ("Ours", "ours", "#9467bd", (0, (5.0, 1.4, 1.2, 1.4)), 2.3),
]


def set_style() -> str:
    preferred = ["Times New Roman", "Arial", "Liberation Serif", "DejaVu Serif"]
    available = {f.name for f in plt.matplotlib.font_manager.fontManager.ttflist}
    selected = next((name for name in preferred if name in available), "DejaVu Sans")
    plt.rcParams.update(
        {
            "font.family": selected,
            "font.size": 10.5,
            "axes.titlesize": 11.5,
            "axes.labelsize": 10.5,
            "legend.fontsize": 9.5,
            "xtick.labelsize": 9.5,
            "ytick.labelsize": 9.5,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": "#d9d9d9",
            "grid.alpha": 1.0,
            "grid.linewidth": 0.55,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    return selected


def read_manifest(path: Path) -> Dict[str, Path]:
    if not path.exists():
        raise FileNotFoundError(f"Missing Bonn sequence manifest: {path}")
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return {row["Dataset"]: Path(row["Path"]) for row in rows}


def load_tum(path: Path) -> Tuple[np.ndarray, np.ndarray]:
    stamps: List[float] = []
    xyz: List[List[float]] = []
    if not path.exists():
        return np.empty((0,)), np.empty((0, 3))
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
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
    pairs: List[Tuple[int, int]] = []
    j = 0
    for i, ta in enumerate(a):
        while j + 1 < len(b) and abs(b[j + 1] - ta) < abs(b[j] - ta):
            j += 1
        if abs(b[j] - ta) <= max_diff:
            pairs.append((i, j))
    return pairs


def align_umeyama(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    if len(src) < 3 or len(dst) < 3:
        return src
    mu_src = src.mean(axis=0)
    mu_dst = dst.mean(axis=0)
    src_centered = src - mu_src
    dst_centered = dst - mu_dst
    cov = src_centered.T @ dst_centered / len(src)
    u, _, vt = np.linalg.svd(cov)
    r = vt.T @ u.T
    if np.linalg.det(r) < 0:
        vt[-1, :] *= -1
        r = vt.T @ u.T
    t = mu_dst - r @ mu_src
    return (r @ src.T).T + t


def aligned_to_gt(est_path: Path, gt_path: Path) -> np.ndarray:
    est_t, est_xyz = load_tum(est_path)
    gt_t, gt_xyz = load_tum(gt_path)
    pairs = associate(est_t, gt_t)
    if not pairs:
        return np.empty((0, 3))
    est_sel = np.asarray([est_xyz[i] for i, _ in pairs])
    gt_sel = np.asarray([gt_xyz[j] for _, j in pairs])
    return align_umeyama(est_sel, gt_sel)


def axis_limits(curves: Iterable[np.ndarray]) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    pts = [curve[:, [0, 2]] for curve in curves if len(curve)]
    if not pts:
        return (-1.0, 1.0), (-1.0, 1.0)
    all_pts = np.vstack(pts)
    x_min, z_min = np.min(all_pts, axis=0)
    x_max, z_max = np.max(all_pts, axis=0)
    x_pad = max((x_max - x_min) * 0.08, 0.05)
    z_pad = max((z_max - z_min) * 0.08, 0.05)
    return (x_min - x_pad, x_max + x_pad), (z_min - z_pad, z_max + z_pad)


def main() -> None:
    font = set_style()
    sequence_paths = read_manifest(MANIFEST)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 3, figsize=(14.2, 3.7), constrained_layout=False)
    audit_lines = [
        "# Figure 2 Bonn Trajectory Revision Audit",
        "",
        f"- Source manifest: `{MANIFEST}`",
        f"- Run root: `{RUN_ROOT}`",
        f"- Output directory: `{OUT_DIR}`",
        f"- Font used: `{font}`",
        "- Experiment data modified: No",
        "- Experiment rerun: No",
        "- Layout: three horizontal subplots for walking, sitting, and crowd.",
        "- Line width: all trajectories are plotted with linewidth >= 2.0.",
        "",
        "## Caption",
        "",
        "中文：图2 Bonn RGB-D Dynamic Dataset不同方法轨迹估计结果",
        "",
        "English: Fig.2 Trajectory comparison on the Bonn RGB-D Dynamic Dataset",
        "",
        "## Data Sources",
        "",
    ]

    for ax, dataset in zip(axes, SEQUENCE_ORDER):
        seq_dir = sequence_paths.get(dataset)
        if seq_dir is None:
            raise KeyError(f"Dataset `{dataset}` not found in {MANIFEST}")
        gt_path = seq_dir / "groundtruth.txt"
        _, gt_xyz = load_tum(gt_path)
        curves = [gt_xyz]
        audit_lines.append(f"### {dataset}")
        audit_lines.append(f"- Ground Truth: `{gt_path}` ({len(gt_xyz)} poses)")

        if len(gt_xyz):
            label, _, color, linestyle, linewidth = METHODS[0]
            ax.plot(gt_xyz[:, 0], gt_xyz[:, 2], color=color, linestyle=linestyle, linewidth=linewidth, label=label)

        for label, slug, color, linestyle, linewidth in METHODS[1:]:
            est_path = RUN_ROOT / dataset / slug / "CameraTrajectory.txt"
            est_xyz = aligned_to_gt(est_path, gt_path)
            curves.append(est_xyz)
            audit_lines.append(f"- {label}: `{est_path}` ({len(est_xyz)} associated poses)")
            if len(est_xyz):
                ax.plot(est_xyz[:, 0], est_xyz[:, 2], color=color, linestyle=linestyle, linewidth=linewidth, label=label)

        xlim, zlim = axis_limits(curves)
        ax.set_xlim(*xlim)
        ax.set_ylim(*zlim)
        ax.set_aspect("auto")
        ax.set_box_aspect(0.72)
        ax.set_title(SEQUENCE_TITLES[dataset], fontweight="bold", pad=6)
        ax.set_xlabel("X (m)")
        ax.set_ylabel("Z (m)")
        ax.tick_params(direction="out", length=3.2, width=0.8)

    handles = [
        Line2D([0], [0], color=color, linestyle=linestyle, linewidth=linewidth)
        for label, _, color, linestyle, linewidth in METHODS
    ]
    labels = [label for label, *_ in METHODS]
    fig.legend(
        handles,
        labels,
        loc="upper center",
        ncol=5,
        frameon=False,
        bbox_to_anchor=(0.5, 1.035),
        columnspacing=1.4,
        handlelength=2.8,
        handletextpad=0.55,
    )
    fig.subplots_adjust(left=0.055, right=0.995, bottom=0.18, top=0.80, wspace=0.28)

    for suffix, kwargs in [
        ("pdf", {}),
        ("svg", {}),
        ("eps", {}),
        ("png", {"dpi": 600}),
    ]:
        fig.savefig(OUT_DIR / f"figure2_bonn_trajectory_comparison.{suffix}", bbox_inches="tight", **kwargs)
    plt.close(fig)

    (OUT_DIR / "figure2_revision_notes.md").write_text("\n".join(audit_lines) + "\n", encoding="utf-8")

    print(f"Output directory: {OUT_DIR}")
    print(f"PDF: {OUT_DIR / 'figure2_bonn_trajectory_comparison.pdf'}")
    print(f"SVG: {OUT_DIR / 'figure2_bonn_trajectory_comparison.svg'}")
    print(f"EPS: {OUT_DIR / 'figure2_bonn_trajectory_comparison.eps'}")
    print(f"PNG: {OUT_DIR / 'figure2_bonn_trajectory_comparison.png'}")
    print(f"Audit: {OUT_DIR / 'figure2_revision_notes.md'}")


if __name__ == "__main__":
    main()
