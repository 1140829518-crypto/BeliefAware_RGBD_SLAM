#!/usr/bin/env python3
"""Collect data needed for paper figures into Paper_Figure_Data.

The script copies or reshapes existing experiment outputs only. It does not
rerun SLAM, change original results, or invent unavailable raw measurements.
"""

from __future__ import annotations

import csv
import shutil
from pathlib import Path
from typing import Dict, Iterable, List, Optional


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Paper_Figure_Data"
EXP = ROOT / "experiment_new"
BONN_MANIFEST = EXP / "results" / "bonn_selected_sequences.csv"
BONN_RUNS = EXP / "results" / "bonn_runs"
ABLATION = EXP / "independent_ablation_v3"


def mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def copy_if_exists(src: Path, dst: Path, audit: List[str]) -> bool:
    if src.exists():
        mkdir(dst.parent)
        shutil.copy2(src, dst)
        audit.append(f"- copied `{src}` -> `{dst}`")
        return True
    audit.append(f"- missing source, not copied: `{src}`")
    return False


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fieldnames: Iterable[str], rows: Iterable[Dict[str, object]]) -> None:
    mkdir(path.parent)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def fmt_float(value: str, ndigits: int = 4) -> str:
    try:
        return f"{float(value):.{ndigits}f}"
    except (TypeError, ValueError):
        return value


def first_existing(paths: Iterable[Path]) -> Optional[Path]:
    for path in paths:
        if path.exists():
            return path
    return None


def prepare_fig1(audit: List[str]) -> None:
    out = OUT / "Fig1_System_Framework"
    mkdir(out)
    (out / "system_description.txt").write_text(
        "\n".join(
            [
                "论文题目：基于时间一致性建模的鲁棒语义动态 RGB-D SLAM 方法",
                "",
                "图1系统框架图不需要Matplotlib数值数据。",
                "图中应包含以下处理模块：",
                "1. RGB-D Input：输入RGB图像与深度图像。",
                "2. ORB-SLAM2 RGB-D Frontend：特征提取、特征匹配、位姿跟踪。",
                "3. YOLOv5 Semantic Detection：目标类别、检测置信度、语义观测。",
                "4. Temporal Dynamic Evidence Model：动态证据分数、lambda衰减、gamma增量、theta阈值。",
                "5. Dynamic Point Suppression：根据动态证据抑制动态点参与跟踪与优化。",
                "6. Backend Optimization：局部建图、回环检测、图优化。",
                "7. Object-level Semantic Map：对象类别、三维位置、ID关联、动态状态。",
                "8. Final Outputs：相机轨迹、特征地图、动态目标信息、语义地图。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (out / "module_relationship.txt").write_text(
        "\n".join(
            [
                "RGB-D Input -> ORB-SLAM2 RGB-D Frontend -> Backend Optimization -> Feature Map / Camera Trajectory",
                "RGB-D Input -> YOLOv5 Semantic Detection -> Dynamic Evidence Update",
                "ORB-SLAM2 RGB-D Frontend -> Dynamic Evidence Update：提供特征观测与跟踪状态。",
                "Dynamic Evidence Update -> Temporal Dynamic Evidence Model：语义观测经时间衰减和证据累积形成动态证据。",
                "Temporal Dynamic Evidence Model -> Dynamic Point Suppression：超过阈值的动态点被抑制。",
                "Dynamic Point Suppression -> Backend Optimization：减少动态目标对位姿估计和地图优化的干扰。",
                "Temporal Dynamic Evidence Model -> Object-level Semantic Map：维护对象类别、ID关联和动态状态。",
                "Object-level Semantic Map -> Final Outputs：输出结构化语义环境表达。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    audit.append(f"- wrote Fig1 text descriptors under `{out}`")


def prepare_fig2(audit: List[str]) -> None:
    out = OUT / "Fig2_Trajectory"
    mkdir(out)

    tum_gt = first_existing(
        [
            Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz/groundtruth.txt"),
            ROOT.parent / "datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz/groundtruth.txt",
            ROOT.parent.parent / "datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz/groundtruth.txt",
        ]
    )
    if tum_gt:
        copy_if_exists(tum_gt, out / "groundtruth.txt", audit)
    tum_sources = {
        "ORB_SLAM2.txt": ROOT / "standard_runs/fr3_walking_xyz/orb_slam2/CameraTrajectory.txt",
        "DS_SLAM.txt": ROOT / "baseline_runs_missing/ds_slam/fr3_walking_xyz/CameraTrajectory.txt",
        "DynaSLAM.txt": ROOT / "baseline_runs_retry/dyna_slam/fr3_walking_xyz/CameraTrajectory.txt",
        "Ours.txt": ROOT / "standard_runs/fr3_walking_xyz/full_method/CameraTrajectory.txt",
    }
    for name, src in tum_sources.items():
        copy_if_exists(src, out / name, audit)

    if BONN_MANIFEST.exists():
        for row in read_csv(BONN_MANIFEST):
            dataset = row["Dataset"]
            seq_dir = Path(row["Path"])
            seq_out = out / dataset
            copy_if_exists(seq_dir / "groundtruth.txt", seq_out / "gt.txt", audit)
            bonn_sources = {
                "orbslam3.txt": BONN_RUNS / dataset / "orb_slam3" / "CameraTrajectory.txt",
                "dsslam.txt": BONN_RUNS / dataset / "ds_slam" / "CameraTrajectory.txt",
                "dynaslam.txt": BONN_RUNS / dataset / "dyna_slam" / "CameraTrajectory.txt",
                "ours.txt": BONN_RUNS / dataset / "ours" / "CameraTrajectory.txt",
            }
            for name, src in bonn_sources.items():
                copy_if_exists(src, seq_out / name, audit)
        (out / "method_mapping.txt").write_text(
            "Bonn trajectory data contain ORB-SLAM3 results (`orbslam3.txt`). "
            "No Bonn ORB-SLAM2 trajectory is available in the current Bonn run directory, "
            "so ORB-SLAM3 is not relabeled as ORB-SLAM2.\n",
            encoding="utf-8",
        )
        audit.append(f"- wrote Bonn method mapping note under `{out}`")


def prepare_fig3(audit: List[str]) -> None:
    out = OUT / "Fig3_Dynamic_Evidence"
    src = ABLATION / "runs/full_model/fr3_walking_xyz/run_01/dynamic_detection.csv"
    rows_out: List[Dict[str, object]] = []
    if src.exists():
        rows = read_csv(src)
        max_keypoints = max((float(r.get("dynamic_keypoints", 0) or 0) for r in rows), default=1.0) or 1.0
        for r in rows:
            total_objects = float(r.get("total_objects", 0) or 0)
            dynamic_objects = float(r.get("dynamic_objects", 0) or 0)
            yolo_proxy = dynamic_objects / total_objects if total_objects > 0 else 0.0
            temporal_proxy = float(r.get("dynamic_keypoints", 0) or 0) / max_keypoints
            rows_out.append(
                {
                    "frame": int(float(r.get("frame_id", 0) or 0)),
                    "YOLO_score": f"{yolo_proxy:.6f}",
                    "motion_score": "NA",
                    "temporal_score": f"{temporal_proxy:.6f}",
                    "dynamic_state": int(float(r.get("frame_dynamic_present", 0) or 0)),
                }
            )
        audit.append(f"- derived Fig3 dynamic_evidence.csv from `{src}`")
    write_csv(out / "dynamic_evidence.csv", ["frame", "YOLO_score", "motion_score", "temporal_score", "dynamic_state"], rows_out)
    (out / "data_note.txt").write_text(
        "The current logs do not contain raw YOLO_score, motion_score, and temporal_score probability columns. "
        "YOLO_score is exported as dynamic_objects / total_objects, temporal_score as normalized dynamic_keypoints, "
        "and motion_score is marked NA. These columns are plotting proxies derived from real run statistics, "
        "not manually fabricated probabilities.\n",
        encoding="utf-8",
    )


def prepare_fig4(audit: List[str]) -> None:
    out = OUT / "Fig4_Detection_Performance"
    src = EXP / "results/dynamic_detection_accuracy.csv"
    rows_out = []
    if src.exists():
        for r in read_csv(src):
            name = r["Method"]
            name = name.replace("YOLO raw detection", "YOLO")
            name = name.replace("YOLO+motion consistency", "YOLO+Motion")
            name = name.replace("YOLO+temporal consistency (Ours)", "Ours")
            rows_out.append(
                {
                    "Method": name,
                    "Precision": fmt_float(r["Precision"]),
                    "Recall": fmt_float(r["Recall"]),
                    "F1-score": fmt_float(r["F1-score"]),
                }
            )
        audit.append(f"- converted detection metrics from `{src}`")
    write_csv(out / "detection_metrics.csv", ["Method", "Precision", "Recall", "F1-score"], rows_out)


def prepare_fig5(audit: List[str]) -> None:
    out = OUT / "Fig5_Parameter_Analysis"
    src = EXP / "lambda_sensitivity_analysis_v1/results/lambda_results.csv"
    rows_out = []
    if src.exists():
        for r in read_csv(src):
            rows_out.append(
                {
                    "lambda": fmt_float(r["Lambda"], 2),
                    "ATE": fmt_float(r["ATE_mean"]),
                    "RPE": fmt_float(r["RPE_mean"]),
                    "FPS": fmt_float(r["FPS_mean"], 2),
                    "Switching_frequency": fmt_float(r["SwitchingFrequency_mean"]),
                }
            )
        audit.append(f"- converted lambda analysis from `{src}`")
    write_csv(out / "lambda_analysis.csv", ["lambda", "ATE", "RPE", "FPS", "Switching_frequency"], rows_out)


def prepare_fig6(audit: List[str]) -> None:
    out = OUT / "Fig6_Ablation"
    src = ABLATION / "paper_figure_revision/figure6_ablation_data.csv"
    rows_out: Dict[str, Dict[str, object]] = {}
    metric_map = {
        "ATE (m)": ("ATE_mean", "ATE_std"),
        "RPE (m)": ("RPE_mean", "RPE_std"),
        "Pose Missing Ratio": ("Missing_ratio", "Missing_ratio_std"),
        "Switching Frequency": ("Switch_frequency", "Switch_frequency_std"),
    }
    if src.exists():
        for r in read_csv(src):
            method = r["Variant"]
            rows_out.setdefault(method, {"Method": method})
            metric = r["Metric"]
            if metric in metric_map:
                mean_col, std_col = metric_map[metric]
                rows_out[method][mean_col] = fmt_float(r["Mean"])
                rows_out[method][std_col] = fmt_float(r["Std"])
        audit.append(f"- reshaped ablation figure data from `{src}`")
    fields = [
        "Method",
        "ATE_mean",
        "ATE_std",
        "RPE_mean",
        "RPE_std",
        "Missing_ratio",
        "Missing_ratio_std",
        "Switch_frequency",
        "Switch_frequency_std",
    ]
    order = ["Baseline", "Semantic Mask", "Temporal Consistency", "Object-level Semantic Map", "Full Model"]
    write_csv(out / "ablation_results.csv", fields, [rows_out[k] for k in order if k in rows_out])


def first_image_from_list(path: Path) -> Optional[Path]:
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            candidate = path.parent / parts[1]
            if candidate.exists():
                return candidate
    return None


def prepare_fig7(audit: List[str]) -> None:
    out = OUT / "Fig7_Visualization"
    for sub in ["rgb", "depth", "mask", "detection_result", "dynamic_points"]:
        mkdir(out / sub)

    manifest = read_csv(BONN_MANIFEST) if BONN_MANIFEST.exists() else []
    walking = next((r for r in manifest if r["Dataset"] == "walking"), None)
    if walking:
        seq_dir = Path(walking["Path"])
        rgb = first_image_from_list(seq_dir / "rgb.txt")
        depth = first_image_from_list(seq_dir / "depth.txt")
        if rgb:
            copy_if_exists(rgb, out / "rgb" / rgb.name, audit)
        if depth:
            copy_if_exists(depth, out / "depth" / depth.name, audit)

    filtered = BONN_RUNS / "walking/ours/Frame_YDOF_filtered.png"
    copy_if_exists(filtered, out / "dynamic_points" / "Frame_YDOF_filtered.png", audit)
    semantic_map = EXP / "figures/semantic_map_showcase.png"
    copy_if_exists(semantic_map, out / "mask" / "semantic_map_showcase.png", audit)
    detection_fig = EXP / "figures/dynamic_detection_accuracy.png"
    copy_if_exists(detection_fig, out / "detection_result" / "dynamic_detection_accuracy.png", audit)

    (out / "visualization_note.txt").write_text(
        "Fig7 contains available visualization assets from the current project. "
        "The current result directories provide RGB/depth frames and dynamic point filtering images. "
        "Standalone per-frame YOLO detection-box images and semantic mask images were not found; "
        "therefore available paper/result visualizations are copied into detection_result/ and mask/ with this note.\n",
        encoding="utf-8",
    )


def main() -> None:
    audit: List[str] = [
        "# Paper Figure Data Audit",
        "",
        f"- Project root: `{ROOT}`",
        f"- Output root: `{OUT}`",
        "- Original experiment files modified: No",
        "- SLAM rerun: No",
        "",
        "## Operations",
        "",
    ]
    for name, func in [
        ("Fig1", prepare_fig1),
        ("Fig2", prepare_fig2),
        ("Fig3", prepare_fig3),
        ("Fig4", prepare_fig4),
        ("Fig5", prepare_fig5),
        ("Fig6", prepare_fig6),
        ("Fig7", prepare_fig7),
    ]:
        audit.append(f"### {name}")
        func(audit)
        audit.append("")

    (OUT / "data_source_audit.md").write_text("\n".join(audit) + "\n", encoding="utf-8")
    print(f"Generated: {OUT}")
    print(f"Audit: {OUT / 'data_source_audit.md'}")


if __name__ == "__main__":
    main()
