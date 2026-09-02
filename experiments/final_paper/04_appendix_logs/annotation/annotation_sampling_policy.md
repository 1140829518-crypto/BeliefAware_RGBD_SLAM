# P4 V2人工标注抽帧策略

抽帧只使用association帧序和去重后的有效MapPoint投影数量，不读取Semantic/Temporal预测状态、dynamic score、threshold、suppression、GT或图像内容。

固定门槛：`minimum_valid_projections = 20`。

候选帧必须在Semantic和Temporal两个独立运行中均具有不少于该门槛的唯一 `(frame_id,map_point_id)` 投影，并且association中存在完整的前2、前1、当前、后1、后2帧上下文。该上下文边界条件不读取算法预测或图像内容。

在每个序列按frame_id排序后的候选集合中，采用端点包含的等间隔索引抽取40帧：

`candidate_index(i) = round(i * (K - 1) / 39), i=0,...,39`。

同一帧内同一MapPoint的多次matcher日志只计为一个评价观测；保留日志顺序中的最终记录用于后续评价。

## 候选帧数量

| Sequence | >=20 | >=10 | >=5 | >=1 |
|---|---:|---:|---:|---:|
| fr3_walking_xyz | 823 | 823 | 823 | 823 |
| fr3_walking_rpy | 500 | 500 | 500 | 500 |
| fr3_walking_halfsphere | 445 | 445 | 445 | 445 |

现有原始日志没有matcher阶段字段，因此不能可靠区分重复记录来自哪个ORBmatcher调用阶段。
