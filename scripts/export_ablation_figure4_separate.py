#!/usr/bin/env python3
"""Generate separate Figure 4 ablation panels for Word insertion."""

from __future__ import annotations

import importlib.util
from pathlib import Path


COMPOSITE_SCRIPT = Path(__file__).with_name("export_ablation_figure4_composite.py")


def load_composite_module():
    spec = importlib.util.spec_from_file_location("figure4_composite", COMPOSITE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {COMPOSITE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    m = load_composite_module()
    m.OUT_DIR = Path("paper_ready_outputs_v13")
    m.FIG_DIR = m.OUT_DIR / "figures"
    m.TABLE_DIR = m.OUT_DIR / "tables"
    m.FIG_DIR.mkdir(parents=True, exist_ok=True)
    m.TABLE_DIR.mkdir(parents=True, exist_ok=True)

    summary = m.read_summary()
    save_figure4a(m, summary)
    save_figure4b(m, summary)
    save_figure4c(m, summary)
    print(f"Wrote separate Figure 4 panels to {m.OUT_DIR}")


def save_figure4a(m, summary) -> None:
    fig, axes = m.plt.subplots(1, 4, figsize=(13.6, 3.1), constrained_layout=True)
    rows = []
    for ax, (short_name, sequence, gt_path, scene_type) in zip(axes, m.SEQUENCES):
        for label, method_key, color, marker, linestyle in m.METHODS:
            run_dir = m.Path(summary[(sequence, method_key)]["run_dir"])
            est, gt, _ = m.aligned_to_gt(run_dir / "CameraTrajectory.txt", gt_path)
            xs, ys = m.prefix_ate_curve(est, gt)
            if len(xs) == 0:
                continue
            ax.plot(xs, ys, color=color, linestyle=linestyle, marker=marker, markersize=3.3, linewidth=1.1, label=label)
            for distance, ate in zip(xs, ys):
                rows.append({"sequence": sequence, "method": label, "distance_m": f"{distance:.9f}", "prefix_ate_rmse_m": f"{ate:.9f}"})
        ax.set_title(f"{short_name} ({scene_type})", fontweight="bold")
        ax.set_xlabel("距离 (m)")
        ax.set_ylabel("ATE RMSE (m)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 1.15), ncol=4, frameon=True)
    fig.savefig(m.FIG_DIR / "figure4a_ate_rmse_ablation_separate.png", bbox_inches="tight")
    fig.savefig(m.FIG_DIR / "figure4a_ate_rmse_ablation_separate.pdf", bbox_inches="tight")
    m.plt.close(fig)
    m.write_dict_csv(m.TABLE_DIR / "figure4a_ate_rmse_ablation_separate.csv", rows)


def save_figure4b(m, summary) -> None:
    fig, axes = m.plt.subplots(1, 5, figsize=(13.8, 3.2), gridspec_kw={"width_ratios": [1, 1, 1, 1, 0.9]}, constrained_layout=True)
    for ax, (short_name, sequence, gt_path, _) in zip(axes[:4], m.SEQUENCES):
        _, gt_xyz = m.read_tum_xyz(gt_path)
        ax.plot(gt_xyz[:, 0], gt_xyz[:, 2], color="#2ca02c", linestyle="-.", linewidth=1.0, label="Ground Truth")
        for label, method_key, color, _, linestyle in m.METHODS:
            run_dir = m.Path(summary[(sequence, method_key)]["run_dir"])
            est, _, _ = m.aligned_to_gt(run_dir / "CameraTrajectory.txt", gt_path)
            if len(est) == 0:
                continue
            ax.plot(est[:, 0], est[:, 2], color=color, linestyle=linestyle, linewidth=1.0, label=label)
        ax.set_title(short_name, fontweight="bold")
        ax.set_xlabel("x (m)")
        ax.set_ylabel("z (m)")
        ax.set_aspect("equal", adjustable="box")

    axes[4].axis("off")
    handles, labels = axes[0].get_legend_handles_labels()
    axes[4].legend(handles, labels, loc="center left", frameon=True)
    fig.savefig(m.FIG_DIR / "figure4b_trajectory_ablation_separate.png", bbox_inches="tight")
    fig.savefig(m.FIG_DIR / "figure4b_trajectory_ablation_separate.pdf", bbox_inches="tight")
    m.plt.close(fig)


def save_figure4c(m, summary) -> None:
    stability = m.collect_stability(summary)
    metric_specs = [
        ("smoothness", "Smoothness (越小越好)", "Smoothness", "{:.4f}"),
        ("variance", "Variance (越小越好)", "Variance", "{:.5f}"),
        ("failure_rate", "Failure Rate (越小越好)", "Failure Rate (%)", "{:.2f}%"),
    ]
    fig, axes = m.plt.subplots(1, 3, figsize=(11.2, 3.6), constrained_layout=True)
    colors = [item[2] for item in m.METHODS]
    method_labels = [item[0] for item in m.METHODS]

    for ax, (metric_key, title, ylabel, value_fmt) in zip(axes, metric_specs):
        values = [stability[label][metric_key] for label in method_labels]
        plot_values = [100.0 * value if metric_key == "failure_rate" else value for value in values]
        ax.bar(range(len(plot_values)), plot_values, color=colors, alpha=0.78, width=0.62)
        ax.set_title(title, fontweight="bold")
        ax.set_ylabel(ylabel)
        ax.set_xticks(range(len(plot_values)))
        ax.set_xticklabels(m.BAR_LABELS, rotation=22, ha="right")
        for i, value in enumerate(plot_values):
            ax.text(i, value + max(plot_values) * 0.025, value_fmt.format(value), ha="center", va="bottom", fontsize=8)

    fig.savefig(m.FIG_DIR / "figure4c_stability_ablation_separate.png", bbox_inches="tight")
    fig.savefig(m.FIG_DIR / "figure4c_stability_ablation_separate.pdf", bbox_inches="tight")
    m.plt.close(fig)


if __name__ == "__main__":
    main()
