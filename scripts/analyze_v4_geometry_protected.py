#!/usr/bin/env python3
"""Analyze the frozen-V3 BELIEF_ONLY vs geometry-protected walking_rpy runs."""
import argparse, bisect, csv, json, math, re, statistics
from collections import defaultdict
from pathlib import Path

MODES = ("belief_only", "geometry_protected")
RUNS = tuple(f"run_{i:02d}" for i in range(1, 6))

def mean(x): return statistics.fmean(x) if x else math.nan
def std(x): return statistics.stdev(x) if len(x) > 1 else 0.0
def pct(x, q):
    if not x: return math.nan
    y=sorted(x); a=(len(y)-1)*q; lo=math.floor(a); hi=math.ceil(a)
    return y[lo] if lo==hi else y[lo]*(hi-a)+y[hi]*(a-lo)
def write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        fields=[]
        for row in rows:
            for key in row:
                if key not in fields: fields.append(key)
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
def assoc_times(path):
    return [float(s.split()[0]) for s in path.read_text().splitlines() if s.strip() and not s.startswith('#')]
def traj_times(path):
    return sorted(float(s.split()[0]) for s in path.read_text().splitlines() if s.strip() and not s.startswith('#'))
def coverage(a,t):
    present=[]
    for x in a:
        i=bisect.bisect_left(t,x); d=min((abs(t[j]-x) for j in (i-1,i) if 0<=j<len(t)),default=math.inf)
        present.append(d<=.02)
    gaps=0; inside=False
    for ok in present:
        if not ok and not inside: gaps+=1; inside=True
        elif ok: inside=False
    return sum(present)/len(present), 1-sum(present)/len(present), gaps
def history_map(path):
    last={}
    for x in csv.DictReader(path.open()): last[(int(x['frame_id']),int(x['map_point_id']))]=x
    h=defaultdict(list)
    for (f,m),x in last.items(): h[m].append((f,int(float(x['observation']))))
    out={}
    for m,z in h.items():
        z.sort(); seq=[v for _,v in z]; sw=sum(a!=b for a,b in zip(seq,seq[1:]))
        out[m]='stable' if len(seq)>=6 and sw==0 else ('contradictory' if len(seq)>=6 and sw>=3 else 'other')
    return out
def summary(z):
    return {'count':len(z),'mean_rb':mean([x['rb'] for x in z]),'mean_reff':mean([x['reff'] for x in z]),
            'mean_rdyn':mean([x['rdyn'] for x in z]),'mean_delta_r':mean([x['reff']-x['rb'] for x in z]),'mean_p':mean([x['p'] for x in z]),
            'mean_u':mean([x['u'] for x in z]),'mean_h':mean([x['h'] for x in z]),
            'final_base_geometric_inlier_ratio':mean([x['base_final_inlier'] for x in z]),
            'final_weighted_inlier_ratio':mean([x['weighted_final_inlier'] for x in z]),
            'contributed_ratio':mean([x['contributed'] for x in z])}

def main():
    global RUNS
    ap=argparse.ArgumentParser(); ap.add_argument('--root',type=Path,required=True); ap.add_argument('--association',type=Path,required=True); ap.add_argument('--out',type=Path,required=True); ap.add_argument('--runs',type=int,default=5); a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    RUNS=tuple(f"run_{i:02d}" for i in range(1,a.runs+1))
    at=assoc_times(a.association); run_rows=[]; allm=[]; frames={}; integrity=[]
    for mode in MODES:
      for run in RUNS:
        d=a.root/mode/run; log=(d/'slam.log').read_text(errors='replace')
        line=next(x for x in log.splitlines() if '[BeliefConfiguration]' in x); cfg=dict(re.findall(r'([A-Z_]+)=([^ ]+)',line))
        expected='BELIEF_ONLY' if mode=='belief_only' else 'GEOMETRY_PROTECTED'
        config_ok=(cfg.get('MEASUREMENT_POLICY')==expected and cfg.get('UNCERTAINTY_MODE')=='PERSISTENT' and
          all(cfg.get(k)==v for k,v in {'ACTIVE_MODE':'1','BELIEF_ENABLED':'1','RELIABILITY_ENABLED':'1','LEGACY_TEMPORAL_WEIGHT_ENABLED':'0','LEGACY_TEMPORAL_HARD_REJECTION_ENABLED':'0'}.items()))
        fr=list(csv.DictReader((d/'ablation_frames.csv').open())); frames[mode,run]=fr
        hm=history_map(d/'belief_updates.csv'); by=defaultdict(list); finite=True; range_ok=True; formula_err=0.; rb_formula_err=0.; policy_values=set()
        for x in csv.DictReader((d/'optimizer_measurements.csv').open()):
            vals=[float(x[k]) for k in ('p','u','h','belief_reliability','dynamic_only_reliability','base_initial_chi2','q','effective_reliability','base_information_scale','effective_information_scale','final_chi2')]
            finite &= all(math.isfinite(v) for v in vals); range_ok &= all(0<=float(x[k])<=1 for k in ('p','u','h','belief_reliability','dynamic_only_reliability','effective_reliability'))
            rb=float(x['belief_reliability']); rd=float(x['dynamic_only_reliability']); q=float(x['q']); reff=float(x['effective_reliability'])
            want=rb if mode=='belief_only' else (max(rb,rd) if q<=1 else rb); formula_err=max(formula_err,abs(reff-want)); policy_values.add(x['measurement_policy']); by[int(x['frame_id'])].append(x)
            if mode=='geometry_protected':
                rb_formula_err=max(rb_formula_err,abs(rb-max(.05,(1-float(x['p']))*(1-float(x['u'])))))
        checked=bad=0
        for fid,fx in enumerate(fr):
            n=int(fx['initial_correspondences']);
            if n<=0: continue
            z=by[fid][-n:]; checked+=1
            if len(z)!=n or sum(int(x['final_inlier']) for x in z)!=int(fx['final_inliers']): bad+=1; continue
            for x in z:
                rb=float(x['belief_reliability']); reff=float(x['effective_reliability']); threshold=float(x['chi2_threshold']); final=float(x['final_chi2'])
                allm.append({'mode':mode,'run':run,'frame':fid,'mp':int(x['map_point_id']),'history':hm.get(int(x['map_point_id']),'other'),
                  'type':x['measurement_type'],'p':float(x['p']),'u':float(x['u']),'h':float(x['h']),'rb':rb,'rdyn':float(x['dynamic_only_reliability']),
                  'q':float(x['q']),'protected':int(x['geometry_protected']),'reff':reff,'base_info':float(x['base_information_scale']),
                  'effective_info':float(x['effective_information_scale']),'threshold':threshold,'base_final_chi2':final/reff if reff>0 else math.inf,
                  'base_final_inlier':int(final/reff<=threshold),'weighted_final_inlier':int(x['final_inlier']),'contributed':int(x['contributed_to_final_pose_optimization'])})
        met=json.loads((d/'eval/metrics.json').read_text()); tsr,pmr,gaps=coverage(at,traj_times(d/'CameraTrajectory.txt'))
        run_rows.append({'mode':mode,'run':run,'ATE_RMSE':met['ate']['rmse'],'RPE_translation':met['rpe_trans']['rmse'],'RPE_rotation_deg':met['rpe_rot_deg']['rmse'],
          'TSR':tsr,'PMR':pmr,'gaps':gaps,'initial_correspondences':mean([int(x['initial_correspondences']) for x in fr]),
          'final_inliers':mean([int(x['final_inliers']) for x in fr]),'optimization_acceptance':mean([int(x['optimization_acceptance']) for x in fr])})
        integrity.append({'mode':mode,'run':run,'config_ok':int(config_ok),'policy_values':'|'.join(sorted(policy_values)),'finite':int(finite),'range_ok':int(range_ok),'max_policy_formula_error':formula_err,'max_gp_rb_formula_error':rb_formula_err,'frames_checked':checked,'frame_alignment_errors':bad})
    write(a.out/'per_run_metrics.csv',run_rows); write(a.out/'integrity.csv',integrity)
    group=[]
    for mode in MODES:
      for k in ('ATE_RMSE','RPE_translation','RPE_rotation_deg','TSR','PMR','gaps','initial_correspondences','final_inliers','optimization_acceptance'):
        v=[x[k] for x in run_rows if x['mode']==mode]; group.append({'mode':mode,'metric':k,'mean':mean(v),'sample_std':std(v)})
    write(a.out/'group_metrics.csv',group)
    paired=[]
    for k in ('ATE_RMSE','RPE_translation','RPE_rotation_deg','TSR','PMR','gaps','initial_correspondences','final_inliers','optimization_acceptance'):
        ds=[]
        for run in RUNS:
            b=next(x[k] for x in run_rows if x['mode']=='belief_only' and x['run']==run); g=next(x[k] for x in run_rows if x['mode']=='geometry_protected' and x['run']==run); ds.append(g-b)
        baseline_mean=mean([x[k] for x in run_rows if x['mode']=='belief_only'])
        paired.append({'metric':k,'mean_paired_difference_GP_minus_BELIEF':mean(ds),'sample_std':std(ds),'relative_difference_percent':100*mean(ds)/baseline_mean if baseline_mean else math.nan})
    write(a.out/'paired_differences.csv',paired)
    gp=[x for x in allm if x['mode']=='geometry_protected']; activation=[]
    for hist in ('all','stable','contradictory','other'):
        z=gp if hist=='all' else [x for x in gp if x['history']==hist]; p=[x for x in z if x['protected']]
        row={'history':hist,'measurement_count':len(z),'protected_count':len(p),'protected_ratio':len(p)/len(z) if z else math.nan}; row.update({f'protected_{k}':v for k,v in summary(p).items()}); activation.append(row)
    write(a.out/'protection_activation.csv',activation)
    restore=[]
    failure_keys={}
    for mode in MODES:
      ks=set()
      for run in RUNS:
        fr=frames[mode,run]
        for i in range(1,len(fr)):
          if int(fr[i-1]['tracking_success']) and not int(fr[i]['tracking_success']): ks.update((run,j) for j in range(max(0,i-10),i))
      failure_keys[mode]=ks
    for scope,z in [('all',gp),('failure_precursor',[x for x in gp if (x['run'],x['frame']) in failure_keys['geometry_protected']])]+[(h,[x for x in gp if x['history']==h]) for h in ('stable','contradictory','other')]:
        z=[x for x in z if x['q']<=1]; base=sum(x['base_info'] for x in z); belief=sum(x['base_info']*x['rb'] for x in z); actual=sum(x['effective_info'] for x in z)
        restore.append({'scope':scope,'count':len(z),'base_budget':base,'belief_only_budget':belief,'actual_budget':actual,'restoration_fraction':(actual-belief)/(base-belief) if base>belief else math.nan,'retained_vs_base':actual/base if base else math.nan})
    write(a.out/'information_restoration.csv',restore)
    safety=[]
    for lo,hi,label in [(0,.2,'0<=p<0.2'),(.2,.5,'0.2<=p<0.5'),(.5,.8,'0.5<=p<0.8'),(.8,1.000001,'0.8<=p<=1')]:
        z=[x for x in gp if lo<=x['p']<hi]; protected=[x for x in z if x['protected']]
        violations=[x for x in protected if x['reff']>max(.05,1-x['p'])+1e-6]
        safety.append({'axis':'p','bin':label,**summary(z),'protected_count':len(protected),'protected_ratio':len(protected)/len(z) if z else math.nan,
          'max_reff':max([x['reff'] for x in z],default=math.nan),'dynamic_cap_violation_count':len(violations),
          'max_dynamic_cap_violation':max([x['reff']-max(.05,1-x['p']) for x in protected],default=math.nan)})
    hc=[x for x in gp if x['p']>=.8 and x['u']<=.3]
    safety.append({'axis':'high_conf_dynamic','bin':'p>=0.8,u<=0.3',**summary(hc),'max_reff':max([x['reff'] for x in hc],default=math.nan),'max_dynamic_cap_violation':max([x['reff']-max(.05,1-x['p']) for x in hc],default=math.nan)})
    for lo,hi,label in [(0,.5,'q<=0.5'),(.5,1,'0.5<q<=1'),(1,2,'1<q<=2'),(2,math.inf,'q>2')]:
        z=[x for x in gp if lo < x['q'] <= hi] if lo else [x for x in gp if x['q']<=hi]; safety.append({'axis':'q','bin':label,**summary(z),'protected_ratio':mean([x['protected'] for x in z])})
    write(a.out/'policy_safety.csv',safety)
    fail=[]
    for mode in MODES:
      events=[]
      for run in RUNS:
        fr=frames[mode,run]
        events += [(run,i) for i in range(1,len(fr)) if int(fr[i-1]['tracking_success']) and not int(fr[i]['tracking_success'])]
      keys={(r,j) for r,i in events for j in range(max(0,i-10),i)}; z=[x for x in allm if x['mode']==mode and (x['run'],x['frame']) in keys]
      frows=[frames[mode,r][j] for r,j in keys]
      rejected_events=sum(int(frames[mode,r][i-1]['optimization_acceptance']) and not int(frames[mode,r][i]['optimization_acceptance']) for r in RUNS for i in range(1,len(frames[mode,r])))
      fail.append({'mode':mode,'tracking_lost_events':len(events),'optimization_rejected_events':rejected_events,
        'gap_starts':next(x['gaps'] for x in run_rows if x['mode']==mode and x['run']==RUNS[0]) if False else sum(x['gaps'] for x in run_rows if x['mode']==mode),
        'precursor_frame_samples':len(keys),'mean_initial_correspondences':mean([int(x['initial_correspondences']) for x in frows]),'mean_final_inliers':mean([int(x['final_inliers']) for x in frows]),'optimization_acceptance':mean([int(x['optimization_acceptance']) for x in frows]),'mean_reff':mean([x['reff'] for x in z]),'effective_information_budget_per_frame':sum(x['effective_info'] for x in z)/len(keys) if keys else math.nan,
        'stable_effective_budget_per_frame':sum(x['effective_info'] for x in z if x['history']=='stable')/len(keys) if keys else math.nan,
        'contradictory_effective_budget_per_frame':sum(x['effective_info'] for x in z if x['history']=='contradictory')/len(keys) if keys else math.nan,
        'other_effective_budget_per_frame':sum(x['effective_info'] for x in z if x['history']=='other')/len(keys) if keys else math.nan,
        'protected_measurement_ratio':mean([x['protected'] for x in z])})
    write(a.out/'failure_precursor_summary.csv',fail)
    asym=[]
    for run in RUNS:
      b=frames['belief_only',run]; g=frames['geometry_protected',run]; n=min(len(b),len(g))
      bo=sum(int(b[i]['optimization_acceptance']) and not int(g[i]['optimization_acceptance']) for i in range(n))
      go=sum(int(g[i]['optimization_acceptance']) and not int(b[i]['optimization_acceptance']) for i in range(n))
      both=sum(int(g[i]['optimization_acceptance']) and int(b[i]['optimization_acceptance']) for i in range(n))
      neither=n-bo-go-both
      asym.append({'run':run,'paired_frames':n,'belief_only_only_accepted':bo,'gp_only_accepted':go,'both_accepted':both,'neither_accepted':neither})
    write(a.out/'acceptance_asymmetry.csv',asym)
    normal=[]
    for run in RUNS:
      b=frames['belief_only',run]; g=frames['geometry_protected',run]; ids=[i for i in range(min(len(b),len(g))) if int(b[i]['optimization_acceptance']) and int(g[i]['optimization_acceptance'])]
      normal.append({'run':run,'paired_accepted_frames':len(ids),
        'mean_delta_initial_GP_minus_BELIEF':mean([int(g[i]['initial_correspondences'])-int(b[i]['initial_correspondences']) for i in ids]),
        'mean_delta_final_inliers_GP_minus_BELIEF':mean([int(g[i]['final_inliers'])-int(b[i]['final_inliers']) for i in ids])})
    write(a.out/'normal_accepted_paired.csv',normal)
    # Real-run representation diagnostics: validate frozen equations/ranges, without requiring stochastic runs to match.
    rep=[]; rep_groups=[]
    for mode in MODES:
      vals=[]; bad=0; finite=True
      for run in RUNS:
        hm=history_map(a.root/mode/run/'belief_updates.csv')
        for x in csv.DictReader((a.root/mode/run/'belief_updates.csv').open()):
          nums=[float(x[k]) for k in ('after_observation_p','after_observation_u','persistence_after','final_reliability')]; finite &= all(math.isfinite(v) for v in nums); bad += any(v<0 or v>1 for v in nums); vals.append(nums)
          kind=hm.get(int(x['map_point_id']),'other')
          if kind in ('stable','contradictory'): rep_groups.append({'mode':mode,'history':kind,'u':nums[1]})
      rep.append({'mode':mode,'rows':len(vals),'finite':int(finite),'range_violations':bad,'mean_p':mean([x[0] for x in vals]),'mean_u':mean([x[1] for x in vals]),'mean_h':mean([x[2] for x in vals])})
    write(a.out/'representation_diagnostics.csv',rep)
    pop=[]
    for kind in ('stable','contradictory'):
      b=[x['u'] for x in rep_groups if x['mode']=='belief_only' and x['history']==kind]; g=[x['u'] for x in rep_groups if x['mode']=='geometry_protected' and x['history']==kind]
      pop.append({'history':kind,'belief_only_count':len(b),'gp_count':len(g),'belief_only_mean_u':mean(b),'gp_mean_u':mean(g),'delta_u_gp_minus_belief':mean(g)-mean(b)})
    write(a.out/'representation_population_shift.csv',pop)
    (a.out/'summary.json').write_text(json.dumps({'runs':len(MODES)*len(RUNS),'all_integrity_ok':all(x['config_ok'] and x['finite'] and x['range_ok'] and x['max_policy_formula_error']<1e-9 and x['frame_alignment_errors']==0 for x in integrity)},indent=2)+'\n')

if __name__=='__main__': main()
