#!/usr/bin/env python3
"""Frozen-parameter Bonn cross-dataset protocol: 3 sequences x 2 configurations x 5."""
from __future__ import annotations
import argparse,hashlib,json,os,subprocess,sys,time
from datetime import datetime
from pathlib import Path
REPO=Path(__file__).resolve().parents[2];sys.path.insert(0,str(REPO/'scripts'))
from paa_prl_common import git_output,sha256,trajectory_coverage,write_json
ROOT=REPO/'experiment_new/dataset/bonn_rgbd_dynamic'; SETTINGS=ROOT/'Bonn.yaml'
SEQS=("rgbd_bonn_person_tracking","rgbd_bonn_synchronous","rgbd_bonn_crowd"); CONFIGS=("Semantic","Temporal")
PARAM_ENV=("ORB_SLAM2_DYNAMIC_THETA","ORB_SLAM2_PERSON_DYNAMIC_THETA","ORB_SLAM2_DYNAMIC_INCREMENT","ORB_SLAM2_PERSON_DYNAMIC_INCREMENT","ORB_SLAM2_DYNAMIC_LAMBDA","ORB_SLAM2_PERSON_DYNAMIC_LAMBDA")
def now():return datetime.now().astimezone().isoformat(timespec='seconds')
def manifest_hash(seq):
 h=hashlib.sha256()
 for name in ('rgb.txt','depth.txt','groundtruth.txt','associate.txt'):
  p=seq/name;h.update(name.encode());h.update(bytes.fromhex(sha256(p)))
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=REPO/'results/paa_prl_strengthening/bonn_cross_dataset');ap.add_argument('--runs',type=int,default=5);ap.add_argument('--device',default='0');ap.add_argument('--execute',action='store_true');a=ap.parse_args()
 if a.runs!=5:ap.error('formal protocol requires five runs')
 root=a.root.resolve()
 if a.execute and root.exists() and any(root.iterdir()):raise RuntimeError(f'refusing overwrite: {root}')
 root.mkdir(parents=True,exist_ok=True);md=root/'metadata';md.mkdir(exist_ok=True)
 probe=md/'runtime_frozen_parameter_probe';subprocess.run(['g++','-std=c++11','-O2','-I',str(REPO/'include'),str(REPO/'experiments/paa_prl_strengthening/runtime_frozen_parameter_probe.cc'),'-o',str(probe)],check=True)
 env_clean=os.environ.copy()
 for k in PARAM_ENV:env_clean.pop(k,None)
 probe_out=subprocess.check_output([str(probe)],env=env_clean,text=True);vals=dict(line.split('=') for line in probe_out.splitlines())
 expected={'ordinary_threshold':3.,'ordinary_increment':1.,'ordinary_decay':.95,'person_threshold':2.,'person_increment':1.,'person_decay':.90}
 if any(abs(float(vals[k])-v)>5e-7 for k,v in expected.items()):raise RuntimeError(f'frozen runtime mismatch {vals}')
 cases=[]
 for seqname in SEQS:
  seq=ROOT/seqname;assoc=seq/'associate.txt'
  for config in CONFIGS:
   for i in range(1,6):
    out=root/config/seqname/f'run_{i:02d}';method='hard' if config=='Semantic' else 'dynamic'
    cmd=[sys.executable,str(REPO/'scripts/run_tum_rgbd_experiment.py'),'--sequence',seqname,'--method',method,'--dataset',str(seq),'--association',str(assoc),'--settings',str(SETTINGS),'--out-dir',str(out),'--device',a.device,'--socket-timeout','300']
    cases.append({'experiment_key':f'{config}/{seqname}/run_{i:02d}','sequence':seqname,'configuration':config,'run_id':f'run_{i:02d}','out_dir':str(out),'command':cmd,'dataset':str(seq),'association':str(assoc),
     'dataset_manifest_hash':manifest_hash(seq),'association_hash':sha256(assoc),'executable_hash':sha256(REPO/'Examples/RGB-D/rgbd_tum'),'config_hash':sha256(SETTINGS),'semantic_model_hash':sha256(REPO/'yolov5_RemoveDynamic/weights/yolov5s.pt')})
 protocol={'created_at':now(),'status':'planned','formal_run_count':30,'sequences':list(SEQS),'configurations':list(CONFIGS),'runs_per_cell':5,'cases':cases,'runtime_read_frozen_parameters':vals,
  'parameter_override_policy':'all sensitivity environment overrides removed; source fallback defaults used','correctness':'NOT AVAILABLE; no Bonn dynamic-state GT is constructed','git_commit':git_output('rev-parse','HEAD'),'git_status':git_output('status','--short')}
 write_json(root/'bonn_protocol.json',protocol)
 if not a.execute:print('planned=30',vals);return
 completed=0
 for case in cases:
  out=Path(case['out_dir']);out.mkdir(parents=True);write_json(out/'metadata.json',case);env=env_clean.copy();env['ORB_SLAM2_SOCKET_PATH']=f"/tmp/bonn_strength_{case['configuration']}_{case['sequence']}_{case['run_id']}_{os.getpid()}.sock";env['ORB_SLAM2_MAPPOINT_EVIDENCE_LOG']=str(out/'mappoint_evidence_raw.csv');env['ORB_SLAM2_MAPPOINT_PROJECTION_LOG']=str(out/'mappoint_projection_raw.csv')
  start=now();tick=time.monotonic()
  with (out/'driver.log').open('w',encoding='utf-8') as log:code=subprocess.run(case['command'],cwd=REPO,env=env,stdout=log,stderr=subprocess.STDOUT,text=True).returncode
  wall=time.monotonic()-tick;total,valid,gaps,tsr,pmr=trajectory_coverage(Path(case['association']),out/'CameraTrajectory.txt')
  if code!=0:fc='process_or_orchestration'
  elif valid<2:fc='invalid_trajectory'
  elif tsr<.9:fc='tracking_failure'
  elif tsr<1 or gaps:fc='tracking_incomplete'
  else:fc='none'
  st={'started_at':start,'finished_at':now(),'exit_code':code,'wall_time_seconds':wall,'expected_frames':total,'valid_poses':valid,'trajectory_valid':valid>=2,'TSR':tsr,'PMR':pmr,'tracking_gaps':gaps,'failure_class':fc,'tracking_failure':fc in ('process_or_orchestration','invalid_trajectory','tracking_failure'),'coverage_warning':fc!='none','formal_run_preserved':True}
  write_json(out/'status.json',st);completed+=1;protocol['status']='running';protocol['completed_runs']=completed;protocol['last_update']=now();write_json(root/'bonn_protocol.json',protocol);print(f"[{completed}/30] {case['experiment_key']} exit={code} valid={valid}/{total} TSR={tsr:.4f} class={fc}",flush=True)
 protocol['status']='complete';protocol['completed_at']=now();write_json(root/'bonn_protocol.json',protocol)
if __name__=='__main__':main()
