#!/usr/bin/env python3
"""Analyze the low TSR of Full Model on fr3_walking_rpy.

The script only reads existing logs and result files. It does not rerun SLAM or
modify any experiment output.
"""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path
from statistics import mean, stdev


ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = ROOT / "experiment_new" / "independent_ablation_v3" / "runs" / "full_model" / "fr3_walking_rpy"
ASSOC = ROOT / "dataset_associations" / "fr3_walking_rpy_associate.txt"
OUT_ROOT = ROOT / "results" / "tracking_success_rate" / "fr3_walking_rpy_full_model_analysis"
SEQ_RESULTS = ROOT / "experiment_new" / "independent_ablation_v3" / "aggregated_results" / "sequence_results.csv"
N_FEATURES_FALLBACK = 1000


def read_assoc_frames() -> list[float]:
    frames: list[float] = []
    for raw in ASSOC.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if not parts:
            continue
        try:
            frames.append(float(parts[0]))
        except ValueError:
            continue
    return frames


def read_valid_pose_timestamps(path: Path) -> list[float]:
    stamps: list[float] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 8:
            continue
        try:
            vals = [float(v) for v in parts[:8]]
        except ValueError:
            continue
        if all(math.isfinite(v) for v in vals):
            stamps.append(vals[0])
    return stamps


def nearest_frame_indices(stamps: list[float], assoc_stamps: list[float], max_diff: float = 0.02) -> list[int]:
    out: list[int] = []
    j = 0
    for stamp in stamps:
        while j + 1 < len(assoc_stamps) and abs(assoc_stamps[j + 1] - stamp) < abs(assoc_stamps[j] - stamp):
            j += 1
        if abs(assoc_stamps[j] - stamp) <= max_diff:
            out.append(j + 1)
    return out


def read_frame_status(path: Path) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            converted: dict[str, float] = {}
            for key, value in row.items():
                try:
                    converted[key] = float(value)
                except (TypeError, ValueError):
                    converted[key] = math.nan
            rows.append(converted)
    return rows


def read_nfeatures(stdout: Path) -> int:
    text = stdout.read_text(encoding="utf-8", errors="ignore") if stdout.exists() else ""
    match = re.search(r"Number of Features:\s*(\d+)", text)
    if match:
        return int(match.group(1))
    return N_FEATURES_FALLBACK


def fmt(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}" if math.isfinite(value) else "NA"


def mean_std(values: list[float], digits: int = 2) -> str:
    if not values:
        return "NA"
    sigma = stdev(values) if len(values) > 1 else 0.0
    return f"{mean(values):.{digits}f} ± {sigma:.{digits}f}"


def read_ate_rpe() -> dict[str, tuple[float, float]]:
    out: dict[str, tuple[float, float]] = {}
    if not SEQ_RESULTS.exists():
        return out
    with SEQ_RESULTS.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row.get("variant_key") == "full_model" and row.get("sequence") == "fr3_walking_rpy":
                try:
                    out[row["run_id"]] = (float(row["ATE_RMSE"]), float(row["RPE_translation_RMSE"]))
                except (KeyError, ValueError):
                    pass
    return out


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    assoc_stamps = read_assoc_frames()
    total_frames = len(assoc_stamps)
    ate_rpe = read_ate_rpe()

    per_frame_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []

    for run_dir in sorted(RUN_ROOT.glob("run_*")):
        if not run_dir.is_dir():
            continue
        run_id = run_dir.name
        nfeatures = read_nfeatures(run_dir / "stdout.log")
        frame_rows = read_frame_status(run_dir / "frame_status.csv")
        pose_stamps = read_valid_pose_timestamps(run_dir / "CameraTrajectory.txt")
        valid_frame_indices = nearest_frame_indices(pose_stamps, assoc_stamps)
        valid_set = set(valid_frame_indices)
        valid_poses = len(pose_stamps)
        last_valid_frame = max(valid_frame_indices) if valid_frame_indices else 0
        first_failure_frame = last_valid_frame + 1 if last_valid_frame < total_frames else None
        failed_frame_count = max(total_frames - last_valid_frame, 0)
        recorded_frame_count = len(frame_rows)

        dynamic_keypoints = [r.get("dynamic_keypoints", math.nan) for r in frame_rows]
        dynamic_map_points = [r.get("dynamic_map_points", math.nan) for r in frame_rows]
        suppressed_map_points = [r.get("suppressed_map_points", math.nan) for r in frame_rows]
        static_objects = [r.get("static_objects", math.nan) for r in frame_rows]
        dynamic_objects = [r.get("dynamic_objects", math.nan) for r in frame_rows]
        effective_est = [max(nfeatures - v, 0.0) for v in dynamic_keypoints if math.isfinite(v)]

        for row in frame_rows:
            frame_id = int(row.get("frame_id", math.nan))
            dyn_kp = row.get("dynamic_keypoints", math.nan)
            effective = max(nfeatures - dyn_kp, 0.0) if math.isfinite(dyn_kp) else math.nan
            per_frame_rows.append(
                {
                    "run_id": run_id,
                    "frame_id": frame_id,
                    "has_valid_pose": 1 if frame_id in valid_set else 0,
                    "dynamic_keypoints": fmt(dyn_kp, 0),
                    "dynamic_map_points": fmt(row.get("dynamic_map_points", math.nan), 0),
                    "suppressed_map_points": fmt(row.get("suppressed_map_points", math.nan), 0),
                    "effective_orb_features_est": fmt(effective, 0),
                    "effective_orb_ratio_est": fmt(effective / nfeatures if nfeatures else math.nan, 4),
                    "dynamic_objects": fmt(row.get("dynamic_objects", math.nan), 0),
                    "static_objects": fmt(row.get("static_objects", math.nan), 0),
                    "total_objects": fmt(row.get("total_objects", math.nan), 0),
                    "frame_dynamic_present": fmt(row.get("frame_dynamic_present", math.nan), 0),
                }
            )

        last_rows = [r for r in frame_rows if int(r.get("frame_id", -1)) >= max(last_valid_frame - 4, 1)]
        last_dyn_kp = [r.get("dynamic_keypoints", math.nan) for r in last_rows]
        last_eff = [max(nfeatures - v, 0.0) for v in last_dyn_kp if math.isfinite(v)]
        ate, rpe = ate_rpe.get(run_id, (math.nan, math.nan))
        summary_rows.append(
            {
                "run_id": run_id,
                "total_frames": total_frames,
                "valid_poses": valid_poses,
                "TSR(%)": fmt(valid_poses / total_frames * 100, 2),
                "recorded_dynamic_frames": recorded_frame_count,
                "last_valid_frame": last_valid_frame,
                "first_failure_frame": first_failure_frame if first_failure_frame else "NA",
                "failed_frame_range": f"{first_failure_frame}-{total_frames}" if first_failure_frame else "NA",
                "failed_frame_count_after_last_pose": failed_frame_count,
                "dynamic_keypoints_mean": fmt(mean(dynamic_keypoints), 2),
                "dynamic_keypoints_max": fmt(max(dynamic_keypoints), 0),
                "dynamic_map_points_mean": fmt(mean(dynamic_map_points), 2),
                "suppressed_map_points_mean": fmt(mean(suppressed_map_points), 2),
                "effective_orb_features_est_mean": fmt(mean(effective_est), 2),
                "effective_orb_features_est_min": fmt(min(effective_est), 0),
                "effective_orb_features_est_last5_mean": fmt(mean(last_eff), 2) if last_eff else "NA",
                "static_objects_min": fmt(min(static_objects), 0),
                "dynamic_objects_mean": fmt(mean(dynamic_objects), 2),
                "ATE_RMSE": fmt(ate, 4),
                "RPE_translation_RMSE": fmt(rpe, 4),
            }
        )

    with (OUT_ROOT / "fr3_walking_rpy_full_model_per_frame.csv").open("w", newline="", encoding="utf-8") as f:
        fields = [
            "run_id",
            "frame_id",
            "has_valid_pose",
            "dynamic_keypoints",
            "dynamic_map_points",
            "suppressed_map_points",
            "effective_orb_features_est",
            "effective_orb_ratio_est",
            "dynamic_objects",
            "static_objects",
            "total_objects",
            "frame_dynamic_present",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(per_frame_rows)

    with (OUT_ROOT / "fr3_walking_rpy_full_model_summary.csv").open("w", newline="", encoding="utf-8") as f:
        fields = list(summary_rows[0].keys()) if summary_rows else []
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summary_rows)

    dyn_means = [float(r["dynamic_keypoints_mean"]) for r in summary_rows]
    eff_means = [float(r["effective_orb_features_est_mean"]) for r in summary_rows]
    last_eff_means = [float(r["effective_orb_features_est_last5_mean"]) for r in summary_rows]
    first_failures = [int(r["first_failure_frame"]) for r in summary_rows if r["first_failure_frame"] != "NA"]
    tsrs = [float(r["TSR(%)"]) for r in summary_rows]
    ates = [float(r["ATE_RMSE"]) for r in summary_rows]
    rpes = [float(r["RPE_translation_RMSE"]) for r in summary_rows]

    report = [
        "# fr3_walking_rpy Full Model TSR Drop Analysis",
        "",
        "## Data Sources",
        "",
        f"- Run directory: `{RUN_ROOT}`",
        f"- Association file: `{ASSOC}`",
        f"- ATE/RPE source: `{SEQ_RESULTS}`",
        "- Per-frame dynamic statistics source: `frame_status.csv` in each run directory.",
        "- Trajectory source: `CameraTrajectory.txt` in each run directory.",
        "",
        "No SLAM algorithm, trajectory file, or experiment result file was modified.",
        "",
        "## Metric Availability",
        "",
        "- Directly recorded: `dynamic_keypoints`, `dynamic_map_points`, `suppressed_map_points`, `dynamic_objects`, `static_objects`, `total_objects`.",
        "- Directly counted: valid poses from `CameraTrajectory.txt`; failure onset from the first input frame after the last valid pose.",
        "- Estimated: effective ORB features after semantic suppression, computed as `ORBextractor.nFeatures - dynamic_keypoints`. The ORB extractor target is 1000 features per frame, read from the run log and `Examples/RGB-D/TUM3.yaml`. This is an estimate because the current logs do not directly export the final number of valid tracking features after matching and map-point association.",
        "",
        "## Run-level Summary",
        "",
        "| Run | TSR (%) | Last valid frame | First failure frame | Dynamic keypoints mean/max | Dynamic map points mean | Suppressed map points mean | Effective ORB est. mean/min | Last-5 effective ORB est. mean | ATE (m) | RPE (m) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        report.append(
            f"| {row['run_id']} | {row['TSR(%)']} | {row['last_valid_frame']} | {row['first_failure_frame']} | "
            f"{row['dynamic_keypoints_mean']}/{row['dynamic_keypoints_max']} | {row['dynamic_map_points_mean']} | "
            f"{row['suppressed_map_points_mean']} | {row['effective_orb_features_est_mean']}/{row['effective_orb_features_est_min']} | "
            f"{row['effective_orb_features_est_last5_mean']} | {row['ATE_RMSE']} | {row['RPE_translation_RMSE']} |"
        )

    report.extend(
        [
            "",
            "## Aggregate Findings",
            "",
            f"- Total input frames per run: {total_frames}.",
            f"- Full Model TSR on `fr3_walking_rpy`: {mean_std(tsrs, 2)}%.",
            f"- First tracking failure frame: {mean_std([float(v) for v in first_failures], 1)}.",
            f"- Mean dynamic keypoints in the tracked prefix: {mean_std(dyn_means, 2)}.",
            f"- Estimated mean effective ORB features after semantic suppression: {mean_std(eff_means, 2)}.",
            f"- Estimated mean effective ORB features in the last five recorded frames before failure: {mean_std(last_eff_means, 2)}.",
            f"- ATE on the remaining tracked fragments: {mean_std(ates, 4)} m.",
            f"- RPE on the remaining tracked fragments: {mean_std(rpes, 4)} m.",
            "",
            "## Interpretation",
            "",
            "The Full Model loses continuous tracking very early on `fr3_walking_rpy`. The three runs output only 33-34 valid poses out of 866 input RGB-D frames, and the first missing-pose frame appears at frame 34-35. The per-frame semantic-dynamic log shows that the tracked prefix contains a large number of dynamic keypoints, typically over 570 per frame and up to about 768-769 near the last valid frame. Under the configured ORB target of 1000 features per image, this leaves only roughly 420 effective static ORB features on average, and about 230-310 estimated effective features in the last few frames before tracking stops.",
            "",
            "The logged `dynamic_map_points` and `suppressed_map_points` remain zero during this short tracked prefix. Therefore, the low TSR should not be described as being caused by accumulated dynamic map-point removal in the available logs. A more careful explanation is that the semantic dynamic filtering identifies many keypoints as dynamic in the initial frames; in the fast rotational `rpy` motion, this reduces the stable feature support available for pose tracking before enough robust static map-point constraints can be maintained. The failure is thus more closely associated with early-stage dynamic-keypoint suppression and limited static feature support than with later map-point suppression.",
            "",
            "The ATE/RPE values for Full Model on this sequence are low, but they are computed only on the very short successful trajectory fragment. They should therefore be interpreted together with TSR. The result supports a trade-off: stronger dynamic suppression can reduce dynamic mismatches and produce locally stable pose estimates on successful fragments, but in fast rotation scenes it can also reduce trajectory completeness and cause early tracking interruption.",
            "",
            "## Paper-ready Text",
            "",
            "进一步分析 `fr3_walking_rpy` 序列可以发现，Full Model 的跟踪成功率下降主要发生在序列初始阶段。三次运行均仅输出约33-34帧有效位姿，首次缺失位姿出现在第34-35帧附近。逐帧动态统计表明，初始跟踪片段中被判定为动态的ORB关键点数量较多，平均每帧超过570个，在跟踪中断前的若干帧中最高接近770个。由于本实验中ORB提取器每帧目标特征数为1000，语义动态抑制后可用于稳定跟踪的静态特征数量明显减少。现有日志中动态地图点和被抑制地图点数量在该短片段内为0，说明该序列的低TSR更可能与早期动态关键点抑制和快速旋转导致的静态约束不足有关，而不是由长期动态地图点累积删除直接造成。",
            "",
            "因此，`fr3_walking_rpy` 上较低的ATE/RPE应结合TSR共同解释。Full Model在成功跟踪的短片段上具有较小误差，说明动态误匹配得到一定抑制；但由于有效轨迹覆盖率较低，该结果不能说明完整序列的连续跟踪能力更强。该现象反映出动态点抑制与轨迹完整性之间的权衡：在快速旋转和强动态干扰同时存在时，较严格的动态观测抑制可能提升局部估计稳定性，但也可能削弱可用特征约束并降低长期跟踪完整性。",
            "",
        ]
    )
    (OUT_ROOT / "fr3_walking_rpy_full_model_analysis.md").write_text("\n".join(report), encoding="utf-8")

    print(f"Output directory: {OUT_ROOT}")
    print(f"Per-frame CSV: {OUT_ROOT / 'fr3_walking_rpy_full_model_per_frame.csv'}")
    print(f"Summary CSV: {OUT_ROOT / 'fr3_walking_rpy_full_model_summary.csv'}")
    print(f"Report: {OUT_ROOT / 'fr3_walking_rpy_full_model_analysis.md'}")


if __name__ == "__main__":
    main()
