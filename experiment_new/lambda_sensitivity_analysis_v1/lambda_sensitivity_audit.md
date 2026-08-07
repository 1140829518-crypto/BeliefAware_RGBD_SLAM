# Lambda Sensitivity Audit

- Generated at: 2026-07-31T10:52:51
- Experiment root: `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/lambda_sensitivity_analysis_v1`
- Expected runs: 45
- Successful newly executed runs: 45
- Skipped existing completed runs: 0
- Failed runs: 0
- Force mode: False

## Real Program Invocation

- Real SLAM program was invoked through `scripts/run_tum_rgbd_experiment.py`.
- The runner calls `Examples/RGB-D/rgbd_tum` and evaluates `CameraTrajectory.txt` against TUM ground truth.
- No old metrics are copied or scaled by this script.

## Lambda Source and Effect

- Parameter source: environment variable `ORB_SLAM2_DYNAMIC_LAMBDA`.
- Code path: `include/SemanticConfig.h::DynamicScoreDecayForClass` reads `ORB_SLAM2_DYNAMIC_LAMBDA` and returns the decay used by `src/MapPoint.cc::UpdateSemanticDynamicScore`.
- Dynamic decision path: accumulated score is compared with `DynamicScoreThresholdForClass`; suppressed MapPoints are removed in `ORBmatcher` and `Tracking`.
- Current code exposes one global decay override. Therefore person decay is also set to the tested lambda in these runs; this limitation is recorded in every `run_config.json`.
- `gamma_c` and `theta_c` remain at code defaults: non-person gamma=1.0, theta=3.0; person gamma=3.0, theta=1.0.

## Actual Lambda Values

0.70, 0.80, 0.85, 0.90, 0.95

## Outputs

- Per-run directories: `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/lambda_sensitivity_analysis_v1/runs`
- Per-run CSV: `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/lambda_sensitivity_analysis_v1/results/lambda_per_run_results.csv`
- Summary CSV: `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/lambda_sensitivity_analysis_v1/results/lambda_results.csv`
- LaTeX table: `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/lambda_sensitivity_analysis_v1/results/table_lambda_sensitivity.tex`
- Figures: `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/lambda_sensitivity_analysis_v1/fig_lambda_sensitivity`

## Best Lambda by Mean Metric

- Lowest ATE: lambda=0.95 (0.471824)
- Lowest RPE: lambda=0.95 (0.045395)
- Lowest Switching Frequency: lambda=0.85 (0.017808)
- Recommended paper value by simple ATE+RPE+SwitchingFrequency criterion: lambda=0.95

## Failed Runs

- None.
