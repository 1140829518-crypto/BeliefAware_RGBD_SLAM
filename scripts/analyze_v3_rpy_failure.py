#!/usr/bin/env python3
"""Read-only failure anatomy for frozen V3 walking_rpy artifacts."""

import argparse, bisect, csv, math, statistics
from collections import defaultdict
from pathlib import Path

MODES=("clean","persistent")
RUNS=("run_01","run_02","run_03")

def mean(x): return statistics.fmean(x) if x else math.nan
def pct(x,q):
    if not x:return math.nan
    y=sorted(x); a=(len(y)-1)*q; lo=int(a); hi=math.ceil(a)
    return y[lo] if lo==hi else y[lo]*(hi-a)+y[hi]*(a-lo)
def ranks(x):
    o=sorted(range(len(x)),key=lambda i:x[i]); r=[0.]*len(x); i=0
    while i<len(o):
        j=i+1
        while j<len(o) and x[o[j]]==x[o[i]]:j+=1
        v=(i+1+j)/2
        for k in range(i,j):r[o[k]]=v
        i=j
    return r
def spear(x,y):
    if len(x)<2:return math.nan
    x,y=ranks(x),ranks(y); mx,my=mean(x),mean(y)
    dx=[z-mx for z in x];dy=[z-my for z in y]
    d=math.sqrt(sum(z*z for z in dx)*sum(z*z for z in dy))
    return sum(a*b for a,b in zip(dx,dy))/d if d else math.nan
def write(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else []);w.writeheader();w.writerows(rows)
def quat_angle(a,b):
    dot=abs(sum(a[i]*b[i] for i in range(4)))
    return 2*math.acos(min(1,max(-1,dot)))*180/math.pi
def load_pose(path):
    out=[]
    for s in path.read_text().splitlines():
        if not s or s.startswith('#'):continue
        z=s.split();out.append((float(z[0]),tuple(map(float,z[1:4])),tuple(map(float,z[4:8]))))
    return out
def nearest_pose(poses,t,tol):
    ts=[x[0] for x in poses];i=bisect.bisect_left(ts,t); c=[j for j in (i-1,i) if 0<=j<len(ts)]
    if not c:return None
    j=min(c,key=lambda j:abs(ts[j]-t));return poses[j] if abs(ts[j]-t)<=tol else None

def load_run(d,seq,mode,run):
    with (d/'ablation_frames.csv').open() as f: frames=list(csv.DictReader(f))
    last={}
    with (d/'belief_updates.csv').open() as f:
        for z in csv.DictReader(f):last[(int(z['frame_id']),int(z['map_point_id']))]=z
    hist=defaultdict(list)
    for (fid,mp),z in last.items():hist[mp].append((fid,int(float(z['observation']))))
    kinds={}
    for mp,h in hist.items():
        h.sort();sw=sum(a[1]!=b[1] for a,b in zip(h,h[1:])); n=len(h)
        kinds[mp]='stable' if n>=6 and sw==0 else ('contradictory' if n>=6 and sw>=3 else 'other')
    byframe=defaultdict(list); obs=[]
    for (fid,mp),z in last.items():
        x={'sequence':seq,'mode':mode,'run':run,'frame_id':fid,'mp':mp,'kind':kinds[mp],
           'p':float(z['after_observation_p']),'u':float(z['after_observation_u']),
           'r':float(z['final_reliability']),'h':float(z['persistence_after']),
           'pc':float(z['persistent_conflict'])}
        x['r_no_u']=1-x['p'];x['weight_loss']=x['r_no_u']-x['r'];obs.append(x);byframe[fid].append(x)
    est=load_pose(d/'CameraTrajectory.txt'); prev=None; motion={}
    for po in est:
        if prev:
            trans=math.sqrt(sum((po[1][i]-prev[1][i])**2 for i in range(3)))
            motion[po[0]]=(trans,quat_angle(po[2],prev[2]))
        prev=po
    out=[]
    for fid,z in enumerate(frames):
        q=byframe.get(fid,[]); ts=float(z['timestamp']); mo=motion.get(ts,(math.nan,math.nan))
        out.append({'sequence':seq,'mode':mode,'run':run,'frame_id':fid,'timestamp':ts,
          'initial':float(z['initial_correspondences']),'inliers':float(z['final_inliers']),
          'inlier_ratio':float(z['final_inliers'])/float(z['initial_correspondences']) if float(z['initial_correspondences']) else math.nan,
          'accept':int(z['optimization_acceptance']),'tracking':int(z['tracking_success']),
          'belief_count':len(q),'mean_p':mean([x['p'] for x in q]),'mean_u':mean([x['u'] for x in q]),
          'mean_r':mean([x['r'] for x in q]),'mean_h':mean([x['h'] for x in q]),'mean_pc':mean([x['pc'] for x in q]),
          'est_translation':mo[0],'est_rotation_deg':mo[1]})
    return out,obs

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--gt',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    frames=[];obs=[]
    for mode in MODES:
      for run in RUNS:
        f,o=load_run(a.root/'fr3_walking_rpy'/mode/run,'fr3_walking_rpy',mode,run);frames+=f;obs+=o
    gt=load_pose(a.gt)
    for mode in MODES:
      for run in RUNS:
        rr=[x for x in frames if x['mode']==mode and x['run']==run];prev=None
        for x in rr:
          po=nearest_pose(gt,x['timestamp'],.02)
          if po and prev:
            x['gt_translation']=math.sqrt(sum((po[1][i]-prev[1][i])**2 for i in range(3)));x['gt_rotation_deg']=quat_angle(po[2],prev[2])
          else:x['gt_translation']=x['gt_rotation_deg']=math.nan
          if po:prev=po
    write(a.out/'rpy_frame_metrics.csv',frames)
    # paired frame deltas and worst 10% by inlier loss
    ix={(x['mode'],x['run'],x['frame_id']):x for x in frames}; paired=[]
    for run in RUNS:
      for fid in range(866):
        c,p=ix['clean',run,fid],ix['persistent',run,fid]
        paired.append({'run':run,'frame_id':fid,'delta_initial':p['initial']-c['initial'],'delta_inliers':p['inliers']-c['inliers'],'inlier_loss':c['inliers']-p['inliers'],
          **{f'clean_{k}':c[k] for k in ('initial','inliers','inlier_ratio','mean_p','mean_u','mean_r','mean_h','mean_pc')},
          **{f'persistent_{k}':p[k] for k in ('initial','inliers','inlier_ratio','mean_p','mean_u','mean_r','mean_h','mean_pc')}})
    paired.sort(key=lambda x:x['inlier_loss'],reverse=True);write(a.out/'top10pct_inlier_loss_frames.csv',paired[:math.ceil(len(paired)*.1)]);write(a.out/'paired_frame_deltas.csv',paired)
    both=[x for x in paired if ix['clean',x['run'],x['frame_id']]['accept'] and ix['persistent',x['run'],x['frame_id']]['accept']]
    write(a.out/'top10pct_inlier_loss_both_accepted.csv',both[:math.ceil(len(both)*.1)])
    pair_summary=[]
    for label,pred in (
      ('all',lambda c,p:True),('both_accepted',lambda c,p:c['accept'] and p['accept']),
      ('clean_only_accepted',lambda c,p:c['accept'] and not p['accept']),
      ('persistent_only_accepted',lambda c,p:p['accept'] and not c['accept']),
      ('both_rejected',lambda c,p:not c['accept'] and not p['accept'])):
      z=[]
      for run in RUNS:
       for fid in range(866):
        c,p=ix['clean',run,fid],ix['persistent',run,fid]
        if pred(c,p):z.append((c,p))
      pair_summary.append({'subset':label,'frames':len(z),'mean_delta_initial':mean([p['initial']-c['initial'] for c,p in z]),'mean_delta_inliers':mean([p['inliers']-c['inliers'] for c,p in z])})
    write(a.out/'paired_frame_summary.csv',pair_summary)
    # reliability distributions and bins (inlier association is frame-level only)
    dist=[];bins=[];edges=[.05,.2,.4,.6,.8,1.0000001]
    frameix={(x['mode'],x['run'],x['frame_id']):x for x in frames}
    for mode in MODES:
      oo=[x for x in obs if x['mode']==mode];rv=[x['r'] for x in oo]
      dist.append({'mode':mode,'count':len(rv),'mean':mean(rv),'median':pct(rv,.5),'P10':pct(rv,.1),'P25':pct(rv,.25),'P75':pct(rv,.75)})
      for lo,hi in zip(edges,edges[1:]):
        z=[x for x in oo if lo<=x['r']<hi]; ff=[frameix[x['mode'],x['run'],x['frame_id']] for x in z]
        bins.append({'mode':mode,'bin':f'[{lo:.2f},{min(hi,1):.1f}{"]" if hi>1 else ")"}','observations':len(z),'mean_frame_final_inliers':mean([x['inliers'] for x in ff]),'mean_frame_acceptance':mean([x['accept'] for x in ff])})
    write(a.out/'reliability_distribution.csv',dist);write(a.out/'reliability_bins.csv',bins)
    # history contributions; no individual inlier identity exists
    contrib=[]
    for mode in MODES:
      for kind in ('stable','contradictory','other'):
        z=[x for x in obs if x['mode']==mode and x['kind']==kind];ff=[frameix[x['mode'],x['run'],x['frame_id']] for x in z]
        contrib.append({'mode':mode,'history':kind,'observations':len(z),'mean_reliability':mean([x['r'] for x in z]),'mean_p':mean([x['p'] for x in z]),'mean_u':mean([x['u'] for x in z]),'mean_frame_final_inliers':mean([x['inliers'] for x in ff]),'mean_frame_inlier_ratio':mean([x['inlier_ratio'] for x in ff if math.isfinite(x['inlier_ratio'])])})
    write(a.out/'history_pose_support.csv',contrib)
    # frame correlations (only frames carrying belief observations)
    corr=[]
    for mode in MODES:
      z=[x for x in frames if x['mode']==mode and x['belief_count'] and x['inliers']>0]
      corr.append({'sequence':'fr3_walking_rpy','mode':mode,'frames':len(z),**{f'spearman_{k}_inliers':spear([x[k] for x in z],[x['inliers'] for x in z]) for k in ('mean_u','mean_r','mean_h','mean_pc')}})
    # minimal controls
    for seq in ('fr3_walking_xyz','fr3_walking_static'):
      for mode in MODES:
        ff=[];oo=[]
        for run in RUNS:
          x,y=load_run(a.root/seq/mode/run,seq,mode,run);ff+=x;oo+=y
        z=[x for x in ff if x['belief_count'] and x['inliers']>0]
        corr.append({'sequence':seq,'mode':mode,'frames':len(z),**{f'spearman_{k}_inliers':spear([x[k] for x in z],[x['inliers'] for x in z]) for k in ('mean_u','mean_r','mean_h','mean_pc')}})
    write(a.out/'frame_correlations.csv',corr)
    # events and aligned windows
    event_frames=[];failure_keys=set()
    for mode in MODES:
      for run in RUNS:
        rr=[x for x in frames if x['mode']==mode and x['run']==run]; lookup={x['frame_id']:x for x in rr}
        for typ,key in [('tracking_lost_gap_start','tracking'),('optimization_rejected','accept')]:
          ids=[x['frame_id'] for i,x in enumerate(rr) if i>0 and rr[i-1][key]==1 and x[key]==0]
          if typ=='tracking_lost_gap_start':
            for fid in ids:failure_keys.update((mode,run,j) for j in range(max(0,fid-10),min(866,fid+11)))
          for fid in ids:event_frames.append({'mode':mode,'run':run,'event':typ,'frame_id':fid})
    window=[]
    for mode in MODES:
      for typ in ('tracking_lost_gap_start','optimization_rejected'):
        ev=[x for x in event_frames if x['mode']==mode and x['event']==typ]
        for off in range(-10,11):
          z=[ix[mode,x['run'],x['frame_id']+off] for x in ev if (mode,x['run'],x['frame_id']+off) in ix]
          window.append({'mode':mode,'event':typ,'offset':off,'samples':len(z),**{k:mean([x[k] for x in z if math.isfinite(x[k])]) for k in ('initial','inliers','mean_u','mean_r','mean_h','mean_pc')}})
    write(a.out/'failure_events.csv',event_frames);write(a.out/'failure_windows.csv',window)
    grouped=[]
    for mode in MODES:
      oo=[x for x in obs if x['mode']==mode]; us=sorted(x['u'] for x in oo); cuts=[pct(us,q) for q in (.25,.5,.75)]
      specs=[('u_Q1',lambda x:x['u']<=cuts[0]),('u_Q2',lambda x:cuts[0]<x['u']<=cuts[1]),('u_Q3',lambda x:cuts[1]<x['u']<=cuts[2]),('u_Q4',lambda x:x['u']>cuts[2]),
       ('h_[0,.1)',lambda x:0<=x['h']<.1),('h_[.1,.3)',lambda x:.1<=x['h']<.3),('h_[.3,.5)',lambda x:.3<=x['h']<.5),('h_[.5,1]',lambda x:.5<=x['h']<=1)]
      for label,pred in specs:
        z=[x for x in oo if pred(x)];ff=[frameix[x['mode'],x['run'],x['frame_id']] for x in z]
        grouped.append({'mode':mode,'group':label,'observations':len(z),'mean_initial':mean([x['initial'] for x in ff]),'mean_final_inliers':mean([x['inliers'] for x in ff]),'failure_window_ratio':sum((x['mode'],x['run'],x['frame_id']) in failure_keys for x in z)/len(z) if z else math.nan})
    write(a.out/'uncertainty_persistence_frame_association.csv',grouped)
    # rotation quartiles using GT; estimate separately
    motion=[]
    for source,key in [('gt','gt_rotation_deg'),('estimated','est_rotation_deg')]:
      for mode in MODES:
        z=[x for x in frames if x['mode']==mode and math.isfinite(x[key]) and x['belief_count']]
        z.sort(key=lambda x:x[key]);n=len(z)
        for qi in range(4):
          q=z[qi*n//4:(qi+1)*n//4]
          motion.append({'source':source,'mode':mode,'quartile':f'Q{qi+1}','frames':len(q),'mean_rotation_deg':mean([x[key] for x in q]),**{k:mean([x[k] for x in q]) for k in ('initial','inliers','mean_r','mean_u','mean_h')}})
    write(a.out/'rotation_quartiles.csv',motion)
    # paired deltas by the common GT-rotation quartile (same run index/frame ID).
    valid=[]
    for run in RUNS:
      for fid in range(866):
        c,p=ix['clean',run,fid],ix['persistent',run,fid]
        if math.isfinite(c['gt_rotation_deg']):valid.append((c['gt_rotation_deg'],c,p))
    valid.sort(key=lambda x:x[0]);n=len(valid);rot_delta=[]
    for qi in range(4):
      z=valid[qi*n//4:(qi+1)*n//4]
      rot_delta.append({'quartile':f'Q{qi+1}','frames':len(z),'mean_gt_rotation_deg':mean([x[0] for x in z]),
        'mean_delta_initial':mean([x[2]['initial']-x[1]['initial'] for x in z]),'mean_delta_inliers':mean([x[2]['inliers']-x[1]['inliers'] for x in z]),
        'clean_acceptance':mean([x[1]['accept'] for x in z]),'persistent_acceptance':mean([x[2]['accept'] for x in z])})
    write(a.out/'paired_rotation_deltas.csv',rot_delta)
    # offline counterfactual weight accounting (logged clamped reliability is r)
    gtrots=[x['gt_rotation_deg'] for x in frames if math.isfinite(x['gt_rotation_deg'])];q75=pct(gtrots,.75)
    weight=[]
    for mode in MODES:
      oo=[x for x in obs if x['mode']==mode]
      groups={'overall':oo,'stable':[x for x in oo if x['kind']=='stable'],'contradictory':[x for x in oo if x['kind']=='contradictory'],
       'high_gt_rotation':[x for x in oo if frameix[x['mode'],x['run'],x['frame_id']]['gt_rotation_deg']>=q75],
       'failure_window':[x for x in oo if (x['mode'],x['run'],x['frame_id']) in failure_keys]}
      for name,z in groups.items():weight.append({'mode':mode,'group':name,'observations':len(z),'mean_r_no_u':mean([x['r_no_u'] for x in z]),'mean_logged_r':mean([x['r'] for x in z]),'mean_weight_loss_due_to_u':mean([x['weight_loss'] for x in z])})
    write(a.out/'counterfactual_weight_loss.csv',weight)

if __name__=='__main__':main()
