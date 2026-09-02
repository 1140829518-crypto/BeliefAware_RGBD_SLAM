# P2 Four-method TUM Comparison Report

## Execution integrity

- New P2 runs: 45/45 fixed run IDs; all recorded `exit_0 + completed`.
- Full: reused unchanged P1 15 runs; no Full rerun or replacement.
- Temporal actual configuration: SemanticMode=2, Shadow=0, Active=0. Shadow is unnecessary for Temporal trajectory generation because MapPoint evidence and suppression are independent of ObjectDynamic Adapter; disabling it removes only object-level observation/logging.

## Summary

| Method | Sequence | n | completed | legal eval | ATE RMSE | RPE trans | RPE rot | TSR | PMR | gaps | Tracking FPS | End-to-end FPS |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ORB-SLAM2 | fr3_walking_xyz | 5 | 5 | 5 | 0.835129 ± 0.222270 | 0.030235 ± 0.002876 | 0.704208 ± 0.052295 | 0.709794 ± 0.085169 | 0.290206 ± 0.085169 | 1.000 ± 0.000 | 27.262 ± 0.943 | 9.469 ± 1.281 |
| ORB-SLAM2 | fr3_walking_rpy | 5 | 5 | 5 | 1.164329 ± 0.152318 | 0.071846 ± 0.042154 | 1.509621 ± 0.820178 | 0.992148 ± 0.007933 | 0.007852 ± 0.007933 | 0.800 ± 0.837 | 27.157 ± 1.167 | 16.048 ± 0.310 |
| ORB-SLAM2 | fr3_walking_halfsphere | 5 | 5 | 5 | 0.644462 ± 0.072637 | 0.042516 ± 0.011690 | 1.015329 ± 0.298280 | 0.785113 ± 0.053496 | 0.214887 ± 0.053496 | 4.000 ± 2.121 | 25.942 ± 0.989 | 13.547 ± 2.702 |
| Semantic | fr3_walking_xyz | 5 | 5 | 5 | 0.504876 ± 0.055832 | 0.020593 ± 0.000933 | 0.503245 ± 0.009725 | 1.000000 ± 0.000000 | 0.000000 ± 0.000000 | 0.000 ± 0.000 | 9.648 ± 0.273 | 7.284 ± 0.129 |
| Semantic | fr3_walking_rpy | 5 | 5 | 5 | 0.749207 ± 0.035709 | 0.095821 ± 0.034087 | 1.990388 ± 0.732092 | 0.644804 ± 0.107429 | 0.355196 ± 0.107429 | 5.200 ± 1.789 | 3.621 ± 0.019 | 3.218 ± 0.012 |
| Semantic | fr3_walking_halfsphere | 5 | 5 | 5 | 0.329266 ± 0.177200 | 0.033917 ± 0.006284 | 0.753824 ± 0.136595 | 0.606660 ± 0.055593 | 0.393340 ± 0.055593 | 7.600 ± 4.393 | 9.488 ± 0.144 | 7.321 ± 0.108 |
| Temporal | fr3_walking_xyz | 5 | 5 | 5 | 0.562268 ± 0.082441 | 0.020463 ± 0.000748 | 0.506879 ± 0.005322 | 1.000000 ± 0.000000 | 0.000000 ± 0.000000 | 0.000 ± 0.000 | 9.044 ± 0.116 | 6.751 ± 0.190 |
| Temporal | fr3_walking_rpy | 5 | 5 | 5 | 0.756381 ± 0.058433 | 0.109898 ± 0.036095 | 2.276387 ± 0.730095 | 0.515242 ± 0.087712 | 0.484758 ± 0.087712 | 6.000 ± 2.915 | 3.572 ± 0.016 | 3.177 ± 0.035 |
| Temporal | fr3_walking_halfsphere | 5 | 5 | 5 | 0.356207 ± 0.215751 | 0.030688 ± 0.002768 | 0.685497 ± 0.041880 | 0.724976 ± 0.174942 | 0.275024 ± 0.174942 | 5.200 ± 3.194 | 9.129 ± 0.060 | 7.058 ± 0.135 |
| Full | fr3_walking_xyz | 5 | 5 | 5 | 0.538911 ± 0.042124 | 0.020008 ± 0.000582 | 0.500840 ± 0.007940 | 1.000000 ± 0.000000 | 0.000000 ± 0.000000 | 0.000 ± 0.000 | 9.104 ± 0.126 | 7.022 ± 0.194 |
| Full | fr3_walking_rpy | 5 | 5 | 5 | 0.465345 ± 0.395890 | 0.068619 ± 0.051352 | 1.469133 ± 1.087748 | 0.334873 ± 0.218158 | 0.665127 ± 0.218158 | 4.200 ± 2.588 | 3.640 ± 0.039 | 3.244 ± 0.034 |
| Full | fr3_walking_halfsphere | 5 | 5 | 5 | 0.443035 ± 0.209126 | 0.041883 ± 0.026302 | 0.903543 ± 0.471233 | 0.739863 ± 0.178745 | 0.260137 ± 0.178745 | 5.200 ± 4.438 | 9.162 ± 0.150 | 7.193 ± 0.109 |

## Incremental comparisons

Percentage uses `(previous - current) / previous × 100%` for error metrics; positive means lower error. TSR is reported as percentage-point change.

### Semantic − ORB-SLAM2

| Sequence | ATE improvement | RPE trans improvement | TSR change | PMR change | gap change | Tracking FPS change | Coverage warning |
|---|---:|---:|---:|---:|---:|---:|---|
| fr3_walking_xyz | 39.55% | 31.89% | 29.02 pp | -29.02 pp | -1.00 | -64.61% | -- |
| fr3_walking_rpy | 35.65% | -33.37% | -34.73 pp | 34.73 pp | 4.40 | -86.67% | ATE improvement may be affected by reduced trajectory coverage. |
| fr3_walking_halfsphere | 48.91% | 20.23% | -17.85 pp | 17.85 pp | 3.60 | -63.43% | ATE improvement may be affected by reduced trajectory coverage. |
### Temporal − Semantic

| Sequence | ATE improvement | RPE trans improvement | TSR change | PMR change | gap change | Tracking FPS change | Coverage warning |
|---|---:|---:|---:|---:|---:|---:|---|
| fr3_walking_xyz | -11.37% | 0.63% | 0.00 pp | 0.00 pp | 0.00 | -6.26% | -- |
| fr3_walking_rpy | -0.96% | -14.69% | -12.96 pp | 12.96 pp | 0.80 | -1.34% | -- |
| fr3_walking_halfsphere | -8.18% | 9.52% | 11.83 pp | -11.83 pp | -2.40 | -3.79% | -- |
### Full − Temporal

| Sequence | ATE improvement | RPE trans improvement | TSR change | PMR change | gap change | Tracking FPS change | Coverage warning |
|---|---:|---:|---:|---:|---:|---:|---|
| fr3_walking_xyz | 4.15% | 2.22% | 0.00 pp | 0.00 pp | 0.00 | 0.66% | -- |
| fr3_walking_rpy | 38.48% | 37.56% | -18.04 pp | 18.04 pp | -1.80 | 1.91% | ATE improvement may be affected by reduced trajectory coverage. |
| fr3_walking_halfsphere | -24.38% | -36.48% | 1.49 pp | -1.49 pp | 0.00 | 0.37% | -- |

## Answers to the requested questions

1. Temporal relative to Semantic has not produced a stable three-sequence ATE improvement. See the table; coverage must be considered jointly.
2. The supported changes are the measured ATE/RPE, TSR/PMR, gaps and FPS values above; no unmeasured detection-accuracy conclusion is inferred.
3. ATE improved while TSR fell for Temporal vs Semantic on: none.
4. Full shows additional ATE benefit without more than 1 pp TSR loss on: fr3_walking_xyz; other cases are trade-offs or regressions.
5. Active filtering has a precision/coverage trade-off wherever lower ATE coincides with lower TSR, higher PMR or more gaps; those rows are explicitly warned above.
6. A paper main method cannot be selected from ATE alone. The defensible choice is the configuration with the best joint accuracy and coverage in the tables; scene-dependent Full results must be disclosed.
7. Shadow is best treated as an analysis mode because it observes object state without feedback. Temporal here is a real SLAM configuration, not merely analysis, because its MapPoint evidence suppresses matches.

## fr3_walking_rpy caution

Every rpy row must be cited as ATE + TSR + PMR. A low ATE with reduced valid-pose coverage is not evidence of better full-sequence localization. Full P1 includes two `exit_130 + completed` rows and all five legal evaluations, as required by the status policy.
