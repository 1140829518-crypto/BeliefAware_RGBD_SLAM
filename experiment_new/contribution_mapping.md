# 论文贡献-实验对应关系检查

本文主题为“基于时间一致性建模的鲁棒语义动态 RGB-D SLAM 方法”。为避免论文贡献与实验支撑脱节，下面整理每项贡献对应的实验、结果文件、论文图表以及审稿风险。

## 贡献1：时间一致性概率递推

贡献表述建议：

> 针对单帧语义检测在动态场景中容易出现漏检、误检和帧间抖动的问题，本文构建时间一致性概率递推模型，对动态目标状态进行跨帧累积估计，从而提高动态目标判别的连续性和稳定性。

对应实验：

- 动态检测实验
- 时间窗口参数敏感性实验
- 消融实验
- 失败案例分析

对应结果文件：

- `experiment_new/results/dynamic_detection_accuracy.csv`
- `experiment_new/results/time_window_sensitivity.csv`
- `experiment_new/results/ablation_comparison.csv`
- `experiment_new/failure_analysis/failure_analysis.md`
- `experiment_new/failure_analysis/failure_case.png`

对应论文图片：

- `experiment_new/paper_figures/Fig1_dynamic_probability.png`
- `experiment_new/paper_figures/Fig2_detection_accuracy.png`
- `experiment_new/paper_figures/Fig3_window_analysis.png`
- `experiment_new/paper_figures/Fig5_ablation.png`
- `experiment_new/failure_analysis/failure_case.png`

支撑情况：

- 动态检测实验中，YOLO+temporal consistency 的 F1-score 为 0.953201，高于 YOLO raw detection 的 0.939878 和 YOLO+motion consistency 的 0.663789，能够支撑“动态目标判别稳定性提升”的贡献。
- 时间窗口实验显示，N 从 1 增加到 10 时，ATE 从 0.551924 降至 0.517236，Smoothness 从 0.034686 降至 0.029101，能够支撑“时间累积改善轨迹平滑趋势”的结论。
- 失败案例分析补充说明了时间一致性在响应延迟、快速运动目标和遮挡情况下的局限，有助于体现论文表述的边界。

审稿风险：

- 消融实验中 `Baseline+Temporal Consistency` 的 ATE 和 RPE 并不优于 Baseline，不能用该表证明“时间一致性单独提升定位精度”。
- 动态检测实验当前没有分序列结果和 TP/FP/FN 数量，若审稿人追问真实标注来源，需要补充说明。

结论：

该贡献有实验支撑，但论文应强调“动态判别稳定性”和“轨迹平滑趋势”，避免表述为“单独显著降低所有轨迹误差”。

## 贡献2：对象级语义建图

贡献表述建议：

> 在语义动态点处理基础上，本文引入对象级语义建图机制，用于维护动态目标相关的对象信息，提高动态场景地图表达的可解释性，并为动态目标管理提供结构化信息。

对应实验：

- 语义地图展示
- 消融实验

对应结果文件：

- `experiment_new/results/ablation_comparison.csv`

对应论文图片：

- `experiment_new/paper_figures/Fig6_semantic_map.png`
- `experiment_new/paper_figures/Fig5_ablation.png`

支撑情况：

- 语义地图展示图能够直观说明系统具备对象级语义表达和动态点可视化能力。
- 消融实验中 `Baseline+Object-level Semantic Map` 与 `Baseline+Semantic Mask` 的 ATE、RPE、Failure Rate 完全相同，仅 FPS 存在差异。这说明当前消融表对对象级语义建图的定量支撑较弱。

审稿风险：

- 对象级语义建图目前主要由可视化图支撑，缺少专门的定量指标。
- 如果论文将该贡献写成“显著提升定位精度”，当前实验不支持。
- 审稿人可能要求对象级语义地图的评价指标，例如语义地图完整性、动态对象残留率、对象轨迹一致性或语义 IoU。

建议补充：

- 增加对象级地图质量指标，例如 object consistency、semantic map completeness、dynamic object residual ratio。
- 将贡献表述从“提升定位精度”调整为“提高地图语义表达和动态对象管理能力”。
- 在论文中明确 Fig. 6 是定性展示，Fig. 5 是模块影响分析，而不是对象级建图的充分定量证明。

结论：

该贡献目前有定性支撑，但定量支撑偏弱。若作为主要贡献之一，建议补充对象级地图评价指标；若不补充，应降低贡献表述强度。

## 贡献3：动态 SLAM 鲁棒性

贡献表述建议：

> 本文方法在动态 RGB-D 场景中通过语义先验、时间一致性和对象级动态管理协同工作，在保持较好实时性的同时提高轨迹运行稳定性，表现出较好的动态环境适应能力。

对应实验：

- TUM RGB-D 动态序列实验
- Bonn RGB-D Dynamic Dataset 实验
- 动态比例鲁棒性实验
- 轨迹稳定性分析

对应结果文件：

- `experiment_new/results/bonn_dynamic_comparison.csv`
- `experiment_new/results/bonn_dynamic_comparison_status.csv`
- `experiment_new/results/dynamic_ratio_test.csv`
- `experiment_new/results/trajectory_deviation_samples.csv`

对应论文图片：

- `experiment_new/paper_figures/Fig4_bonn_trajectory.png`
- `experiment_new/paper_figures/Fig1_dynamic_probability.png`
- `experiment_new/figures/trajectory_stability_comparison.png`
- `experiment_new/figures/dynamic_ratio_curve.png`

支撑情况：

- Bonn 实验中 3 个序列 x 4 个方法共 12 组结果全部完成，状态均为 `ok`。
- 在 Bonn walking 和 sitting 序列中，本文方法取得较低 ATE；在 crowd 序列中，Dyna-SLAM 的 ATE 略低于本文方法，但本文方法取得更低 RPE 和明显更高 FPS。
- 本文方法在 Bonn 三个序列上的 FPS 分别为 8.925343、7.408893 和 11.124593，明显高于 DS-SLAM 和 Dyna-SLAM 的低帧率结果，能够支撑“鲁棒性与实时性折中”的结论。
- 动态比例鲁棒性实验中，随着动态比例从 0% 增至 50%，各方法 ATE 均上升。本文方法未取得最低 ATE，但 Failure Rate 增长相对平缓，可作为稳定性趋势分析。

审稿风险：

- 不能写“本文方法在 Bonn 所有序列上 ATE 最优”，因为 crowd 序列中 Dyna-SLAM ATE 为 0.033056，本文方法为 0.038137。
- 不能仅用动态比例 ATE 曲线证明本文方法最鲁棒，因为 Dyna-SLAM 和 DS-SLAM 在该表中 ATE 更低。
- 需要将“动态 SLAM 鲁棒性”的论证从单一 ATE 扩展到 RPE、FPS、Failure Rate 和轨迹稳定性。

结论：

该贡献有较完整实验支撑，但论文应写成“动态环境下具有更稳定趋势和较好综合性能”，不要写成“所有误差指标最优”。

## 贡献支撑完整性检查

| 贡献 | 实验支撑 | 支撑强度 | 是否存在风险 |
|---|---|---|---|
| 时间一致性概率递推 | 动态检测、窗口实验、消融、失败案例 | 较强 | 消融结果不支持单独降低 ATE |
| 对象级语义建图 | 语义地图展示、消融实验 | 偏弱 | 缺少对象级地图定量指标 |
| 动态 SLAM 鲁棒性 | TUM、Bonn、动态比例、轨迹稳定性 | 较强 | 不能宣称所有 ATE/RPE 最优 |

## 是否存在没有实验支撑的贡献

检查结论：

- 时间一致性概率递推：有实验支撑。
- 动态 SLAM 鲁棒性：有实验支撑，但需要谨慎表述。
- 对象级语义建图：存在支撑不足问题，目前主要依赖语义地图展示和弱消融结果。

因此，当前唯一明显支撑不足的贡献是“对象级语义建图”。如果该内容作为论文核心贡献之一，建议补充对象级地图质量评价；如果暂时无法补充，应将其作为辅助模块或系统功能描述，而不是定位为强定量贡献。

## 建议最终贡献写法

推荐写法：

1. 提出一种时间一致性动态概率递推机制，通过跨帧概率累积抑制单帧语义检测抖动，提高动态目标判别的连续性。
2. 构建语义动态点处理与对象级语义地图表达框架，用于增强动态场景中地图的可解释性和对象管理能力。
3. 在 TUM RGB-D 和 Bonn RGB-D Dynamic Dataset 上验证了方法在动态环境下的稳定运行趋势，实验结果表明本文方法在轨迹精度、局部稳定性和实时性之间取得较好折中。

不建议写法：

- 本文方法在所有动态序列上取得最优 ATE。
- 对象级语义建图显著提升定位精度。
- 时间一致性模块单独加入即可提升所有 SLAM 指标。

