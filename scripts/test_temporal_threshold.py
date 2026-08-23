import pandas as pd
import cv2
from pathlib import Path


ROOT=Path("experiments/final_paper/04_mappoint_gt_eval")

GT_ROOT=ROOT/"annotation_v2"

CSV=ROOT/"mappoint_observations_v2.csv"


df=pd.read_csv(CSV)

df=df[df.method=="Temporal"]


def load_gt(seq,frame):

    p=GT_ROOT/seq/f"frame_{frame:04d}_gt.png"

    if not p.exists():
        return None

    return cv2.imread(
        str(p),
        0
    )


for th in [1,2,3,5,10]:

    TP=FP=FN=0

    for _,r in df.iterrows():

        gt=load_gt(
            r.sequence,
            int(r.frame_id)
        )

        if gt is None:
            continue

        u=int(round(r.u))
        v=int(round(r.v))

        if v>=gt.shape[0] or u>=gt.shape[1]:
            continue


        gt_dynamic=gt[v,u]>0


        pred=float(r.temporal_score)>=th


        if gt_dynamic and pred:
            TP+=1
        elif (not gt_dynamic) and pred:
            FP+=1
        elif gt_dynamic and (not pred):
            FN+=1


    P=TP/(TP+FP) if TP+FP else 0
    R=TP/(TP+FN) if TP+FN else 0
    F1=2*P*R/(P+R) if P+R else 0


    print(
        "threshold",
        th,
        "TP",
        TP,
        "FP",
        FP,
        "FN",
        FN,
        "P",
        round(P,4),
        "R",
        round(R,4),
        "F1",
        round(F1,4)
    )
