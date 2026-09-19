# Frozen PAA results and provenance

## Accuracy campaign artifacts

| Artifact | SHA-256 |
|---|---|
| `Examples/RGB-D/rgbd_tum` used by the formal accuracy campaign | `0079490eaf05c513ce18b5de95f66e54c98ba30e47511d17bd5a26ae4fcbddc9` |
| `lib/libORB_SLAM2.so` used by the formal accuracy campaign | `85a1ec7d6c2786ad2fd2497ce0de2710c725a693ebd6b4d46c3bea63628c8687` |
| `scripts/evaluate_tum_metrics.py` | `cfdd35d556afcd5d080fe109396f5ffa7da1810a5e2c26a656c648216db24b13` |

The final internal benchmark contains 84 planned valid algorithm runs across
Vanilla, Legacy Temporal, V3 BELIEF_ONLY, and V4 GEOMETRY_PROTECTED. The
Vanilla/Legacy formal campaign records 36 original attempts, one pre-SLAM
infrastructure failure, one declared replacement, and 36 valid algorithm runs.
Failures and coverage limitations are retained; no best-run selection is used.

Authoritative internal result (not replaced by this package):

```text
experiment_new/paper2_belief_eval/output/final_internal_baseline_benchmark/
  final_internal_comparison.csv
SHA-256: 6d46679c02fb821b421d38dddc312db610bc5ef988c5ed316f05f929d325f519
```

## External DS-SLAM comparison

The external baseline comprises 18/18 successful OUR RUN trials: six sequences
times three predetermined runs. The local DS-SLAM source tree lacked Git
metadata, so its exact upstream revision is not fully verifiable. The campaign
used the same evaluator and associations; equivalent final-inlier
instrumentation was unavailable.

```text
experiment_new/external_dynamic_baselines/dsslam_six_sequence/
  dsslam_vs_v4_comparison.csv
SHA-256: 7213b808d93443d9acc59fc27070872fd9c70bfebd4887b7fd2bc392f68d3eca
```

Recorded DS-SLAM executable SHA-256:
`1914b48c8492fe4b30fe2ad97b783382fb42cc137f481b0b5dc4de58fa15f4dd`.

## Dedicated runtime campaign

Runtime used a separately instrumented lightweight binary and must not be
treated as the formal accuracy executable:

| Artifact | SHA-256 |
|---|---|
| Runtime `rgbd_tum` | `331a3609e265e16e28b9c51015e288f4ac3671d05dc4f61f3468923a5dc1a471` |
| Runtime `libORB_SLAM2.so` | `de0c8a80dd7618874a6a0c6af6858ebd54dfaf3705cff63e365d53ab13cfa074` |

```text
runtime_experiment/runtime_v4_vs_v3.csv
SHA-256: 7dea1b1a1670912f285efa435fa6cc0790067eadc83b041f3d9068980d88d3ba
```

The runtime protocol used one warm-up and three measured serial runs per cell,
lightweight logging, and one CPU/GPU platform. It supports hardware-specific
cost statements only.

## Metric protocol

- ATE: rigidly aligned translational RMSE in metres.
- RPE-t: frame-to-frame relative translation RMSE in metres.
- RPE-r: frame-to-frame relative rotation RMSE in degrees.
- TSR: valid estimated trajectory poses divided by association frames.
- PMR: `1-TSR`.
- Final inliers and acceptance: internal optimizer instrumentation only; not
  imputed for DS-SLAM.

ATE/RPE are interpreted jointly with coverage. Results with low TSR are not
treated as directly equivalent full-trajectory comparisons.
