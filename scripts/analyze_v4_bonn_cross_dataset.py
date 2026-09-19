#!/usr/bin/env python3
"""Aggregate frozen V4 Bonn validation and merge it with completed TUM results."""
import argparse,bisect,csv,math,statistics,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from evaluate_tum_metrics import load_tum
from analyze_v4_cross_sequence import common_metrics,coverage_mask,longest,assoc_stamps

SEQS=('rgbd_bonn_person_tracking','rgbd_bonn_synchronous','rgbd_bonn_crowd'); MODES=('belief_only','geometry_protected'); RUNS=('run_01','run_02','run_03')
def mean(x):return statistics.fmean(x) if x else math.nan
def std(x):return statistics.stdev(x) if len(x)>1 else 0.
def read(p):return list(csv.DictReader(p.open()))
def write(p,rows):
 fields=[]
 for r in rows:
  for k in r:
   if k not in fields:fields.append(k)
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--data',type=Path,required=True);ap.add_argument('--tum-master',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 master=[];common=[];continuity=[];composition=[];paired=[]
 for seq in SEQS:
  an=a.root/seq/'analysis';group=read(an/'group_metrics.csv');act={x['history']:x for x in read(an/'protection_activation.csv')};rest={x['scope']:x for x in read(an/'information_restoration.csv')};safety=read(an/'policy_safety.csv')
  def gm(m,k):return next(float(x['mean']) for x in group if x['mode']==m and x['metric']==k)
  violations=sum(int(float(x.get('dynamic_cap_violation_count') or 0)) for x in safety if x['axis']=='p')
  for mode in MODES:
   master.append({'dataset':'Bonn','sequence':seq,'policy':mode,'runs':3,'ATE':gm(mode,'ATE_RMSE'),'RPE_t':gm(mode,'RPE_translation'),'RPE_r':gm(mode,'RPE_rotation_deg'),'TSR':gm(mode,'TSR'),'PMR':gm(mode,'PMR'),'final_inliers':gm(mode,'final_inliers'),'acceptance':gm(mode,'optimization_acceptance'),'protected_ratio':float(act['all']['protected_ratio']) if mode=='geometry_protected' else 0,'stable_restoration':float(rest['stable']['restoration_fraction']) if mode=='geometry_protected' else 0,'contradictory_restoration':float(rest['contradictory']['restoration_fraction']) if mode=='geometry_protected' else 0,'dynamic_safety_violations':violations if mode=='geometry_protected' else 0})
  total_rest=float(rest['all']['actual_budget'])-float(rest['all']['belief_only_budget'])
  shares={}
  for kind in ('stable','contradictory','other'):
   rr=rest[kind]; restored=float(rr['actual_budget'])-float(rr['belief_only_budget']);shares[kind]=restored/total_rest if total_rest else math.nan
   composition.append({'sequence':seq,'history':kind,'restored_information':restored,'share':shares[kind],'protected_ratio':float(act[kind]['protected_ratio']),'mean_delta_r':float(act[kind]['protected_mean_delta_r']),'restoration_ratio':float(rr['restoration_fraction']),'final_base_survival':float(act[kind]['protected_final_base_geometric_inlier_ratio'])})
  stamps=assoc_stamps(a.data/seq/'associate.txt')
  for mode in MODES:
   for run in RUNS:
    ts=sorted(load_tum(a.root/seq/mode/run/'CameraTrajectory.txt')[0]);mask=coverage_mask(stamps,ts);continuity.append({'sequence':seq,'policy':mode,'run':run,'longest_tracked':longest(mask,True),'longest_lost':longest(mask,False)})
  normal=read(an/'normal_accepted_paired.csv')
  for x in normal:paired.append({'sequence':seq,**x,'positive_final_inlier_delta':int(float(x['mean_delta_final_inliers_GP_minus_BELIEF'])>0)})
  for run in RUNS:
   bm,gm_,ratio=common_metrics(a.data/seq/'groundtruth.txt',a.root/seq/'belief_only'/run/'CameraTrajectory.txt',a.root/seq/'geometry_protected'/run/'CameraTrajectory.txt',len(stamps));common.append({'sequence':seq,'run':run,'coverage':ratio,'belief_ATE':bm[0],'gp_ATE':gm_[0],'belief_RPE_t':bm[1],'gp_RPE_t':gm_[1],'belief_RPE_r':bm[2],'gp_RPE_r':gm_[2]})
 write(a.out/'bonn_master.csv',master);write(a.out/'restoration_composition.csv',composition);write(a.out/'common_accepted_per_run.csv',paired);write(a.out/'continuity_per_run.csv',continuity);write(a.out/'common_coverage_per_run.csv',common)
 cs=[]
 for seq in SEQS:
  z=[x for x in common if x['sequence']==seq];row={'sequence':seq}
  for k in ('coverage','belief_ATE','gp_ATE','belief_RPE_t','gp_RPE_t','belief_RPE_r','gp_RPE_r'):row[k+'_mean']=mean([x[k] for x in z]);row[k+'_std']=std([x[k] for x in z])
  cs.append(row)
 write(a.out/'common_coverage_summary.csv',cs)
 cont=[]
 for seq in SEQS:
  for mode in MODES:
   z=[x for x in continuity if x['sequence']==seq and x['policy']==mode];cont.append({'sequence':seq,'policy':mode,'longest_tracked_mean':mean([x['longest_tracked'] for x in z]),'longest_lost_mean':mean([x['longest_lost'] for x in z])})
 write(a.out/'continuity_summary.csv',cont)
 # Merge previously frozen TUM master and Bonn, adding common metrics by sequence/policy.
 common_map={x['sequence']:x for x in cs}
 tum_common={x['sequence']:x for x in read(a.tum_master.parent/'common_coverage_summary.csv')}
 combined=[]
 for x in read(a.tum_master):
  c=tum_common[x['sequence']]; prefix='belief' if x['policy']=='belief_only' else 'gp'
  combined.append({'dataset':'TUM','sequence':x['sequence'],'policy':x['policy'],'runs':5,'ATE':x['ATE'],'RPE_t':x['RPE_t'],'RPE_r':x['RPE_r'],'TSR':x['TSR'],'PMR':x['PMR'],'final_inliers':x['final_inliers'],'acceptance':x['acceptance'],'common_coverage':c['intersection_coverage_ratio_mean'],'common_ATE':c[prefix+'_common_ATE_mean'],'common_RPE_t':c[prefix+'_common_RPE_t_mean'],'common_RPE_r':c[prefix+'_common_RPE_r_mean'],'protected_ratio':float(x['protected_percent'])/100,'stable_restoration':x['stable_restoration'],'contradictory_restoration':x['contradictory_restoration'],'dynamic_safety_violations':0})
 for x in master:
  c=common_map[x['sequence']];prefix='belief' if x['policy']=='belief_only' else 'gp';x=dict(x);x.update({'common_coverage':c['coverage_mean'],'common_ATE':c[prefix+'_ATE_mean'],'common_RPE_t':c[prefix+'_RPE_t_mean'],'common_RPE_r':c[prefix+'_RPE_r_mean']});combined.append(x)
 write(a.out/'cross_dataset_master_table.csv',combined)
if __name__=='__main__':main()
