#!/usr/bin/env python3

import csv
from pathlib import Path
from collections import defaultdict
import cv2


ROOT = Path(__file__).resolve().parents[1]

GT_ROOT = ROOT / "experiments/final_paper/04_mappoint_gt_eval/annotation_v2"

OBS_FILE = ROOT / "experiments/final_paper/04_mappoint_gt_eval/mappoint_observations_v2.csv"


gt_cache = {}


def load_gt(sequence, frame_id):

    key = (sequence, frame_id)

    if key in gt_cache:
        return gt_cache[key]

    path = (
        GT_ROOT /
        sequence /
        f"frame_{frame_id:04d}_gt.png"
    )

    if not path.exists():
        gt_cache[key] = None
        return None

    img = cv2.imread(
        str(path),
        cv2.IMREAD_GRAYSCALE
    )

    gt_cache[key] = img

    return img



# 保存每个MapPoint所有观测
records = defaultdict(list)


with OBS_FILE.open() as f:

    reader = csv.DictReader(f)

    for row in reader:

        key = (
            row["method"],
            row["sequence"],
            int(row["map_point_id"])
        )


        gt = load_gt(
            row["sequence"],
            int(row["frame_id"])
        )

        if gt is None:
            continue


        u = int(round(float(row["u"])))
        v = int(round(float(row["v"])))


        if (
            u < 0 or
            v < 0 or
            u >= gt.shape[1] or
            v >= gt.shape[0]
        ):
            continue


        gt_dynamic = gt[v,u] > 0


        if row["method"] == "Semantic":

            pred_dynamic = (
                int(row["semantic_state"]) == 1
            )

        else:

            pred_dynamic = (
                int(row["temporal_state"]) == 1
            )


        records[key].append(
            (
                gt_dynamic,
                pred_dynamic
            )
        )



def calc(tp,fp,fn):

    p = tp/(tp+fp) if tp+fp else 0

    r = tp/(tp+fn) if tp+fn else 0

    f1 = (
        2*p*r/(p+r)
        if p+r
        else 0
    )

    return p,r,f1



ratios = [
    0.1,
    0.2,
    0.3,
    0.4,
    0.5
]


for ratio in ratios:


    result = {

        "Semantic":[0,0,0],
        "Temporal":[0,0,0]

    }


    for key, obs in records.items():

        method = key[0]


        total = len(obs)


        gt_ratio = sum(
            x[0]
            for x in obs
        ) / total


        pred_ratio = sum(
            x[1]
            for x in obs
        ) / total



        gt_state = gt_ratio >= ratio

        pred_state = pred_ratio >= ratio



        if gt_state and pred_state:

            result[method][0]+=1


        elif (not gt_state) and pred_state:

            result[method][1]+=1


        elif gt_state and (not pred_state):

            result[method][2]+=1



    print("\nratio =",ratio)


    for method,v in result.items():

        p,r,f1 = calc(
            v[0],
            v[1],
            v[2]
        )

        print(
            method,
            "TP=",v[0],
            "FP=",v[1],
            "FN=",v[2],
            "P=",round(p,4),
            "R=",round(r,4),
            "F1=",round(f1,4)
        )
