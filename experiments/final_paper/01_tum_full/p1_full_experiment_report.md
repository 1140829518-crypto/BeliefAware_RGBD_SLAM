# P1 Full TUM Repeated Experiment Report

## Completion

- Fixed run IDs completed: 15/15.
- Raw process `exit_0`: 13/15.
- Raw process nonzero/unknown: 2/15.
- Evidence-based experiment completion: 15/15.
- No failed run was deleted or replaced.
- Raw process status and experiment completion are independent; exit codes are never rewritten from artifact evidence.

## Statistical inclusion policy actually used

- ATE/RPE: all runs with a non-empty trajectory and valid `eval/metrics.json` (`has_legal_evaluation=1`). In P1 this is 5/5 runs for every sequence, including rpy run_01 and run_03; it is not limited to the three rpy `exit_0` runs.
- TSR/PMR and tracking gaps: all five fixed run IDs per sequence, derived from each trajectory against the association file, regardless of raw exit status.
- Tracking FPS: every run containing a parseable `runtime.txt`; P1 has this for all 15 runs.
- End-to-end FPS: every run with recorded outer runtime; P1 has this for all 15 runs.

## Per-run Status

| Sequence | Run | Original status | Raw process | Completion | Valid poses | ATE RMSE | RPE trans | TSR | PMR | Tracking FPS | End-to-end FPS |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| fr3_walking_xyz | run_01 | success | exit_0 | completed | 827 | 0.502111 | 0.020390 | 1.000000 | 0.000000 | 9.046417 | 6.693824 |
| fr3_walking_xyz | run_02 | success | exit_0 | completed | 827 | 0.517861 | 0.019272 | 1.000000 | 0.000000 | 9.199209 | 7.140240 |
| fr3_walking_xyz | run_03 | success | exit_0 | completed | 827 | 0.576413 | 0.020117 | 1.000000 | 0.000000 | 9.168088 | 7.118760 |
| fr3_walking_xyz | run_04 | success | exit_0 | completed | 827 | 0.592021 | 0.020691 | 1.000000 | 0.000000 | 8.907258 | 6.998455 |
| fr3_walking_xyz | run_05 | success | exit_0 | completed | 827 | 0.506151 | 0.019571 | 1.000000 | 0.000000 | 9.196586 | 7.158713 |
| fr3_walking_rpy | run_01 | interrupted | exit_130 | completed | 503 | 0.708897 | 0.050499 | 0.580831 | 0.419169 | 3.605540 | 3.202999 |
| fr3_walking_rpy | run_02 | success | exit_0 | completed | 34 | 0.031456 | 0.019123 | 0.039261 | 0.960739 | 3.649169 | 3.241939 |
| fr3_walking_rpy | run_03 | interrupted | exit_130 | completed | 160 | 0.036664 | 0.027178 | 0.184758 | 0.815242 | 3.624147 | 3.234663 |
| fr3_walking_rpy | run_04 | success | exit_0 | completed | 376 | 0.730244 | 0.115850 | 0.434180 | 0.565820 | 3.618364 | 3.244404 |
| fr3_walking_rpy | run_05 | success | exit_0 | completed | 377 | 0.819465 | 0.130441 | 0.435335 | 0.564665 | 3.704184 | 3.297038 |
| fr3_walking_halfsphere | run_01 | success | exit_0 | completed | 925 | 0.546454 | 0.021610 | 0.905975 | 0.094025 | 9.146453 | 7.060669 |
| fr3_walking_halfsphere | run_02 | success | exit_0 | completed | 646 | 0.529430 | 0.087763 | 0.632713 | 0.367287 | 9.305355 | 7.289371 |
| fr3_walking_halfsphere | run_03 | success | exit_0 | completed | 548 | 0.274866 | 0.036169 | 0.536729 | 0.463271 | 9.244878 | 7.211606 |
| fr3_walking_halfsphere | run_04 | success | exit_0 | completed | 690 | 0.178974 | 0.035149 | 0.675808 | 0.324192 | 8.914563 | 7.102305 |
| fr3_walking_halfsphere | run_05 | success | exit_0 | completed | 968 | 0.685452 | 0.028725 | 0.948090 | 0.051910 | 9.198617 | 7.301643 |

## Sequence Summary

| Sequence | n total | raw exit 0 | completed | legal eval | raw exit-0 rate | completion rate | ATE RMSE mean ± std | RPE trans mean ± std | TSR mean | PMR mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fr3_walking_xyz | 5 | 5 | 5 | 5 | 1.000 | 1.000 | 0.538911 ± 0.042124 | 0.020008 ± 0.000582 | 1.000000 | 0.000000 |
| fr3_walking_rpy | 5 | 3 | 5 | 5 | 0.600 | 1.000 | 0.465345 ± 0.395890 | 0.068619 ± 0.051352 | 0.334873 | 0.665127 |
| fr3_walking_halfsphere | 5 | 5 | 5 | 5 | 1.000 | 1.000 | 0.443035 ± 0.209126 | 0.041883 ± 0.026302 | 0.739863 | 0.260137 |

## Stability and Outliers

- `fr3_walking_xyz`: 2-sample-standard-deviation rule flags no run; no value was removed.
- `fr3_walking_rpy`: 2-sample-standard-deviation rule flags no run; no value was removed.
- `fr3_walking_halfsphere`: 2-sample-standard-deviation rule flags no run; no value was removed.
- `fr3_walking_rpy` recorded 3/5 success and 2/5 interrupted metadata states. Both interrupted directories nevertheless contain normal SLAM shutdown markers and valid evaluation files; see `fr3_walking_rpy_interruption_audit.md`. This metadata/runner inconsistency must accompany any accuracy summary.

## Artifacts

- Root: `/home/djn/123/ORB_SLAM2_AddSemantic/experiments/final_paper/01_tum_full`
- Every run directory contains its configuration and available terminal/SLAM/YOLO logs, trajectories, semantic statistics, and evaluation output.
- Environment and hashes: `experiment_environment.json`.
