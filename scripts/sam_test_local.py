import cv2
import torch
import numpy as np
from pathlib import Path
import time

from segment_anything import sam_model_registry, SamAutomaticMaskGenerator


ROOT = Path("experiments/final_paper/04_mappoint_gt_eval")

INPUT = ROOT / "annotation_v2"
OUTPUT = ROOT / "sam_test_candidate"

CHECKPOINT = "segment-anything/sam_vit_b_01ec64.pth"


OUTPUT.mkdir(exist_ok=True)


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
    stability_score_thresh=0.92
)


# 找5张没有人工GT的RGB
imgs=[]

for p in INPUT.glob("*/*_rgb.png"):

    gt=p.parent / p.name.replace("_rgb.png","_gt.png")

    if gt.exists():
        gt_img=cv2.imread(str(gt),0)

        # 已经有人工作业，跳过
        if np.count_nonzero(gt_img)>0:
            continue

    imgs.append(p)


imgs=imgs[:5]


print("test images:")
for x in imgs:
    print(x)


for img_path in imgs:

    print("\nprocessing:",img_path.name)

    t=time.time()

    img=cv2.imread(str(img_path))

    rgb=cv2.cvtColor(
        img,
        cv2.COLOR_BGR2RGB
    )


    masks=mask_generator.generate(rgb)


    final=np.zeros(
        img.shape[:2],
        np.uint8
    )


    count=0

    for m in masks:

        area=np.sum(m["segmentation"])

        # 过滤太小区域
        if area>1000:
            final[m["segmentation"]]=255
            count+=1


    seq=img_path.parent.name

    out=OUTPUT/seq

    out.mkdir(
        exist_ok=True
    )


    cv2.imwrite(
        str(out/(img_path.stem+"_sam.png")),
        final
    )


    overlay=img.copy()

    overlay[final>0]=(0,255,0)


    cv2.imwrite(
        str(out/(img_path.stem+"_preview.png")),
        overlay
    )


    print(
        "objects:",
        count,
        "pixels:",
        np.count_nonzero(final),
        "time:",
        time.time()-t
    )


print("\nSAM test finished")
