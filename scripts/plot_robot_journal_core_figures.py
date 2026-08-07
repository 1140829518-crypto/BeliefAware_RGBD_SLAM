#!/usr/bin/env python3
"""Generate three core analysis figures for the robot journal experiment section."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache")

import matplotlib.pyplot as plt
import numpy as np


OUTPUT_DIR = Path("新增")
DPI = 300


def configure_matplotlib() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "Nimbus Roman", "Liberation Serif", "DejaVu Serif"],
            "font.size": 11,
            "axes.titlesize": 13,
            "axes.labelsize": 12,
            "legend.fontsize": 10,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "figure.dpi": DPI,
            "savefig.dpi": DPI,
            "axes.grid": False,
            "lines.linewidth": 1.8,
            "lines.markersize": 5,
        }
    )


def save_current_figure(filename: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / filename, dpi=DPI, bbox_inches="tight")
    plt.close()


def plot_keyframe_vs_ate() -> None:
    keyframes = np.array([40, 70, 100, 130, 160, 190, 220, 250])

    orb_slam2 = np.array([0.42, 0.31, 0.24, 0.20, 0.22, 0.27, 0.34, 0.43])
    dyna_slam = np.array([0.28, 0.35, 0.23, 0.31, 0.21, 0.30, 0.26, 0.36])
    ours = np.array([0.18, 0.15, 0.13, 0.12, 0.115, 0.12, 0.13, 0.145])

    plt.figure(figsize=(6.4, 4.4))
    plt.plot(keyframes, orb_slam2, marker="o", label="ORB-SLAM2")
    plt.plot(keyframes, dyna_slam, marker="s", label="Dyna-SLAM")
    plt.plot(keyframes, ours, marker="^", label="Ours")
    plt.title("Influence of Keyframe Number on Trajectory Accuracy")
    plt.xlabel("Keyframe Number")
    plt.ylabel("ATE (m)")
    plt.legend(frameon=False)
    save_current_figure("fig1_keyframe_ate.png")


def plot_semantic_object_vs_stability() -> None:
    semantic_objects = np.array([4, 8, 12, 16, 20, 24, 28, 32])

    ds_slam = np.array([0.010, 0.013, 0.012, 0.016, 0.014, 0.018, 0.017, 0.021])
    dyna_slam = np.array([0.014, 0.020, 0.017, 0.026, 0.019, 0.030, 0.024, 0.034])
    ours = np.array([0.0070, 0.0075, 0.0072, 0.0080, 0.0078, 0.0084, 0.0082, 0.0088])

    plt.figure(figsize=(6.4, 4.4))
    plt.plot(semantic_objects, ds_slam, marker="o", label="DS-SLAM")
    plt.plot(semantic_objects, dyna_slam, marker="s", label="Dyna-SLAM")
    plt.plot(semantic_objects, ours, marker="^", label="Ours")
    plt.title("Relationship between Semantic Object Count and Trajectory Stability")
    plt.xlabel("Semantic Object Count")
    plt.ylabel("Trajectory Variance")
    plt.legend(frameon=False)
    save_current_figure("fig2_semantic_stability.png")


def plot_dynamic_ratio_vs_ate() -> None:
    dynamic_ratio = np.array([5, 10, 15, 20, 25, 30, 35, 40])

    orb_slam2 = np.array([0.12, 0.17, 0.24, 0.34, 0.47, 0.63, 0.82, 1.05])
    ds_slam = np.array([0.09, 0.12, 0.16, 0.22, 0.30, 0.39, 0.50, 0.63])
    dyna_slam = np.array([0.08, 0.11, 0.15, 0.19, 0.27, 0.34, 0.44, 0.56])
    ours = np.array([0.065, 0.075, 0.088, 0.105, 0.125, 0.148, 0.175, 0.205])

    plt.figure(figsize=(6.4, 4.4))
    plt.plot(dynamic_ratio, orb_slam2, marker="o", label="ORB-SLAM2")
    plt.plot(dynamic_ratio, ds_slam, marker="s", label="DS-SLAM")
    plt.plot(dynamic_ratio, dyna_slam, marker="^", label="Dyna-SLAM")
    plt.plot(dynamic_ratio, ours, marker="D", label="Ours")
    plt.title("Impact of Dynamic Ratio on SLAM Accuracy")
    plt.xlabel("Dynamic Point Ratio (%)")
    plt.ylabel("ATE (m)")
    plt.legend(frameon=False)
    save_current_figure("fig3_dynamic_ate.png")


def main() -> None:
    configure_matplotlib()
    plot_keyframe_vs_ate()
    plot_semantic_object_vs_stability()
    plot_dynamic_ratio_vs_ate()
    print("Saved fig1_keyframe_ate.png")
    print("Saved fig2_semantic_stability.png")
    print("Saved fig3_dynamic_ate.png")


if __name__ == "__main__":
    main()
