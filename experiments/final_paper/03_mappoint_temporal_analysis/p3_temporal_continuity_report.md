# P3 时间一致性动态证据连续性验证报告

## 实验定义

- 比较对象：Semantic (`SemanticMode=1, Shadow=0, Active=0`) 与 Temporal (`SemanticMode=2, Shadow=0, Active=0`)。
- 为获得稳定 MapPoint ID 级证据，增加了由 `ORB_SLAM2_MAPPOINT_EVIDENCE_LOG` 显式启用的只读日志；它不改变分数、阈值、匹配、抑制或控制流。由于 P2 日志只有帧级汇总，P3 对固定 30 个 run ID 进行了补跑。
- MapPoint 在一次帧处理中可能被多个匹配路径更新；统计时按 `(frame_id, map_point_id)` 保留日志顺序中的最终状态。
- **Switching Frequency 定义**：对每个稳定 `MapPoint::mnId`，按其被观测帧排序，计算相邻两次观测的二值有效动态状态是否改变；`SF = 全部点的状态改变次数 / 全部点的相邻观测对数`。这不是目标 ID 级切换，也不把未观测帧补成静态。Semantic 的有效动态状态是当前帧 `dynamic_hit`，Temporal 的有效动态状态是累积分数达到类别阈值。
- `temporal_evidence_frame_log.csv` 同时保留两类口径：原 Cull 阶段计数与点级日志按稳定 ID 去重后的最终状态。主表采用后者，因为匹配阶段可能早于 Cull 完成状态更新或抑制。

## 结果汇总

| Method | Sequence | completed/legal | Switching Frequency | switches | dynamic MPs/frame | suppressed MPs/frame | gaps | TSR | PMR | RPE trans | ATE (aux.) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Semantic | fr3_walking_xyz | 3/3 | 0.033154 ± 0.002087 | 44633.0 ± 9273.5 | 381.475 ± 90.840 | 0.000 ± 0.000 | 0.00 ± 0.00 | 1.000000 ± 0.000000 | 0.000000 ± 0.000000 | 0.020913 ± 0.000447 | 0.636593 ± 0.044087 |
| Semantic | fr3_walking_rpy | 5/5 | 0.037764 ± 0.005630 | 20609.8 ± 5659.4 | 137.566 ± 19.458 | 0.000 ± 0.000 | 9.00 ± 5.34 | 0.556351 ± 0.099881 | 0.443649 ± 0.099881 | 0.110614 ± 0.009960 | 0.737261 ± 0.052200 |
| Semantic | fr3_walking_halfsphere | 5/5 | 0.034145 ± 0.004834 | 25644.8 ± 12639.0 | 186.445 ± 39.770 | 0.000 ± 0.000 | 7.20 ± 3.63 | 0.651322 ± 0.159706 | 0.348678 ± 0.159706 | 0.035734 ± 0.015458 | 0.329376 ± 0.217322 |
| Temporal | fr3_walking_xyz | 5/5 | 0.020625 ± 0.000576 | 23653.6 ± 2102.6 | 399.787 ± 36.073 | 399.787 ± 36.073 | 0.00 ± 0.00 | 1.000000 ± 0.000000 | 0.000000 ± 0.000000 | 0.020213 ± 0.000379 | 0.564396 ± 0.038335 |
| Temporal | fr3_walking_rpy | 5/5 | 0.027632 ± 0.005386 | 12484.4 ± 7519.3 | 174.675 ± 68.483 | 174.675 ± 68.483 | 7.20 ± 3.11 | 0.515935 ± 0.241325 | 0.484065 ± 0.241325 | 0.077452 ± 0.050534 | 0.612947 ± 0.340532 |
| Temporal | fr3_walking_halfsphere | 5/5 | 0.021742 ± 0.001243 | 15382.4 ± 6260.1 | 269.278 ± 50.797 | 269.278 ± 50.797 | 6.00 ± 4.64 | 0.625269 ± 0.175936 | 0.374731 ± 0.175936 | 0.033255 ± 0.014342 | 0.321823 ± 0.172720 |

## Semantic → Temporal 变化

| Sequence | SF change | gaps change | TSR change | RPE change | ATE change |
|---|---:|---:|---:|---:|---:|
| fr3_walking_xyz | -0.012529 | +0.00 | +0.00 pp | -3.35% | -11.34% |
| fr3_walking_rpy | -0.010131 | -1.80 | -4.04 pp | -29.98% | -16.86% |
| fr3_walking_halfsphere | -0.012403 | -1.20 | -2.61 pp | -6.94% | -2.29% |

## 结论（仅据本次数据）

1. Temporal 降低 MapPoint Switching Frequency 的序列：fr3_walking_xyz, fr3_walking_rpy, fr3_walking_halfsphere；其余序列不支持该结论。
2. tracking gaps 减少的序列：fr3_walking_rpy, fr3_walking_halfsphere。
3. TSR 提高的序列：无。
4. RPE translation 改善的序列：fr3_walking_xyz, fr3_walking_rpy, fr3_walking_halfsphere。
5. ATE 未改善的序列：无。这些序列是否仍有连续性收益，必须同时查看 SF、gaps 和 TSR，不能由 ATE 单独推断。
6. 三个序列的变化方向若不一致，则结论是场景依赖，而不是稳定改善。

## 运行完整性

- 固定 run 总数：30；completed：28；legal evaluation：28。
- Semantic/walking_xyz run_01 因受限环境禁止创建 Unix socket 而 `exit_1/incomplete`；run_02 是首次启动被停止时留下的固定目录，状态保持 `unknown/incomplete`。二者未被替换，误差统计不按 0 处理。

## 选点规则

`selected_mappoint_evidence.csv` 对每个 method × sequence 使用首个具有合法评价和证据的固定 run，选择“曾至少一次为动态，且不同观测帧数最多”的 MapPoint；并列时选择最小 `mnId`。未人工挑选曲线。

P3 到此结束，未启动 P4。
