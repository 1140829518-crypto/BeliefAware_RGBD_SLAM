#!/usr/bin/env python3

"""Analyze the measured effect of Paper2 Active MapPoint filtering."""

import argparse
import csv
import re
from pathlib import Path


SEQUENCES = (
    "fr3_walking_xyz",
    "fr3_walking_rpy",
    "fr3_walking_halfsphere",
)
ACTIVE_PATTERN = re.compile(
    r"\[ObjectDynamicActive\]\s+frame=(\d+)\s+before_points=(\d+)\s+"
    r"filtered_points=(\d+)\s+after_points=(\d+)"
)
SHADOW_PATTERN = re.compile(
    r"\[ObjectDynamicShadow\]\s+frame=(\d+)\s+detections=(\d+)\s+"
    r"active=(\d+)\s+dynamic=(\d+)"
)
TIME_PATTERN = re.compile(r"(mean|median) tracking time:\s*([0-9.]+)")
IMAGE_COUNT_PATTERN = re.compile(r"Images in the sequence:\s*(\d+)")


def read_sequence(run_log):
    for line in run_log.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("sequence_name="):
            return line.split("=", 1)[1].strip()
    return None


def latest_runs(results_root):
    runs = {}
    for run_log in results_root.glob("*/run.log"):
        sequence = read_sequence(run_log)
        if sequence not in SEQUENCES:
            continue
        if sequence not in runs or run_log.stat().st_mtime > runs[sequence].stat().st_mtime:
            runs[sequence] = run_log
    return runs


def count_data_lines(path):
    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#"))


def dynamic_statistics(path):
    if not path.is_file():
        return 0, 0.0
    frames = {}
    with path.open("r", encoding="utf-8") as stream:
        header = stream.readline().split()
        frame_index = header.index("frame_id")
        dynamic_index = header.index("dynamic_objects")
        for line in stream:
            fields = line.split()
            if fields:
                frames[int(fields[frame_index])] = int(fields[dynamic_index])
    total = sum(frames.values())
    return total, (float(total) / len(frames) if frames else 0.0)


def count_missing_intervals(successful_frames, total_frames):
    """Count contiguous missing-frame intervals after Tracking first succeeds."""
    if not successful_frames:
        return 1 if total_frames else 0
    successful = set(successful_frames)
    lost_intervals = 0
    inside_gap = False
    for frame_id in range(min(successful), total_frames):
        missing = frame_id not in successful
        if missing and not inside_gap:
            lost_intervals += 1
        inside_gap = missing
    return lost_intervals


def load_ate(path):
    values = {}
    if not path.is_file():
        return values
    with path.open("r", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            values[row["sequence"]] = float(row["ATE_RMSE"])
    return values


def analyze_run(sequence, run_log, shadow_ate, active_ate):
    text = run_log.read_text(encoding="utf-8", errors="replace")
    active_rows = [tuple(map(int, match.groups())) for match in ACTIVE_PATTERN.finditer(text)]
    shadow_rows = [tuple(map(int, match.groups())) for match in SHADOW_PATTERN.finditer(text)]
    times = {name: float(value) for name, value in TIME_PATTERN.findall(text)}
    image_match = IMAGE_COUNT_PATTERN.search(text)
    total_frames = int(image_match.group(1)) if image_match else 0
    filtered = [row[2] for row in active_rows]
    dynamic_total, dynamic_average = dynamic_statistics(
        run_log.with_name("SemanticDynamicStatistics.txt")
    )
    shadow_value = shadow_ate.get(sequence)
    active_value = active_ate.get(sequence)
    improvement = (
        100.0 * (shadow_value - active_value) / shadow_value
        if shadow_value is not None and active_value is not None
        else None
    )
    return {
        "sequence": sequence,
        "total_input_frames": total_frames,
        "active_log_frames": len(active_rows),
        "filtered_points_total": sum(filtered),
        "filtered_points_per_frame": sum(filtered) / len(filtered) if filtered else 0.0,
        "filtered_points_max": max(filtered) if filtered else 0,
        "frames_with_filtering": sum(value > 0 for value in filtered),
        "tracking_time_mean": times.get("mean", 0.0),
        "tracking_time_median": times.get("median", 0.0),
        "keyframe_count": count_data_lines(run_log.with_name("KeyFrameTrajectory.txt")),
        "lost_count": count_missing_intervals([row[0] for row in shadow_rows], total_frames),
        "dynamic_object_count": dynamic_total,
        "average_dynamic_objects": dynamic_average,
        "shadow_ate": shadow_value,
        "active_ate": active_value,
        "ate_improvement_percent": improvement,
        "result_directory": str(run_log.parent.resolve()),
    }


def write_csv(path, rows):
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def frame_rows(sequence, run_log, summary):
    text = run_log.read_text(encoding="utf-8", errors="replace")
    dynamic_by_frame = {
        int(match.group(1)): int(match.group(4))
        for match in SHADOW_PATTERN.finditer(text)
    }
    rows = []
    for match in ACTIVE_PATTERN.finditer(text):
        frame_id, before, filtered, after = map(int, match.groups())
        rows.append(
            {
                "sequence": sequence,
                "frame": frame_id,
                "before_points": before,
                "filtered_map_points": filtered,
                "after_points": after,
                "dynamic_objects": dynamic_by_frame.get(frame_id, ""),
                "tracking_time_mean": summary["tracking_time_mean"],
                "keyframe_count": summary["keyframe_count"],
                "lost_count": summary["lost_count"],
            }
        )
    return rows


def write_analysis(path, rows):
    improved = [row for row in rows if row["ate_improvement_percent"] is not None and row["ate_improvement_percent"] > 0]
    degraded = [row for row in rows if row["ate_improvement_percent"] is not None and row["ate_improvement_percent"] <= 0]
    with path.open("w", encoding="utf-8") as stream:
        stream.write("# Paper2 Active Mode Effect Analysis\n\n")
        stream.write("本报告基于 Active 实验日志、轨迹和语义统计自动生成，未调整算法参数。\n\n")
        stream.write("## Active 有效场景\n\n")
        for row in improved:
            stream.write(
                "- `{}`：ATE RMSE 从 {:.6f} m 降至 {:.6f} m，改善 {:.2f}%；"
                "平均每个 Active 日志帧过滤 {:.2f} 个 MapPoint。\n".format(
                    row["sequence"], row["shadow_ate"], row["active_ate"],
                    row["ate_improvement_percent"], row["filtered_points_per_frame"]
                )
            )
        stream.write("\n## Active 退化场景\n\n")
        for row in degraded:
            stream.write(
                "- `{}`：ATE RMSE 从 {:.6f} m 增至 {:.6f} m，变化 {:.2f}%；"
                "lost episode 代理计数为 {}，关键帧数为 {}。\n".format(
                    row["sequence"], row["shadow_ate"], row["active_ate"],
                    row["ate_improvement_percent"], row["lost_count"], row["keyframe_count"]
                )
            )
        stream.write("\n## 可能原因\n\n")
        stream.write(
            "1. Active 过滤在动态点占比较高且静态背景仍足够时，可以减少运动目标对位姿估计的干扰。\n"
            "2. 过滤过多或对象与 MapPoint 关联存在误差时，可能同时移除有效静态约束，降低局部匹配和重定位稳定性。\n"
            "3. 不同相机运动方式改变了可见静态纹理、运动模糊和对象遮挡比例，因此同一过滤策略在 xyz、rpy 和 halfsphere 上表现不同。\n"
            "4. `lost_count` 是成功 `[ObjectDynamicShadow]` 帧之间连续缺口的日志代理指标；当前代码未直接导出内部 Tracking::LOST 转换次数。\n"
            "5. 当前结果是单次运行，论文结论应在多次重复实验后报告均值、标准差和跟踪成功率。\n"
        )


def main():
    project_root = Path(__file__).resolve().parents[1]
    results_root = project_root / "experiment_new" / "paper2" / "results"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--active-results", type=Path, default=results_root / "active")
    parser.add_argument("--shadow-evaluation", type=Path, default=results_root / "final" / "trajectory_evaluation.csv")
    parser.add_argument("--active-evaluation", type=Path, default=results_root / "active" / "trajectory_evaluation.csv")
    parser.add_argument("--output", type=Path, default=results_root / "active" / "active_effect_analysis.csv")
    parser.add_argument("--report", type=Path, default=results_root / "active" / "active_analysis.md")
    args = parser.parse_args()

    runs = latest_runs(args.active_results)
    missing = [sequence for sequence in SEQUENCES if sequence not in runs]
    if missing:
        raise SystemExit("missing Active runs for: {}".format(", ".join(missing)))
    shadow_ate = load_ate(args.shadow_evaluation)
    active_ate = load_ate(args.active_evaluation)
    rows = [analyze_run(sequence, runs[sequence], shadow_ate, active_ate) for sequence in SEQUENCES]
    per_frame_rows = []
    for row in rows:
        per_frame_rows.extend(frame_rows(row["sequence"], runs[row["sequence"]], row))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_csv(args.output, per_frame_rows)
    write_analysis(args.report, rows)
    print("Wrote {}".format(args.output.resolve()))
    print("Wrote {}".format(args.report.resolve()))


if __name__ == "__main__":
    main()
