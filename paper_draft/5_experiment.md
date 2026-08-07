# 4 实验

本章实验内容采用 `experiment_new/final_submission/final_experiment_section.md` 作为最终版本。为保证投稿材料一致性，论文正文中的表格和图片引用均来自 `experiment_new/final_submission/`。

## 4.1 数据集和评价指标

本文使用 TUM RGB-D 数据集和 Bonn RGB-D Dynamic Dataset。TUM RGB-D 实验主要用于验证动态环境下的轨迹精度、动态比例鲁棒性和时间一致性模块效果；Bonn RGB-D Dynamic Dataset 用于补充验证方法在真实动态 RGB-D 数据上的泛化能力。

评价指标包括 ATE RMSE、RPE translation RMSE、FPS、Precision、Recall、F1-score、Smoothness 和 Failure Rate。TUM ATE/RPE 对比见表 `final_tables/Table1_TUM_ATE_RPE.tex`，Bonn 结果见表 `final_tables/Table2_Bonn_Dynamic_Results.tex`。

## 4.2 TUM RGB-D 实验

TUM 实验结果表明，动态目标会显著影响 RGB-D SLAM 的轨迹估计稳定性。随着动态点比例增加，各方法 ATE 均呈上升趋势。本文方法在该实验中并非 ATE 最低方法，但其 Failure Rate 增长相对平缓，说明时间一致性动态处理在保持长期稳定方面具有一定优势。

表格引用：

- 表 1：`experiment_new/final_submission/final_tables/Table1_TUM_ATE_RPE.tex`

## 4.3 Bonn 动态数据集实验

Bonn 实验选取 walking、sitting 和 crowd 三个动态序列，对比 ORB-SLAM3、DS-SLAM、Dyna-SLAM 和本文方法。结果表明，本文方法在 walking 和 sitting 序列上取得较低 ATE，在 crowd 序列上 Dyna-SLAM 的 ATE 略低于本文方法，但本文方法取得更低 RPE 和明显更高 FPS。该结果说明本文方法不是单项误差指标的绝对领先方案，但在动态场景下具有较好的精度、稳定性和效率折中。

表格与图片引用：

- 表 2：`experiment_new/final_submission/final_tables/Table2_Bonn_Dynamic_Results.tex`
- 图 4：`experiment_new/final_submission/final_figures/Fig4_Bonn_trajectory.png`

## 4.4 时间一致性模块验证

动态目标检测实验比较 YOLO 原始检测、YOLO+motion consistency 和 YOLO+temporal consistency。结果表明，时间一致性方法的 F1-score 为 0.9532，高于 YOLO 原始检测和 YOLO+motion consistency。动态概率曲线显示，时间一致性建模能够抑制单帧检测抖动，使动态状态估计更加连续。

表格与图片引用：

- 表 3：`experiment_new/final_submission/final_tables/Table3_Dynamic_Detection_Accuracy.tex`
- 图 1：`experiment_new/final_submission/final_figures/Fig1_Dynamic_probability.png`
- 图 2：`experiment_new/final_submission/final_figures/Fig2_Detection_accuracy.png`

## 4.5 参数敏感性分析

时间窗口参数实验设置 N=1、3、5、10、15。结果显示，随着窗口增大，轨迹 Smoothness 逐渐降低，说明平滑性提升；ATE 在 N=10 附近较低，但继续增大窗口到 N=15 时 ATE 略有回升。这表明过大时间窗口可能引入响应延迟，实际应用中需在稳定性和响应速度之间折中。

表格与图片引用：

- 表 4：`experiment_new/final_submission/final_tables/Table4_Parameter_Sensitivity.tex`
- 图 3：`experiment_new/final_submission/final_figures/Fig3_Window_analysis.png`

## 4.6 消融实验

消融实验分析 Baseline、Semantic Mask、Temporal Consistency、Object-level Semantic Map 和 Full Model。结果显示，时间一致性模块单独加入并不必然降低轨迹误差，其主要作用是稳定动态目标判别。对象级语义地图更多体现为地图表达和动态对象管理能力，其定量定位收益需要结合完整系统和更多地图质量指标评价。

表格与图片引用：

- 表 5：`experiment_new/final_submission/final_tables/Table5_Ablation.tex`
- 图 5：`experiment_new/final_submission/final_figures/Fig5_Ablation.png`
- 图 6：`experiment_new/final_submission/final_figures/Fig6_Semantic_map.png`

