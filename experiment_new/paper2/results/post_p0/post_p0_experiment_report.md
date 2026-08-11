# Paper2 Post-P0 正式实验报告

## 可复现性记录

- Git 分支：`main`
- Git HEAD：`84cc42d8e92be23ddde9747253b9986595502c70`
- P0 代码状态：未提交；运行结束时 `git diff` SHA-256 为 `66e7a0f400090937ed4b03a9055137c7108e196297a68f28d09a167efad01c76`
- Shadow 编译宏：`ENABLE_OBJECT_DYNAMIC_SHADOW_MODE=1`，`ENABLE_OBJECT_DYNAMIC_ACTIVE_MODE=0`
- Active 编译宏：`ENABLE_OBJECT_DYNAMIC_SHADOW_MODE=1`，`ENABLE_OBJECT_DYNAMIC_ACTIVE_MODE=1`
- Active `libORB_SLAM2.so` SHA-256：`b23357a453dd9ef0bf7c6a58af212365ee1029273dab4a4a183ae84c25b04bda`
- 数据集根目录：`/home/djn/datasets/TUMRGBD/`
- ATE：`evo_ape tum <groundtruth> <trajectory> --align`
- RPE translation：`evo_rpe tum <groundtruth> <trajectory> --align --pose_relation trans_part`
- RPE rotation：`evo_rpe tum <groundtruth> <trajectory> --align --pose_relation angle_deg`
- Baseline/Paper1 使用原正式结果；Shadow/Active 仅使用本目录的 post-P0 结果。

## 六组实验完整性

三组 Shadow 与三组 Active 均正常结束。每个目录均包含非空的 `CameraTrajectory.txt`、`KeyFrameTrajectory.txt`、`SemanticDynamicStatistics.txt`、`run.log` 和 `yolo.log`，旧结果没有删除或覆盖。

## 四方法轨迹结果

|Sequence|Method|ATE RMSE (m)|ATE mean (m)|RPE trans (m)|RPE rot (degree)|Tracked frames|KeyFrames|
|---|---|---:|---:|---:|---:|---:|---:|
|walking_xyz|Baseline|0.745552|0.686975|0.029168|0.674883|562|246|
|walking_xyz|Paper1|0.751667|0.689691|0.020589|0.509030|827|309|
|walking_xyz|Shadow|0.571050|0.504861|0.020219|0.514203|827|317|
|walking_xyz|Active|0.598146|0.530894|0.020518|0.516467|827|298|
|walking_rpy|Baseline|1.121808|0.951351|0.129090|2.212913|836|362|
|walking_rpy|Paper1|1.032188|0.915605|0.059162|1.013814|547|219|
|walking_rpy|Shadow|0.882434|0.774228|0.051776|0.877387|548|235|
|walking_rpy|Active|0.229810|0.196864|0.047588|0.882494|371|174|
|walking_halfsphere|Baseline|0.366398|0.260632|0.050478|1.331842|573|229|
|walking_halfsphere|Paper1|0.478962|0.457083|0.020470|0.513546|915|253|
|walking_halfsphere|Shadow|0.447759|0.398584|0.020276|0.525027|1021|299|
|walking_halfsphere|Active|0.426866|0.389276|0.042873|0.904924|575|113|

## 分场景结论与改善率

- `walking_xyz`：完整覆盖条件下 Shadow 最优。Shadow 相对 Paper1 改善 24.03%；Active 相对 Shadow退化 4.74%。
- `walking_rpy`：按已跟踪片段的 ATE，Active 数值最低；Shadow 相对 Paper1 改善 14.51%，Active 相对 Shadow 改善 73.96%。但 Active 仅输出 371 帧，而 Shadow 为 548 帧、Baseline 为 836 帧，因此不能把该低 ATE 解释为完整序列性能最优。
- `walking_halfsphere`：Baseline ATE 最低。Shadow 相对 Paper1 改善 6.51%；Active 相对 Shadow改善 4.67%，但 Active 只有 575 个轨迹帧，Shadow 为 1021 帧。

## P0 修复前后变化

|Sequence|Mode|旧 ATE|post-P0 ATE|变化|
|---|---|---:|---:|---:|
|walking_xyz|Shadow|0.641814|0.571050|-11.03%|
|walking_xyz|Active|0.539422|0.598146|+10.89%|
|walking_rpy|Shadow|0.724790|0.882434|+21.75%|
|walking_rpy|Active|0.898274|0.229810|-74.42%*|
|walking_halfsphere|Shadow|0.370537|0.447759|+20.84%|
|walking_halfsphere|Active|0.406562|0.426866|+4.99%|

正号表示 ATE 增大。带星号结果同时伴随轨迹覆盖下降，不能只归因于精度改善。

## ObjectDynamic 与过滤统计

|Sequence|Mode|Detections|Valid 3D|Invalid 3D|Dynamic transitions|Recovered|Dynamic object-frame sum|Filtered points|Filtering frames|Tracking gaps|
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|walking_xyz|Shadow|4552|4341|211|2|32|20|0|0|0|
|walking_rpy|Shadow|2198|2044|154|2|34|20|0|0|2|
|walking_halfsphere|Shadow|4781|4416|365|2|44|82|0|0|0|
|walking_xyz|Active|4552|4341|211|2|32|20|754|10|0|
|walking_rpy|Active|1388|1285|103|2|13|17|244|10|19|
|walking_halfsphere|Active|3311|3055|256|2|12|85|64|44|8|

`tracking gaps` 是成功 ObjectDynamic 日志帧之间连续缺口的代理计数，不等同于内部 Tracking 状态机导出的 LOST 次数。

## 异常轨迹与最终使用建议

Active `walking_rpy` 和 `walking_halfsphere` 存在明显轨迹覆盖下降及多个 gap episodes；尤其 `walking_rpy` 的低 ATE 只评价成功关联的较短轨迹片段。它们必须作为负面/异常结果如实保留，不能仅按 ATE 排名。

建议将本次 post-P0 Shadow 结果作为当前论文主结果候选；Active 结果适合用于过滤策略分析和局限性讨论。正式定稿前应对六种 Paper2 配置至少进行多次重复运行，报告轨迹覆盖率、成功率、均值和标准差，再决定是否把 Active 数值作为最终主表结论。
