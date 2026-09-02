#!/usr/bin/env python3
"""Generate reviewer-safe provenance and manuscript evidence from completed outputs."""
from pathlib import Path
import csv,json
R=Path(__file__).resolve().parents[1];BASE=R/'results/paa_prl_strengthening';OUT=BASE/'manuscript_evidence';OUT.mkdir(parents=True,exist_ok=True)
def rows(p):return list(csv.DictReader(p.open(encoding='utf-8-sig')))
ds=rows(BASE/'dsslam_repeated/dsslam_sequence_summary.csv');dc=rows(BASE/'dsslam_repeated/dsslam_vs_temporal_summary.csv');bs=rows(BASE/'bonn_cross_dataset/bonn_sequence_summary.csv');bc=rows(BASE/'bonn_cross_dataset/bonn_semantic_vs_temporal.csv')
hist='''# Historical Bonn provenance audit

## Classification: NOT COMPARABLE

The historical rows (`walking≈0.0465`, `sitting≈0.0418`, `crowd≈0.0381`) must not enter the current PAA quantitative tables.

Evidence:

- Historical commands are preserved under `experiment_new/results/bonn_runs/*/ours/command.txt`.
- They invoke `--method full --device cpu`, not the current core Temporal configuration.
- They contain one run per sequence, without a five-run predetermined protocol.
- Commit `6e57296f74e4cd80b1f7b7675764717921bd78fd` is an ancestor snapshot, but its `SemanticConfig.h` used person threshold=1.0, increment=3.0, decay=0.85. Current frozen values are 2.0, 1.0, 0.90.
- The historical result CSV is not recoverable as a tracked file at that commit, and per-run executable/config/model hashes are absent.
- Sequence directories correspond to person_tracking, synchronous, and crowd, but configuration, parameters, device, repetition count, and provenance differ.

The old values may be described only as superseded development-stage observations, not as current evidence or a secondary quantitative comparison.
''';(BASE/'historical_bonn_provenance.md').write_text(hist)

core='''# Core claim matrix

| Evidence level | Question | Evidence | Supported conclusion | Claim boundary |
|---|---|---|---|---|
| Continuity | Does Temporal reduce persistent MapPoint switching? | Six-sequence TUM repeated SF; three-sequence Bonn repeated SF | SF decreases on all evaluated TUM sequences and all three Bonn sequences | Lower SF means continuity, not correctness |
| Correctness | Are dynamic states more correct? | Existing 120-frame manual TUM validation | Temporal persistence changes the precision/recall trade-off; stability is not equivalent to correctness | No Bonn correctness claim; Bonn GT unavailable |
| Downstream SLAM | Does changed selection help tracking/localization? | ATE, RPE, TSR, PMR, gaps, failures | Effects are scene dependent | No universal localization-improvement claim |
| External context | How does Temporal compare with DS-SLAM? | New 6×5 DS-SLAM protocol versus frozen Temporal 5-run summaries | Repeated external reference is available; coverage must accompany ATE | Local DS-SLAM provenance is not fully verifiable; no paired p-value |
| Extension | Does Full always help? | Existing TUM Full results | Full is an exploratory object-level extension | Not the core proposed configuration; not universally beneficial |
''';(OUT/'core_claim_matrix.md').write_text(core)

outline='''# Results restructuring recommendation

## 5.1 Overall Localization and Tracking Results
Keep one compact TUM accuracy/coverage overview. Move detailed mechanism claims out of this subsection. Delete repeated prose that ranks configurations by ATE alone.

## 5.2 Temporal Continuity of Persistent MapPoints
Move the TUM Semantic-versus-Temporal SF paragraph and state-switching figure here. Add the Bonn frozen-parameter SF reductions. This is the primary mechanism result.

## 5.3 Dynamic-State Correctness
Move the 120 annotated-frame observation-level confusion-matrix experiment here. State explicitly that continuity is not correctness and discuss Precision/Recall/F1/BA/FPR/FNR jointly with SF.

## 5.4 Downstream SLAM Consequences
Move ATE/RPE, TSR/PMR, gaps and failures here. Delete or rewrite any sentence interpreting lower ATE without coverage. Explain person_tracking as favorable, synchronous as degradation, and crowd as incomplete tracking.

## 5.5 Repeated External Comparison with DS-SLAM
Replace the exploratory one-run DS-SLAM table/figure with the new five-run-per-sequence table. Retain the local-provenance limitation and do not claim paired significance.

## 5.6 Cross-Dataset Generalization on Bonn RGB-D
Report exact IDs: rgbd_bonn_person_tracking, rgbd_bonn_synchronous, rgbd_bonn_crowd. Present frozen parameters, SF continuity, and scene-dependent downstream outcomes. Do not include historical Bonn numbers.

## 5.7 Exploratory Object-Level Extension
Move and compress Full-related paragraphs here. Delete wording that treats Full as the universally strongest method.

## 5.8 Decay Sensitivity
Keep v2 forgetting-rate results and the persistence–responsiveness/correctness trade-off. Remove the superseded clamped-factor sensitivity.

## 5.9 Runtime
Keep measured Temporal overhead and identify the semantic frontend as the dominant bottleneck where supported. Do not compare unlike internal/runtime definitions.
''';(OUT/'results_restructure.md').write_text(outline)

def table(items,cols):
 s='| '+' | '.join(cols)+' |\n|'+'|'.join(['---']*len(cols))+'|\n'
 for r in items:s+='| '+' | '.join(str(r.get(c,'')) for c in cols)+' |\n'
 return s
tables='# Tables for manuscript\n\n## Repeated DS-SLAM baseline\n\n'+table(ds,['sequence','ATE_mean','ATE_std','RPE_translation_mean','RPE_rotation_mean','TSR_mean','PMR_mean','incomplete_count','failure_count'])
tables+='\nCaption: Repeated local DS-SLAM results over five predetermined runs per TUM sequence. ATE/RPE are computed for valid trajectories; coverage and incomplete/failure counts retain all runs. The local implementation provenance is not fully verifiable, and SF is not available.\n\n## Frozen-parameter Bonn cross-dataset results\n\n'+table(bs,['sequence','configuration','ATE_RMSE_mean','ATE_RMSE_std','RPE_translation_mean','RPE_rotation_mean','TSR_mean','PMR_mean','SF_mean','incomplete_count','failure_count'])
tables+='\nCaption: Frozen-parameter Semantic and Temporal results on three Bonn RGB-D Dynamic sequences, five predetermined runs per cell. Lower SF indicates greater temporal continuity, not necessarily more accurate dynamic-state classification or better tracking.\n'
(OUT/'tables_for_manuscript.md').write_text(tables)

abstract='''# Abstract update candidate

Across six repeated TUM RGB-D sequences, MapPoint-level temporal evidence consistently reduced state-switching frequency, while manual observation-level validation showed that increased continuity does not necessarily imply improved dynamic-state correctness. With the same frozen parameters on three Bonn RGB-D Dynamic sequences, switching frequency was again reduced, but localization and trajectory coverage remained scene dependent: person tracking retained complete coverage with a small ATE reduction, whereas synchronous and crowd scenes showed degraded coverage and/or error. These results support cross-dataset continuity of the mechanism, not universal localization improvement.
''';(OUT/'abstract_update_candidate.md').write_text(abstract)
limits='''# Limitations update candidate

- The original single-sequence/clamped decay limitation is substantially mitigated by five distinct effective decay settings, but sensitivity is still evaluated on one TUM sequence.
- The external DS-SLAM comparison now uses five predetermined runs per sequence; however, the local checkout lacks verifiable Git metadata, so exact upstream provenance remains a limitation.
- Bonn extends dataset coverage under frozen parameters, but it has no independently aligned dynamic-state annotation in this study; correctness generalization is therefore not established.
- Bonn results reveal scene-dependent coverage degradation, especially on rgbd_bonn_synchronous, and should be presented as a limitation rather than hidden.
- Full remains exploratory and should not be framed as a universal improvement.
''';(OUT/'limitations_update_candidate.md').write_text(limits)
conclusion='''# Conclusion replacement candidate

This study isolates the role of observation-driven accumulation and temporal decay on persistent sparse MapPoints. Repeated TUM experiments show consistent reductions in state-switching frequency, while manual correctness validation demonstrates that temporal continuity and dynamic-state correctness are distinct objectives. Frozen-parameter Bonn experiments reproduce the continuity reduction across three additional scenes, but also show that its downstream effect on ATE, RPE, and trajectory coverage is scene dependent. Repeated DS-SLAM runs provide an external accuracy-and-coverage reference, subject to incomplete local implementation provenance. The evidence therefore supports persistent MapPoint-level temporal state maintenance as a mechanism for stabilizing dynamic decisions, not a claim of universal localization improvement; the object-level Full configuration remains an exploratory extension.
''';(OUT/'conclusion_update_candidate.md').write_text(conclusion)

p=BASE/'bonn_cross_dataset/bonn_protocol.json';j=json.load(open(p));j['orchestration_history']={'excluded_attempt_directory':str(BASE/'bonn_cross_dataset_aborted_orchestration_20260829T0841'),'reason':'cold-start socket timeout followed by operator interruption during diagnosis; no result counted in formal 30-row table','formal_restart':'clean root; 30 unique completed keys'};p.write_text(json.dumps(j,indent=2)+'\n')
print(OUT)
