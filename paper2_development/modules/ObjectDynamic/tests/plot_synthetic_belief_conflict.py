#!/usr/bin/env python3
"""Plot values emitted by the C++ production-path synthetic experiment."""

import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def plot_comparison(output, sequences, column, ylabel, filename):
    fig, axis = plt.subplots(figsize=(7.2, 4.2))
    for label, rows, style in sequences:
        axis.plot([int(row["step"]) for row in rows],
                  [float(row[column]) for row in rows], label=label,
                  linewidth=1.8, linestyle=style)
    axis.set_xlabel("Observation step")
    axis.set_ylabel(ylabel)
    axis.grid(alpha=0.25)
    axis.legend()
    fig.tight_layout()
    fig.savefig(output / filename, dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    figures = args.output / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    abc = []
    for mode, style in (("off", "--"), ("on", "-")):
        for label, filename in (
                ("Stable Static", "A_stable_static.csv"),
                ("Stable Dynamic", "B_stable_dynamic.csv"),
                ("Alternating Conflict", "C_alternating_conflict.csv")):
            abc.append((f"{label} ({mode.upper()})",
                        load(args.output / mode / filename), style))
    for column, ylabel, filename in (
        ("after_observation_p", "Dynamic probability p", "abc_probability.png"),
        ("after_observation_u", "Uncertainty u", "abc_uncertainty.png"),
        ("conflict", "Diagnostic conflict", "abc_conflict.png"),
        ("reliability", "Reliability r", "abc_reliability.png")):
        plot_comparison(figures, abc, column, ylabel, filename)

    de = []
    for mode, style in (("off", "--"), ("on", "-")):
        for label, filename in (
                ("Static-Dynamic-Static", "D_static_dynamic_static.csv"),
                ("Dynamic-Static-Dynamic", "E_dynamic_static_dynamic.csv")):
            de.append((f"{label} ({mode.upper()})",
                       load(args.output / mode / filename), style))
    fig, axes = plt.subplots(2, 1, figsize=(8.0, 6.5), sharex=True)
    for label, rows, style in de:
        steps = [int(row["step"]) for row in rows]
        axes[0].plot(steps, [float(row["after_observation_p"]) for row in rows],
                     label=label, linewidth=1.8, linestyle=style)
        axes[1].plot(steps, [float(row["after_observation_u"]) for row in rows],
                     label=label, linewidth=1.8, linestyle=style)
    axes[0].axhline(0.5, color="black", linestyle="--", linewidth=0.8)
    axes[0].axhline(0.8, color="black", linestyle=":", linewidth=0.8)
    axes[0].set_ylabel("p")
    axes[1].set_ylabel("u")
    axes[1].set_xlabel("Observation step")
    for axis in axes:
        axis.grid(alpha=0.25)
        axis.legend()
    fig.tight_layout()
    fig.savefig(figures / "de_transition_curves.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
