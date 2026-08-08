# ORB-SLAM3 fr1 Metrics

| Sequence | Matches | ATE RMSE (m) | RPE-trans RMSE (m) | RPE-rot RMSE (deg) | Mean tracking time (s) | Median tracking time (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| fr1_xyz | 792 | 0.010462 | 0.006091 | 0.400968 | 0.031429 | 0.028544 |
| fr1_desk | 586 | 0.016205 | 0.009583 | 0.597504 | 0.032235 | 0.030254 |

Source trajectories:

- `orbslam3_runs_missing/fr1_xyz/CameraTrajectory.txt`
- `orbslam3_runs_missing/fr1_desk/CameraTrajectory.txt`

Evaluation outputs:

- `orbslam3_runs_missing/fr1_xyz/eval/metrics.json`
- `orbslam3_runs_missing/fr1_desk/eval/metrics.json`
