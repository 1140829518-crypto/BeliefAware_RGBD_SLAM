#!/usr/bin/env python3
"""Run isolated Frame-Temporal experiments without replacing prior attempts."""
from __future__ import annotations

import argparse, json, os, subprocess, sys, time
from datetime import datetime
from pathlib import Path

REPO=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(REPO/'scripts'))
from paa_prl_common import (SEQUENCE_NAMES, SETTINGS, association_path, data_lines,
                            dataset_path, git_output, sha256, write_json)

METHOD={'Semantic':'hard','Frame-Temporal':'frame-temporal','MapPoint-Temporal':'dynamic'}
RUNNER=REPO/'scripts/run_tum_rgbd_experiment.py'

def now(): return datetime.now().astimezone().isoformat(timespec='seconds')

def run_one(root, config, seq, run_id, device):
    out=root/config/seq/f'run_{run_id:02d}'
    if out.exists():
        raise RuntimeError(f'preserved output already exists: {out}')
    out.mkdir(parents=True)
    dataset=dataset_path(seq); association=association_path(seq)
    socket=Path(f'/tmp/frame_temporal_{config.lower().replace("-","_")}_{seq}_{run_id}_{os.getpid()}.sock')
    cmd=[sys.executable,str(RUNNER),'--sequence',seq,'--method',METHOD[config],
         '--dataset',str(dataset),'--association',str(association),'--settings',str(SETTINGS),
         '--out-dir',str(out),'--device',device,'--socket-timeout','300']
    env=os.environ.copy(); env['ORB_SLAM2_SOCKET_PATH']=str(socket)
    env['ORB_SLAM2_MAPPOINT_PROJECTION_LOG']=str(out/'mappoint_projection_raw.csv')
    env['ORB_SLAM2_MAPPOINT_EVIDENCE_LOG']=str(out/'mappoint_evidence_raw.csv')
    meta={'protocol':'Frame-Temporal control v1','configuration':config,'sequence':seq,
          'run_id':f'run_{run_id:02d}','command':cmd,'started_at':now(),'random_seed':'not applicable',
          'git_commit':git_output('rev-parse','HEAD'),'git_status':git_output('status','--short'),
          'dataset':str(dataset),'association':str(association),'association_rows':data_lines(association),
          'hashes':{'executable':sha256(REPO/'Examples/RGB-D/rgbd_tum'),
                    'library':sha256(REPO/'lib/libORB_SLAM2.so'),'settings':sha256(SETTINGS),
                    'association':sha256(association),'frame_temporal_config':sha256(REPO/'include/FrameTemporalConfig.h')},
          'frame_temporal':{'method':'image-plane binary-mask EMA','current_observation_alpha':0.60,
                            'threshold':0.50,'initialization':0.0,
                            'missing_observation':'current binary image-plane observation is zero; EMA decays',
                            'persistent_mappoint_state_used':False}}
    write_json(out/'metadata.json',meta)
    start=time.monotonic()
    with (out/'driver.stdout.log').open('w') as so,(out/'driver.stderr.log').open('w') as se:
        p=subprocess.run(cmd,cwd=REPO,env=env,stdout=so,stderr=se,text=True)
    wall=time.monotonic()-start
    traj=out/'CameraTrajectory.txt'; metrics=out/'eval/metrics.json'
    ok=p.returncode==0 and traj.exists() and traj.stat().st_size>0 and metrics.exists()
    status={'status':'success' if ok else 'failed','exit_code':p.returncode,'wall_time_seconds':wall,
            'trajectory_valid':bool(traj.exists() and traj.stat().st_size>0),'metrics_exists':metrics.exists(),
            'failure_preserved':not ok,'finished_at':now()}
    write_json(out/'status.json',status); meta.update(status); write_json(out/'metadata.json',meta)
    try: socket.unlink()
    except FileNotFoundError: pass
    print(config,seq,run_id,status['status'],flush=True)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--sequences',nargs='+',choices=SEQUENCE_NAMES,required=True)
    ap.add_argument('--configurations',nargs='+',choices=tuple(METHOD),required=True)
    ap.add_argument('--runs',type=int,default=1); ap.add_argument('--device',default='0'); a=ap.parse_args()
    for c in a.configurations:
      for s in a.sequences:
       for r in range(1,a.runs+1): run_one(a.root.resolve(),c,s,r,a.device)
if __name__=='__main__': main()
