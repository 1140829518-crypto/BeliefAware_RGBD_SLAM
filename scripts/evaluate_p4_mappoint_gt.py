
#!/usr/bin/env python3

import csv
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]

GT_ROOT = ROOT / "experiments/final_paper/04_mappoint_gt_eval/annotation_v2"

OBS_FILE = ROOT / "experiments/final_paper/04_mappoint_gt_eval/mappoint_observations_v2.csv"

OUT_FILE = ROOT / "experiments/final_paper/04_mappoint_gt_eval/p4_metrics.csv"


def calc_metrics(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall)
        else 0.0
    )
    return precision, recall, f1


gt_cache = {}


def load_gt(sequence, frame_id):

    key = (sequence, frame_id)

    if key in gt_cache:
        return gt_cache[key]

    path = GT_ROOT / sequence / f"frame_{frame_id:04d}_gt.png"

    if not path.exists():
        gt_cache[key] = None
        return None

    mask = cv2.imread(
        str(path),
        cv2.IMREAD_GRAYSCALE
    )

    gt_cache[key] = mask

    return mask


results = {
    "Semantic": {
        "tp": 0,
        "fp": 0,
        "fn": 0
    },
    "Temporal": {
        "tp": 0,
        "fp": 0,
        "fn": 0
    }
}


total = 0
missing_gt = 0


with OBS_FILE.open() as f:

    reader = csv.DictReader(f)

    for row in reader:

        method = row["method"]

        if method not in results:
            continue


        sequence = row["sequence"]
        frame_id = int(row["frame_id"])

        u = int(round(float(row["u"])))
        v = int(round(float(row["v"])))


        gt = load_gt(
            sequence,
            frame_id
        )


        if gt is None:
            missing_gt += 1
            continue


        h, w = gt.shape

        if u < 0 or u >= w or v < 0 or v >= h:
            continue

        # ignore边界
        ignore_path = (
            GT_ROOT
            / sequence
            / f"frame_{frame_id:04d}_ignore.png"
        )

        ignore = cv2.imread(
            str(ignore_path),
            cv2.IMREAD_GRAYSCALE
        )

        if ignore is not None and ignore[v, u] > 0:
            continue

        # 人工GT
        gt_dynamic = gt[v, u] > 0


        # ===== 预测判断 =====

        if method == "Semantic":

            # Semantic baseline
            pred_dynamic = (
                int(row["semantic_state"]) == 1
            )


        elif method == "Temporal":

            # Temporal consistency(Ours)
            # 使用连续动态概率 + 自适应阈值
            pred_dynamic = (
                float(row["temporal_score"])
                >=
                float(row["threshold"])
            )


        # ===== 混淆矩阵 =====

        if gt_dynamic and pred_dynamic:
            results[method]["tp"] += 1

        elif (not gt_dynamic) and pred_dynamic:
            results[method]["fp"] += 1

        elif gt_dynamic and (not pred_dynamic):
            results[method]["fn"] += 1


        total += 1



output = []


for method, m in results.items():

    p, r, f1 = calc_metrics(
        m["tp"],
        m["fp"],
        m["fn"]
    )

    output.append({
        "method": method,
        "TP": m["tp"],
        "FP": m["fp"],
        "FN": m["fn"],
        "Precision": p,
        "Recall": r,
        "F1": f1
    })


with OUT_FILE.open(
    "w",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "method",
            "TP",
            "FP",
            "FN",
            "Precision",
            "Recall",
            "F1"
        ]
    )

    writer.writeheader()
    writer.writerows(output)



print("Evaluation finished")
print("total observations:", total)
print("missing GT:", missing_gt)

for r in output:
    print(
        r["method"],
        "TP=", r["TP"],
        "FP=", r["FP"],
        "FN=", r["FN"],
        "Precision=", round(r["Precision"],4),
        "Recall=", round(r["Recall"],4),
        "F1=", round(r["F1"],4)
    )

print("saved:", OUT_FILE)
