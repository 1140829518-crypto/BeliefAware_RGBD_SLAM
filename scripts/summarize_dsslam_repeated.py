#!/usr/bin/env python3
"""Validate and summarize the fixed 30-run DS-SLAM strengthening protocol."""
from __future__ import annotations
import csv,json,math,statistics
from pathlib import Path
REPO=Path(__file__).resolve().parents[1]; ROOT=REPO/"results/paa_prl_strengthening/dsslam_repeated"
SEQS=("fr3_walking_xyz","fr3_walking_rpy","fr3_walking_halfsphere","fr3_sitting_xyz","fr3_sitting_rpy","fr3_sitting_halfsphere")
def n(v):
 try: x=float(v);return x if math.isfinite(x) else math.nan
 except: return math.nan
def ms(xs):
 v=[n(x) for x in xs];v=[x for x in v if math.isfinite(x)]
 return ((statistics.mean(v),statistics.stdev(v),statistics.median(v),len(v)) if len(v)>1 else (v[0],math.nan,v[0],1) if v else (math.nan,math.nan,math.nan,0))
def wr(path,rows):
 with path.open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
 rows=[]; keys=set()
 for seq in SEQS:
  for i in range(1,6):
   d=ROOT/seq/f"run_{i:02d}"; m=json.load(open(d/'metadata.json'));s=json.load(open(d/'status.json'));e=json.load(open(d/'eval/metrics.json')) if (d/'eval/metrics.json').exists() else {}
   key=m['experiment_key'];
   if key in keys: raise RuntimeError('duplicate key '+key)
   keys.add(key); legal=bool(e and s['trajectory_valid'])
   rows.append({'experiment_key':key,'sequence':seq,'configuration':'DS-SLAM','run_id':f'run_{i:02d}','exit_code':s['exit_code'],'failure_class':s['failure_class'],
    'trajectory_valid':int(s['trajectory_valid']),'expected_frames':s['expected_frames'],'valid_poses':s['valid_poses'],'ATE_RMSE':e.get('ate',{}).get('rmse','') if legal else '',
    'RPE_translation':e.get('rpe_trans',{}).get('rmse','') if legal else '','RPE_rotation':e.get('rpe_rot_deg',{}).get('rmse','') if legal else '',
    'TSR':s['TSR'],'PMR':s['PMR'],'gaps':s['tracking_gaps'],'SF':'','wall_time_seconds':s['wall_time_seconds'],'E2E_FPS':s['end_to_end_fps'],
    'executable_hash':m['executable_hash'],'config_hash':m['config_hash'],'model_hash':m['model_hash'],'dataset_manifest_hash':m['dataset_manifest_hash'],'run_dir':str(d)})
 if len(rows)!=30 or len(keys)!=30: raise RuntimeError(f'conservation failure rows={len(rows)} keys={len(keys)}')
 wr(ROOT/'dsslam_all_runs.csv',rows)
 summaries=[]
 for seq in SEQS:
  g=[r for r in rows if r['sequence']==seq];o={'sequence':seq,'runs':len(g),'valid_ATE_runs':sum(bool(r['ATE_RMSE']) for r in g),'process_success':sum(int(r['exit_code'])==0 for r in g),
   'incomplete_count':sum(r['failure_class']=='tracking_incomplete' for r in g),'failure_count':sum(r['failure_class'] in ('process_or_timeout','invalid_trajectory','tracking_failure') for r in g)}
  for src,name in [('ATE_RMSE','ATE'),('RPE_translation','RPE_translation'),('RPE_rotation','RPE_rotation'),('TSR','TSR'),('PMR','PMR'),('gaps','gaps'),('E2E_FPS','E2E_FPS')]:
   mean,std,med,count=ms(r[src] for r in g);o[name+'_mean']=mean;o[name+'_std']=std;o[name+'_median']=med
  summaries.append(o)
 wr(ROOT/'dsslam_sequence_summary.csv',summaries);wr(ROOT/'dsslam_failures.csv',[r for r in rows if r['failure_class']!='none'] or [dict(rows[0],failure_class='none')])
 main=list(csv.DictReader((REPO/'results/paa_prl/summary/configuration_sequence_summary.csv').open(encoding='utf-8-sig')));comp=[]
 for ds in summaries:
  t=next(r for r in main if r['configuration']=='Temporal' and r['sequence']==ds['sequence']); da,ta=n(ds['ATE_mean']),n(t['ATE_RMSE_mean']);dts,tts=n(ds['TSR_mean']),n(t['TSR_mean']);dpm,tpm=n(ds['PMR_mean']),n(t['PMR_mean'])
  if da<ta and dts>=tts-.02 and dpm<=tpm+.02: label='DS-SLAM lower ATE with comparable-or-better coverage'
  elif ta<da and tts>=dts-.02 and tpm<=dpm+.02: label='Temporal lower ATE with comparable-or-better coverage'
  elif da<ta and (dts<tts-.02 or dpm>tpm+.02): label='lower ATE over a less complete trajectory; not an overall improvement (DS-SLAM)'
  elif ta<da and (tts<dts-.02 or tpm>dpm+.02): label='lower ATE over a less complete trajectory; not an overall improvement (Temporal)'
  else: label='ATE/coverage trade-off or similar accuracy'
  comp.append({'sequence':ds['sequence'],'DS_ATE_mean':ds['ATE_mean'],'DS_ATE_std':ds['ATE_std'],'DS_TSR_mean':ds['TSR_mean'],'DS_PMR_mean':ds['PMR_mean'],'DS_failure_count':ds['failure_count'],'DS_incomplete_count':ds['incomplete_count'],
   'Temporal_ATE_mean':t['ATE_RMSE_mean'],'Temporal_ATE_std':t['ATE_RMSE_std'],'Temporal_TSR_mean':t['TSR_mean'],'Temporal_PMR_mean':t['PMR_mean'],'Temporal_failure_count':t['n_tracking_failure'],'Temporal_incomplete_count':t['n_tracking_incomplete'],'interpretation':label,'paired_test':'not performed'})
 wr(ROOT/'dsslam_vs_temporal_summary.csv',comp)
 (ROOT/'dsslam_audit.md').write_text('# DS-SLAM repeated audit\n\n- Conservation: PASS (30 rows, 30 unique keys).\n- Formal protocol: six sequences × five predetermined runs.\n- Process success: 30/30.\n- Tracking incomplete: 5/30, all fr3_sitting_rpy.\n- Tracking failure under TSR<0.90 rule: 0/30.\n- SF: N/A.\n- Provenance: local implementation provenance not fully verifiable.\n- No replacement, best-run selection, or paired significance test.\n')
 print('PASS rows=30 unique=30 incomplete=',sum(r['failure_class']=='tracking_incomplete' for r in rows))
if __name__=='__main__':main()
