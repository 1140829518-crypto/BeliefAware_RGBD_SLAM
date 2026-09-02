#!/usr/bin/env python3
import csv,collections,json,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[1];D=R/'results/reobservation'
order=['1-5','6-10','11-20','>20']
pooled=collections.defaultdict(lambda:[0,0,set()]); permp=collections.defaultdict(lambda:[0,0])
with (D/'reobservation_events.csv').open(newline='') as f:
 for r in csv.DictReader(f):
  k=(r['configuration'],r['gap_bin']);ch=int(r['state_changed']);
  pooled[k][0]+=1;pooled[k][1]+=ch;pooled[k][2].add((r['sequence'],r['run'],r['mappoint_id']))
  q=(r['sequence'],r['configuration'],r['gap_bin'],r['run'],r['mappoint_id']);permp[q][0]+=1;permp[q][1]+=ch
rows=[]
for (cfg,b),(n,ch,mps) in pooled.items(): rows.append({'configuration':cfg,'gap_bin':b,'event_count':n,'unique_run_local_mappoints':len(mps),'RSC':(n-ch)/n,'RSR':ch/n})
rows.sort(key=lambda x:(x['configuration'],order.index(x['gap_bin'])))
with (D/'reobservation_overall.csv').open('w',newline='') as f:w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
rob=collections.defaultdict(list)
for (seq,cfg,b,run,mp),(n,ch) in permp.items():rob[(cfg,b)].append((n-ch)/n)
mr=[]
for (cfg,b),v in rob.items():mr.append({'configuration':cfg,'gap_bin':b,'mappoint_count':len(v),'mean_per_mappoint_RSC':sum(v)/len(v)})
mr.sort(key=lambda x:(x['configuration'],order.index(x['gap_bin'])))
with (D/'reobservation_mappoint_robustness.csv').open('w',newline='') as f:w=csv.DictWriter(f,list(mr[0]));w.writeheader();w.writerows(mr)

import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
colors={'Semantic':'#f28e2b','Frame-Temporal':'#9467bd','MapPoint-Temporal':'#2ca02c'}
fig,ax=plt.subplots(figsize=(6.8,4.2))
for cfg in colors:
 q=[x for x in rows if x['configuration']==cfg];ax.plot(order,[next(x['RSC'] for x in q if x['gap_bin']==b) for b in order],marker='o',label=cfg,color=colors[cfg])
ax.set_xlabel('Observation-gap length (frames)');ax.set_ylabel('Re-observation State Consistency (RSC)');ax.set_ylim(0,1);ax.grid(False);ax.legend(frameon=False);fig.tight_layout()
fig.savefig(D/'reobservation_rsc_by_gap.pdf');fig.savefig(D/'reobservation_rsc_by_gap.png',dpi=600);plt.close(fig)

audit=f'''# Re-observation analysis audit

- Events: {sum(x['event_count'] for x in rows):,}.
- Identity: exact run-local MapPoint ID; IDs are never joined across runs.
- Deduplication: last state per `(configuration, sequence, run, frame, MapPoint)`.
- Gap: `frame_after - frame_before - 1`; only gaps >=1 are events.
- Physical occlusion cause is not observable and is **not claimed**.
- Three malformed tail rows from terminated failure logs were excluded and recorded in the protocol.
- RSC/RSR measure continuity, not correctness.
- Recovery delay is not reported: the logs do not provide a defensible reference state or recovery target after re-observation.
'''
(D/'reobservation_audit.md').write_text(audit)
print('done',len(rows),len(mr))
