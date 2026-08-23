#!/usr/bin/env python3
"""Run fixed Semantic/Temporal P3 attempts with optional MapPoint evidence logging."""

from __future__ import annotations
import fcntl, hashlib, json, os, re, subprocess, sys, time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "experiments/final_paper/03_temporal_continuity"
ONE = REPO / "scripts/run_tum_rgbd_experiment.py"
SETTINGS = REPO / "Examples/RGB-D/TUM3.yaml"
BINARY = REPO / "Examples/RGB-D/rgbd_tum"
LIBRARY = REPO / "lib/libORB_SLAM2.so"
WEIGHTS = REPO / "yolov5_RemoveDynamic/weights/yolov5s.pt"
METHODS = {"Semantic": ("hard", 1), "Temporal": ("dynamic", 2)}
SEQUENCES = {
    "fr3_walking_xyz": (Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz"), REPO / "dataset_associations/fr3_walking_xyz_associate.txt", 827),
    "fr3_walking_rpy": (Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_rpy"), REPO / "dataset_associations/fr3_walking_rpy_associate.txt", 866),
    "fr3_walking_halfsphere": (Path("/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_halfsphere"), REPO / "dataset_associations/fr3_walking_halfsphere_associate.txt", 1021),
}

def now(): return datetime.now().astimezone().isoformat(timespec="seconds")
def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""): h.update(b)
    return h.hexdigest()
def association_rows(path):
    return sum(bool(x.strip()) and not x.lstrip().startswith("#") for x in path.read_text(errors="ignore").splitlines())

def build(method):
    build_dir=REPO/f"build_p3_{method.lower()}"
    flags="-DENABLE_OBJECT_DYNAMIC_SHADOW_MODE=0 -DENABLE_OBJECT_DYNAMIC_ACTIVE_MODE=0"
    log=ROOT/"builds"/f"{method.lower()}.log"; log.parent.mkdir(parents=True,exist_ok=True)
    with log.open("w") as out:
        for cmd in (["cmake","-S",str(REPO),"-B",str(build_dir),f"-DCMAKE_CXX_FLAGS={flags}"], ["cmake","--build",str(build_dir),"-j8","--target","rgbd_tum"]):
            out.write("COMMAND: "+" ".join(cmd)+"\n"); out.flush()
            p=subprocess.run(cmd,cwd=REPO,stdout=out,stderr=subprocess.STDOUT,text=True)
            if p.returncode: raise RuntimeError(f"build failed: {log}")
    snap={"method":method,"semantic_mode":METHODS[method][1],"shadow":0,"active":0,"compile_flags":flags,"git_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=REPO,text=True).strip(),"binary_sha256":sha(BINARY),"library_sha256":sha(LIBRARY),"yolo_weights":str(WEIGHTS.resolve()),"yolo_sha256":sha(WEIGHTS),"recorded_at":now()}
    path=ROOT/"builds"/f"{method.lower()}_snapshot.json"; path.write_text(json.dumps(snap,indent=2)+"\n"); return path

def completion(run):
    text="\n".join(p.read_text(errors="ignore") for p in (run/"slam.log",run/"terminal.log") if p.exists()).lower()
    fatal=any(x in text for x in ("segmentation fault","out of memory","timeout expired"))
    marker="trajectory saved!" in text and "semantic dynamic statistics saved!" in text
    traj=(run/"CameraTrajectory.txt").exists() and (run/"CameraTrajectory.txt").stat().st_size>0
    ev=(run/"eval/metrics.json").exists() and (run/"eval/metrics.json").stat().st_size>0
    return "invalid" if fatal else "completed" if marker and traj and ev else "incomplete"

def run_one(method,sequence,rid,snapshot):
    runner,mode=METHODS[method]; dataset,assoc,total=SEQUENCES[sequence]
    if association_rows(assoc)!=total: raise RuntimeError(f"association count mismatch: {sequence}")
    run=ROOT/method/sequence/f"run_{rid:02d}"
    if run.exists(): print("PRESERVE",run,flush=True); return
    run.mkdir(parents=True)
    socket=Path(f"/tmp/p3_{method.lower()}_{sequence}_{rid:02d}_{os.getpid()}.sock")
    cmd=[sys.executable,str(ONE),"--sequence",sequence,"--method",runner,"--dataset",str(dataset),"--association",str(assoc),"--settings",str(SETTINGS),"--out-dir",str(run),"--device","0"]
    conf={"method":method,"sequence":sequence,"run_id":f"run_{rid:02d}","raw_process_status":"unknown","experiment_completion_status":"incomplete","association_total_frames":total,"semantic_mode":mode,"shadow":0,"active":0,"socket":str(socket),"build_snapshot":str(snapshot),"started_at":now(),"command":cmd}
    cp=run/"run_config.json"; cp.write_text(json.dumps(conf,indent=2)+"\n")
    env=os.environ.copy(); env["ORB_SLAM2_SOCKET_PATH"]=str(socket); env["ORB_SLAM2_SEMANTIC_MODE"]=str(mode); env["ORB_SLAM2_MAPPOINT_EVIDENCE_LOG"]=str(run/"mappoint_evidence_raw.csv")
    for key in ("ORB_SLAM2_DYNAMIC_LAMBDA","ORB_SLAM2_DYNAMIC_THETA","ORB_SLAM2_PERSON_DYNAMIC_THETA"): env.pop(key,None)
    start=time.monotonic(); code=None
    try:
        with (run/"terminal.log").open("w") as out: code=subprocess.run(cmd,cwd=REPO,env=env,stdout=out,stderr=subprocess.STDOUT,text=True).returncode
    except KeyboardInterrupt: code=130
    finally:
        try: socket.unlink()
        except FileNotFoundError: pass
    conf.update(exit_code=code,raw_process_status=(f"exit_{code}" if code is not None else "unknown"),experiment_completion_status=completion(run),runtime_seconds=time.monotonic()-start,finished_at=now())
    cp.write_text(json.dumps(conf,indent=2)+"\n"); print(method,sequence,rid,conf["raw_process_status"],conf["experiment_completion_status"],flush=True)

def main():
    ROOT.mkdir(parents=True,exist_ok=True); lock=(ROOT/".p3.lock").open("w")
    try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: raise SystemExit("another P3 runner owns the lock")
    for method in METHODS:
        snapshot=build(method)
        for sequence in SEQUENCES:
            for rid in range(1,6): run_one(method,sequence,rid,snapshot)

if __name__=="__main__": main()
