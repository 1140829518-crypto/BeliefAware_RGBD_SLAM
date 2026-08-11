# 4 实验结果与分析

## 4.1 实验设置

实验采用 TUM RGB-D 动态场景中的 `fr3_walking_xyz`、`fr3_walking_rpy` 和 `fr3_walking_halfsphere`。四种对比模式为：Baseline（基础 ORB-SLAM2）、Paper1（已有 SemanticDynamic 方法）、Shadow（运行 ObjectDynamic 但不反馈 Tracking）以及 Active（依据 StableMapView 过滤 Tracking 动态候选关联）。

轨迹评价对所有方法采用一致参数：ATE 使用 `evo_ape tum --align`；平移 RPE 使用 `evo_rpe tum --align --pose_relation trans_part`；旋转 RPE 使用 `evo_rpe tum --align --pose_relation angle_deg`。本文同时报告 tracked frames、KeyFrames 和 tracking gap episodes，避免仅以成功轨迹片段的误差评价不完整运行。

post-P0 Shadow 编译宏为 `SHADOW=1, ACTIVE=0`，Active 为 `SHADOW=1, ACTIVE=1`。三组 Shadow 与三组 Active 均完成程序运行并输出轨迹，但“程序完整结束”不等同于“全序列持续跟踪”。

## 4.2 定位精度比较

|序列|Baseline ATE RMSE/m|Paper1/m|Shadow/m|Active/m|
|---|---:|---:|---:|---:|
|walking_xyz|0.745552|0.751667|**0.571050**|0.598146|
|walking_rpy|1.121808|1.032188|0.882434|0.229810*|
|walking_halfsphere|**0.366398**|0.478962|0.447759|0.426866|

Shadow 相对 Paper1 在三个序列上的 ATE RMSE 均降低：walking_xyz 从0.751667 m降至0.571050 m，改善24.03%；walking_rpy 从1.032188 m降至0.882434 m，改善14.51%；walking_halfsphere 从0.478962 m降至0.447759 m，改善6.51%。这组单次实验事实表明，在不反馈地图点过滤的条件下，post-P0 Shadow 的轨迹误差均低于相应 Paper1 运行，但尚不能据此声称统计显著性。

Shadow 并不修改当前帧位姿优化，因此其与 Paper1 的差异还可能受到 ORB-SLAM2 多线程和单次运行随机波动影响。正式论文应将其表述为当前三次单次运行的观测结果，并在条件允许时通过重复实验报告均值和标准差。

完整评价指标如下：

|序列|方法|ATE mean/m|RPE trans/m|RPE rot/degree|Tracked frames|KeyFrames|
|---|---|---:|---:|---:|---:|---:|
|walking_xyz|Shadow|0.504861|0.020219|0.514203|827|317|
|walking_xyz|Active|0.530894|0.020518|0.516467|827|298|
|walking_rpy|Shadow|0.774228|0.051776|0.877387|548|235|
|walking_rpy|Active|0.196864|0.047588|0.882494|371|174|
|walking_halfsphere|Shadow|0.398584|0.020276|0.525027|1021|299|
|walking_halfsphere|Active|0.389276|0.042873|0.904924|575|113|

## 4.3 目标级动态建模分析

post-P0 日志记录了检测数、有效/无效三维观测、Dynamic 转换、Recovered 在线事件及每帧动态对象数。

|序列|模式|Detections|Valid 3D|Invalid 3D|Dynamic transitions|Recovered transitions|Dynamic object-frame sum|
|---|---|---:|---:|---:|---:|---:|---:|
|walking_xyz|Shadow|4552|4341|211|2|32|20|
|walking_rpy|Shadow|2198|2044|154|2|34|20|
|walking_halfsphere|Shadow|4781|4416|365|2|44|82|
|walking_xyz|Active|4552|4341|211|2|32|20|
|walking_rpy|Active|1388|1285|103|2|13|17|
|walking_halfsphere|Active|3311|3055|256|2|12|85|

三组 Shadow 均出现2次进入 Dynamic 的生命周期转换，并出现32、34和44次三帧确认后的 Recovered 事件，说明修复后的 Lost/Recovered 在线路径在真实序列中可达。`position_valid` 将无效深度从几何关联和速度估计中排除；表中无效观测仍被保留为二维/语义观测，但不提供三维运动证据。

动态对象的帧累计量并非目标实例数，而是各日志帧 dynamic objects 数量之和。它反映目标级时间状态在序列上的持续程度，不能直接解释为独立动态目标总数。

## 4.4 Active 候选过滤策略分析

|序列|过滤MapPoint总数|发生过滤的帧数|Tracking gaps|Active相对Shadow ATE变化|
|---|---:|---:|---:|---:|
|walking_xyz|754|10|0|退化4.74%|
|walking_rpy|244|10|19|数值改善73.96%*|
|walking_halfsphere|64|44|8|数值改善4.67%*|

walking_xyz 中 Shadow 与 Active 均输出827个轨迹帧且无 gap episode，Active ATE由0.571050 m增至0.598146 m。该结果未显示主动过滤带来精度收益，可能与过滤部分仍可用约束有关，但这一解释需要消融实验验证。

walking_rpy 的 Active ATE为0.229810 m，低于 Shadow 的0.882434 m；然而 tracked frames 从548降至371，KeyFrames 从235降至174，并出现19个 gap episodes。evo 只评价成功输出并能与真值关联的轨迹片段，因此该低 ATE 不能解释为完整序列定位能力提升，更不能作为“Active 显著优于 Shadow”的证据。

walking_halfsphere 的 Active ATE为0.426866 m，略低于 Shadow 的0.447759 m，但 tracked frames 从1021降至575、KeyFrames 从299降至113，并出现8个 gap episodes；其平移和旋转 RPE也分别从0.020276 m、0.525027 degree上升至0.042873 m、0.904924 degree。该场景同样表现出轨迹覆盖与局部误差之间的权衡。

综上，Shadow 在三个序列中相对 Paper1 均取得较低 ATE，并保持较高或完整的轨迹覆盖；Active 的结果具有明显场景依赖性，其过滤机制在当前参数下可能减少动态干扰，也可能减少定位约束。论文应同时报告误差、覆盖率和gap，不隐藏退化结果。

## 4.5 实验有效性边界

当前结果来自每种配置每个序列的一次正式运行，尚无重复运行方差和显著性检验。ORB-SLAM2 的并行建图过程可能导致单次结果波动，尤其 Shadow 本身不反馈 Tracking。因此，本文可以报告当前真实测量值和观察到的趋势，但不使用“全面优于”“显著提升”或“证明优越性”等结论。

