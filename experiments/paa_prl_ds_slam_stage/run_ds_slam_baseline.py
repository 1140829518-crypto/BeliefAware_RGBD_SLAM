#!/usr/bin/env python3
"""Run the local DS-SLAM checkout under the frozen PAA/PRL TUM protocol."""

from __future__ import annotations

import argparse, hashlib, json, os, subprocess, sys, time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
from paa_prl_common import association_path, dataset_path, git_output, sha256, trajectory_coverage, write_json

SEQUENCES = ("fr3_walking_xyz", "fr3_walking_rpy", "fr3_walking_halfsphere",
             "fr3_sitting_xyz", "fr3_sitting_rpy", "fr3_sitting_halfsphere")
DS = REPO / "baselines/DS-SLAM-master"
EXE = DS / "build/ds_rgbd_tum"
LIB = DS / "build/libORB_SLAM2_PointMap_SegNetM.so"
VOC = REPO / "Vocabulary/ORBvoc.txt"
BASE = DS / "Examples/ROS/ORB_SLAM2_PointMap_SegNetM"
SETTINGS = BASE / "TUM3.yaml"
MODEL = BASE / "models/segnet_pascal.caffemodel"
PROTOTXT = BASE / "prototxts/segnet_pascal.prototxt"
PALETTE = BASE / "tools/pascal.png"

def now(): return datetime.now().astimezone().isoformat(timespec="seconds")

def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    excluded = {"build", "devel", ".git"}
    for path in sorted(p for p in root.rglob("*") if p.is_file()
                       and not any(part in excluded for part in p.relative_to(root).parts)):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(bytes.fromhex(sha256(path)))
    return digest.hexdigest()

def readiness(root: Path) -> dict:
    required = [EXE, LIB, VOC, SETTINGS, MODEL, PROTOTXT, PALETTE]
    missing = [str(p) for p in required if not p.is_file()]
    ldd = subprocess.run(["ldd", str(EXE)], text=True, capture_output=True).stdout if EXE.exists() else ""
    report = {
        "checked_at": now(), "status": "ready" if not missing and "not found" not in ldd else "unavailable",
        "provenance": "local DS-SLAM checkout", "official_commit": None,
        "official_commit_note": "no nested .git metadata; no official commit is claimed",
        "source_path": str(DS), "source_tree_sha256_excluding_build": tree_hash(DS),
        "executable_sha256": sha256(EXE), "core_library_sha256": sha256(LIB),
        "model_sha256": sha256(MODEL), "config_sha256": sha256(SETTINGS),
        "prototxt_sha256": sha256(PROTOTXT), "palette_sha256": sha256(PALETTE),
        "missing": missing, "unresolved_dependencies": [line.strip() for line in ldd.splitlines() if "not found" in line],
        "mode": "RGB-D; System::RGBD and TrackRGBD confirmed in local entrypoint",
        "association_format": "timestamp rgb_path timestamp depth_path (four columns)",
        "trajectory_format": "TUM; CameraTrajectory.txt and KeyFrameTrajectory.txt",
        "algorithm_evidence": "SegNet semantic thread plus Frame::ProcessMovingObject optical flow/F-matrix RANSAC/epipolar consistency",
        "local_modifications": {
            "vcs_diff_available": False,
            "note": "No nested VCS metadata or pristine archive is available, so a complete upstream diff cannot be proven.",
            "observed_integration": "Examples/RGB-D/rgbd_tum_ds.cc is a local non-ROS batch entrypoint with association parsing and output_dir support."
        },
        "main_experiment_git_commit": git_output("rev-parse", "HEAD"),
        "main_experiment_tracked_diff": git_output("diff", "--stat"),
    }
    write_json(root / "readiness.json", report)
    return report

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=REPO / "results/paa_prl_baselines/DS-SLAM")
    ap.add_argument("--sequences", nargs="+", choices=SEQUENCES, default=list(SEQUENCES))
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--device", default="0")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--timeout-seconds", type=int, default=7200)
    args = ap.parse_args()
    if args.runs not in (1, 5): ap.error("DS-SLAM protocol supports exactly 1 exploratory run or 5 formal runs")
    root = args.root.resolve(); root.mkdir(parents=True, exist_ok=True)
    ready = readiness(root)
    if ready["status"] != "ready": raise RuntimeError(json.dumps(ready, indent=2))
    cases=[]
    for sequence in args.sequences:
        assoc=association_path(sequence); data=dataset_path(sequence)
        for run_id in range(1,args.runs+1):
            out=root/sequence/f"run_{run_id:02d}"
            cmd=[str(EXE),str(VOC),str(SETTINGS),str(data),str(assoc),str(PROTOTXT),str(MODEL),str(PALETTE),str(out)]
            meta={"baseline":"DS-SLAM","provenance":"local DS-SLAM checkout","sequence":sequence,"run_id":run_id,
                  "created_at":now(),"command":cmd,"device":args.device,"timeout_seconds":args.timeout_seconds,
                  "main_experiment_git_commit":git_output("rev-parse","HEAD"),"main_experiment_git_status":git_output("status","--short"),
                  "source_tree_sha256_excluding_build":ready["source_tree_sha256_excluding_build"],
                  "executable_sha256":ready["executable_sha256"],"core_library_sha256":ready["core_library_sha256"],
                  "model_sha256":ready["model_sha256"],"config_sha256":ready["config_sha256"],
                  "association_sha256":sha256(assoc),"dataset_path":str(data),"association_path":str(assoc),"sf":"N/A"}
            cases.append(meta)
            if not args.execute: continue
            if out.exists(): raise RuntimeError(f"refusing to overwrite {out}")
            out.mkdir(parents=True); write_json(out/"metadata.json",meta)
            env=os.environ.copy(); env["CUDA_VISIBLE_DEVICES"]=args.device
            started=now(); tick=time.monotonic(); timed_out=False
            with (out/"run.log").open("w",encoding="utf-8") as log:
                log.write("COMMAND: "+" ".join(cmd)+"\n"); log.flush()
                try:
                    proc=subprocess.run(cmd,cwd=REPO,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=args.timeout_seconds)
                    code=proc.returncode
                except subprocess.TimeoutExpired:
                    code=124; timed_out=True; log.write("\nTIMEOUT\n")
            wall=time.monotonic()-tick
            total,valid,gaps,tsr,pmr=trajectory_coverage(assoc,out/"CameraTrajectory.txt")
            eval_code=None
            if valid>=2:
                ev=[sys.executable,str(REPO/"scripts/evaluate_tum_metrics.py"),"--gt",str(data/"groundtruth.txt"),
                    "--est",str(out/"CameraTrajectory.txt"),"--out-dir",str(out/"eval"),"--title",f"{sequence} DS-SLAM run {run_id}"]
                eval_code=subprocess.run(ev,cwd=REPO,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT).returncode
            failure=code!=0 or valid<2 or tsr<0.90
            status={"status":"success" if code==0 else "failed","exit_code":code,"timed_out":timed_out,
                    "started_at":started,"finished_at":now(),"wall_time_seconds":wall,
                    "end_to_end_fps":total/wall if wall>0 else None,"runtime_definition":"association frames / subprocess wall time",
                    "internal_runtime":"N/A","total_association_frames":total,"valid_poses":valid,"TSR":tsr,"PMR":pmr,
                    "tracking_gaps":gaps,"tracking_failure":failure,"coverage_warning":tsr<0.90,"evaluation_exit_code":eval_code,
                    "failed_run_preserved":failure}
            write_json(out/"status.json",status)
            print(f"[{len([p for p in root.glob('*/*/status.json')])}/{len(args.sequences)*args.runs}] {sequence} run_{run_id:02d} exit={code} TSR={tsr:.4f}",flush=True)
            if len(cases)==1 and (code!=0 or valid<2):
                raise RuntimeError("first formal run failed readiness/model-load validation; stopping")
    write_json(root/"protocol.json",{"created_at":now(),"execute":args.execute,"cases":cases,"runs_per_sequence":args.runs,
                                     "sequences":list(args.sequences),"readiness_file":str(root/"readiness.json")})
    print(f"cases={len(cases)} execute={args.execute}")

if __name__ == "__main__": main()
