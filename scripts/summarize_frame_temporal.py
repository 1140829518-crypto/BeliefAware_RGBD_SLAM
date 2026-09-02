#!/usr/bin/env python3
"""Summarize the fixed Frame-Temporal runs and frozen comparison rows."""
import csv,json,math,statistics,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
from paa_prl_common import SEQUENCE_NAMES,association_path,trajectory_coverage
ROOT=R/'results/frame_temporal'; OUT=ROOT

def sf(path):
    if not path.exists(): return math.nan,0,0,0
    last_frame=None; frame_rows={}; last_state={}; sw=opp=malformed=0
    def flush():
      nonlocal sw,opp
      for mp,state in frame_rows.items():
       if mp in last_state: opp+=1; sw+=state!=last_state[mp]
       last_state[mp]=state
    with path.open(newline='') as f:
      for r in csv.DictReader(f):
       try: fr=int(r['frame_id']); mp=int(r['map_point_id']); state=int(r['temporal_state'])
       except (TypeError,ValueError,KeyError): malformed+=1; continue
       if last_frame is not None and fr!=last_frame: flush();frame_rows={}
       last_frame=fr;frame_rows[mp]=state
    if frame_rows: flush()
    return sw/opp if opp else math.nan,sw,opp,malformed
def num(x):
 try:return float(x)
 except:return math.nan
def stat(v):
 v=[x for x in v if math.isfinite(x)]
 return (statistics.mean(v),statistics.stdev(v) if len(v)>1 else 0.0,statistics.median(v),len(v)) if v else (math.nan,math.nan,math.nan,0)
rows=[]
for seq in SEQUENCE_NAMES:
 for i in range(1,6):
  d=ROOT/'Frame-Temporal'/seq/f'run_{i:02d}'; status=json.load(open(d/'status.json'))
  m=json.load(open(d/'eval/metrics.json')) if (d/'eval/metrics.json').exists() else {}
  total,poses,gaps,tsr,pmr=trajectory_coverage(association_path(seq),d/'CameraTrajectory.txt')
  s,sw,opp,malformed=sf(d/'mappoint_projection_raw.csv')
  rows.append({'sequence':seq,'configuration':'Frame-Temporal','run_id':f'run_{i:02d}',
   'exit_code':status['exit_code'],'process_status':status['status'],'trajectory_valid':status['trajectory_valid'],
   'expected_frames':total,'valid_poses':poses,'ATE_RMSE':m.get('ate',{}).get('rmse',''),
   'RPE_translation':m.get('rpe_trans',{}).get('rmse',''),'RPE_rotation':m.get('rpe_rot_deg',{}).get('rmse',''),
   'TSR':tsr,'PMR':pmr,'tracking_gaps':gaps,'tracking_incomplete':int(tsr<.99 if math.isfinite(tsr) else 1),
   'tracking_failure':int(tsr<.90 if math.isfinite(tsr) else 1),'SF':s,'state_switches':sw,'transition_opportunities':opp,
   'malformed_projection_rows_excluded':malformed,'wall_time_seconds':status['wall_time_seconds'],'run_dir':str(d)})
fields=list(rows[0]);
with (OUT/'frame_temporal_runs.csv').open('w',newline='') as f:w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)
summ=[]
for seq in SEQUENCE_NAMES:
 rr=[r for r in rows if r['sequence']==seq]; x={'sequence':seq,'configuration':'Frame-Temporal','fixed_runs':5,
 'process_success':sum(r['process_status']=='success' for r in rr),'failure_count':sum(r['tracking_failure'] for r in rr),
 'incomplete_count':sum(r['tracking_incomplete'] for r in rr)}
 for key in ('ATE_RMSE','RPE_translation','RPE_rotation','TSR','PMR','tracking_gaps','SF','wall_time_seconds'):
  a=stat([num(r[key]) for r in rr]);x.update({key+'_mean':a[0],key+'_std':a[1],key+'_median':a[2],key+'_valid_runs':a[3]})
 summ.append(x)
with (OUT/'frame_temporal_summary.csv').open('w',newline='') as f:w=csv.DictWriter(f,list(summ[0]));w.writeheader();w.writerows(summ)

# Combine frozen Semantic/Temporal summaries without rerunning them.
frozen=list(csv.DictReader(open(R/'results/paa_prl/summary/configuration_sequence_summary.csv',encoding='utf-8-sig')))
comparison=[]
for seq in SEQUENCE_NAMES:
 for cfg in ('Semantic','Temporal'):
  r=next(x for x in frozen if x['sequence']==seq and x['configuration']==cfg)
  comparison.append({'sequence':seq,'configuration':'MapPoint-Temporal' if cfg=='Temporal' else cfg,
   'ATE_mean':r['ATE_RMSE_mean'],'ATE_std':r['ATE_RMSE_std'],'RPE_translation_mean':r['RPE_translation_RMSE_mean'],
   'RPE_rotation_mean':r['RPE_rotation_RMSE_deg_mean'],'TSR_mean':r['TSR_mean'],'PMR_mean':r['PMR_mean'],
   'gaps_mean':r['tracking_gap_episodes_mean'],'SF_mean':r['SF_mean'],'failure_count':r['n_tracking_failure'],'valid_runs':r['n_legal_evaluation']})
 s=next(x for x in summ if x['sequence']==seq)
 comparison.append({'sequence':seq,'configuration':'Frame-Temporal','ATE_mean':s['ATE_RMSE_mean'],'ATE_std':s['ATE_RMSE_std'],
 'RPE_translation_mean':s['RPE_translation_mean'],'RPE_rotation_mean':s['RPE_rotation_mean'],'TSR_mean':s['TSR_mean'],
 'PMR_mean':s['PMR_mean'],'gaps_mean':s['tracking_gaps_mean'],'SF_mean':s['SF_mean'],'failure_count':s['failure_count'],
 'valid_runs':s['ATE_RMSE_valid_runs']})
with (OUT/'semantic_frame_mappoint_comparison.csv').open('w',newline='') as f:w=csv.DictWriter(f,list(comparison[0]));w.writeheader();w.writerows(comparison)
print('rows',len(rows),'success',sum(r['process_status']=='success' for r in rows))
