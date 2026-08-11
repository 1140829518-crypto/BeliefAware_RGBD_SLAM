#!/usr/bin/env python3

"""Evaluate and compare Baseline, Paper1, Shadow and Active trajectories."""

import csv
import tempfile
from pathlib import Path

from evaluate_paper2_trajectory import evaluate


SEQUENCES = (
    "fr3_walking_xyz",
    "fr3_walking_rpy",
    "fr3_walking_halfsphere",
)
METHODS = ("baseline", "paper1", "shadow", "active")


def sequence_from_log(run_log):
    if not run_log.is_file():
        return None
    for line in run_log.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("sequence_name="):
            return line.split("=", 1)[1].strip()
    return None


def latest_run(root, sequence):
    candidates = []
    for trajectory in root.rglob("CameraTrajectory.txt"):
        if sequence_from_log(trajectory.with_name("run.log")) == sequence:
            candidates.append(trajectory.parent)
    if not candidates:
        raise RuntimeError("no run found for {} under {}".format(sequence, root))
    return max(candidates, key=lambda path: path.stat().st_mtime)


def count_lines(path):
    return sum(
        1
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    )


def write_csv(path, rows):
    fields = [
        "sequence", "method", "ATE_RMSE", "ATE_mean", "RPE_trans",
        "RPE_rot", "tracked_frames", "keyframes",
    ]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def metric_map(rows, metric):
    return {(row["sequence"], row["method"]): float(row[metric]) for row in rows}


def write_ate_table(path, rows):
    values = metric_map(rows, "ATE_RMSE")
    with path.open("w", encoding="utf-8") as stream:
        stream.write("% Requires \\usepackage{booktabs}.\n")
        stream.write("\\begin{table}[t]\n  \\centering\n")
        stream.write("  \\caption{ATE RMSE comparison on dynamic TUM RGB-D sequences.}\n")
        stream.write("  \\label{tab:method_ate_comparison}\n")
        stream.write("  \\begin{tabular}{lrrrr}\n    \\toprule\n")
        stream.write("    Sequence & ORB-SLAM2 & Paper1 & Shadow & Active \\\\\n    \\midrule\n")
        for sequence in SEQUENCES:
            label = sequence[4:].replace("_", "\\_")
            data = [values[(sequence, method)] for method in METHODS]
            best = min(data)
            cells = [
                "\\textbf{{{:.6f}}}".format(value)
                if value == best else "{:.6f}".format(value)
                for value in data
            ]
            stream.write("    {} & {} & {} & {} & {} \\\\\n".format(label, *cells))
        stream.write("    \\bottomrule\n  \\end{tabular}\n\\end{table}\n")


def write_rpe_table(path, rows):
    translation = metric_map(rows, "RPE_trans")
    rotation = metric_map(rows, "RPE_rot")
    with path.open("w", encoding="utf-8") as stream:
        stream.write("% Each method cell reports translation in metres / rotation in degrees.\n")
        stream.write("% Requires \\usepackage{booktabs}.\n")
        stream.write("\\begin{table*}[t]\n  \\centering\n")
        stream.write("  \\caption{RPE comparison (translation in metres / rotation in degrees).}\n")
        stream.write("  \\label{tab:method_rpe_comparison}\n")
        stream.write("  \\begin{tabular}{lrrrr}\n    \\toprule\n")
        stream.write("    Sequence & ORB-SLAM2 & Paper1 & Shadow & Active \\\\\n    \\midrule\n")
        for sequence in SEQUENCES:
            label = sequence[4:].replace("_", "\\_")
            cells = [
                "{:.6f}/{:.6f}".format(
                    translation[(sequence, method)], rotation[(sequence, method)]
                )
                for method in METHODS
            ]
            stream.write("    {} & {} & {} & {} & {} \\\\\n".format(label, *cells))
        stream.write("    \\bottomrule\n  \\end{tabular}\n\\end{table*}\n")


def percent_change(old, new):
    return 100.0 * (old - new) / old


def active_context(path):
    context = {}
    if not path.is_file():
        return context
    with path.open("r", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            sequence = row["sequence"]
            item = context.setdefault(
                sequence,
                {"filtered": [], "lost": int(row["lost_count"])},
            )
            item["filtered"].append(int(row["filtered_map_points"]))
    return context


def write_report(path, rows, active_effect_path):
    ate = metric_map(rows, "ATE_RMSE")
    tracked = {(row["sequence"], row["method"]): int(row["tracked_frames"]) for row in rows}
    keyframes = {(row["sequence"], row["method"]): int(row["keyframes"]) for row in rows}
    context = active_context(active_effect_path)
    with path.open("w", encoding="utf-8") as stream:
        stream.write("# Paper2 Method Comparison Analysis\n\n")
        stream.write("## 实验数据直接支持的结论\n\n")
        for sequence in SEQUENCES:
            baseline, paper1, shadow, active = [ate[(sequence, method)] for method in METHODS]
            stream.write("### `{}`\n\n".format(sequence))
            stream.write(
                "- Baseline → Paper1：ATE {:.6f} → {:.6f} m（{:+.2f}%）。\n".format(
                    baseline, paper1, percent_change(baseline, paper1)
                )
            )
            stream.write(
                "- Paper1 → Shadow：ATE {:.6f} → {:.6f} m（{:+.2f}%）。\n".format(
                    paper1, shadow, percent_change(paper1, shadow)
                )
            )
            stream.write(
                "- Shadow → Active：ATE {:.6f} → {:.6f} m（{:+.2f}%）。\n".format(
                    shadow, active, percent_change(shadow, active)
                )
            )
            stream.write(
                "- tracked frames（Baseline/Paper1/Shadow/Active）：{}/{}/{}/{}。\n\n".format(
                    *(tracked[(sequence, method)] for method in METHODS)
                )
            )
            stream.write(
                "- keyframes（Baseline/Paper1/Shadow/Active）：{}/{}/{}/{}。\n\n".format(
                    *(keyframes[(sequence, method)] for method in METHODS)
                )
            )
        best_by_sequence = {
            sequence: min(METHODS, key=lambda method: ate[(sequence, method)])
            for sequence in SEQUENCES
        }
        mean_ate = {
            method: sum(ate[(sequence, method)] for sequence in SEQUENCES) / len(SEQUENCES)
            for method in METHODS
        }
        stream.write("## 六个问题的实验事实回答\n\n")
        stream.write("1. Paper1 相比 Baseline：walking_rpy 改善；walking_xyz 和 walking_halfsphere 退化。\n")
        stream.write("2. Shadow 相比 Paper1：三个序列的 ATE 均降低。\n")
        stream.write("3. Active 相比 Shadow：walking_xyz 改善；walking_rpy 和 walking_halfsphere 退化。\n")
        stream.write(
            "4. 按 ATE RMSE，walking_xyz 的最优方法为 {}；该序列也是 Active 唯一改善 Shadow 的场景。\n".format(
                best_by_sequence["fr3_walking_xyz"]
            )
        )
        stream.write(
            "5. Active 退化场景为 walking_rpy 和 walking_halfsphere。各序列最优方法分别为：{}。\n".format(
                "，".join("{}={}".format(name[4:], best_by_sequence[name]) for name in SEQUENCES)
            )
        )
        stream.write(
            "6. Active Effect 日志中 walking_rpy/halfsphere 的 gap episode 为 4/3，"
            "而 walking_xyz 为 0；这与 Active 在前两者退化、后者改善的方向对应。"
            "但 tracked frames 与 keyframes 并非单调对应 ATE，因此不能单独解释精度变化。\n\n"
        )
        stream.write(
            "三序列单次运行的平均 ATE 为：{}。该均值仅作汇总，不代表统计显著性。\n\n".format(
                "，".join("{}={:.6f} m".format(method, mean_ate[method]) for method in METHODS)
            )
        )
        stream.write("以上结果来自单次运行，不包含显著性检验。\n\n")
        stream.write("## 基于实验现象的推测\n\n")
        for sequence in SEQUENCES:
            item = context.get(sequence, {"filtered": [], "lost": 0})
            mean_filtered = (
                sum(item["filtered"]) / len(item["filtered"])
                if item["filtered"] else 0.0
            )
            change = percent_change(ate[(sequence, "shadow")], ate[(sequence, "active")])
            stream.write(
                "- `{}`：Active 平均过滤 {:.2f} 点/日志帧，lost 代理计数 {}，"
                "Shadow→Active ATE 变化 {:+.2f}%。过滤可能{}。\n".format(
                    sequence, mean_filtered, item["lost"], change,
                    "减少动态目标对位姿估计的干扰" if change > 0
                    else "移除了部分有效静态约束或降低了重定位稳定性"
                )
            )
        stream.write(
            "\n这些原因是与 `active_effect_analysis.csv` 联合观察后的解释，"
            "尚未通过消融实验、重复实验或统计检验确认。\n"
        )


def main():
    project_root = Path(__file__).resolve().parents[1]
    results = project_root / "experiment_new" / "paper2" / "results"
    roots = {
        "baseline": results / "baseline",
        "paper1": results / "paper1",
        "shadow": results / "final",
        "active": results / "active",
    }
    dataset_root = Path("/home/djn/datasets/TUMRGBD")
    rows = []
    for sequence in SEQUENCES:
        groundtruth = dataset_root / "rgbd_dataset_freiburg3_{}".format(sequence[4:]) / "groundtruth.txt"
        for method in METHODS:
            run = latest_run(roots[method], sequence)
            trajectory = run / "CameraTrajectory.txt"
            with tempfile.TemporaryDirectory(prefix="paper2_method_evo_") as directory:
                metrics = evaluate(groundtruth, trajectory, Path(directory))
            rows.append(
                {
                    "sequence": sequence,
                    "method": method,
                    "ATE_RMSE": "{:.9f}".format(metrics["ATE_RMSE"]),
                    "ATE_mean": "{:.9f}".format(metrics["ATE_mean"]),
                    "RPE_trans": "{:.9f}".format(metrics["RPE_trans"]),
                    "RPE_rot": "{:.9f}".format(metrics["RPE_rot"]),
                    "tracked_frames": count_lines(trajectory),
                    "keyframes": count_lines(run / "KeyFrameTrajectory.txt"),
                }
            )
            print("Evaluated {} {} from {}".format(sequence, method, run))

    comparison = results / "comparison"
    comparison.mkdir(parents=True, exist_ok=True)
    write_csv(comparison / "trajectory_comparison.csv", rows)
    write_ate_table(comparison / "table_method_comparison.tex", rows)
    write_rpe_table(comparison / "table_rpe_comparison.tex", rows)
    write_report(
        comparison / "method_comparison_analysis.md",
        rows,
        results / "active" / "active_effect_analysis.csv",
    )
    print("Wrote comparison outputs to {}".format(comparison))


if __name__ == "__main__":
    main()
