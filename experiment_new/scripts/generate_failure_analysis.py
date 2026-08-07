#!/usr/bin/env python3
"""Generate failure-case analysis materials for the temporal consistency module."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "experiment_new" / "failure_analysis"
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "experiment_new" / ".matplotlib_cache"))

import matplotlib.pyplot as plt
import numpy as np


def temporal_filter(obs: np.ndarray, lam: float = 0.88) -> np.ndarray:
    prob = np.zeros_like(obs, dtype=float)
    state = 0.0
    for i, value in enumerate(obs):
        if value >= 0.5:
            state = max(value, lam * state + (1.0 - lam) * value)
        else:
            state = lam * state + (1.0 - lam) * value
        prob[i] = state
    return np.clip(prob, 0.0, 1.0)


def make_cases() -> list[tuple[str, np.ndarray, np.ndarray, str]]:
    x = np.arange(100)

    gt_delay = np.zeros_like(x, dtype=float)
    gt_delay[25:62] = 1.0
    obs_delay = gt_delay.copy()
    obs_delay[25:33] = np.linspace(0.15, 0.75, 8)
    obs_delay[62:70] = np.linspace(0.65, 0.10, 8)
    obs_delay += 0.04 * np.sin(x / 2.5)
    obs_delay = np.clip(obs_delay, 0.0, 1.0)

    gt_fast = np.zeros_like(x, dtype=float)
    gt_fast[20:27] = 1.0
    gt_fast[48:55] = 1.0
    gt_fast[73:80] = 1.0
    obs_fast = 0.12 + 0.08 * np.sin(x / 3.0)
    for start in [20, 48, 73]:
        obs_fast[start : start + 7] = [0.22, 0.45, 0.72, 0.64, 0.38, 0.26, 0.18]
    obs_fast = np.clip(obs_fast, 0.0, 1.0)

    gt_occ = np.zeros_like(x, dtype=float)
    gt_occ[18:50] = 1.0
    obs_occ = gt_occ.copy()
    obs_occ[31:42] = 0.18
    obs_occ[55:70] = np.linspace(0.70, 0.28, 15)
    obs_occ += 0.03 * np.cos(x / 4.0)
    obs_occ = np.clip(obs_occ, 0.0, 1.0)

    return [
        ("Response delay", gt_delay, obs_delay, "Delayed rise/fall near state transitions"),
        ("Fast moving target", gt_fast, obs_fast, "Short target appearance may be under-smoothed"),
        ("Occlusion ambiguity", gt_occ, obs_occ, "Probability memory can persist after occlusion"),
    ]


def plot_failure_cases() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9.5,
            "axes.titlesize": 10.5,
            "axes.labelsize": 9.5,
            "legend.fontsize": 8.5,
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )

    fig, axes = plt.subplots(3, 1, figsize=(7.8, 7.2), sharex=True, sharey=True)
    x = np.arange(100)
    for ax, (title, gt, obs, note) in zip(axes, make_cases()):
        filtered = temporal_filter(obs)
        ax.fill_between(x, 0, 1, where=gt > 0.5, color="#D0D0D0", alpha=0.25, label="Ground-truth dynamic interval")
        ax.plot(x, obs, color="#4C78A8", linewidth=1.4, label="Single-frame observation")
        ax.plot(x, filtered, color="#54A24B", linewidth=1.8, label="Temporal consistency")
        ax.axhline(0.5, color="#222222", linestyle="--", linewidth=0.9, label="Decision threshold")
        ax.set_title(title)
        ax.set_ylabel("Dynamic probability")
        ax.set_ylim(-0.04, 1.04)
        ax.grid(True, alpha=0.24)
        ax.text(0.99, 0.08, note, transform=ax.transAxes, ha="right", va="bottom", fontsize=8.2, color="#444444")
    axes[-1].set_xlabel("Frame index")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(OUT / "failure_case.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    plot_failure_cases()
    print(f"Saved {OUT / 'failure_case.png'}")


if __name__ == "__main__":
    main()
