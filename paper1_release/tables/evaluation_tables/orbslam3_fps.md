# ORB-SLAM3 FPS

| Methods | fr1_xyz | fr1_desk | fr3_xyz | fr3_rpy | fr3_halfsphere | fr3_static |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ORB-SLAM3 | 31.82 | 31.02 | 14.93 | 19.01 | 14.16 | 20.07 |

FPS is computed as `1 / mean_tracking_time` from ORB-SLAM3 RGB-D runs.

| Sequence | Mean tracking time (s) | Median tracking time (s) | FPS |
| --- | ---: | ---: | ---: |
| fr1_xyz | 0.031429 | 0.028544 | 31.82 |
| fr1_desk | 0.032235 | 0.030254 | 31.02 |
| fr3_xyz | 0.066983 | 0.062158 | 14.93 |
| fr3_rpy | 0.052597 | 0.045317 | 19.01 |
| fr3_halfsphere | 0.070604 | 0.065586 | 14.16 |
| fr3_static | 0.049824 | 0.045567 | 20.07 |
