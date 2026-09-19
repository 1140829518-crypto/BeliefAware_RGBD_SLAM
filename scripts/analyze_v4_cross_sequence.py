#!/usr/bin/env python3
"""Cross-sequence descriptive validation for frozen V4."""
import argparse,bisect,csv,json,math,statistics,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parent))
from evaluate_tum_metrics import load_tum,associate,align_se3,make_poses

SEQS=('fr3_walking_xyz','fr3_walking_static','fr3_walking_rpy'); MODES=('belief_only','geometry_protected'); RUNS=tuple(f'run_{i:02d}' for i in range(1,6))
def mean(x): return statistics.fmean(x) if x else math.nan
def std(x): return statistics.stdev(x) if len(x)>1 else 0.
def readcsv(p): return list(csv.DictReader(p.open()))
def write(p,rows):
 p.parent.mkdir(parents=True,exist_ok=True); fields=[]
 for r in rows:
  for k in r:
   if k not in fields: fields.append(k)
 with p.open('w',newline='') as f: w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def assoc_stamps(p): return [float(s.split()[0]) for s in p.read_text().splitlines() if s.strip() and not s.startswith('#')]
def coverage_mask(a,t):
 out=[]
 for x in a:
  i=bisect.bisect_left(t,x); d=min((abs(t[j]-x) for j in (i-1,i) if 0<=j<len(t)),default=math.inf); out.append(d<=.02)
 return out
def longest(mask,value):
 best=cur=0
 for x in mask:
  cur=cur+1 if x==value else 0; best=max(best,cur)
 return best
def common_metrics(gt_path,b_path,g_path,total):
 gs,gx,gq=load_tum(gt_path); bs,bx,bq=load_tum(b_path); ps,px,pq=load_tum(g_path)
 common=[]
 for i,t in enumerate(bs):
  j=np.searchsorted(ps,t); cand=[k for k in (j-1,j) if 0<=k<len(ps)]
  if cand:
   k=min(cand,key=lambda q:abs(ps[q]-t))
   if abs(ps[k]-t)<=.02: common.append((i,k,t))
 def eval_one(stamps,xyz,quat,indices):
  sub_s=np.array([stamps[i] for i in indices]); matches=associate(sub_s,gs,.02); si=np.array([indices[i] for i,_ in matches]); gi=np.array([j for _,j in matches])
  src=xyz[si]; dst=gx[gi]; R,t=align_se3(src,dst); ate=np.linalg.norm((R@src.T).T+t-dst,axis=1)
  ep=make_poses(src,quat[si]); gp=make_poses(dst,gq[gi]); rt=[];rr=[]
  for i in range(len(matches)-1):
   e=np.linalg.inv(np.linalg.inv(gp[i])@gp[i+1])@(np.linalg.inv(ep[i])@ep[i+1]);rt.append(np.linalg.norm(e[:3,3]));rr.append(np.degrees(Rotation.from_matrix(e[:3,:3]).magnitude()))
  return math.sqrt(mean([x*x for x in ate])),math.sqrt(mean([x*x for x in rt])),math.sqrt(mean([x*x for x in rr])),len(matches)
 bi=[x[0] for x in common]; pi=[x[1] for x in common]
 return eval_one(bs,bx,bq,bi),eval_one(ps,px,pq,pi),len(common)/total
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--associations',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--xyz-gt',type=Path,required=True);ap.add_argument('--static-gt',type=Path,required=True);ap.add_argument('--rpy-gt',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 gt={'fr3_walking_xyz':a.xyz_gt,'fr3_walking_static':a.static_gt,'fr3_walking_rpy':a.rpy_gt}; master=[]; continuity=[]; common=[]; side=[]
 for seq in SEQS:
  analysis=a.root/seq/'analysis'; grouped=readcsv(analysis/'group_metrics.csv'); activation={x['history']:x for x in readcsv(analysis/'protection_activation.csv')}; restore={x['scope']:x for x in readcsv(analysis/'information_restoration.csv')}; pop={x['history']:x for x in readcsv(analysis/'representation_population_shift.csv')}
  def gm(mode,key): return next(float(x['mean']) for x in grouped if x['mode']==mode and x['metric']==key)
  for mode in MODES:
   master.append({'sequence':seq,'policy':mode,'ATE':gm(mode,'ATE_RMSE'),'RPE_t':gm(mode,'RPE_translation'),'RPE_r':gm(mode,'RPE_rotation_deg'),'TSR':gm(mode,'TSR'),'PMR':gm(mode,'PMR'),'initial_corr':gm(mode,'initial_correspondences'),'final_inliers':gm(mode,'final_inliers'),'acceptance':gm(mode,'optimization_acceptance'),'protected_percent':100*float(activation['all']['protected_ratio']) if mode=='geometry_protected' else 0,'stable_restoration':float(restore['stable']['restoration_fraction']) if mode=='geometry_protected' else 0,'contradictory_restoration':float(restore['contradictory']['restoration_fraction']) if mode=='geometry_protected' else 0})
  all_rest=float(restore['all']['actual_budget'])-float(restore['all']['belief_only_budget'])
  for kind in ('stable','contradictory'):
   ar=activation[kind]; rr=restore[kind]; restored=float(rr['actual_budget'])-float(rr['belief_only_budget'])
   side.append({'sequence':seq,'history':kind,'population':int(ar['measurement_count']),'protected_ratio':float(ar['protected_ratio']),'mean_delta_r':float(ar['protected_mean_delta_r']),'restoration_ratio':float(rr['restoration_fraction']),'restoration_share':restored/all_rest if all_rest else math.nan,'final_base_geometric_inlier_ratio':float(ar['protected_final_base_geometric_inlier_ratio']),'final_weighted_inlier_ratio':float(ar['protected_final_weighted_inlier_ratio']),'contributed_ratio':float(ar['protected_contributed_ratio']),'delta_u_gp_minus_belief':float(pop[kind]['delta_u_gp_minus_belief'])})
  stamps=assoc_stamps(a.associations/f'{seq}_associate.txt')
  for mode in MODES:
   for run in RUNS:
    ts=sorted(load_tum(a.root/seq/mode/run/'CameraTrajectory.txt')[0]); mask=coverage_mask(stamps,ts)
    continuity.append({'sequence':seq,'policy':mode,'run':run,'longest_tracked_segment':longest(mask,True),'longest_lost_segment':longest(mask,False)})
  for run in RUNS:
   b=a.root/seq/'belief_only'/run/'CameraTrajectory.txt';g=a.root/seq/'geometry_protected'/run/'CameraTrajectory.txt'; bm,gm_,ratio=common_metrics(gt[seq],b,g,len(stamps))
   common.append({'sequence':seq,'run':run,'intersection_coverage_ratio':ratio,'belief_common_ATE':bm[0],'gp_common_ATE':gm_[0],'belief_common_RPE_t':bm[1],'gp_common_RPE_t':gm_[1],'belief_common_RPE_r':bm[2],'gp_common_RPE_r':gm_[2],'common_matches':bm[3]})
 write(a.out/'master_table.csv',master);write(a.out/'continuity_per_run.csv',continuity);write(a.out/'common_coverage_per_run.csv',common);write(a.out/'population_restoration.csv',side)
 cont=[]
 for seq in SEQS:
  for mode in MODES:
   z=[x for x in continuity if x['sequence']==seq and x['policy']==mode];cont.append({'sequence':seq,'policy':mode,'longest_tracked_mean':mean([x['longest_tracked_segment'] for x in z]),'longest_tracked_std':std([x['longest_tracked_segment'] for x in z]),'longest_lost_mean':mean([x['longest_lost_segment'] for x in z]),'longest_lost_std':std([x['longest_lost_segment'] for x in z])})
 write(a.out/'continuity_summary.csv',cont)
 cs=[]
 for seq in SEQS:
  z=[x for x in common if x['sequence']==seq]
  row={'sequence':seq}
  for k in ('intersection_coverage_ratio','belief_common_ATE','gp_common_ATE','belief_common_RPE_t','gp_common_RPE_t','belief_common_RPE_r','gp_common_RPE_r'): row[k+'_mean']=mean([x[k] for x in z]);row[k+'_std']=std([x[k] for x in z])
  cs.append(row)
 write(a.out/'common_coverage_summary.csv',cs)
if __name__=='__main__':main()
