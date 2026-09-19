#!/usr/bin/env python3
import csv,json,statistics,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[3]; O=Path(__file__).resolve().parent
P=O/'dsslam_six_sequence_results.csv'; rows=list(csv.DictReader(open(P)))
# Fill preserved-run wall-clock runtime from its immutable status record.
for x in rows:
 if x['Runtime']=='see preserved prior status':
  s=json.load(open(R/'results/paa_prl_strengthening/dsslam_repeated'/x['Sequence']/x['Run']/'status.json'))
  x['Runtime']=str(1000*float(s['wall_time_seconds'])/float(s['expected_frames']))
with open(P,'w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
internal=list(csv.DictReader(open(R/'experiment_new/paper2_belief_eval/output/final_internal_baseline_benchmark/final_internal_comparison.csv',encoding='utf-8-sig')))
imap={'fr3_walking_xyz':'TUM xyz','fr3_walking_static':'TUM static','fr3_walking_rpy':'TUM rpy','rgbd_bonn_person_tracking':'Bonn person_tracking','rgbd_bonn_synchronous':'Bonn synchronous','rgbd_bonn_crowd':'Bonn crowd'}
def ms(rr,k):
 v=[float(x[k]) for x in rr];return statistics.mean(v),statistics.stdev(v)
fields=['Sequence','DS_runs','DS_success','DS_ATE_mean','DS_ATE_std','V4_ATE_mean','V4_ATE_std','DS_RPE_t_mean','DS_RPE_t_std','V4_RPE_t_mean','V4_RPE_t_std','DS_RPE_r_mean','DS_RPE_r_std','V4_RPE_r_mean','V4_RPE_r_std','DS_TSR_mean','DS_TSR_std','V4_TSR_mean','V4_TSR_std','DS_PMR_mean','DS_PMR_std','V4_PMR_mean','V4_PMR_std','DS_final_tracked_frames_mean','DS_final_tracked_frames_std','DS_runtime_ms_mean','DS_runtime_ms_std','ProtocolComparable','Notes']
comp=[]
for seq in imap:
 rr=[x for x in rows if x['Sequence']==seq]; v4=next(x for x in internal if x['Method']=='V4 Full' and x['Sequence']==imap[seq])
 d={'Sequence':seq,'DS_runs':len(rr),'DS_success':sum(x['Status']=='SUCCESS' for x in rr),'ProtocolComparable':'FULL','Notes':'DS exact upstream revision not verifiable; final inliers N/A because DS-SLAM lacks matching instrumentation'}
 for dk,ik in [('ATE','ATE_RMSE'),('RPE_t','RPE_translation'),('RPE_r','RPE_rotation_deg'),('TSR','TSR'),('PMR','PMR')]:
  a,b=ms(rr,dk);d[f'DS_{dk}_mean']=a;d[f'DS_{dk}_std']=b;d[f'V4_{dk}_mean']=v4[f'{ik}_mean'];d[f'V4_{dk}_std']=v4[f'{ik}_std']
 a,b=ms(rr,'final_tracked_frames');d['DS_final_tracked_frames_mean']=a;d['DS_final_tracked_frames_std']=b
 a,b=ms(rr,'Runtime');d['DS_runtime_ms_mean']=a;d['DS_runtime_ms_std']=b
 comp.append(d)
with open(O/'dsslam_vs_v4_comparison.csv','w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(comp)
attempts=len(rows);success=sum(x['Status']=='SUCCESS' for x in rows);failed=attempts-success
report=f'''# DS-SLAM six-sequence reproduction report

## Outcome

- Six sequences completed: **YES**
- Total formal attempts: **{attempts}**
- Successful runs: **{success}**
- Failed runs: **{failed}**
- Protocol compatibility: **FULL for dataset association, sequence boundaries, camera calibration, and metric definitions**
- Best-run selection: **NO**
- Failed-run discard/replacement: **NO**

## Protocol

Each sequence has three predetermined runs. TUM uses the frozen DS-SLAM TUM3 configuration. Bonn uses the project Bonn-specific calibration rather than TUM intrinsics. All trajectories were evaluated with `scripts/evaluate_tum_metrics.py` (SHA-256 `cfdd35d556afcd5d080fe109396f5ffa7da1810a5e2c26a656c648216db24b13`). TSR and PMR use the same association-frame coverage definition.

The first three existing xyz/rpy DS-SLAM trials were copied into this campaign and re-evaluated; their executable, configuration, model, dataset, and association hashes match the frozen protocol. The other twelve trials were newly executed. This reuse is declared and is not best-run selection.

## Coverage and instrumentation

All 18 processes and evaluations succeeded. TUM, Bonn person_tracking, and Bonn synchronous runs produced complete association-frame trajectories. All three Bonn crowd runs produced 927/928 poses; this observed incompleteness is retained. DS-SLAM does not expose the same final-inlier instrumentation as V4, so final inliers are reported as N/A rather than estimated.

Runtime is subprocess wall-clock time divided by association frames. It includes segmentation and tracking but is not directly interchangeable with the manuscript's dedicated nested-timer runtime experiment.

## Limitations

The local DS-SLAM source tree lacks `.git` metadata, so its exact upstream revision remains unverified. Accordingly, results must be labeled **OUR RUN (local DS-SLAM implementation; upstream provenance not fully verifiable)**. This limitation does not change the matched dataset/evaluator protocol, but it prevents claiming an exact reproduction of a named official revision.
'''
(O/'dsslam_reproduction_report.md').write_text(report)
(O/'external_comparison_section_update.md').write_text('''# Proposed external-comparison manuscript text

To provide an external dynamic-SLAM reference, DS-SLAM was evaluated under the same metric protocol on the three TUM walking and three Bonn dynamic sequences. Three predetermined runs were retained per sequence, including incomplete trajectories; no best-run selection or failure replacement was used. The TUM runs used the DS-SLAM TUM3 calibration, whereas the Bonn runs used the Bonn-specific calibration employed by the internal benchmark. All 18 runs completed successfully. The three Bonn crowd runs retained 927 of 928 associated frames; the remaining runs had complete association-frame coverage.

The comparison should be interpreted as an OUR RUN result from a local DS-SLAM implementation. Its exact upstream revision cannot be verified because the source tree lacks Git provenance. ATE, translational and rotational RPE, TSR, and PMR are directly evaluated with the frozen metric pipeline, while final-inlier counts are unavailable because DS-SLAM does not expose matching instrumentation. The results provide a controlled external reference under the evaluated protocol; they do not establish that V4 universally outperforms DS-SLAM or other dynamic-SLAM systems.
''')
print(attempts,success,failed,len(comp))
