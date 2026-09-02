#!/usr/bin/env python3
"""Analyze state continuity after true MapPoint-ID observation gaps."""
import csv,collections,json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];OUT=R/'results/reobservation';OUT.mkdir(parents=True,exist_ok=True)
SEQS=('fr3_walking_xyz','fr3_walking_rpy','fr3_walking_halfsphere','fr3_sitting_xyz','fr3_sitting_rpy','fr3_sitting_halfsphere')
def source(cfg,seq,i):
 if cfg=='Frame-Temporal': return R/'results/frame_temporal'/cfg/seq/f'run_{i:02d}'/'mappoint_projection_raw.csv','temporal_state'
 base='Temporal' if cfg=='MapPoint-Temporal' else cfg
 return R/'results/paa_prl'/base/seq/f'run_{i:02d}'/'attempt_01'/'mappoint_evidence_raw.csv','dynamic_state'
def gapbin(g): return '1-5' if g<=5 else '6-10' if g<=10 else '11-20' if g<=20 else '>20'
agg=collections.defaultdict(lambda:[0,set(),0,0,0]);malformed=0
with (OUT/'reobservation_events.csv').open('w',newline='') as fo:
 fields=['sequence','configuration','run','mappoint_id','frame_before','frame_after','gap_length','gap_bin','state_before','state_after','state_changed']
 w=csv.DictWriter(fo,fields);w.writeheader()
 for cfg in ('Semantic','Frame-Temporal','MapPoint-Temporal'):
  for seq in SEQS:
   for i in range(1,6):
    path,statecol=source(cfg,seq,i)
    if not path.exists(): continue
    last_by_mp={}; current_frame=None; frame_rows={}
    def flush():
     for mp,state in frame_rows.items():
      if mp in last_by_mp:
       before,old=last_by_mp[mp]; gap=current_frame-before-1
       if gap>=1:
        changed=int(old!=state); b=gapbin(gap)
        w.writerow({'sequence':seq,'configuration':cfg,'run':f'run_{i:02d}','mappoint_id':mp,
        'frame_before':before,'frame_after':current_frame,'gap_length':gap,'gap_bin':b,
        'state_before':old,'state_after':state,'state_changed':changed})
        a=agg[(seq,cfg,b)];a[0]+=1;a[1].add((i,mp));a[2]+=changed;a[3]+=int(old==1 and state==0);a[4]+=int(old==0 and state==1)
      last_by_mp[mp]=(current_frame,state)
    with path.open(newline='') as f:
     for row in csv.DictReader(f):
      try: fr=int(row['frame_id']);mp=int(row['map_point_id']);state=int(row[statecol])
      except (TypeError,ValueError,KeyError): malformed+=1;continue
      if current_frame is not None and fr!=current_frame: flush();frame_rows={}
      current_frame=fr;frame_rows[mp]=state
    if frame_rows:flush()
summary=[]
for (seq,cfg,b),(events,mps,changed,d2s,s2d) in sorted(agg.items()):
 summary.append({'sequence':seq,'configuration':cfg,'gap_bin':b,'event_count':events,
 'unique_mappoint_count':len(mps),'RSC':(events-changed)/events,'RSR':changed/events,
 'dynamic_to_static':d2s,'static_to_dynamic':s2d})
with (OUT/'reobservation_summary.csv').open('w',newline='') as f:w=csv.DictWriter(f,list(summary[0]));w.writeheader();w.writerows(summary)
protocol={'evaluation_unit':'re-observation event identified by exact run-local MapPoint ID',
 'gap_definition':'frame_after-frame_before-1','deduplication':'last row per (run, frame_id, map_point_id)',
 'bins':['1-5','6-10','11-20','>20'],'occlusion_claim':False,
 'note':'Observation gaps are not asserted to be physical occlusions.',
 'malformed_input_rows_excluded':malformed}
(OUT/'reobservation_protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
print('events',sum(x[0] for x in agg.values()),'summary_rows',len(summary))
