#!/usr/bin/env python3
"""Analyze frozen V3 walking_rpy optimizer instrumentation."""
import argparse,csv,json,math,statistics
from collections import defaultdict
from pathlib import Path

MODES=('clean','persistent');RUNS=('run_01','run_02','run_03')
def mean(x):return statistics.fmean(x) if x else math.nan
def pct(x,q):
 y=sorted(x)
 if not y:return math.nan
 a=(len(y)-1)*q;l=int(a);h=math.ceil(a)
 return y[l] if l==h else y[l]*(h-a)+y[h]*(a-l)
def write(p,rows):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else []);w.writeheader();w.writerows(rows)
def summarize(z,extra=None):
 out={'measurement_count':len(z),'mean_p':mean([x['p'] for x in z]),'mean_u':mean([x['u'] for x in z]),'mean_h':mean([x['h'] for x in z]),'mean_r':mean([x['r'] for x in z]),
      'mean_initial_chi2':mean([x['initial_chi2'] for x in z]),'mean_final_chi2':mean([x['final_chi2'] for x in z]),
      'mean_final_base_chi2':mean([x['final_base_chi2'] for x in z]),'final_inlier_ratio':mean([x['final_inlier'] for x in z]),
      'final_active_ratio':mean([x['final_active'] for x in z]),'contributed_final_ratio':mean([x['contributed'] for x in z])}
 if extra:out.update(extra)
 return out
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 frames={};measurements=[];belief_info={};integrity=[]
 for mode in MODES:
  for run in RUNS:
   d=a.root/mode/run
   fr=list(csv.DictReader((d/'ablation_frames.csv').open()))
   for fid,x in enumerate(fr):frames[mode,run,fid]={k:int(x[k]) for k in ('tracking_success','optimization_acceptance','initial_correspondences','final_inliers')}
   hist=defaultdict(dict)
   with (d/'belief_updates.csv').open() as f:
    for x in csv.DictReader(f):hist[int(x['map_point_id'])][int(x['frame_id'])]=int(float(x['observation']))
   for mp,h in hist.items():
    seq=[h[k] for k in sorted(h)];sw=sum(x!=y for x,y in zip(seq,seq[1:]));n=len(seq)
    belief_info[mode,run,mp]='stable' if n>=6 and sw==0 else ('contradictory' if n>=6 and sw>=3 else 'other')
   by=defaultdict(list);maxerr=0.0
   with (d/'optimizer_measurements.csv').open() as f:
    for x in csv.DictReader(f):
     maxerr=max(maxerr,abs(float(x['effective_information_scale'])-float(x['base_information_scale'])*float(x['belief_reliability'])))
     by[int(x['frame_id'])].append(x)
   checked=bad=0
   for fid,fx in enumerate(fr):
    n=int(fx['initial_correspondences'])
    if n<=0:continue
    z=by[fid][-n:]; checked+=1
    if len(z)!=n or sum(int(x['final_inlier']) for x in z)!=int(fx['final_inliers']):bad+=1;continue
    for x in z:
     r=float(x['reliability']);typ=x['measurement_type'];threshold=5.991 if typ=='mono' else 7.815
     q={'mode':mode,'run':run,'frame_id':fid,'mp':int(x['map_point_id']),'history':belief_info.get((mode,run,int(x['map_point_id'])),'other'),
        'type':typ,'threshold':threshold,'p':float(x['p']),'u':float(x['u']),'h':float(x['h']),'r':r,
        'initial_chi2':float(x['initial_chi2']),'final_chi2':float(x['final_chi2']),
        'final_base_chi2':float(x['final_chi2'])/r if r>0 else math.inf,'final_inlier':int(x['final_inlier']),
        'final_active':int(x['final_active']),'contributed':int(x['contributed_to_final_pose_optimization'])}
     q['potentially_useful_low_weight']=int(r<.4 and q['final_base_chi2']<=threshold)
     measurements.append(q)
   integrity.append({'mode':mode,'run':run,'frames_checked':checked,'frame_final_mismatches':bad,'max_information_scale_error':maxerr})
 write(a.out/'integrity.csv',integrity)
 # paired normally accepted frames
 paired=set()
 for run in RUNS:
  for fid in range(866):
   if frames['clean',run,fid]['optimization_acceptance'] and frames['persistent',run,fid]['optimization_acceptance']:paired.add((run,fid))
 normal=[x for x in measurements if (x['run'],x['frame_id']) in paired]
 rows=[]
 for mode in MODES:
  for kind in ('stable','contradictory','other'):
   rows.append(summarize([x for x in normal if x['mode']==mode and x['history']==kind],{'mode':mode,'history':kind,'paired_frames':len(paired)}))
 write(a.out/'normal_accepted_history.csv',rows)
 # conditioned survival, persistent paired accepted population
 pp=[x for x in normal if x['mode']=='persistent']; conditioned=[]
 for lo,hi in ((.05,.2),(.2,.4),(.4,.6),(.6,.8),(.8,1.000001)):
  conditioned.append(summarize([x for x in pp if lo<=x['r']<hi],{'conditioning':'reliability','bin':f'[{lo},{min(hi,1.0)}{",closed" if hi>1 else ")"}'}))
 ordered=sorted(pp,key=lambda x:x['u']);nq=len(ordered)
 for qi in range(4):
  conditioned.append(summarize(ordered[qi*nq//4:(qi+1)*nq//4],{'conditioning':'u_quartile','bin':f'Q{qi+1}'}))
 for lo,hi in ((0,.1),(.1,.3),(.3,.5),(.5,1.000001)):
  conditioned.append(summarize([x for x in pp if lo<=x['h']<hi],{'conditioning':'h','bin':f'[{lo},{min(hi,1.0)}{",closed" if hi>1 else ")"}'}))
 write(a.out/'persistent_conditioned_survival.csv',conditioned)
 # failure precursors: transition success -> failure, only preceding accepted frames
 failures=[];precursor_keys=set()
 for run in RUNS:
  for fid in range(1,866):
   if frames['persistent',run,fid-1]['tracking_success'] and not frames['persistent',run,fid]['tracking_success']:
    failures.append((run,fid))
    for j in range(max(0,fid-10),fid):
     if frames['persistent',run,j]['optimization_acceptance']:precursor_keys.add((run,j))
 curve=[]
 for off in range(-10,0):
  keys={(run,fid+off) for run,fid in failures if fid+off>=0 and frames['persistent',run,fid+off]['optimization_acceptance']}
  z=[x for x in measurements if x['mode']=='persistent' and (x['run'],x['frame_id']) in keys]
  stable=[x for x in z if x['history']=='stable'];con=[x for x in z if x['history']=='contradictory']
  curve.append({'offset':off,'accepted_frame_samples':len(keys),'measurement_count':len(z),'stable_count':len(stable),'contradictory_count':len(con),
   'mean_r':mean([x['r'] for x in z]),'stable_mean_r':mean([x['r'] for x in stable]),'contradictory_mean_r':mean([x['r'] for x in con]),
   'final_inlier_ratio':mean([x['final_inlier'] for x in z]),'stable_final_inlier_ratio':mean([x['final_inlier'] for x in stable]),'contradictory_final_inlier_ratio':mean([x['final_inlier'] for x in con]),
   'active_measurement_count':sum(x['contributed'] for x in z)})
 write(a.out/'failure_precursor.csv',curve);write(a.out/'failure_events.csv',[{'run':r,'frame_id':f} for r,f in failures])
 # critical diagnostic based on base-information chi2, avoiding the circular weighted-chi2 test
 crit=[]
 scopes=[('overall',measurements),('failure_precursor',[x for x in measurements if x['mode']=='persistent' and (x['run'],x['frame_id']) in precursor_keys])]
 for mode in MODES:
  scopes += [(f'{mode}_{k}',[x for x in measurements if x['mode']==mode and x['history']==k]) for k in ('stable','contradictory','other')]
 for name,z in scopes:
  q=[x for x in z if x['potentially_useful_low_weight']]
  low=[x for x in z if x['r']<.4]
  crit.append({'scope':name,'measurement_count':len(z),'low_weight_count':len(low),'potentially_useful_low_weight_count':len(q),
   'ratio_of_all':len(q)/len(z) if z else math.nan,'ratio_within_low_weight':len(q)/len(low) if low else math.nan})
 write(a.out/'potentially_useful_low_weight.csv',crit)
 (a.out/'summary.json').write_text(json.dumps({'paired_accepted_frames':len(paired),'persistent_failures':len(failures),'integrity':integrity},indent=2)+'\n')
if __name__=='__main__':main()
