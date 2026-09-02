#!/usr/bin/env python3
"""Summarize decay-v2 runs without selecting, replacing, or hiding failures."""
from __future__ import annotations
import argparse, csv, json, math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import cv2, numpy as np

from paa_prl_common import REPO, association_path, sample_mean_std, trajectory_coverage
from summarize_paa_prl_results import switching_frequency, runtime_breakdown, runtime_values

GT_ROOT=REPO/"experiments/final_paper/04_appendix_logs/annotation/annotation_v2"
PROGRESS=REPO/"experiments/final_paper/04_appendix_logs/annotation/annotation_progress.csv"
SELECTED=REPO/"experiments/final_paper/04_appendix_logs/annotation/selected_frames_v2.csv"

def num(x):
    try: v=float(x); return v if math.isfinite(v) else math.nan
    except (TypeError,ValueError): return math.nan
def div(a,b): return a/b if b else math.nan
def stats(tp,fp,tn,fn):
    p,r,s=div(tp,tp+fp),div(tp,tp+fn),div(tn,tn+fp)
    return {"Precision":p,"Recall":r,"F1":div(2*tp,2*tp+fp+fn),"Balanced_Accuracy":(r+s)/2,
            "FPR":div(fp,fp+tn),"FNR":div(fn,fn+tp)}
def write_csv(path,rows):
    if not rows: path.write_text(""); return
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader()
        for row in rows: w.writerow({k:("" if isinstance(v,float) and not math.isfinite(v) else f"{v:.9f}" if isinstance(v,float) else v) for k,v in row.items()})
def boundary(gt):
    b=(gt==255).astype(np.uint8); k=np.ones((5,5),np.uint8)
    return cv2.dilate(b,k)!=cv2.erode(b,k)
def validate_frame_alignment():
    selected={int(r["frame_id"]):float(r["timestamp"]) for r in csv.DictReader(SELECTED.open(encoding="utf-8-sig"))
              if r["sequence"]=="fr3_walking_xyz"}
    association=[]
    for raw in association_path("fr3_walking_xyz").read_text().splitlines():
        if raw.strip() and not raw.lstrip().startswith("#"): association.append(float(raw.split()[0]))
    mismatches={frame:(stamp, association[frame] if frame<len(association) else None) for frame,stamp in selected.items()
                if frame>=len(association) or abs(stamp-association[frame])>1e-6}
    if len(selected)!=40 or mismatches:
        raise RuntimeError(f"annotation frame/association alignment failed: frames={len(selected)} mismatches={mismatches}")
    return len(selected)
def correctness(run):
    path=run/"mappoint_projection_raw.csv"
    if not path.exists(): return None
    frames=set()
    with PROGRESS.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r["sequence"]=="fr3_walking_xyz" and int(r["completed"])==1: frames.add(int(r["frame_id"]))
    masks={}
    for frame in frames:
        g=cv2.imread(str(GT_ROOT/"fr3_walking_xyz"/f"frame_{frame:04d}_gt.png"),0)
        i=cv2.imread(str(GT_ROOT/"fr3_walking_xyz"/f"frame_{frame:04d}_ignore.png"),0)
        if g is None or i is None: return None
        masks[frame]=(g,i,boundary(g))
    dedup={}; raw=0
    with path.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            frame=int(r["frame_id"])
            if frame in frames: raw+=1; dedup[(frame,int(r["map_point_id"]))]=r
    tp=fp=tn=fn=ignored=band=oob=0; used=set()
    for (frame,_),r in dedup.items():
        g,i,b=masks[frame]; x,y=int(round(float(r["u"]))),int(round(float(r["v"])))
        if x<0 or y<0 or x>=g.shape[1] or y>=g.shape[0]: oob+=1; continue
        if i[y,x]==255: ignored+=1; continue
        if b[y,x]: band+=1; continue
        truth=g[y,x]==255; pred=int(r["temporal_state"])!=0; used.add(frame)
        if truth and pred: tp+=1
        elif pred: fp+=1
        elif truth: fn+=1
        else: tn+=1
    return {"correctness_available":1,"correctness_raw":raw,"correctness_dedup":len(dedup),"correctness_ignore":ignored,
            "correctness_boundary_ignore":band,"correctness_oob":oob,"correctness_evaluated":tp+fp+tn+fn,
            "correctness_frames":len(used),"TP":tp,"FP":fp,"TN":tn,"FN":fn,**stats(tp,fp,tn,fn)}
def read_run(run):
    m=json.loads((run/"decay_metadata.json").read_text()); st=json.loads((run/"decay_status.json").read_text())
    total,poses,gaps,tsr,pmr=trajectory_coverage(association_path(m["sequence"]),run/"CameraTrajectory.txt")
    metrics=json.loads((run/"eval/metrics.json").read_text()) if (run/"eval/metrics.json").exists() else {}
    legal=bool(metrics and poses>=2); comp=runtime_breakdown(run/"runtime_summary.csv"); rt=runtime_values(run/"runtime.txt")
    _,_,sf=switching_frequency(run/"mappoint_evidence_raw.csv")
    row={"setting":m["setting"],"forgetting_rate_factor":m["forgetting_rate_factor"],"run_id":m["run_id"],
         "ordinary_decay_requested":m["ordinary_decay_requested"],"ordinary_decay_effective":m["ordinary_decay_effective"],
         "person_decay_requested":m["person_decay_requested"],"person_decay_effective":m["person_decay_effective"],
         "clamp_applied":int(m["clamp_applied"]),"process_status":st["status"],"exit_code":st["return_code"],
         "wall_time_seconds":num(st.get("wall_time_seconds")),"association_frames":total,"valid_poses":poses,"TSR":tsr,"PMR":pmr,
         "tracking_gaps":gaps,"tracking_incomplete":int(st["status"]!="success" or tsr<1.0),
         "tracking_failure":int(st["status"]!="success" or tsr<.9),
         "coverage_warning":int(st["status"]!="success" or tsr<1.0 or gaps>0),
         "ATE_RMSE":num(metrics.get("ate",{}).get("rmse")) if legal else math.nan,
         "RPE_translation":num(metrics.get("rpe_trans",{}).get("rmse")) if legal else math.nan,
         "RPE_rotation":num(metrics.get("rpe_rot_deg",{}).get("rmse")) if legal else math.nan,"SF":sf,
         "Tracking_FPS":num(comp.get("tracking_total_fps_steady",rt.get("fps"))),
         "E2E_FPS":num(comp.get("end_to_end_frame_fps_steady")),"run_dir":str(run)}
    c=correctness(run); row.update(c or {"correctness_available":0})
    return row
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",type=Path,default=REPO/"results/paa_prl_limitation2/sensitivity_decay_v2"); a=ap.parse_args(); root=a.root.resolve()
    aligned_frames=validate_frame_alignment()
    rows=[read_run(p.parent) for p in sorted((root/"settings").glob("*/run_*/decay_metadata.json"))]
    if len(rows)!=25: raise RuntimeError(f"expected 25 fixed runs, found {len(rows)}")
    write_csv(root/"decay_all_runs.csv",rows)
    groups=defaultdict(list)
    for r in rows: groups[r["setting"]].append(r)
    order=["fast","moderately_fast","default","slow","very_slow"]; summaries=[]; csum=[]
    metrics=["ATE_RMSE","RPE_translation","RPE_rotation","TSR","PMR","tracking_gaps","SF","Tracking_FPS","E2E_FPS"]
    for setting in order:
        g=groups[setting]; out={k:g[0][k] for k in ("setting","forgetting_rate_factor","ordinary_decay_effective","person_decay_effective")}
        out.update({"runs":len(g),"success_count":sum(r["process_status"]=="success" for r in g),
                    "incomplete_count":sum(r["tracking_incomplete"] for r in g),
                    "coverage_warning_count":sum(r["coverage_warning"] for r in g),
                    "failure_count":sum(r["tracking_failure"] for r in g)})
        for key in metrics:
            mean,std=sample_mean_std(num(r[key]) for r in g); out[key+"_mean"],out[key+"_std"]=mean,std
        summaries.append(out)
        if all(r.get("correctness_available") for r in g):
            co={**{k:out[k] for k in ("setting","forgetting_rate_factor","ordinary_decay_effective","person_decay_effective")},"runs":len(g)}
            for key in ("Precision","Recall","F1","Balanced_Accuracy","FPR","FNR"):
                co[key+"_mean"],co[key+"_std"]=sample_mean_std(r[key] for r in g)
            co["evaluated_observations_total"]=sum(r["correctness_evaluated"] for r in g); csum.append(co)
    write_csv(root/"decay_sequence_summary.csv",summaries); write_csv(root/"decay_sensitivity_summary.csv",summaries)
    if csum: write_csv(root/"decay_correctness_summary.csv",csum)
    audit=["# Decay sensitivity v2 audit","",f"Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}",
           f"- Fixed runs found: {len(rows)}/25",f"- Failed runs retained: {sum(r['tracking_failure'] for r in rows)}",
           f"- Clamp applied rows: {sum(r['clamp_applied'] for r in rows)}",f"- Unique ordinary effective values: {len(set(r['ordinary_decay_effective'] for r in rows))}",
           f"- Unique person effective values: {len(set(r['person_decay_effective'] for r in rows))}",
           f"- Annotation alignment: PASS ({aligned_frames} frame IDs map to association timestamps within 1e-6 s)",
           "- Projection timestamp caveat: the C++ CSV field is low-precision; alignment uses frame_id and the high-precision association file.",
           f"- Sampled correctness: {'AVAILABLE (independent annotation_v2, 2-px boundary ignored)' if csum else 'NOT AVAILABLE'}",
           "- No run was selected, replaced, deleted, or used to alter the frozen main defaults."]
    (root/"decay_audit.md").write_text("\n".join(audit)+"\n")
    protocol_path=root/"decay_protocol.json"; protocol=json.loads(protocol_path.read_text())
    protocol["completed_at"]=datetime.now().astimezone().isoformat(timespec="seconds")
    protocol["correctness_evaluation"]={"available":bool(csum),"gt_root":str(GT_ROOT),"progress":str(PROGRESS),
        "selected_frames":str(SELECTED),"annotated_frames":aligned_frames,"unit":"MapPoint projection observation",
        "deduplication":"last row for each (run, frame_id, map_point_id)","boundary_ignore":"5x5 dilation minus erosion (2-pixel Chebyshev band)",
        "alignment":"frame_id -> association row timestamp -> selected annotation timestamp; tolerance 1e-6 s"}
    protocol_path.write_text(json.dumps(protocol,indent=2)+"\n")
    print(f"summarized {len(rows)} runs; correctness={'available' if csum else 'not available'}")
if __name__=="__main__": main()
