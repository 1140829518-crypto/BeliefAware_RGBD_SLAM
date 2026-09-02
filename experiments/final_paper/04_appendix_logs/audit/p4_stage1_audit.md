# P4 Stage1：MapPoint级动态状态人工真值准备审计

## 范围

本阶段仅完成已有日志审计、只读投影日志采集、客观抽帧和人工标注模板准备。未生成动态GT，未计算TP/FP/FN/TN、Precision、Recall或F1，未修改论文。

## 现有P2/P3日志审计

P3已有 `mappoint_evidence_raw.csv` 字段为：

`frame_id,map_point_id,class_id,dynamic_hit,dynamic_score,dynamic_state,suppressed`

它缺少人工mask索引所必需的像素投影 `u,v`，也缺少输入时间戳和当次类别阈值，因此不能直接用于P4像素GT评价。

为此，在 `src/ORBmatcher.cc` 的三个既有MapPoint投影与动态分数更新位置增加由 `ORB_SLAM2_MAPPOINT_PROJECTION_LOG` 显式开启的只读日志。日志仅复制已经计算出的 `frame_id,timestamp,map_point_id,u,v,class_id,semantic_state,temporal_state,temporal_score,threshold`，没有修改分数、阈值、匹配条件、抑制条件、返回值或控制流。环境变量未设置时立即返回。

原始C++流中的timestamp采用默认输出精度；汇总文件 `mappoint_observations.csv` 的timestamp使用同一 `frame_id` 在正式association文件中的精确输入时间戳，未使用算法输出推断。

## 评价日志运行配置

- Semantic：`SemanticMode=1, Shadow=0, Active=0`。
- Temporal：`SemanticMode=2, Shadow=0, Active=0`。
- ObjectDynamic未启用。
- 未覆盖P2/P3历史结果；P4运行独立保存在 `runs/`。
- 6个必要运行均为 `exit_code=0`。
- 首次沙箱内socket启动在处理任何帧前失败，原始证据保存在 `runs/Semantic/fr3_walking_xyz/attempt_00_sandbox_denied/`，未计入实验。

## 抽帧规则

每个序列对association有效行使用固定、端点包含的等间隔抽样：

`frame_id(i) = round(i * (N - 1) / 39), i=0,...,39`

每个序列40帧，共120帧。选择过程不读取Semantic/Temporal状态、分数或轨迹误差。三个数据集所有选中RGB均存在，无替换帧。

## 标注材料

每帧生成：

- `frame_XXXX_rgb.png`：原始RGB的逐文件副本；
- `frame_XXXX_preview.png`：仅显示中性青色MapPoint投影；
- `frame_XXXX_gt.png`：全0动态GT模板；
- `frame_XXXX_ignore.png`：全0 ignore模板。

辅助预览只使用Semantic `run_01`的投影几何，不显示类别、Semantic状态、Temporal状态、分数或阈值。120帧中39帧在该次Semantic运行没有有效投影，仍按客观规则保留，未替换。

## 输出与计数

- `selected_frames.csv`：120行，每序列40行；
- `mappoint_observations.csv`：253495个去重后的选中帧MapPoint观测；
- RGB：120张；preview：120张；GT模板：120张；ignore模板：120张；
- GT非零像素：0；ignore非零像素：0；
- 标注规则：`annotation_guideline.md`。

选中帧观测数：

| Method | Sequence | Observations |
|---|---|---:|
| Semantic | fr3_walking_xyz | 78939 |
| Semantic | fr3_walking_rpy | 30984 |
| Semantic | fr3_walking_halfsphere | 22794 |
| Temporal | fr3_walking_xyz | 56275 |
| Temporal | fr3_walking_rpy | 36829 |
| Temporal | fr3_walking_halfsphere | 27674 |

同一运行路径中可能多次更新同一 `(frame_id,map_point_id)`；汇总时保留日志顺序中的最后状态，与P3口径一致。Semantic与Temporal为独立运行，其MapPoint ID仅在各自运行内部稳定，不能跨运行假定同号MapPoint为同一物理点。

## 下一阶段前置条件

人工必须逐帧完成 `*_gt.png` 和 `*_ignore.png`。不得使用YOLO框或算法状态生成GT。Stage2开始前还需检查mask尺寸、取值集合和人工完成状态，并固定生成2像素GT边缘ignore band。当前不得计算P/R/F1。
