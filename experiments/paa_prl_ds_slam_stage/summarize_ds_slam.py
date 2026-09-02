#!/usr/bin/env python3
"""Summarize local DS-SLAM runs and compare with frozen main configurations."""
from __future__ import annotations
import argparse,csv,json,math,statistics
from datetime import datetime
from pathlib import Path

REPO=Path(__file__).resolve().parents[2]
SEQUENCES=("fr3_walking_xyz","fr3_walking_rpy","fr3_walking_halfsphere","fr3_sitting_xyz","fr3_sitting_rpy","fr3_sitting_halfsphere")

def num(v):
    try: x=float(v); return x if math.isfinite(x) else math.nan
    except: return math.nan
def mean(xs):
    v=[x for x in xs if math.isfinite(x)]; return statistics.mean(v) if v else math.nan
def stdev(xs):
    v=[x for x in xs if math.isfinite(x)]; return statistics.stdev(v) if len(v)>1 else math.nan
def write(path,fields,rows):
    with path.open('w',newline='',encoding='utf-8-sig') as f: w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=REPO/'results/paa_prl_baselines/DS-SLAM');args=ap.parse_args();root=args.root.resolve()
    rows=[]
    for seq in SEQUENCES:
        for run in sorted((root/seq).glob('run_*')):
            m=json.loads((run/'metadata.json').read_text());s=json.loads((run/'status.json').read_text())
            ep=run/'eval/metrics.json';e=json.loads(ep.read_text()) if ep.exists() else {}
            rows.append({'Sequence':seq,'Run':m['run_id'],'ATE_RMSE':e.get('ate',{}).get('rmse',''),
              'RPE_translation':e.get('rpe_trans',{}).get('rmse',''),'RPE_rotation':e.get('rpe_rot_deg',{}).get('rmse',''),
              'valid_poses':s['valid_poses'],'total_association_frames':s['total_association_frames'],'TSR':s['TSR'],'PMR':s['PMR'],
              'Gaps':s['tracking_gaps'],'tracking_failure':int(s['tracking_failure']),'coverage_warning':int(s['coverage_warning']),
              'exit_code':s['exit_code'],'wall_time_seconds':s['wall_time_seconds'],'end_to_end_FPS':s['end_to_end_fps'],'SF':''})
    fields=list(rows[0]);write(root/'ds_slam_all_runs.csv',fields,rows)
    sums=[]
    for seq in SEQUENCES:
        g=[r for r in rows if r['Sequence']==seq]
        if len(g)!=1: raise RuntimeError(f'{seq}: expected 1 exploratory run, got {len(g)}')
        sums.append({'Sequence':seq,'ATE_mean':mean([num(r['ATE_RMSE']) for r in g]),'ATE_std':stdev([num(r['ATE_RMSE']) for r in g]),
          'RPE_translation':mean([num(r['RPE_translation']) for r in g]),'RPE_rotation':mean([num(r['RPE_rotation']) for r in g]),
          'TSR':mean([num(r['TSR']) for r in g]),'PMR':mean([num(r['PMR']) for r in g]),'Gaps':mean([num(r['Gaps']) for r in g]),
          'Failure_runs':sum(int(r['tracking_failure']) for r in g),'valid_ATE_runs':sum(math.isfinite(num(r['ATE_RMSE'])) for r in g),'SF':''})
    write(root/'ds_slam_sequence_summary.csv',list(sums[0]),sums)
    main=list(csv.DictReader((REPO/'results/paa_prl_submission_stage/main_analysis/main_results.csv').open(encoding='utf-8-sig')))
    comp=[]
    for seq in SEQUENCES:
        ds=next(r for r in sums if r['Sequence']==seq);t=next(r for r in main if r['Sequence']==seq and r['Configuration']=='Temporal')
        da,ta=num(ds['ATE_mean']),num(t['ATE_mean']);dts,dpm=num(ds['TSR']),num(ds['PMR']);tts,tpm=num(t['TSR']),num(t['PMR'])
        comparable=lambda a,b: abs(a-b)<=0.02
        if not math.isfinite(da): label='DS-SLAM_tracking_incomplete_no_ATE'
        elif dts<.9 and tts<.9: label='both_tracking_incomplete'
        elif ta<da and tts>=dts-.02 and tpm<=dpm+.02: label='Temporal_lower_ATE_coverage_comparable_or_better'
        elif da<ta and dts>=tts-.02 and dpm<=tpm+.02: label='DS-SLAM_lower_ATE_coverage_comparable_or_better'
        else: label='ATE_coverage_trade_off'
        for source in [r for r in main if r['Sequence']==seq]:
            comp.append({'Sequence':seq,'Configuration':source['Configuration'],'ATE_mean':source['ATE_mean'],'ATE_std':source['ATE_std'],
              'RPE_translation':source['RPE_translation'],'RPE_rotation':source['RPE_rotation'],'TSR':source['TSR'],'PMR':source['PMR'],
              'Failure_count':source['Tracking_failure_count'],'SF':source['SF'],'Temporal_DS_comparison':''})
        comp.append({'Sequence':seq,'Configuration':'DS-SLAM','ATE_mean':ds['ATE_mean'],'ATE_std':ds['ATE_std'],
          'RPE_translation':ds['RPE_translation'],'RPE_rotation':ds['RPE_rotation'],'TSR':ds['TSR'],'PMR':ds['PMR'],
          'Failure_count':ds['Failure_runs'],'SF':'','Temporal_DS_comparison':label})
    write(root/'baseline_comparison.csv',list(comp[0]),comp)
    (root/'summary_metadata.json').write_text(json.dumps({'generated_at':datetime.now().astimezone().isoformat(timespec='seconds'),
      'protocol':'6 sequences x 1 exploratory run','runs':len(rows),
      'failure_policy':'process failure, invalid trajectory, or TSR < 0.90','sf':'N/A','sample_standard_deviation':False,
      'note':'No standard deviation is defined for one run per sequence. The interrupted walking_xyz attempt is preserved and was not rerun.'},indent=2)+'\n')
    print(root)
if __name__=='__main__':main()
