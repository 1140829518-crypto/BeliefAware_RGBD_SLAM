#!/usr/bin/env python3
"""Thirty predetermined DS-SLAM runs; failures are retained and never replaced."""
from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from datetime import datetime
from pathlib import Path

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/"scripts")); sys.path.insert(0,str(REPO/"experiments/paa_prl_ds_slam_stage"))
from paa_prl_common import association_path,dataset_path,git_output,sha256,trajectory_coverage,write_json
from run_ds_slam_baseline import DS,EXE,LIB,VOC,BASE,SETTINGS,MODEL,PROTOTXT,PALETTE,SEQUENCES,readiness

def now(): return datetime.now().astimezone().isoformat(timespec="seconds")
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--root",type=Path,default=REPO/"results/paa_prl_strengthening/dsslam_repeated")
 ap.add_argument("--runs",type=int,default=5); ap.add_argument("--device",default="0"); ap.add_argument("--execute",action="store_true"); ap.add_argument("--timeout-seconds",type=int,default=7200); a=ap.parse_args()
 if a.runs!=5: ap.error("formal protocol requires exactly five runs")
 root=a.root.resolve()
 if a.execute and root.exists() and any(root.iterdir()): raise RuntimeError(f"refusing to overwrite non-empty formal root: {root}")
 root.mkdir(parents=True,exist_ok=True); ready=readiness(root)
 if ready["status"]!="ready": raise RuntimeError(json.dumps(ready,indent=2))
 cases=[]
 for seq in SEQUENCES:
  assoc=association_path(seq); data=dataset_path(seq)
  for run_id in range(1,6):
   out=root/seq/f"run_{run_id:02d}"; cmd=[str(EXE),str(VOC),str(SETTINGS),str(data),str(assoc),str(PROTOTXT),str(MODEL),str(PALETTE),str(out)]
   cases.append({"experiment_key":f"DS-SLAM/{seq}/run_{run_id:02d}","sequence":seq,"configuration":"DS-SLAM","run_id":f"run_{run_id:02d}","out_dir":str(out),"command":cmd,
    "dataset":str(data),"association":str(assoc),"dataset_manifest_hash":sha256(assoc),"executable_hash":ready["executable_sha256"],"config_hash":ready["config_sha256"],"model_hash":ready["model_sha256"]})
 protocol={"created_at":now(),"status":"planned","formal_run_count":30,"runs_per_sequence":5,"cases":cases,"failure_policy":"retain every formal run; no replacement",
  "provenance":"local implementation provenance not fully verifiable","readiness":ready,"main_git_commit":git_output("rev-parse","HEAD"),"main_git_status":git_output("status","--short")}
 write_json(root/"dsslam_protocol.json",protocol)
 if not a.execute: print("planned=30"); return
 completed=0
 for case in cases:
  out=Path(case["out_dir"]); out.mkdir(parents=True); write_json(out/"metadata.json",case)
  env=os.environ.copy(); env["CUDA_VISIBLE_DEVICES"]=a.device; start=now(); tick=time.monotonic(); timeout=False
  with (out/"run.log").open("w",encoding="utf-8") as log:
   log.write("COMMAND: "+" ".join(case["command"])+"\n"); log.flush()
   try: code=subprocess.run(case["command"],cwd=REPO,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=a.timeout_seconds).returncode
   except subprocess.TimeoutExpired: code=124; timeout=True; log.write("\nTIMEOUT\n")
  wall=time.monotonic()-tick; assoc=Path(case["association"]); data=Path(case["dataset"])
  total,valid,gaps,tsr,pmr=trajectory_coverage(assoc,out/"CameraTrajectory.txt"); eval_code=None
  if valid>=2:
   ev=[sys.executable,str(REPO/"scripts/evaluate_tum_metrics.py"),"--gt",str(data/"groundtruth.txt"),"--est",str(out/"CameraTrajectory.txt"),"--out-dir",str(out/"eval"),"--title",case["experiment_key"]]
   eval_code=subprocess.run(ev,cwd=REPO,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT).returncode
  if code!=0: failure_class="process_or_timeout"
  elif valid<2: failure_class="invalid_trajectory"
  elif tsr<.9: failure_class="tracking_failure"
  elif tsr<1 or gaps: failure_class="tracking_incomplete"
  else: failure_class="none"
  status={"started_at":start,"finished_at":now(),"exit_code":code,"timed_out":timeout,"wall_time_seconds":wall,"runtime_definition":"association frames / subprocess wall time",
   "end_to_end_fps":total/wall if wall else None,"internal_runtime":"N/A","expected_frames":total,"valid_poses":valid,"trajectory_valid":valid>=2,
   "TSR":tsr,"PMR":pmr,"tracking_gaps":gaps,"failure_class":failure_class,"tracking_failure":failure_class in ("process_or_timeout","invalid_trajectory","tracking_failure"),
   "coverage_warning":failure_class!="none","evaluation_exit_code":eval_code,"formal_run_preserved":True}
  write_json(out/"status.json",status); completed+=1; protocol["status"]="running"; protocol["completed_runs"]=completed; protocol["last_update"]=now(); write_json(root/"dsslam_protocol.json",protocol)
  print(f"[{completed}/30] {case['experiment_key']} exit={code} valid={valid}/{total} TSR={tsr:.4f} class={failure_class}",flush=True)
 protocol["status"]="complete"; protocol["completed_at"]=now(); write_json(root/"dsslam_protocol.json",protocol)
if __name__=="__main__": main()
