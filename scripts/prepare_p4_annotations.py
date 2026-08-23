#!/usr/bin/env python3
"""Create objective P4 frame samples and blank manual-GT assets."""

from __future__ import annotations

import csv
from pathlib import Path
import shutil

import cv2
import numpy as np


REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "experiments/final_paper/04_mappoint_gt_eval"
SEQUENCES = {
    "fr3_walking_xyz": (
        Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz"),
        REPO / "dataset_associations/fr3_walking_xyz_associate.txt"),
    "fr3_walking_rpy": (
        Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_rpy"),
        REPO / "dataset_associations/fr3_walking_rpy_associate.txt"),
    "fr3_walking_halfsphere": (
        Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_halfsphere"),
        REPO / "dataset_associations/fr3_walking_halfsphere_associate.txt"),
}


def association_rows(path: Path):
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split()
        rows.append((parts[0], parts[1]))
    return rows


def uniform_indices(count: int, samples: int = 40):
    # Deterministic endpoint-inclusive nearest-integer sampling.
    return [int(round(i * (count - 1) / (samples - 1))) for i in range(samples)]


def read_projections(path: Path, allowed_frames):
    final = {}
    with path.open(newline="") as stream:
        for row in csv.DictReader(stream):
            frame_id = int(row["frame_id"])
            if frame_id not in allowed_frames:
                continue
            key = (frame_id, int(row["map_point_id"]))
            final[key] = row  # keep the final log state for repeated update paths
    by_frame = {}
    for (frame_id, _), row in final.items():
        by_frame.setdefault(frame_id, []).append(row)
    return by_frame, final


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    annotation_root = ROOT / "annotation"
    selected = []
    selected_ids = {
        sequence: set(uniform_indices(len(association_rows(association))))
        for sequence, (_, association) in SEQUENCES.items()
    }

    # Preview uses Semantic projection geometry only; no prediction/state color is shown.
    semantic_projections = {}
    all_final = {}
    for method in ("Semantic", "Temporal"):
        for sequence in SEQUENCES:
            path = ROOT / "runs" / method / sequence / "run_01" / "mappoint_projection_raw.csv"
            by_frame, final = read_projections(path, selected_ids[sequence])
            if method == "Semantic":
                semantic_projections[sequence] = by_frame
            all_final[(method, sequence)] = final

    for sequence, (dataset, association) in SEQUENCES.items():
        rows = association_rows(association)
        indices = uniform_indices(len(rows))
        out_dir = annotation_root / sequence
        out_dir.mkdir(parents=True, exist_ok=True)
        for order, frame_id in enumerate(indices, 1):
            timestamp, rgb_relative = rows[frame_id]
            rgb_source = dataset / rgb_relative
            if not rgb_source.exists():
                raise RuntimeError(f"selected RGB missing: {rgb_source}")
            stem = f"frame_{frame_id:04d}"
            rgb_target = out_dir / f"{stem}_rgb.png"
            shutil.copy2(rgb_source, rgb_target)
            image = cv2.imread(str(rgb_source), cv2.IMREAD_COLOR)
            if image is None:
                raise RuntimeError(f"cannot read {rgb_source}")
            preview = image.copy()
            projections = semantic_projections[sequence].get(frame_id, [])
            visible = 0
            height, width = image.shape[:2]
            for row in projections:
                u, v = float(row["u"]), float(row["v"])
                x, y = int(round(u)), int(round(v))
                if 0 <= x < width and 0 <= y < height:
                    # Neutral cyan ring: no Semantic/Temporal prediction is encoded.
                    cv2.circle(preview, (x, y), 2, (255, 255, 0), 1, cv2.LINE_AA)
                    visible += 1
            cv2.imwrite(str(out_dir / f"{stem}_preview.png"), preview)
            for mask_suffix in ("_gt.png", "_ignore.png"):
                mask_path = out_dir / f"{stem}{mask_suffix}"
                if mask_path.exists():
                    existing = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
                    if existing is None or np.any(existing):
                        raise RuntimeError(f"refusing to overwrite a nonblank/manual mask: {mask_path}")
                cv2.imwrite(str(mask_path), np.zeros((height, width), np.uint8))
            selected.append({
                "sequence": sequence, "sample_order": order, "frame_id": frame_id,
                "timestamp": timestamp, "association_row": frame_id,
                "rgb_relative_path": rgb_relative, "rgb_source": str(rgb_source),
                "selection_rule": "40 endpoint-inclusive uniformly spaced association rows; nearest integer",
                "substitution": "none", "preview_projection_source": "Semantic run_01 geometry only",
                "preview_visible_mappoints": visible,
            })

    with (ROOT / "selected_frames.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(selected[0]))
        writer.writeheader(); writer.writerows(selected)

    # Export only observations belonging to the objectively selected annotation frames.
    observations = []
    exact_timestamps = {
        sequence: {frame_id: timestamp for frame_id, (timestamp, _) in enumerate(association_rows(association))}
        for sequence, (_, association) in SEQUENCES.items()
    }
    for (method, sequence), final in all_final.items():
        for (frame_id, map_point_id), row in final.items():
            if frame_id not in selected_ids[sequence]:
                continue
            # Use the exact input timestamp from the association file. The C++ raw
            # stream's timestamp is retained in each run but has default precision.
            row["timestamp"] = exact_timestamps[sequence][frame_id]
            observations.append({"method": method, "sequence": sequence, "run_id": "run_01", **row})
    observations.sort(key=lambda r: (r["sequence"], r["method"], int(r["frame_id"]), int(r["map_point_id"])))
    with (ROOT / "mappoint_observations.csv").open("w", newline="") as stream:
        fields = ["method", "sequence", "run_id", "frame_id", "timestamp", "map_point_id",
                  "u", "v", "class_id", "semantic_state", "temporal_state",
                  "temporal_score", "threshold"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader(); writer.writerows(observations)

    guideline = """# P4 MapPoint级动态状态人工标注规范

## 标注对象

- `Dynamic`：当前帧中**实际处于运动状态的人体像素区域**，在 `*_gt.png` 中标为255。
- `Static`：明确静止的背景、静态物体，以及当前帧明确静止的人体，在GT中保持0。
- `Ignore`：在 `*_ignore.png` 中标为255；其余有效区域保持0。

## Ignore规则

- 人体轮廓边界无法可靠判断；
- 严重遮挡；
- 深度或MapPoint投影明显异常；
- 仅凭当前帧无法确认人体是否真实运动；
- 投影位于人体与背景边界附近。

## 强制原则

1. 禁止将YOLO框、Semantic输出或Temporal输出作为GT。
2. 禁止直接用矩形检测框代替人体像素掩膜。
3. 预览图中的青色小圆仅表示MapPoint投影位置，不编码任何预测状态。
4. person类别不等于Dynamic；当前帧明确静止的人体不得标为Dynamic。
5. 必要时结合相邻原始RGB帧判断真实运动，但不得查看算法动态状态日志。
6. GT边界的固定2像素ignore band将在评价阶段统一生成；不得按算法结果调整。
7. 保持PNG尺寸、文件名和单通道0/255编码不变。

## 文件

- `frame_XXXX_rgb.png`：原始RGB；
- `frame_XXXX_preview.png`：仅含中性MapPoint投影的辅助图；
- `frame_XXXX_gt.png`：人工动态人体mask模板；
- `frame_XXXX_ignore.png`：人工ignore mask模板。
"""
    (ROOT / "annotation_guideline.md").write_text(guideline)


if __name__ == "__main__":
    main()
