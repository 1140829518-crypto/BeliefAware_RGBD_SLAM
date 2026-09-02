# P3.5：P2 与 P3 实验结果一致性审计

本报告仅读取既有运行目录与评价结果；未运行 SLAM、未重新评价轨迹、未覆盖任何既有 CSV。

## 结论摘要

- P2 与 P3 **不是同一批 run**。P3 为获得稳定 MapPoint ID 级日志，独立重新运行了 Semantic/Temporal。
- 两阶段使用同一个 `scripts/evaluate_tum_metrics.py`，默认最大时间戳差均为 0.02 s；轨迹均为 TUM 8列格式；ATE 均采用一次 SE(3) SVD 对齐，RPE 均基于相邻匹配位姿的相对运动误差。未发现评价口径差异。
- P3 报告的百分比采用 `(Temporal/Semantic-1)×100%`：负数表示误差下降。其“改善”解释没有写反。P2 使用 `(Semantic-Temporal)/Semantic×100%`：负数表示退化。两者数值符号表达不同，但各自文字解释正确。
- 方向冲突来自独立运行样本、P3点级日志带来的实时调度扰动，以及 P3 Semantic/xyz 仅有3个合法run；不是把同一数据算出相反结论，也不是评价参数改变。
- P3 Temporal/rpy run_03 只有102/866个轨迹位姿（约11.78%覆盖），ATE为0.019923 m。该低ATE不能代表完整序列性能，并明显影响P3 rpy均值。

## 实际纳入统计的 run

| Stage | Method | Sequence | legal run IDs | n |
|---|---|---|---|---:|
| P2 | Semantic | fr3_walking_xyz | run_01, run_02, run_03, run_04, run_05 | 5 |
| P2 | Semantic | fr3_walking_rpy | run_01, run_02, run_03, run_04, run_05 | 5 |
| P2 | Semantic | fr3_walking_halfsphere | run_01, run_02, run_03, run_04, run_05 | 5 |
| P2 | Temporal | fr3_walking_xyz | run_01, run_02, run_03, run_04, run_05 | 5 |
| P2 | Temporal | fr3_walking_rpy | run_01, run_02, run_03, run_04, run_05 | 5 |
| P2 | Temporal | fr3_walking_halfsphere | run_01, run_02, run_03, run_04, run_05 | 5 |
| P3 | Semantic | fr3_walking_xyz | run_03, run_04, run_05 | 3 |
| P3 | Semantic | fr3_walking_rpy | run_01, run_02, run_03, run_04, run_05 | 5 |
| P3 | Semantic | fr3_walking_halfsphere | run_01, run_02, run_03, run_04, run_05 | 5 |
| P3 | Temporal | fr3_walking_xyz | run_01, run_02, run_03, run_04, run_05 | 5 |
| P3 | Temporal | fr3_walking_rpy | run_01, run_02, run_03, run_04, run_05 | 5 |
| P3 | Temporal | fr3_walking_halfsphere | run_01, run_02, run_03, run_04, run_05 | 5 |

## ATE RMSE 原始值与均值

| Stage | Method | Sequence | run_01 | run_02 | run_03 | run_04 | run_05 | mean |
|---|---|---|---:|---:|---:|---:|---:|---:|
| P2 | Semantic | fr3_walking_xyz | 0.447311 | 0.499783 | 0.566868 | 0.556620 | 0.453799 | 0.504876 |
| P2 | Semantic | fr3_walking_rpy | 0.748928 | 0.784735 | 0.744158 | 0.693140 | 0.775076 | 0.749207 |
| P2 | Semantic | fr3_walking_halfsphere | 0.202230 | 0.541292 | 0.491000 | 0.143008 | 0.268802 | 0.329266 |
| P2 | Temporal | fr3_walking_xyz | 0.428491 | 0.573195 | 0.612378 | 0.553838 | 0.643438 | 0.562268 |
| P2 | Temporal | fr3_walking_rpy | 0.760188 | 0.775252 | 0.656909 | 0.809671 | 0.779885 | 0.756381 |
| P2 | Temporal | fr3_walking_halfsphere | 0.647710 | 0.527970 | 0.191112 | 0.205268 | 0.208973 | 0.356207 |
| P3 | Semantic | fr3_walking_xyz | NA | NA | 0.586818 | 0.670727 | 0.652233 | 0.636593 |
| P3 | Semantic | fr3_walking_rpy | 0.694688 | 0.730975 | 0.695282 | 0.822425 | 0.742936 | 0.737261 |
| P3 | Semantic | fr3_walking_halfsphere | 0.181248 | 0.640052 | 0.461111 | 0.252224 | 0.112243 | 0.329376 |
| P3 | Temporal | fr3_walking_xyz | 0.572063 | 0.502372 | 0.583228 | 0.559944 | 0.604371 | 0.564396 |
| P3 | Temporal | fr3_walking_rpy | 0.754035 | 0.884950 | 0.019923 | 0.670588 | 0.735237 | 0.612947 |
| P3 | Temporal | fr3_walking_halfsphere | 0.213528 | 0.182423 | 0.504070 | 0.192046 | 0.517046 | 0.321823 |

## Semantic 与 Temporal 的阶段内 ATE 对比

| Stage | Sequence | Semantic mean | Temporal mean | Temporal相对Semantic | 解释 |
|---|---|---:|---:|---:|---|
| P2 | fr3_walking_xyz | 0.504876 | 0.562268 | +11.37% | 误差上升（退化） |
| P2 | fr3_walking_rpy | 0.749207 | 0.756381 | +0.96% | 误差上升（退化） |
| P2 | fr3_walking_halfsphere | 0.329266 | 0.356207 | +8.18% | 误差上升（退化） |
| P3 | fr3_walking_xyz | 0.636593 | 0.564396 | -11.34% | 误差下降（改善） |
| P3 | fr3_walking_rpy | 0.737261 | 0.612947 | -16.86% | 误差下降（改善） |
| P3 | fr3_walking_halfsphere | 0.329376 | 0.321823 | -2.29% | 误差下降（改善） |

## RPE translation RMSE 原始值与均值

| Stage | Method | Sequence | run_01 | run_02 | run_03 | run_04 | run_05 | mean |
|---|---|---|---:|---:|---:|---:|---:|---:|
| P2 | Semantic | fr3_walking_xyz | 0.019787 | 0.019788 | 0.020191 | 0.021546 | 0.021651 | 0.020593 |
| P2 | Semantic | fr3_walking_rpy | 0.113550 | 0.105805 | 0.110475 | 0.035132 | 0.114142 | 0.095821 |
| P2 | Semantic | fr3_walking_halfsphere | 0.039214 | 0.033547 | 0.027569 | 0.041278 | 0.027978 | 0.033917 |
| P2 | Temporal | fr3_walking_xyz | 0.019556 | 0.021136 | 0.020227 | 0.020067 | 0.021330 | 0.020463 |
| P2 | Temporal | fr3_walking_rpy | 0.118554 | 0.128377 | 0.109741 | 0.143480 | 0.049340 | 0.109898 |
| P2 | Temporal | fr3_walking_halfsphere | 0.028687 | 0.030483 | 0.035180 | 0.030924 | 0.028165 | 0.030688 |
| P3 | Semantic | fr3_walking_xyz | NA | NA | 0.020671 | 0.020639 | 0.021429 | 0.020913 |
| P3 | Semantic | fr3_walking_rpy | 0.095851 | 0.114802 | 0.106773 | 0.113203 | 0.122439 | 0.110614 |
| P3 | Semantic | fr3_walking_halfsphere | 0.027988 | 0.020573 | 0.061457 | 0.033889 | 0.034764 | 0.035734 |
| P3 | Temporal | fr3_walking_xyz | 0.020543 | 0.020253 | 0.020548 | 0.019632 | 0.020089 | 0.020213 |
| P3 | Temporal | fr3_walking_rpy | 0.123785 | 0.113100 | 0.017071 | 0.104848 | 0.028455 | 0.077452 |
| P3 | Temporal | fr3_walking_halfsphere | 0.021328 | 0.026057 | 0.053330 | 0.043391 | 0.022169 | 0.033255 |

## RPE一致性结论

| Stage | Sequence | Semantic mean | Temporal mean | Temporal相对Semantic |
|---|---|---:|---:|---:|
| P2 | fr3_walking_xyz | 0.020593 | 0.020463 | -0.63% |
| P2 | fr3_walking_rpy | 0.095821 | 0.109898 | +14.69% |
| P2 | fr3_walking_halfsphere | 0.033917 | 0.030688 | -9.52% |
| P3 | fr3_walking_xyz | 0.020913 | 0.020213 | -3.35% |
| P3 | fr3_walking_rpy | 0.110614 | 0.077452 | -29.98% |
| P3 | fr3_walking_halfsphere | 0.035734 | 0.033255 | -6.94% |

## 逐项核查

1. **是否同一批 run**：否。目录、轨迹 SHA-256 与原始指标均不同。
2. **P3是否重跑**：是。P3运行脚本创建了独立的 `03_temporal_continuity` 目录，并为点级证据日志重跑。
3. **纳入run_id**：见上表。P2每个 method×sequence 均为5个合法run；P3 Semantic/xyz仅run_03–05合法，其余组合均为run_01–05。
4. **每run原始指标**：ATE与RPE已逐项列出，CSV同时保留ATE mean/median及旋转RPE。
5. **评价脚本**：两阶段配置均调用 `scripts/evaluate_tum_metrics.py`。
6. **时间戳匹配**：所有现有 `metrics.json` 记录 `max_timestamp_diff=0.02`。
7. **轨迹格式**：合法轨迹均为每行8列的TUM格式。
8. **对齐方式**：ATE使用同一SE(3) SVD对齐；RPE实现不对绝对轨迹施加该对齐，而比较连续相对位姿，此行为两阶段一致。
9. **运行差异**：存在。ORB-SLAM2多线程调度、特征/地图演化及实时YOLO交互使独立运行轨迹不完全相同；轨迹SHA不同提供了直接证据。此外，P3启用逐MapPoint文件日志，单run日志约5–35 MB；虽然不改变算法判定，却会扰动实时I/O与线程调度，因此P3并非与P2完全无侵入的性能重复。
10. **百分比符号**：P3没有写反。其负百分比表示Temporal误差更低；P2报告的正向改善公式与P3变化率公式相反，但文字与各自公式一致。
11. **28/30影响**：影响Semantic/xyz均值与方差估计。P3该格仅3个合法run，不能与P2的5-run均值视为同等重复设计。run_01为socket权限失败，run_02无有效运行；二者未作为0纳入。其余格均5个。
12. **RPE**：评价脚本、匹配阈值与数据格式一致；RPE的阶段间差异同样来自不同轨迹样本，而非口径变化。

## 差异来源判定

- **统计错误**：未发现均值计算或改善/退化符号写反。
- **评价口径差异**：未发现；脚本、0.02 s匹配阈值、格式及对齐实现一致。
- **独立重复运行随机波动**：是来源之一。
- **统计日志的运行时扰动**：也是重要来源。P3新增的高频点级磁盘写入不改变算法逻辑，但可能改变实时执行时序；因此P3的ATE/RPE不宜视作P2的同条件复测。
- **覆盖异常**：P3 Temporal/rpy run_03仅102/866个位姿，ATE=0.019923 m；低误差与低覆盖同时出现，拉低了Temporal/rpy的平均ATE和RPE。
- **统计设计不完全一致**：是附加来源。P2是完整5×重复；P3整体固定30次但仅28次合法，Semantic/xyz为3×有效重复。

## 正式论文采用建议

- 定位精度、RPE与覆盖率的正式四方法对比应采用 **P2**：它是预先定义的完整5次重复设计，Semantic/Temporal各序列均有5个合法run，并与ORB-SLAM2、Full处于同一对比框架。
- P3应仅用于时间连续性专项分析，主张应基于P3新日志的Switching Frequency和点级证据；P3的ATE/RPE只能作为该批连续性实验的辅助伴随指标，不应替换P2主性能结果。尤其不能用rpy run_03的低覆盖低ATE声称定位改善。
- 论文必须同时说明：P3点级连续性结果来自独立补跑；其ATE方向与P2不同，说明定位误差具有运行波动，不能据P3辅助ATE推翻P2主实验。

P3.5审计结束；未启动新实验。
