#!/usr/bin/env python3
"""Audit P4 projection duplicates and prepare objective v2 manual annotation assets."""

from __future__ import annotations

import csv
from collections import Counter
import gc
from pathlib import Path
import shutil

import cv2
import numpy as np


REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "experiments/final_paper/04_mappoint_gt_eval"
METHODS = ("Semantic", "Temporal")
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
THRESHOLDS = (20, 10, 5, 1)


def association_rows(path: Path):
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fields = line.split()
        rows.append((fields[0], fields[1]))
    return rows


def audit_raw(path: Path):
    """Return raw/unique statistics and per-frame unique MapPoint counts."""
    seen = set()
    per_frame = Counter()
    raw_rows = 0
    duplicate_rows = 0
    with path.open(newline="") as stream:
        for row in csv.DictReader(stream):
            raw_rows += 1
            frame_id = int(row["frame_id"])
            map_point_id = int(row["map_point_id"])
            key = (frame_id << 40) | map_point_id
            if key in seen:
                duplicate_rows += 1
            else:
                seen.add(key)
                per_frame[frame_id] += 1
    return {
        "raw_rows": raw_rows,
        "unique_observations": len(seen),
        "duplicate_rows": duplicate_rows,
        "duplicate_rate": duplicate_rows / raw_rows if raw_rows else 0.0,
        "matcher_stage_available": 0,
        "matcher_stage_conclusion": "unknown: current log has no matcher-stage field",
    }, per_frame


def uniform_candidates(candidates, samples=40):
    if len(candidates) < samples:
        raise RuntimeError(f"only {len(candidates)} eligible frames for {samples} samples")
    return [candidates[int(round(i * (len(candidates) - 1) / (samples - 1)))]
            for i in range(samples)]


def read_selected_semantic_projections(sequence, selected_frames):
    path = ROOT / "runs/Semantic" / sequence / "run_01/mappoint_projection_raw.csv"
    final = {}
    selected = set(selected_frames)
    with path.open(newline="") as stream:
        for row in csv.DictReader(stream):
            frame_id = int(row["frame_id"])
            if frame_id in selected:
                final[(frame_id, int(row["map_point_id"]))] = row
    by_frame = {}
    for (frame_id, _), row in final.items():
        by_frame.setdefault(frame_id, []).append(row)
    return by_frame


def make_context(dataset, rows, center):
    images = []
    for frame_id in range(center - 2, center + 3):
        if frame_id < 0 or frame_id >= len(rows):
            raise RuntimeError(f"context frame outside association range: center={center}")
        image = cv2.imread(str(dataset / rows[frame_id][1]), cv2.IMREAD_COLOR)
        if image is None:
            raise RuntimeError(f"cannot read context image: {dataset / rows[frame_id][1]}")
        images.append(image)
    return cv2.hconcat(images)


def main():
    counts = {}
    duplicate_audit = []
    association_cache = {sequence: association_rows(association)
                         for sequence, (_, association) in SEQUENCES.items()}

    for method in METHODS:
        for sequence in SEQUENCES:
            path = ROOT / "runs" / method / sequence / "run_01/mappoint_projection_raw.csv"
            audit, per_frame = audit_raw(path)
            counts[(method, sequence)] = per_frame
            duplicate_audit.append({"method": method, "sequence": sequence,
                                    "source": str(path), **audit})
            gc.collect()

    with (ROOT / "projection_duplicate_audit.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(duplicate_audit[0]))
        writer.writeheader(); writer.writerows(duplicate_audit)

    eligibility = []
    candidate_counts = {sequence: {threshold: 0 for threshold in THRESHOLDS}
                        for sequence in SEQUENCES}
    candidates = {sequence: {threshold: [] for threshold in THRESHOLDS}
                  for sequence in SEQUENCES}
    for sequence, rows in association_cache.items():
        for frame_id, (timestamp, rgb_path) in enumerate(rows):
            semantic_count = counts[("Semantic", sequence)].get(frame_id, 0)
            temporal_count = counts[("Temporal", sequence)].get(frame_id, 0)
            context_available = int(2 <= frame_id <= len(rows) - 3)
            row = {"sequence": sequence, "frame_id": frame_id, "timestamp": timestamp,
                   "rgb_relative_path": rgb_path,
                   "semantic_unique_projections": semantic_count,
                   "temporal_unique_projections": temporal_count,
                   "context_available": context_available}
            for threshold in THRESHOLDS:
                eligible = int(context_available and semantic_count >= threshold
                               and temporal_count >= threshold)
                row[f"both_ge_{threshold}"] = eligible
                if eligible:
                    candidate_counts[sequence][threshold] += 1
                    candidates[sequence][threshold].append(frame_id)
            eligibility.append(row)

    with (ROOT / "frame_eligibility_audit.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(eligibility[0]))
        writer.writeheader(); writer.writerows(eligibility)

    minimum = next((threshold for threshold in THRESHOLDS
                    if all(candidate_counts[sequence][threshold] >= 40
                           for sequence in SEQUENCES)), None)
    if minimum is None:
        raise RuntimeError("no common projection threshold provides 40 frames per sequence")

    policy_lines = [
        "# P4 V2人工标注抽帧策略", "",
        "抽帧只使用association帧序和去重后的有效MapPoint投影数量，不读取Semantic/Temporal预测状态、dynamic score、threshold、suppression、GT或图像内容。", "",
        f"固定门槛：`minimum_valid_projections = {minimum}`。", "",
        "候选帧必须在Semantic和Temporal两个独立运行中均具有不少于该门槛的唯一 `(frame_id,map_point_id)` 投影，并且association中存在完整的前2、前1、当前、后1、后2帧上下文。该上下文边界条件不读取算法预测或图像内容。", "",
        "在每个序列按frame_id排序后的候选集合中，采用端点包含的等间隔索引抽取40帧：", "",
        "`candidate_index(i) = round(i * (K - 1) / 39), i=0,...,39`。", "",
        "同一帧内同一MapPoint的多次matcher日志只计为一个评价观测；保留日志顺序中的最终记录用于后续评价。", "",
        "## 候选帧数量", "",
        "| Sequence | >=20 | >=10 | >=5 | >=1 |", "|---|---:|---:|---:|---:|",
    ]
    for sequence in SEQUENCES:
        policy_lines.append("| " + sequence + " | " + " | ".join(
            str(candidate_counts[sequence][threshold]) for threshold in THRESHOLDS) + " |")
    policy_lines += ["", "现有原始日志没有matcher阶段字段，因此不能可靠区分重复记录来自哪个ORBmatcher调用阶段。"]
    (ROOT / "annotation_sampling_policy.md").write_text("\n".join(policy_lines) + "\n")

    selected_rows = []
    annotation_root = ROOT / "annotation_v2"
    for sequence, (dataset, _) in SEQUENCES.items():
        rows = association_cache[sequence]
        selected = uniform_candidates(candidates[sequence][minimum])
        projections = read_selected_semantic_projections(sequence, selected)
        output = annotation_root / sequence
        output.mkdir(parents=True, exist_ok=True)
        for order, frame_id in enumerate(selected, 1):
            timestamp, relative = rows[frame_id]
            source = dataset / relative
            image = cv2.imread(str(source), cv2.IMREAD_COLOR)
            if image is None:
                raise RuntimeError(f"cannot read selected image: {source}")
            stem = f"frame_{frame_id:04d}"
            shutil.copy2(source, output / f"{stem}_rgb.png")
            preview = image.copy()
            visible = 0
            height, width = image.shape[:2]
            for row in projections.get(frame_id, []):
                x, y = int(round(float(row["u"]))), int(round(float(row["v"])))
                if 0 <= x < width and 0 <= y < height:
                    cv2.circle(preview, (x, y), 2, (255, 255, 0), 1, cv2.LINE_AA)
                    visible += 1
            cv2.imwrite(str(output / f"{stem}_preview.png"), preview)
            cv2.imwrite(str(output / f"{stem}_context.png"), make_context(dataset, rows, frame_id))
            for suffix in ("_gt.png", "_ignore.png"):
                path = output / f"{stem}{suffix}"
                if path.exists():
                    old = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
                    if old is None or np.any(old):
                        raise RuntimeError(f"refusing to overwrite nonblank/manual mask: {path}")
                cv2.imwrite(str(path), np.zeros((height, width), np.uint8))
            selected_rows.append({
                "sequence": sequence, "sample_order": order, "frame_id": frame_id,
                "timestamp": timestamp, "association_row": frame_id,
                "rgb_relative_path": relative, "rgb_source": str(source),
                "minimum_valid_projections": minimum,
                "semantic_unique_projections": counts[("Semantic", sequence)].get(frame_id, 0),
                "temporal_unique_projections": counts[("Temporal", sequence)].get(frame_id, 0),
                "selection_rule": "uniform over eligible frames; no prediction/score/GT/image-content selection",
                "preview_projection_source": "Semantic run_01 geometry only; neutral markers",
                "preview_visible_mappoints": visible,
                "context_frame_ids": f"{frame_id-2};{frame_id-1};{frame_id};{frame_id+1};{frame_id+2}",
            })

    with (ROOT / "selected_frames_v2.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(selected_rows[0]))
        writer.writeheader(); writer.writerows(selected_rows)

    guideline = """# P4 MapPoint级动态状态人工标注规范（V2）

## 必须结合时间上下文

人工判断中心帧中的人体是否真实运动时，必须同时查看对应 `*_context.png`。context从左至右仅包含前2帧、前1帧、当前帧、后1帧和后2帧，不含任何算法状态。

## 标签定义

- `Dynamic`：中心帧中实际处于运动状态的人体像素，在 `*_gt.png` 标为255。
- `Static`：明确静止背景，或结合相邻帧可以确认处于静止状态的目标；GT保持0。
- `Ignore`：无法从时间上下文可靠判断运动状态、严重遮挡、人体边缘、投影或深度异常区域，在 `*_ignore.png` 标为255。

## 禁止事项

1. 禁止使用YOLO检测框、Semantic/Temporal输出、score、state、threshold或suppression生成GT。
2. 禁止直接使用矩形检测框代替像素级人体mask。
3. preview中的青色小圆仅表示MapPoint投影，不编码预测状态。
4. person类别不自动等于Dynamic。
5. 不得改变PNG尺寸、文件名或0/255编码。

后续评价将统一添加固定2像素边界ignore band；人工标注不得根据算法结果调整边界规则。
"""
    (ROOT / "annotation_guideline.md").write_text(guideline)

    print(f"minimum_valid_projections={minimum}")
    for sequence in SEQUENCES:
        print(sequence, candidate_counts[sequence])


if __name__ == "__main__":
    main()
