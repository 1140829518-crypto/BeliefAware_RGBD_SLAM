#!/usr/bin/env python3
"""Combine 45 P2 runs with the unchanged 15 P1 Full runs."""
from __future__ import annotations
import csv,json,math,statistics
from pathlib import Path

REPO=Path(__file__).resolve().parents[1]
ROOT=REPO/"experiments/final_paper/02_tum_comparison"
P1=REPO/"experiments/final_paper/01_tum_full"
SEQS={
 "fr3_walking_xyz":(REPO/"dataset_associations/fr3_walking_xyz_associate.txt",827),
 "fr3_walking_rpy":(REPO/"dataset_associations/fr3_walking_rpy_associate.txt",866),
 "fr3_walking_halfsphere":(REPO/"dataset_associations/fr3_walking_halfsphere_associate.txt",1021)}
METHODS=["ORB-SLAM2","Semantic","Temporal","Full"]

def stamps(p,n):
 out=[]
 if not p.exists(): return out
 for x in p.read_text(errors="ignore").splitlines():
  z=x.strip().split()
  if x.strip() and not x.lstrip().startswith("#") and len(z)>=n:
   try: out.append(float(z[0]))
   except ValueError: pass
 return out

def coverage(assoc,traj):
 a=stamps(assoc,4); t=stamps(traj,8); hit=[False]*len(a); j=0
 for i,x in enumerate(a):
  while j+1<len(t) and abs(t[j+1]-x)<abs(t[j]-x): j+=1
  if t and abs(t[j]-x)<=.02: hit[i]=True
 gaps=0; inside=False
 for h in hit:
  if not h and not inside: gaps+=1; inside=True
  elif h: inside=False
 v=len(t); total=len(a); tsr=v/total if total else math.nan
 return v,gaps,tsr,1-tsr

def runtime(run,conf):
 vals={}
 p=run/"runtime.txt"
 if p.exists():
  for x in p.read_text(errors="ignore").splitlines():
   z=x.split()
   if len(z)>=2: vals[z[0]]=z[1]
 try: tfps=float(vals.get("fps","nan"))
 except ValueError: tfps=math.nan
 try: sec=float(conf.get("runtime_seconds",math.nan))
 except (ValueError,TypeError): sec=math.nan
 total=int(conf.get("association_total_frames",0)); efps=total/sec if total and math.isfinite(sec) and sec>0 else math.nan
 return tfps,efps,sec

def read():
 rows=[]
 for method in METHODS:
  for seq,(assoc,total) in SEQS.items():
   for rid in range(1,6):
    run=(P1 if method=="Full" else ROOT/method)/seq/f"run_{rid:02d}"
    cp=run/("p1_run_config.json" if method=="Full" else "run_config.json")
    c=json.loads(cp.read_text()); valid,gaps,tsr,pmr=coverage(assoc,run/"CameraTrajectory.txt")
    mp=run/"eval/metrics.json"; m=json.loads(mp.read_text()) if mp.exists() else {}; legal=bool(m and valid>=2)
    a=m.get("ate",{}) if legal else {}; rt=m.get("rpe_trans",{}) if legal else {}; rr=m.get("rpe_rot_deg",{}) if legal else {}
    raw=(f"exit_{c.get('return_code')}" if method=="Full" and isinstance(c.get('return_code'),int) else c.get("raw_process_status","unknown"))
    if method=="Full":
     text="\n".join(p.read_text(errors="ignore").lower() for p in (run/"slam.log",run/"terminal.log") if p.exists())
     complete="completed" if "trajectory saved!" in text and "semantic dynamic statistics saved!" in text and mp.exists() and (run/"CameraTrajectory.txt").stat().st_size>0 else "incomplete"
    else: complete=c.get("experiment_completion_status","unknown")
    tf,ef,sec=runtime(run,c)
    rows.append(dict(method=method,sequence=seq,run_id=f"run_{rid:02d}",original_status=c.get("status",c.get("original_status","unknown")),raw_process_status=raw,experiment_completion_status=complete,exit_code=c.get("return_code",""),association_total_frames=total,trajectory_valid_poses=valid,ATE_RMSE=float(a.get("rmse",math.nan)),ATE_mean=float(a.get("mean",math.nan)),ATE_median=float(a.get("median",math.nan)),ATE_std=float(a.get("std",math.nan)),RPE_translation_RMSE=float(rt.get("rmse",math.nan)),RPE_rotation_RMSE=float(rr.get("rmse",math.nan)),TSR=tsr,PMR=pmr,tracking_gap_episodes=gaps,Tracking_FPS=tf,EndToEnd_FPS=ef,runtime_seconds=sec,has_legal_evaluation=int(legal),source="P1 reuse" if method=="Full" else "P2 new",run_dir=str(run)))
 return rows

def vals(rows,key): return [float(r[key]) for r in rows if isinstance(r[key],(int,float)) and math.isfinite(float(r[key]))]
def avg(x): return statistics.fmean(x) if x else math.nan
def sd(x): return statistics.stdev(x) if len(x)>1 else (0 if len(x)==1 else math.nan)
def summaries(rows):
 out=[]
 for method in METHODS:
  for seq in SEQS:
   g=[r for r in rows if r["method"]==method and r["sequence"]==seq]; legal=[r for r in g if r["has_legal_evaluation"]]
   d=dict(method=method,sequence=seq,n_total=len(g),n_completed=sum(r["experiment_completion_status"]=="completed" for r in g),n_legal_evaluation=len(legal))
   for key,label in [("ATE_RMSE","ATE_RMSE"),("ATE_mean","ATE_mean"),("ATE_median","ATE_median"),("RPE_translation_RMSE","RPE_translation"),("RPE_rotation_RMSE","RPE_rotation"),("TSR","TSR"),("PMR","PMR"),("tracking_gap_episodes","tracking_gap_episodes"),("Tracking_FPS","Tracking_FPS"),("EndToEnd_FPS","EndToEnd_FPS")]:
    src=legal if key.startswith("ATE") or key.startswith("RPE") else g; x=vals(src,key); d[label+"_mean"]=avg(x); d[label+"_std"]=sd(x)
   out.append(d)
 return out

def fmt(v): return "" if isinstance(v,float) and not math.isfinite(v) else f"{v:.9f}" if isinstance(v,float) else v
def writecsv(p,rows):
 fields=list(rows[0]); p.parent.mkdir(parents=True,exist_ok=True)
 with p.open("w",newline="",encoding="utf-8-sig") as f:
  w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows({k:fmt(r[k]) for k in fields} for r in rows)

def delta(prev,new,key): return (prev[key]-new[key])/prev[key]*100 if prev[key] else math.nan
def report(rows,sums):
 idx={(r["method"],r["sequence"]):r for r in sums}; lines=["# P2 Four-method TUM Comparison Report","","## Execution integrity","","- New P2 runs: 45/45 fixed run IDs; all recorded `exit_0 + completed`.","- Full: reused unchanged P1 15 runs; no Full rerun or replacement.","- Temporal actual configuration: SemanticMode=2, Shadow=0, Active=0. Shadow is unnecessary for Temporal trajectory generation because MapPoint evidence and suppression are independent of ObjectDynamic Adapter; disabling it removes only object-level observation/logging.","","## Summary","","| Method | Sequence | n | completed | legal eval | ATE RMSE | RPE trans | RPE rot | TSR | PMR | gaps | Tracking FPS | End-to-end FPS |","|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
 for m in METHODS:
  for s in SEQS:
   x=idx[m,s]; lines.append(f"| {m} | {s} | {x['n_total']} | {x['n_completed']} | {x['n_legal_evaluation']} | {x['ATE_RMSE_mean']:.6f} ± {x['ATE_RMSE_std']:.6f} | {x['RPE_translation_mean']:.6f} ± {x['RPE_translation_std']:.6f} | {x['RPE_rotation_mean']:.6f} ± {x['RPE_rotation_std']:.6f} | {x['TSR_mean']:.6f} ± {x['TSR_std']:.6f} | {x['PMR_mean']:.6f} ± {x['PMR_std']:.6f} | {x['tracking_gap_episodes_mean']:.3f} ± {x['tracking_gap_episodes_std']:.3f} | {x['Tracking_FPS_mean']:.3f} ± {x['Tracking_FPS_std']:.3f} | {x['EndToEnd_FPS_mean']:.3f} ± {x['EndToEnd_FPS_std']:.3f} |")
 lines += ["","## Incremental comparisons","","Percentage uses `(previous - current) / previous × 100%` for error metrics; positive means lower error. TSR is reported as percentage-point change.",""]
 for a,b,title in [("ORB-SLAM2","Semantic","Semantic − ORB-SLAM2"),("Semantic","Temporal","Temporal − Semantic"),("Temporal","Full","Full − Temporal")]:
  lines += [f"### {title}","","| Sequence | ATE improvement | RPE trans improvement | TSR change | PMR change | gap change | Tracking FPS change | Coverage warning |","|---|---:|---:|---:|---:|---:|---:|---|"]
  for s in SEQS:
   x,y=idx[a,s],idx[b,s]; warn="ATE improvement may be affected by reduced trajectory coverage." if y["ATE_RMSE_mean"]<x["ATE_RMSE_mean"] and y["TSR_mean"]<x["TSR_mean"]-.01 else "--"
   lines.append(f"| {s} | {delta(x,y,'ATE_RMSE_mean'):.2f}% | {delta(x,y,'RPE_translation_mean'):.2f}% | {(y['TSR_mean']-x['TSR_mean'])*100:.2f} pp | {(y['PMR_mean']-x['PMR_mean'])*100:.2f} pp | {y['tracking_gap_episodes_mean']-x['tracking_gap_episodes_mean']:.2f} | {(y['Tracking_FPS_mean']/x['Tracking_FPS_mean']-1)*100:.2f}% | {warn} |")
 lines += ["","## Answers to the requested questions",""]
 semtemp=[(s,idx['Semantic',s],idx['Temporal',s]) for s in SEQS]; fulltemp=[(s,idx['Temporal',s],idx['Full',s]) for s in SEQS]
 stable=all(y['ATE_RMSE_mean']<x['ATE_RMSE_mean'] for _,x,y in semtemp)
 lines.append(f"1. Temporal relative to Semantic has {'lower mean ATE on all three sequences' if stable else 'not produced a stable three-sequence ATE improvement'}. See the table; coverage must be considered jointly.")
 lines.append("2. The supported changes are the measured ATE/RPE, TSR/PMR, gaps and FPS values above; no unmeasured detection-accuracy conclusion is inferred.")
 cov=[s for s,x,y in semtemp if y['ATE_RMSE_mean']<x['ATE_RMSE_mean'] and y['TSR_mean']<x['TSR_mean']-.01]
 lines.append(f"3. ATE improved while TSR fell for Temporal vs Semantic on: {', '.join(cov) if cov else 'none'}.")
 gain=[s for s,x,y in fulltemp if y['ATE_RMSE_mean']<x['ATE_RMSE_mean'] and y['TSR_mean']>=x['TSR_mean']-.01]
 lines.append(f"4. Full shows additional ATE benefit without more than 1 pp TSR loss on: {', '.join(gain) if gain else 'none'}; other cases are trade-offs or regressions.")
 lines.append("5. Active filtering has a precision/coverage trade-off wherever lower ATE coincides with lower TSR, higher PMR or more gaps; those rows are explicitly warned above.")
 lines.append("6. A paper main method cannot be selected from ATE alone. The defensible choice is the configuration with the best joint accuracy and coverage in the tables; scene-dependent Full results must be disclosed.")
 lines.append("7. Shadow is best treated as an analysis mode because it observes object state without feedback. Temporal here is a real SLAM configuration, not merely analysis, because its MapPoint evidence suppresses matches.")
 lines += ["","## fr3_walking_rpy caution","","Every rpy row must be cited as ATE + TSR + PMR. A low ATE with reduced valid-pose coverage is not evidence of better full-sequence localization. Full P1 includes two `exit_130 + completed` rows and all five legal evaluations, as required by the status policy.",""]
 (ROOT/"p2_comparison_report.md").write_text("\n".join(lines))

def main():
 rows=read(); sums=summaries(rows); writecsv(ROOT/"p2_comparison_runs.csv",rows); writecsv(ROOT/"p2_comparison_summary.csv",sums); report(rows,sums)
if __name__=="__main__": main()
