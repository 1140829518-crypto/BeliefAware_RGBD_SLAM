#!/usr/bin/env python3
"""Run the 45 new fixed P2 comparison attempts, never replacing run IDs."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "experiments/final_paper/02_tum_comparison"
RUNNER = REPO / "scripts/run_tum_rgbd_experiment.py"
SETTINGS = REPO / "Examples/RGB-D/TUM3.yaml"
BINARY = REPO / "Examples/RGB-D/rgbd_tum"
LIBRARY = REPO / "lib/libORB_SLAM2.so"
WEIGHTS = REPO / "yolov5_RemoveDynamic/weights/yolov5s.pt"
METHODS = {
    "ORB-SLAM2": {"runner": "orb", "semantic": 0, "shadow": 0, "active": 0},
    "Semantic": {"runner": "hard", "semantic": 1, "shadow": 0, "active": 0},
    "Temporal": {"runner": "dynamic", "semantic": 2, "shadow": 0, "active": 0},
}
SEQUENCES = {
    "fr3_walking_xyz": (Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz"), REPO / "dataset_associations/fr3_walking_xyz_associate.txt", 827),
    "fr3_walking_rpy": (Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_rpy"), REPO / "dataset_associations/fr3_walking_rpy_associate.txt", 866),
    "fr3_walking_halfsphere": (Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_halfsphere"), REPO / "dataset_associations/fr3_walking_halfsphere_associate.txt", 1021),
}
FATAL = ("segmentation fault", "segfault", "out of memory", "oom-killer", "timed out", "timeout expired")

def now(): return datetime.now().astimezone().isoformat(timespec="seconds")

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""): h.update(b)
    return h.hexdigest()

def lines(path: Path) -> int:
    return sum(bool(x.strip()) and not x.lstrip().startswith("#") for x in path.read_text(errors="ignore").splitlines())

def raw_status(code):
    if code is None: return "unknown"
    if code < 0: return "killed"
    return f"exit_{code}"

def completion(run: Path):
    text="\n".join(p.read_text(errors="ignore") for p in (run/"slam.log",run/"terminal.log") if p.exists()).lower()
    marker="trajectory saved!" in text and "semantic dynamic statistics saved!" in text
    traj=(run/"CameraTrajectory.txt").exists() and (run/"CameraTrajectory.txt").stat().st_size>0
    ev=(run/"eval/metrics.json").exists() and (run/"eval/metrics.json").stat().st_size>0
    fatal=[x for x in FATAL if x in text]
    evidence=f"slam_marker={int(marker)};trajectory_nonempty={int(traj)};evaluation_nonempty={int(ev)};fatal_patterns={'|'.join(fatal) or 'none'}"
    return ("invalid" if fatal else "completed" if marker and traj and ev else "incomplete"),evidence

def build(method: str):
    cfg=METHODS[method]; slug=method.lower().replace("-","_")
    build=REPO/f"build_p2_{slug}"
    flags=f"-DENABLE_OBJECT_DYNAMIC_SHADOW_MODE={cfg['shadow']} -DENABLE_OBJECT_DYNAMIC_ACTIVE_MODE={cfg['active']}"
    log=ROOT/"builds"/f"{slug}.log"; log.parent.mkdir(parents=True,exist_ok=True)
    with log.open("w") as out:
        for cmd in (["cmake","-S",str(REPO),"-B",str(build),f"-DCMAKE_CXX_FLAGS={flags}"],["cmake","--build",str(build),"-j8","--target","rgbd_tum"]):
            out.write("COMMAND: "+" ".join(cmd)+"\n"); out.flush()
            p=subprocess.run(cmd,cwd=REPO,stdout=out,stderr=subprocess.STDOUT,text=True)
            if p.returncode: raise RuntimeError(f"build failed: {log}")
    cache=(build/"CMakeCache.txt").read_text(errors="ignore")
    actual=re.search(r"^CMAKE_CXX_FLAGS:STRING=(.*)$",cache,re.M)
    if not actual or actual.group(1)!=flags: raise RuntimeError("compile macro verification failed")
    snapshot={"method":method,"semantic_mode":cfg["semantic"],"shadow":cfg["shadow"],"active":cfg["active"],"flags":flags,"binary":{"path":str(BINARY),"sha256":sha(BINARY)},"library":{"path":str(LIBRARY),"sha256":sha(LIBRARY)},"yolo":{"path":str(WEIGHTS.resolve()),"sha256":sha(WEIGHTS)},"settings_sha256":sha(SETTINGS),"recorded_at":now()}
    p=ROOT/"builds"/f"{slug}_snapshot.json"; p.write_text(json.dumps(snapshot,indent=2)+"\n")
    return p

def run_one(method,sequence,run_id,snapshot):
    cfg=METHODS[method]; dataset,assoc,total=SEQUENCES[sequence]
    run=ROOT/method/sequence/f"run_{run_id:02d}"
    if run.exists(): print("PRESERVE",run,flush=True); return
    if lines(assoc)!=total: raise RuntimeError(f"association mismatch {sequence}")
    run.mkdir(parents=True)
    socket=Path(f"/tmp/p2_{method.lower().replace('-','_')}_{sequence}_{run_id:02d}_{os.getpid()}.sock")
    cmd=[sys.executable,str(RUNNER),"--sequence",sequence,"--method",cfg["runner"],"--dataset",str(dataset),"--association",str(assoc),"--settings",str(SETTINGS),"--out-dir",str(run),"--device","0"]
    data={"method":method,"sequence":sequence,"run_id":run_id,"original_status":"running","exit_code":None,"raw_process_status":"unknown","experiment_completion_status":"incomplete","started_at":now(),"association_total_frames":total,"semantic_mode":cfg["semantic"],"shadow":cfg["shadow"],"active":cfg["active"],"socket":str(socket),"build_snapshot":str(snapshot),"command":cmd}
    conf=run/"run_config.json"; conf.write_text(json.dumps(data,indent=2)+"\n")
    env=os.environ.copy(); env["ORB_SLAM2_SOCKET_PATH"]=str(socket); env["ORB_SLAM2_SEMANTIC_MODE"]=str(cfg["semantic"])
    for k in ("ORB_SLAM2_DYNAMIC_LAMBDA","ORB_SLAM2_DYNAMIC_THETA","ORB_SLAM2_PERSON_DYNAMIC_THETA"): env.pop(k,None)
    start=time.monotonic(); code=None
    try:
        with (run/"terminal.log").open("w") as out: code=subprocess.run(cmd,cwd=REPO,env=env,stdout=out,stderr=subprocess.STDOUT,text=True).returncode
        original="success" if code==0 else "failed"
    except KeyboardInterrupt: code=130; original="interrupted"
    except Exception as e: original="failed"; (run/"driver_exception.txt").write_text(repr(e)+"\n")
    finally:
        try: socket.unlink()
        except FileNotFoundError: pass
    complete,evidence=completion(run)
    data.update(original_status=original,exit_code=code,raw_process_status=raw_status(code),experiment_completion_status=complete,completion_evidence=evidence,finished_at=now(),runtime_seconds=time.monotonic()-start)
    conf.write_text(json.dumps(data,indent=2)+"\n"); print(method,sequence,run_id,data["raw_process_status"],complete,flush=True)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--method",choices=list(METHODS)+["all"],default="all"); args=ap.parse_args()
    ROOT.mkdir(parents=True,exist_ok=True)
    lock=(ROOT/".p2.lock").open("w")
    try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: raise SystemExit("Another P2 runner owns the lock")
    selected=list(METHODS) if args.method=="all" else [args.method]
    for method in selected:
        snapshot=build(method)
        for sequence in SEQUENCES:
            for run_id in range(1,6): run_one(method,sequence,run_id,snapshot)

if __name__=="__main__": main()
