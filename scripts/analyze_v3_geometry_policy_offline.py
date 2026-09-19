#!/usr/bin/env python3
"""Offline-only geometry/reliability diagnostics for frozen V3 logs."""
import argparse,csv,json,math,statistics
from collections import defaultdict
from pathlib import Path

RUNS=('run_01','run_02','run_03')
def mean(x):return statistics.fmean(x) if x else math.nan
def write(p,rows):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else []);w.writeheader();w.writerows(rows)
def summary(z,extra):
 return {**extra,'count':len(z),'mean_p':mean([x['p'] for x in z]),'mean_u':mean([x['u'] for x in z]),'mean_h':mean([x['h'] for x in z]),'mean_reliability':mean([x['r'] for x in z]),
  'mean_base_initial_chi2':mean([x['base_initial'] for x in z]),'mean_base_final_chi2':mean([x['base_final'] for x in z]),
  'final_base_geometric_inlier_ratio':mean([x['base_final_inlier'] for x in z]),'final_weighted_inlier_ratio':mean([x['weighted_inlier'] for x in z]),
  'contributed_ratio':mean([x['contributed'] for x in z])}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 frames={};meas=[];kinds={};integrity=[]
 for run in RUNS:
  d=a.root/'persistent'/run
  fr=list(csv.DictReader((d/'ablation_frames.csv').open()))
  for fid,x in enumerate(fr):frames[run,fid]={k:int(x[k]) for k in ('tracking_success','optimization_acceptance','initial_correspondences','final_inliers')}
  hist=defaultdict(dict)
  with (d/'belief_updates.csv').open() as f:
   for x in csv.DictReader(f):hist[int(x['map_point_id'])][int(x['frame_id'])]=int(float(x['observation']))
  for mp,h in hist.items():
   z=[h[k] for k in sorted(h)];sw=sum(x!=y for x,y in zip(z,z[1:]));n=len(z)
   kinds[run,mp]='stable' if n>=6 and sw==0 else ('contradictory' if n>=6 and sw>=3 else 'other')
  by=defaultdict(list);finite=True;floor_ok=True;checked=bad=0
  with (d/'optimizer_measurements.csv').open() as f:
   for x in csv.DictReader(f):by[int(x['frame_id'])].append(x)
  for fid,fx in enumerate(fr):
   n=int(fx['initial_correspondences'])
   if n<=0:continue
   z=by[fid][-n:];checked+=1
   if len(z)!=n or sum(int(x['final_inlier']) for x in z)!=int(fx['final_inliers']):bad+=1;continue
   for x in z:
    r=float(x['reliability']);floor_ok &= r>=.05-1e-7
    T=5.991 if x['measurement_type']=='mono' else 7.815
    bi=float(x['initial_chi2'])/r;bf=float(x['final_chi2'])/r
    finite &= all(math.isfinite(v) for v in (r,bi,bf))
    q=bi/T
    meas.append({'run':run,'frame_id':fid,'mp':int(x['map_point_id']),'history':kinds.get((run,int(x['map_point_id'])),'other'),'type':x['measurement_type'],'T':T,
      'p':float(x['p']),'u':float(x['u']),'h':float(x['h']),'r':r,'base_info':float(x['base_information_scale']),'effective_info':float(x['effective_information_scale']),
      'base_initial':bi,'base_final':bf,'q':q,'base_final_inlier':int(bf<=T),'weighted_inlier':int(x['final_inlier']),'contributed':int(x['contributed_to_final_pose_optimization'])})
  integrity.append({'run':run,'frames_checked':checked,'frame_final_mismatches':bad,'finite_base_chi2':int(finite),'reliability_floor_valid':int(floor_ok)})
 write(a.out/'integrity.csv',integrity)
 contradictory=[x for x in meas if x['history']=='contradictory']
 qbins=[('q<=0.25',lambda q:q<=.25),('0.25<q<=0.5',lambda q:.25<q<=.5),('0.5<q<=1',lambda q:.5<q<=1),('1<q<=2',lambda q:1<q<=2),('q>2',lambda q:q>2)]
 write(a.out/'contradictory_q_bins.csv',[summary([x for x in contradictory if pred(x['q'])],{'q_bin':name}) for name,pred in qbins])
 rbins=[('r<0.2',lambda r:r<.2),('0.2<=r<0.4',lambda r:.2<=r<.4),('0.4<=r<0.6',lambda r:.4<=r<.6),('0.6<=r<0.8',lambda r:.6<=r<.8),('r>=0.8',lambda r:r>=.8)]
 gbins=[('q<=0.5',lambda q:q<=.5),('0.5<q<=1',lambda q:.5<q<=1),('1<q<=2',lambda q:1<q<=2),('q>2',lambda q:q>2)]
 cells=[]
 for rn,rp in rbins:
  for gn,gp in gbins:
   z=[x for x in contradictory if rp(x['r']) and gp(x['q'])]
   cells.append({'reliability_bin':rn,'geometry_bin':gn,'count':len(z),'final_base_geometric_inlier_ratio':mean([x['base_final_inlier'] for x in z]),'contributed_ratio':mean([x['contributed'] for x in z])})
 write(a.out/'reliability_geometry_2d.csv',cells)
 compare=[]
 for kind in ('stable','contradictory','other'):
  allz=[x for x in meas if x['history']==kind];z=[x for x in allz if x['r']<.4 and x['q']<=1]
  compare.append({'history':kind,'all_count':len(allz),'low_r_good_initial_count':len(z),'probability':len(z)/len(allz) if allz else math.nan,
   'final_base_geometric_inlier_ratio':mean([x['base_final_inlier'] for x in z]),'final_weighted_inlier_ratio':mean([x['weighted_inlier'] for x in z]),'contributed_ratio':mean([x['contributed'] for x in z])})
 write(a.out/'history_comparison.csv',compare)
 failures=[];precursor_by_offset={i:set() for i in range(-10,0)}
 for run in RUNS:
  for fid in range(1,866):
   if frames[run,fid-1]['tracking_success'] and not frames[run,fid]['tracking_success']:
    failures.append((run,fid))
    for off in range(-10,0):
     j=fid+off
     if j>=0 and frames[run,j]['optimization_acceptance']:precursor_by_offset[off].add((run,j))
 precursor=[]
 for off in range(-10,0):
  allz=[x for x in meas if (x['run'],x['frame_id']) in precursor_by_offset[off]];z=[x for x in allz if x['r']<.4 and x['q']<=1]
  precursor.append({'offset':off,'accepted_frames':len(precursor_by_offset[off]),'total_measurements':len(allz),'selected_count':len(z),'selected_ratio':len(z)/len(allz) if allz else math.nan,
    'stable_count':sum(x['history']=='stable' for x in z),'contradictory_count':sum(x['history']=='contradictory' for x in z),'other_count':sum(x['history']=='other' for x in z),
    'final_base_geometric_inlier_ratio':mean([x['base_final_inlier'] for x in z]),'contributed_ratio':mean([x['contributed'] for x in z])})
 write(a.out/'failure_precursor_geometry.csv',precursor);write(a.out/'failure_events.csv',[{'run':r,'frame_id':f} for r,f in failures])
 # Information budgets per frame/group. Normal excludes every accepted precursor frame.
 precursor_keys=set().union(*precursor_by_offset.values());minus1=precursor_by_offset[-1]
 accepted={(run,fid) for run in RUNS for fid in range(866) if frames[run,fid]['optimization_acceptance']}
 scopes={'normal_accepted':accepted-precursor_keys,'failure_precursor':precursor_keys,'failure_minus_1':minus1}
 budgets=[]
 for scope,keys in scopes.items():
  for kind in ('all','stable','contradictory','other'):
   z=[x for x in meas if (x['run'],x['frame_id']) in keys and (kind=='all' or x['history']==kind) and x['q']<=1]
   base=sum(x['base_info'] for x in z);cur=sum(x['effective_info'] for x in z)
   frame_base=defaultdict(float);frame_cur=defaultdict(float)
   for x in z:frame_base[x['run'],x['frame_id']]+=x['base_info'];frame_cur[x['run'],x['frame_id']]+=x['effective_info']
   budgets.append({'scope':scope,'history':kind,'frame_count':len(keys),'consistent_measurements':len(z),'B_geom_consistent':base,'B_current_geom_consistent':cur,
    'retained_information_ratio':cur/base if base else math.nan,'mean_frame_B_geom_consistent':mean(list(frame_base.values())),'mean_frame_B_current_geom_consistent':mean(list(frame_cur.values()))})
 write(a.out/'information_budget.csv',budgets)
 (a.out/'summary.json').write_text(json.dumps({'measurements':len(meas),'contradictory_measurements':len(contradictory),'failures':len(failures),'integrity':integrity},indent=2)+'\n')
if __name__=='__main__':main()
