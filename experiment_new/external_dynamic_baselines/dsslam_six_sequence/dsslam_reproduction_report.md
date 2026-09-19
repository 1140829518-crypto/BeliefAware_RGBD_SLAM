# DS-SLAM six-sequence reproduction report

## Outcome

- Six sequences completed: **YES**
- Total formal attempts: **18**
- Successful runs: **18**
- Failed runs: **0**
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
