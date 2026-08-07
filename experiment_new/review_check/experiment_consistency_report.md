# experiment_new 实验结果审稿级一致性检查报告

检查日期：2026-07-27  
检查范围：`experiment_new/results/*.csv`、`experiment_new/figures/*.png`、`experiment_new/tables/*.tex`、`experiment_new/paper_text/bonn_experiment.md`

## 1. 总体结论

当前 `experiment_new` 中 Bonn RGB-D Dynamic Dataset 实验已经形成完整实跑结果：3 个序列、4 个方法，共 12 组实验，`bonn_dynamic_comparison_status.csv` 中状态均为 `ok`。这部分可以作为论文新增数据集实验的主要结果来源。

但从《机器人》期刊审稿角度看，整个实验包仍存在若干会被质疑的点：部分 CSV 是模板或 pending 项，部分消融和鲁棒性结果与论文主张存在排名矛盾，部分指标缺少定义或数据来源说明。若直接全部放入论文，容易被认为实验设计不够严谨或存在选择性报告。

建议论文正文优先采用：

- `bonn_dynamic_comparison.csv`
- `dynamic_detection_accuracy.csv`
- `time_window_sensitivity.csv`
- `trajectory_deviation_samples.csv` 对应稳定性图

谨慎使用或修改后再使用：

- `ablation_comparison.csv`
- `dynamic_ratio_test.csv`
- `bonn_dataset_comparison.csv`
- `real_robot_experiment_manifest.csv`

## 2. CSV 数据完整性检查

### 2.1 Bonn 动态数据集结果

文件：

- `experiment_new/results/bonn_dynamic_comparison.csv`
- `experiment_new/results/bonn_dynamic_comparison_status.csv`

完整性：

- `walking / sitting / crowd` 三个序列均包含 `ORB-SLAM3 / DS-SLAM / Dyna-SLAM / Ours`。
- ATE、RPE、FPS 均有数值。
- 状态表 12 行全部为 `ok`。

主要结果：

| Sequence | 最优 ATE | 最优 RPE | 实时性最优 |
|---|---|---|---|
| walking | Ours 0.046535 | DS-SLAM 0.020147 | ORB-SLAM3 20.682597 FPS |
| sitting | Ours 0.041766 | Ours 0.022094 | ORB-SLAM3 16.390451 FPS |
| crowd | Dyna-SLAM 0.033056 | Ours 0.018340 | ORB-SLAM3 18.017313 FPS |

审稿风险：

- `crowd` 序列上 Dyna-SLAM 的 ATE 为 0.033056，略优于 Ours 的 0.038137。论文不能写成“本文方法在所有 Bonn 序列上取得最低 ATE”。
- `walking` 序列上 DS-SLAM 的 RPE 为 0.020147，略优于 Ours 的 0.021345。论文不能写成“本文方法在所有序列上 RPE 最优”。
- DS-SLAM 与 Dyna-SLAM FPS 极低，特别是 DS-SLAM 在 `sitting` 上 FPS 为 0.028179，约 35.5 秒/帧。这个数值合理地反映了重语义分割基线的开销，但审稿人可能要求说明硬件平台、是否使用 GPU、是否包括分割时间。
- 运行目录中仍残留早期失败的 `failed.txt`，虽然最终状态表为 `ok`，但如果提交补充材料，建议清理旧失败文件或在 README 中说明以 `*_status.csv` 和 `eval/metrics.json` 为准。

建议表述：

- 强调本文方法在 Bonn 上取得更稳定的综合表现：多数序列 ATE/RPE 最优或接近最优，同时 FPS 显著高于 DS-SLAM/Dyna-SLAM。
- 避免单纯宣称“精度全面最优”。
- 在正文中加入“部分序列上 Dyna-SLAM 的 ATE 略低，但其 FPS 低于 0.3，实时性不足；本文方法在精度与效率之间取得更好平衡”。

### 2.2 旧 Bonn 模板结果

文件：

- `experiment_new/results/bonn_dataset_comparison.csv`

问题：

- 所有行均为 `pending_dataset`。
- ATE、RPE、FPS 全部为 `--`。
- 该文件与已经完成的 `bonn_dynamic_comparison.csv` 功能重复。

审稿风险：

- 如果该表或对应 `table_bonn_dataset_comparison.tex` 被纳入论文/补充材料，会被认为 Bonn 实验未完成。

建议：

- 论文和最终结果目录中不要使用该文件。
- 可将其改名为 `bonn_dataset_comparison_template.csv` 或从最终论文实验包中移除。
- LaTeX 表格应只使用 `table_bonn_dynamic_comparison.tex`。

### 2.3 动态目标检测准确率

文件：

- `experiment_new/results/dynamic_detection_accuracy.csv`

结果：

| Method | Precision | Recall | F1-score |
|---|---:|---:|---:|
| YOLO raw detection | 1.000000 | 0.886576 | 0.939878 |
| YOLO+motion consistency | 1.000000 | 0.496770 | 0.663789 |
| YOLO+temporal consistency (Ours) | 0.996088 | 0.913855 | 0.953201 |

优点：

- Ours 的 F1-score 最高，符合“时间一致性提高动态目标识别稳定性”的论文主张。
- Ours 的 Recall 高于 YOLO raw，说明时间建模减少漏检。

审稿风险：

- YOLO raw 与 YOLO+motion consistency 的 Precision 都是 1.000000，过于理想。审稿人可能质疑标注方式、样本规模或评价口径是否偏向检测框。
- Motion Only 的 Recall 仅 0.496770，下降过大，需要解释其保守性：运动一致性通常只保留几何证据强的动态点，漏检更多。
- CSV 中没有区分 `fr3_walking_xyz` 和 `fr3_rpy` 两个序列，也没有给出每个序列的单独结果。用户原始实验目标要求测试序列包括两个 TUM 序列，审稿人可能要求分序列表。
- 缺少 FP、FN、FPR、FNR 等更完整检测指标。早期需求中曾要求 FPR/FNR，但当前论文级版本只保留 Precision/Recall/F1。

建议：

- 增加 per-sequence 版本：`Sequence, Method, Precision, Recall, F1-score`。
- 若标注来自语义类别或轨迹一致性伪标签，需要在论文中明确“动态目标真值”的来源。
- 可在附录增加混淆矩阵或 FP/FN 数量，增强可信度。

### 2.4 时间窗口参数敏感性

文件：

- `experiment_new/results/time_window_sensitivity.csv`

结果趋势：

- ATE 从 N=1 的 0.551924 降到 N=10 的 0.517236，在 N=15 回升到 0.522591。
- Smoothness 从 0.034686 持续降低到 0.028631。
- FPS 从 14.690698 下降到 13.542799。
- RPE 基本不变，范围仅 0.066966 到 0.067012。

优点：

- 趋势符合论文叙事：窗口增加提升平滑性，但带来响应/计算代价。
- N=10 附近 ATE 最优，N=10 到 N=15 Smoothness 继续改善但 ATE 略回升，适合说明过大窗口会带来响应滞后。

审稿风险：

- RPE 几乎不变，审稿人可能认为时间窗口主要影响平滑性，对局部位姿误差影响不足。
- 当前 CSV 未说明测试序列，是单序列结果还是多序列平均结果。
- 缺少标准差或多次运行统计。SLAM 存在随机性时，单次结果说服力有限。

建议：

- 增加列：`Sequence` 或 `Mean±Std`。
- 在论文中明确 N=10 是经验折中点，而不是绝对最优。
- 增加“动态响应延迟”的定量指标，例如动态状态切换延迟帧数或概率收敛帧数。

### 2.5 消融实验

文件：

- `experiment_new/results/ablation_comparison.csv`

主要问题：

- Full Model 的 ATE 为 0.439188，只略好于 A/C 的 0.442878，但明显差于 Baseline 的 0.431422。
- Full Model 的 Failure Rate 为 0.351681，明显高于 Baseline 的 0.042905。
- B: Baseline+Temporal Consistency 的 ATE 为 0.656059、RPE 为 0.127939，是所有变体中最差。
- A 与 C 的 ATE、RPE、Failure Rate 完全相同，仅 FPS 不同。这很容易被审稿人认为不是独立实验结果，或者 C 模块没有实际生效。
- Baseline 的 FPS 为 `--`，不完整。

审稿风险：

- 该表与论文核心主张矛盾：时间一致性模块单独加入后性能大幅变差，Full Model 失败率也最高。
- 若论文声称“各模块均有效”，该表会直接被审稿人质疑。
- Failure Rate 的数量级与常规 SLAM 失败率表述不一致，需要说明其计算定义。0.351681 是比例还是归一化失败评分？

建议：

- 不建议直接使用当前消融表。
- 重新检查消融实验配置，确认 Baseline 是否与其他模块使用相同序列、相同评价脚本、相同初始化条件。
- 将消融结果拆成定位精度、动态判别稳定性、地图质量三类指标。对象级语义地图不一定显著降低 ATE，但应改善语义地图一致性。
- 若真实结果确实如此，应修改论文主张：时间一致性不是单独提升轨迹精度，而是与语义地图/动态点策略联合时提升鲁棒性。

### 2.6 动态比例鲁棒性实验

文件：

- `experiment_new/results/dynamic_ratio_test.csv`

趋势：

- 所有方法 ATE 随动态比例 0% 到 50% 单调上升，趋势合理。
- ORB-SLAM2 退化最明显，符合动态点干扰预期。

主要矛盾：

- 在所有动态比例下，Ours 的 ATE 都不是最优。
- 0% 到 50% 下，Dyna-SLAM 始终 ATE 最低；DS-SLAM 通常第二；Ours 通常第三。
- 例如 50% 动态比例下：Dyna-SLAM 0.049230，DS-SLAM 0.121452，Ours 0.175596。

审稿风险：

- 该表会削弱“本文方法具有更强动态鲁棒性”的主结论。
- 如果论文强调 Ours 在动态点比例上最鲁棒，目前数据并不支持。
- Dyna-SLAM Failure Rate 高于 Ours，但 ATE 显著低于 Ours。审稿人会要求解释“失败率”和“ATE”的关系。
- 人为增加动态点的方式未在 CSV 中体现，缺少注入策略、随机种子、动态点空间分布、遮挡模型等信息。

建议：

- 不要只画 ATE 曲线；同时展示 Failure Rate 或稳定性指标，否则 Ours 不占优势。
- 将论文表述调整为：Ours 在动态比例升高时保持较低失败率或更高运行稳定性，而非最低 ATE。
- 增加多次随机注入平均值和标准差，避免单次注入造成排名偶然性。
- 明确动态点注入是在图像特征层、深度点云层还是地图点层进行。

### 2.7 真实机器人实验

文件：

- `experiment_new/results/real_robot_experiment_manifest.csv`

问题：

- 两个场景 `office`、`laboratory` 均为 `pending`。
- RGB、动态概率、语义地图、轨迹均未采集。

审稿风险：

- 如果论文中写“进行了真实机器人实验”，但只提供 pending 表，风险很高。

建议：

- 若没有真实采集数据，正文中应写“作为未来工作”或“不纳入定量实验”。
- 若保留为可选展示，不应放入主实验表。

### 2.8 轨迹偏差样本

文件：

- `experiment_new/results/trajectory_deviation_samples.csv`

观察：

- 该文件包含轨迹偏差随时间采样，可支撑 `trajectory_stability_comparison.png`。
- 最大偏差约 0.875814 m，属于动态序列中可解释范围。

审稿风险：

- CSV 未标明使用的 TUM 序列名称。
- 不同方法采样时间点可能不完全一致，审稿人可能要求说明对齐方式。
- 稳定性曲线如果只选一个序列，容易被认为选择性展示。

建议：

- 增加元数据：序列名、轨迹对齐方式、采样间隔、平滑窗口。
- 若篇幅允许，补充 2 到 3 个序列的稳定性曲线或平均 deviation 曲线。

## 3. 图表问题检查

已存在图：

- `bonn_trajectory_comparison.png`
- `trajectory_stability_comparison.png`
- `dynamic_detection_accuracy.png`
- `dynamic_probability_curve.png`
- `dynamic_ratio_curve.png`
- `time_window_curves.png`
- `trajectory_comparison.png`
- `semantic_map_showcase.png`

主要问题：

- `trajectory_comparison.png` 与 `trajectory_stability_comparison.png` 功能接近，论文中应避免重复放置。建议保留稳定性图作为核心图。
- `bonn_trajectory_comparison.png` 是论文级大图，分辨率为 4324 x 1280，适合作为横向多子图；但需要确认图例中是否包含 Ground Truth、ORB-SLAM3、DS-SLAM、Dyna-SLAM、Ours。
- `dynamic_probability_curve.png` 缺少对应 CSV 文件，图的可复现性不足。当前结果目录中没有 `dynamic_probability_curve.csv`。
- `semantic_map_showcase.png` 若作为真实结果图，需要说明来源序列和生成方式；如果是展示图或示意图，应避免写成定量实验证据。
- `table_bonn_dataset_comparison.tex` 对应 pending 模板，不建议用于论文。
- `table_real_robot_manifest.tex` 是采集清单，不是实验结果表，不建议作为论文结果表。

建议：

- 论文图只保留与实测 CSV 一一对应的图。
- 每张图在 caption 中写明数据集、序列、评价坐标系、是否 Sim(3)/SE(3) 对齐。
- 对轨迹图补充“同一坐标系、单位 m、Ground Truth 为黑色虚线”等说明。

## 4. 可能被审稿人质疑的问题

### 4.1 “本文方法是否真的优于 Dyna-SLAM？”

Bonn `crowd` 上，Dyna-SLAM 的 ATE 低于 Ours：

- Dyna-SLAM ATE：0.033056
- Ours ATE：0.038137

但 Ours 的 RPE 与 FPS 更好：

- Ours RPE：0.018340，Dyna-SLAM RPE：0.022007
- Ours FPS：11.124593，Dyna-SLAM FPS：0.290078

建议回答：

本文方法不是单纯追求所有序列上的最低 ATE，而是在保证精度接近最优的同时显著提升实时性和局部运动稳定性。对于移动机器人系统，RPE 和 FPS 同样关键。

### 4.2 “消融实验为什么 Full Model 没有优于 Baseline？”

当前消融表中 Full Model 的 ATE 和 Failure Rate 均没有优于 Baseline。这与方法有效性主张冲突。

建议处理：

- 重新跑消融或核对数据来源。
- 不要用当前表直接证明“所有模块提升定位精度”。
- 将对象级语义地图模块的评价转向地图质量、语义一致性、动态点残留率，而不是只看 ATE。

### 4.3 “动态比例实验为什么 Ours 不如 Dyna-SLAM？”

当前动态比例鲁棒性实验中，Dyna-SLAM 在所有比例下 ATE 最低。

建议处理：

- 将该实验定位为“鲁棒性趋势”而非“绝对精度最优”。
- 同时报告 Failure Rate、轨迹连续性、运行效率。
- 若论文主张是“动态比例升高时更稳定”，应增加稳定性指标和多次随机注入标准差。

### 4.4 “检测评价是否有真实标注？”

Precision/Recall/F1 的可信度取决于动态目标真值标注来源。当前 CSV 未给出样本数量、GT 生成方式、评价粒度。

建议处理：

- 明确是像素级、实例级、目标框级还是点级评价。
- 给出 TP/FP/FN 数量。
- 分序列报告 `fr3_walking_xyz` 与 `fr3_rpy`。

### 4.5 “FPS 是否公平？”

Bonn 表中 ORB-SLAM3 FPS 最高，Ours 次之，DS/Dyna 极慢。审稿人会问是否：

- 都在同一机器运行；
- 都使用 CPU/GPU；
- FPS 是否包含语义分割、YOLO、Mask-RCNN 等前处理；
- 是否包含加载模型时间。

建议处理：

- 在实验设置中明确硬件、线程数、GPU、是否包含前处理时间。
- 对所有方法使用统一 wall-time FPS 定义。

## 5. 建议修改方式

优先级 P0：

- 从论文主结果中移除或忽略 `bonn_dataset_comparison.csv` 和 `table_bonn_dataset_comparison.tex`，改用 `bonn_dynamic_comparison.csv` 和 `table_bonn_dynamic_comparison.tex`。
- 不要把 `real_robot_experiment_manifest.csv` 写成已完成真实机器人实验。
- 修改 Bonn 实验文字，避免宣称 Ours 在所有指标上最优；应强调精度、稳定性和实时性的综合优势。

优先级 P1：

- 重新核对或重跑 `ablation_comparison.csv`。当前 Full Model 和 Temporal Consistency 单模块结果不支持论文主张。
- 对 `dynamic_ratio_test.csv` 增加稳定性和失败率讨论，避免只用 ATE 曲线支撑鲁棒性。
- 为 `dynamic_detection_accuracy.csv` 增加分序列结果和 TP/FP/FN 数量。

优先级 P2：

- 为所有参数实验和轨迹稳定性图增加序列名称、运行次数、均值/标准差。
- 为 `dynamic_probability_curve.png` 增加对应 CSV，保证图表可复现。
- 清理运行目录中旧的 `failed.txt` 或增加说明，避免补充材料审查时产生误解。

## 6. 推荐论文表述调整

不建议写：

> 本文方法在所有动态序列和所有指标上均取得最优结果。

建议写：

> 在 Bonn RGB-D Dynamic Dataset 上，本文方法在 walking 和 sitting 序列中取得最低 ATE，在 crowd 序列中取得最低 RPE，并在所有 Bonn 动态序列中保持明显高于 DS-SLAM 和 Dyna-SLAM 的运行帧率。实验结果表明，时间一致性建模并非单纯追求单项 ATE 最优，而是在动态目标持续干扰下提升轨迹连续性和局部运动稳定性，同时保持较好的实时性。

不建议写：

> 消融实验表明每个模块均能提升定位精度。

建议写：

> 消融实验用于分析不同模块对动态点剔除、轨迹稳定性和语义地图一致性的影响。时间一致性模块的主要作用是降低动态判别抖动，其收益需要结合稳定性指标和完整模型进行评价。

## 7. 最终可用性判断

| 实验 | 当前状态 | 是否建议直接用于论文 |
|---|---|---|
| Bonn 动态数据集比较 | 完整，12/12 ok | 可以使用 |
| 动态检测准确率 | 数值完整，但缺少分序列/标注说明 | 修改说明后使用 |
| 时间窗口参数敏感性 | 趋势合理，但缺少序列/方差 | 可以作为补充实验，建议增强 |
| 消融实验 | 与主张存在明显冲突 | 不建议直接使用 |
| 动态比例鲁棒性 | 趋势完整，但 Ours 非 ATE 最优 | 谨慎使用，需改叙事 |
| 真实机器人实验 | pending | 不应作为已完成实验 |
| 轨迹稳定性图 | 已生成，有助于支撑稳定性主张 | 可以使用，建议补充序列说明 |

