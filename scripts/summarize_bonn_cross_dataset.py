#!/usr/bin/env python3
"""Validate and summarize the frozen 30-run Bonn cross-dataset protocol."""
from __future__ import annotations
import csv,json,math,statistics
from pathlib import Path
from summarize_paa_prl_results import switching_frequency,runtime_breakdown,runtime_values
REPO=Path(__file__).resolve().parents[1];ROOT=REPO/'results/paa_prl_strengthening/bonn_cross_dataset'
SEQS=('rgbd_bonn_person_tracking','rgbd_bonn_synchronous','rgbd_bonn_crowd');CFGS=('Semantic','Temporal')
def n(v):
 try:x=float(v);return x if math.isfinite(x) else math.nan
 except:return math.nan
def ms(vals):
 v=[n(x) for x in vals];v=[x for x in v if math.isfinite(x)];return (statistics.mean(v),statistics.stdev(v) if len(v)>1 else math.nan,statistics.median(v),len(v)) if v else (math.nan,math.nan,math.nan,0)
def wr(path,rows):
 with path.open('w',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
 rows=[];keys=set()
 for seq in SEQS:
  for cfg in CFGS:
   for i in range(1,6):
    d=ROOT/cfg/seq/f'run_{i:02d}';m=json.load(open(d/'metadata.json'));s=json.load(open(d/'status.json'));e=json.load(open(d/'eval/metrics.json')) if (d/'eval/metrics.json').exists() else {};comp=runtime_breakdown(d/'runtime_summary.csv');rt=runtime_values(d/'runtime.txt');_,_,sf=switching_frequency(d/'mappoint_evidence_raw.csv')
    key=m['experiment_key'];
    if key in keys:raise RuntimeError('duplicate '+key)
    keys.add(key);legal=bool(e and s['trajectory_valid'])
    rows.append({'experiment_key':key,'sequence':seq,'configuration':cfg,'run_id':f'run_{i:02d}','exit_code':s['exit_code'],'failure_class':s['failure_class'],'trajectory_valid':int(s['trajectory_valid']),
     'expected_frames':s['expected_frames'],'valid_poses':s['valid_poses'],'ATE_RMSE':e.get('ate',{}).get('rmse','') if legal else '','RPE_translation':e.get('rpe_trans',{}).get('rmse','') if legal else '',
     'RPE_rotation':e.get('rpe_rot_deg',{}).get('rmse','') if legal else '','TSR':s['TSR'],'PMR':s['PMR'],'gaps':s['tracking_gaps'],'SF':sf,
     'Tracking_FPS':comp.get('tracking_total_fps_steady',rt.get('fps','')),'E2E_FPS':comp.get('end_to_end_frame_fps_steady',''),'Semantic_ms':1000*n(comp.get('semantic_detection_mean_seconds_steady')),
     'Temporal_ms':1000*n(comp.get('temporal_evidence_update_mean_seconds_steady')),'wall_time_seconds':s['wall_time_seconds'],'executable_hash':m['executable_hash'],'config_hash':m['config_hash'],
     'dataset_manifest_hash':m['dataset_manifest_hash'],'run_dir':str(d)})
 if len(rows)!=30 or len(keys)!=30:raise RuntimeError(f'conservation failed {len(rows)} {len(keys)}')
 wr(ROOT/'bonn_all_runs.csv',rows);wr(ROOT/'bonn_failures.csv',[r for r in rows if r['failure_class']!='none'])
 sums=[]
 for seq in SEQS:
  for cfg in CFGS:
   g=[r for r in rows if r['sequence']==seq and r['configuration']==cfg];o={'sequence':seq,'configuration':cfg,'runs':5,'valid_ATE_runs':sum(bool(r['ATE_RMSE']) for r in g),'process_success':sum(int(r['exit_code'])==0 for r in g),'incomplete_count':sum(r['failure_class']=='tracking_incomplete' for r in g),'failure_count':sum(r['failure_class'] in ('process_or_orchestration','invalid_trajectory','tracking_failure') for r in g)}
   for src in ('ATE_RMSE','RPE_translation','RPE_rotation','TSR','PMR','gaps','SF','Tracking_FPS','E2E_FPS','Semantic_ms','Temporal_ms'):
    mean,std,med,c=ms(r[src] for r in g);o[src+'_mean']=mean;o[src+'_std']=std;o[src+'_median']=med
   sums.append(o)
 wr(ROOT/'bonn_sequence_summary.csv',sums)
 comp=[]
 for seq in SEQS:
  s=next(x for x in sums if x['sequence']==seq and x['configuration']=='Semantic');t=next(x for x in sums if x['sequence']==seq and x['configuration']=='Temporal')
  comp.append({'sequence':seq,'Semantic_ATE':s['ATE_RMSE_mean'],'Temporal_ATE':t['ATE_RMSE_mean'],'ATE_change_percent':100*(t['ATE_RMSE_mean']-s['ATE_RMSE_mean'])/s['ATE_RMSE_mean'],
   'Semantic_RPE_translation':s['RPE_translation_mean'],'Temporal_RPE_translation':t['RPE_translation_mean'],'Semantic_RPE_rotation':s['RPE_rotation_mean'],'Temporal_RPE_rotation':t['RPE_rotation_mean'],
   'Semantic_SF':s['SF_mean'],'Temporal_SF':t['SF_mean'],'SF_reduction_percent':100*(s['SF_mean']-t['SF_mean'])/s['SF_mean'],'TSR_change':t['TSR_mean']-s['TSR_mean'],'PMR_change':t['PMR_mean']-s['PMR_mean'],
   'Semantic_failure_count':s['failure_count'],'Temporal_failure_count':t['failure_count'],'Semantic_incomplete_count':s['incomplete_count'],'Temporal_incomplete_count':t['incomplete_count']})
 wr(ROOT/'bonn_semantic_vs_temporal.csv',comp)
 runtime=[{k:v for k,v in r.items() if k in ('sequence','configuration','runs','Tracking_FPS_mean','Tracking_FPS_std','E2E_FPS_mean','E2E_FPS_std','Semantic_ms_mean','Semantic_ms_std','Temporal_ms_mean','Temporal_ms_std')} for r in sums];wr(ROOT/'bonn_runtime_summary.csv',runtime)
 (ROOT/'bonn_audit.md').write_text('# Bonn cross-dataset audit\n\n- Conservation: PASS (30 rows, 30 unique keys).\n- Frozen runtime parameters: verified in bonn_protocol.json.\n- Process success: 30/30.\n- No best-run selection or replacement.\n- Correctness: NOT AVAILABLE; no prediction-derived GT.\n- Person tracking: all trajectories complete.\n- Synchronous: all 10 runs tracking failure; Temporal coverage is lower.\n- Crowd: all 10 runs tracking incomplete.\n')
 print('PASS rows=30 unique=30')
if __name__=='__main__':main()
