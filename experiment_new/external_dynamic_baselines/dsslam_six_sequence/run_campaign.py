#!/usr/bin/env python3
import csv,json,hashlib,os,shutil,statistics,subprocess,time
from datetime import datetime
from pathlib import Path
R=Path(__file__).resolve().parents[3]; O=Path(__file__).resolve().parent
EXE=R/'baselines/DS-SLAM-master/build/ds_rgbd_tum'; VOC=R/'Vocabulary/ORBvoc.txt'; DS=R/'baselines/DS-SLAM-master/Examples/ROS/ORB_SLAM2_PointMap_SegNetM'
MODEL=DS/'models/segnet_pascal.caffemodel'; PROTO=DS/'prototxts/segnet_pascal.prototxt'; PAL=DS/'tools/pascal.png'; EVAL=R/'scripts/evaluate_tum_metrics.py'
CASES={
'fr3_walking_xyz':('/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz',R/'dataset_associations/fr3_walking_xyz_associate.txt',DS/'TUM3.yaml','reuse'),
'fr3_walking_static':(R/'rgbd_dataset_freiburg3_walking_static',R/'dataset_associations/fr3_walking_static_associate.txt',DS/'TUM3.yaml','run'),
'fr3_walking_rpy':('/home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_rpy',R/'dataset_associations/fr3_walking_rpy_associate.txt',DS/'TUM3.yaml','reuse'),
'rgbd_bonn_person_tracking':(R/'experiment_new/dataset/bonn_rgbd_dynamic/rgbd_bonn_person_tracking',R/'experiment_new/dataset/bonn_rgbd_dynamic/rgbd_bonn_person_tracking/associate.txt',R/'experiment_new/dataset/bonn_rgbd_dynamic/Bonn.yaml','run'),
'rgbd_bonn_synchronous':(R/'experiment_new/dataset/bonn_rgbd_dynamic/rgbd_bonn_synchronous',R/'experiment_new/dataset/bonn_rgbd_dynamic/rgbd_bonn_synchronous/associate.txt',R/'experiment_new/dataset/bonn_rgbd_dynamic/Bonn.yaml','run'),
'rgbd_bonn_crowd':(R/'experiment_new/dataset/bonn_rgbd_dynamic/rgbd_bonn_crowd',R/'experiment_new/dataset/bonn_rgbd_dynamic/rgbd_bonn_crowd/associate.txt',R/'experiment_new/dataset/bonn_rgbd_dynamic/Bonn.yaml','run')}
def now():return datetime.now().astimezone().isoformat(timespec='seconds')
def cov(assoc,traj):
 total=sum(1 for x in open(assoc) if x.strip() and not x.startswith('#')); valid=0
 if traj.exists(): valid=sum(1 for x in open(traj) if x.strip() and not x.startswith('#'))
 return total,valid,valid/total if total else 0,1-valid/total if total else 1
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
rows=[]; protocol={'created_at':now(),'target_attempts':18,'runs_per_sequence':3,'failure_policy':'retain all; no replacement; no best-run selection','cases':[]}
for seq,(data,assoc,cfg,mode) in CASES.items():
 data=Path(data)
 for i in range(1,4): protocol['cases'].append({'sequence':seq,'run':f'run_{i:02d}','mode':mode,'dataset':str(data),'association':str(assoc),'config':str(cfg)})
dump(O/'protocol.json',protocol)
for ci,c in enumerate(protocol['cases'],1):
 seq,run,mode=c['sequence'],c['run'],c['mode']; data,assoc,cfg,_=CASES[seq]; data=Path(data); out=O/'runs'/seq/run; out.mkdir(parents=True,exist_ok=True)
 start=time.monotonic(); code=0; source='new execution'
 if mode=='reuse':
  old=R/'results/paa_prl_strengthening/dsslam_repeated'/seq/run
  for f in ['CameraTrajectory.txt','KeyFrameTrajectory.txt','run.log','status.json','metadata.json']:
   if (old/f).exists(): shutil.copy2(old/f,out/f)
  source='pre-existing predetermined run, copied and re-evaluated'
 else:
  cmd=[str(EXE),str(VOC),str(cfg),str(data),str(assoc),str(PROTO),str(MODEL),str(PAL),str(out)]
  with open(out/'run.log','w') as log:
   log.write('COMMAND: '+' '.join(cmd)+'\n');log.flush()
   try: code=subprocess.run(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=7200).returncode
   except subprocess.TimeoutExpired: code=124;log.write('\nTIMEOUT\n')
 wall=time.monotonic()-start; total,valid,tsr,pmr=cov(assoc,out/'CameraTrajectory.txt'); evalcode=None; metrics={}
 if valid>=2:
  ev=out/'eval'; ev.mkdir(exist_ok=True)
  evalcode=subprocess.run(['python3',str(EVAL),'--gt',str(data/'groundtruth.txt'),'--est',str(out/'CameraTrajectory.txt'),'--out-dir',str(ev),'--title',f'DS-SLAM {seq} {run}'],cwd=R).returncode
  if evalcode==0: metrics=json.load(open(ev/'metrics.json'))
 status='SUCCESS' if code==0 and evalcode==0 and valid>=2 else 'FAILED'
 runtime=wall/total*1000 if mode=='run' and total else None
 rec={'Method':'DS-SLAM','Sequence':seq,'Run':run,'ATE':metrics.get('ate',{}).get('rmse',''),'RPE_t':metrics.get('rpe_trans',{}).get('rmse',''),'RPE_r':metrics.get('rpe_rot_deg',{}).get('rmse',''),'TSR':tsr,'PMR':pmr,'Runtime':runtime if runtime is not None else 'see preserved prior status','Status':status,'final_tracked_frames':valid,'final_inliers':'N/A','source':source,'exit_code':code,'evaluation_exit_code':evalcode}
 rows.append(rec); dump(out/'campaign_status.json',rec)
 with open(O/'dsslam_six_sequence_results.csv','w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=rec.keys());w.writeheader();w.writerows(rows)
 print(f'[{ci}/18] {seq}/{run} {status} poses={valid}/{total}',flush=True)
protocol['completed_at']=now();protocol['completed_attempts']=len(rows);dump(O/'protocol.json',protocol)
