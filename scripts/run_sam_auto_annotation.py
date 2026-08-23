import os
import cv2
import torch
import numpy as np
from pathlib import Path

from segment_anything import sam_model_registry, SamAutomaticMaskGenerator


# 路径
ROOT = Path("experiments/final_paper/04_mappoint_gt_eval")

INPUT_DIR = ROOT / "annotation_v2"
OUTPUT_DIR = ROOT / "sam_candidate"

CHECKPOINT = "segment-anything/sam_vit_b_01ec64.pth"


OUTPUT_DIR.mkdir(exist_ok=True)


# SAM加载
device = "cuda" if torch.cuda.is_available() else "cpu"

print("device:", device)

sam = sam_model_registry["vit_b"](
    checkpoint=CHECKPOINT
)

sam.to(device)


mask_generator = SamAutomaticMaskGenerator(
    sam,
    points_per_side=32,
    pred_iou_thresh=0.86,
    stability_score_thresh=0.92,
)


# 找RGB
images = list(INPUT_DIR.glob("*/*_rgb.png"))

print("images:", len(images))


for idx, img_path in enumerate(images):

    print(
        f"[{idx+1}/{len(images)}]",
        img_path.name
    )

    img = cv2.imread(str(img_path))

    if img is None:
        continue

    img_rgb = cv2.cvtColor(
        img,
        cv2.COLOR_BGR2RGB
    )


    masks = mask_generator.generate(img_rgb)


    # 合并所有SAM候选
    mask_all = np.zeros(
        img.shape[:2],
        dtype=np.uint8
    )


    for m in masks:
        seg = m["segmentation"]

        # 面积过滤
        area = np.sum(seg)

        if area > 500:
            mask_all[seg] = 255


    seq = img_path.parent.name

    out_dir = OUTPUT_DIR / seq
    out_dir.mkdir(
        exist_ok=True
    )


    cv2.imwrite(
        str(
            out_dir /
            img_path.name.replace(
                "_rgb.png",
                "_sam_candidate.png"
            )
        ),
        mask_all
    )


print("SAM finished")
