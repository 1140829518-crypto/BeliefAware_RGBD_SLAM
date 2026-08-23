#!/usr/bin/env python3

import csv
from pathlib import Path
from collections import defaultdict
import cv2


ROOT = Path(__file__).resolve().parents[1]

GT_ROOT = (
    ROOT /
    "experiments/final_paper/04_mappoint_gt_eval/annotation_v2"
)

OBS_FILE = (
    ROOT /
    "experiments/final_paper/04_mappoint_gt_eval/mappoint_observations_v2.csv"
)

OUT_FILE = (
    ROOT /
    "experiments/final_paper/04_mappoint_gt_eval/"
    "p4_mappoint_level_metrics.csv"
)


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



# 
# method + sequence + map_point_id
#
mappoints = defaultdict(list)



with OBS_FILE.open() as f:

    reader = csv.DictReader(f)

    for row in reader:


        method = row["method"]

        sequence = row["sequence"]

        map_point_id = int(row["map_point_id"])


        gt = load_gt(
            sequence,
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


        gt_dynamic = (
            gt[v, u] > 0
        )


        if method == "Semantic":

            pred_dynamic = (
                int(row["semantic_state"]) == 1
            )

        elif method == "Temporal":

            pred_dynamic = (
                int(row["temporal_state"]) == 1
            )

        else:
            continue



        key = (
            method,
            sequence,
            map_point_id
        )


        mappoints[key].append(
            (
                gt_dynamic,
                pred_dynamic
            )
        )



results = {

    "Semantic":
        {"tp":0,"fp":0,"fn":0},

    "Temporal":
        {"tp":0,"fp":0,"fn":0}

}



for key, observations in mappoints.items():

    method = key[0]


    total = len(observations)


    gt_dynamic_count = sum(
        x[0]
        for x in observations
    )


    pred_dynamic_count = sum(
        x[1]
        for x in observations
    )


    gt_ratio = (
        gt_dynamic_count /
        total
    )


    pred_ratio = (
        pred_dynamic_count /
        total
    )


    gt_state = (
        gt_ratio >= 0.1
    )


    pred_state = (
        pred_ratio >= 0.1
    )


    if gt_state and pred_state:

        results[method]["tp"] += 1


    elif (not gt_state) and pred_state:

        results[method]["fp"] += 1


    elif gt_state and (not pred_state):

        results[method]["fn"] += 1



def calc(tp, fp, fn):

    precision = (
        tp/(tp+fp)
        if tp+fp
        else 0
    )


    recall = (
        tp/(tp+fn)
        if tp+fn
        else 0
    )


    f1 = (
        2*precision*recall/(precision+recall)
        if precision+recall
        else 0
    )


    return precision, recall, f1



with OUT_FILE.open(
    "w",
    newline=""
) as f:

    writer = csv.writer(f)

    writer.writerow(
        [
            "method",
            "TP",
            "FP",
            "FN",
            "Precision",
            "Recall",
            "F1"
        ]
    )


    for method, r in results.items():

        p,rec,f1 = calc(
            r["tp"],
            r["fp"],
            r["fn"]
        )


        writer.writerow(
            [
                method,
                r["tp"],
                r["fp"],
                r["fn"],
                p,
                rec,
                f1
            ]
        )


        print(
            method,
            "TP=",r["tp"],
            "FP=",r["fp"],
            "FN=",r["fn"],
            "Precision=",round(p,4),
            "Recall=",round(rec,4),
            "F1=",round(f1,4)
        )



print("saved:", OUT_FILE)
