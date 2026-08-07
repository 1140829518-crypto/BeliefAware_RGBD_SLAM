# Retained Metrics

## 原始文件中保留的全部指标

- ATE_RMSE
- RPE_translation_RMSE
- RPE_rotation_RMSE
- FPS
- Total_Runtime_sec
- Input_Frames
- Valid_Poses
- Pose_Missing_Ratio
- Precision
- Recall
- F1
- Trajectory_Smoothness
- Switching_Frequency
- Label_Fluctuation
- Probability_Variance
- Mean_Probability_Change
- Temporal_Consistency_Score
- ID_Switches
- Average_Track_Length

这些指标继续保留在 `aggregated_results/sequence_results.csv`、`ablation_results.csv`、`statistical_summary.csv`、`temporal_metrics.csv` 和 `experiment_audit.md` 中，本次整理未修改原始统计文件。

## 论文主表采用的指标

- ATE (m)：定位精度指标，越低越好。
- RPE (m)：相邻位姿相对误差，反映相对轨迹稳定性，越低越好。
- FPS (frame/s)：端到端运行效率，越高越好。
- Pose Missing Ratio：轨迹输出不完整程度，越低越好，不等同于严格系统失败率。
- Switching Frequency：动态状态切换频率，越低表示帧级动态状态更连续。Baseline不输出动态目标状态，因此论文表中记为“—”，不参与该列比较。

## 论文主表暂不采用的指标

- F1-score：当前独立实验没有人工动态目标真值，Precision、Recall、F1无法严谨计算，不能使用旧实验F1替代，也不能由其他指标推算。
- Temporal Consistency Score：Baseline没有动态状态输出，得到TCS=1.0只是因为没有状态切换，容易被误读为Baseline时间一致性最好，因此不进入论文主表。
- Probability_Variance、Mean_Probability_Change：当前二进制没有输出逐目标动态概率序列，原始统计中为NA。
- ID_Switches、Average_Track_Length：当前输出没有可靠目标ID连续跟踪信息，原始统计中为NA。
- RPE_rotation_RMSE、Trajectory_Smoothness、Label_Fluctuation：作为补充指标保留在完整统计文件中，但为避免论文主表过宽，暂不纳入表5。
