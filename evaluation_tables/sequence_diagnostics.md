# Sequence Diagnostics

| Method | Sequence | 输入帧数 | 关键帧数 | 平均跟踪时间 (ms) | 平均动态点数 | 语义对象数 | 轨迹完整率 (%) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ORB-SLAM2 | fr1_xyz | 794 | 36 | 51.49 | 0.00 | -- | 99.75 |
| ORB-SLAM2 | fr1_desk | 586 | 77 | 61.57 | 0.00 | -- | 100.00 |
| ORB-SLAM2 | fr3_xyz | 827 | 160 | 103.87 | 0.00 | -- | 50.79 |
| ORB-SLAM2 | fr3_rpy | 866 | 327 | 100.91 | 0.00 | -- | 98.73 |
| ORB-SLAM2 | fr3_halfsphere | 1021 | 346 | 113.57 | 0.00 | -- | 76.40 |
| ORB-SLAM2 | fr3_static | 717 | 104 | 105.08 | 0.00 | -- | 82.29 |
| ORB-SLAM3 | fr1_xyz | 794 | 52 | 31.43 | -- | -- | 99.75 |
| ORB-SLAM3 | fr1_desk | 586 | 95 | 32.24 | -- | -- | 100.00 |
| ORB-SLAM3 | fr3_xyz | 827 | 384 | 66.98 | -- | -- | 99.88 |
| ORB-SLAM3 | fr3_rpy | 866 | 418 | 52.60 | -- | -- | 99.77 |
| ORB-SLAM3 | fr3_halfsphere | 1021 | 392 | 70.60 | -- | -- | 99.71 |
| ORB-SLAM3 | fr3_static | 717 | 81 | 49.82 | -- | -- | 98.33 |
| DS-SLAM | fr1_xyz | 794 | 63 | 3474.27 | -- | -- | 99.75 |
| DS-SLAM | fr1_desk | 586 | 162 | 3274.28 | -- | -- | 100.00 |
| DS-SLAM | fr3_xyz | 827 | 81 | 3329.37 | -- | -- | 99.88 |
| DS-SLAM | fr3_rpy | 866 | 213 | 3269.37 | -- | -- | 99.77 |
| DS-SLAM | fr3_halfsphere | 1021 | 98 | 5139.17 | -- | -- | 99.71 |
| DS-SLAM | fr3_static | 717 | 23 | 4466.80 | -- | -- | 98.33 |
| Dyna-SLAM | fr1_xyz | 794 | 64 | 654.30 | -- | -- | 99.50 |
| Dyna-SLAM | fr1_desk | 586 | 104 | 681.76 | -- | -- | 96.08 |
| Dyna-SLAM | fr3_xyz | 827 | -- | -- | -- | -- | -- |
| Dyna-SLAM | fr3_rpy | 866 | 74 | 1028.15 | -- | -- | 56.35 |
| Dyna-SLAM | fr3_halfsphere | 1021 | -- | -- | -- | -- | -- |
| Dyna-SLAM | fr3_static | 717 | 63 | 3245.71 | -- | -- | 67.09 |
| Hard Remove | fr1_xyz | 794 | 41 | 53.15 | 10.09 | -- | 99.75 |
| Hard Remove | fr1_desk | 586 | 76 | 77.90 | 0.18 | -- | 100.00 |
| Hard Remove | fr3_xyz | 827 | 262 | 103.03 | 263.83 | -- | 94.68 |
| Hard Remove | fr3_rpy | 866 | 150 | 73.08 | 251.15 | -- | 59.12 |
| Hard Remove | fr3_halfsphere | 1021 | 78 | 60.18 | 231.24 | -- | 51.42 |
| Hard Remove | fr3_static | 717 | 159 | 312.36 | 249.40 | -- | 93.44 |
| Ours | fr1_xyz | 794 | 41 | 78.74 | 10.08 | 8 | 99.75 |
| Ours | fr1_desk | 586 | 85 | 341.61 | 0.18 | 24 | 100.00 |
| Ours | fr3_xyz | 827 | 186 | 74.21 | 233.92 | 22 | 80.89 |
| Ours | fr3_rpy | 866 | 280 | 62.87 | 249.97 | 31 | 69.40 |
| Ours | fr3_halfsphere | 1021 | 84 | 64.24 | 233.84 | 14 | 52.20 |
| Ours | fr3_static | 717 | 181 | 266.68 | 249.12 | 12 | 92.75 |

Notes:

- `平均动态点数` uses the per-frame average of `dynamic_keypoints` when `SemanticDynamicStatistics.txt` is available.
- `语义对象数` counts rows in `SemanticObjects.txt`; `--` means that method did not export object-level semantic map data.
- `轨迹完整率` is `timestamp matches / input frames * 100` using each run's `eval/metrics.json`.
- Dyna-SLAM has no valid local trajectory for `fr3_xyz` and `fr3_halfsphere`, so those fields remain `--`.
