# RGB-D 动态 SLAM 论文实验 P0 可行性审计

审计日期：2026-08-12  
项目路径：`/home/djn/123/ORB_SLAM2_AddSemantic`  
当前分支：`main`  
当前提交：`92733684846a6c578d409b127a4271876ea27077`

本报告只检查源码、开关、数据集和评价工具。未启动批量实验，未修改任何 SLAM、ObjectDynamic 或 YOLO 算法源码。

## 1. 版本与工作区状态

当前工作区不是干净状态，存在未跟踪的构建目录、论文草稿、`paer2/` 和实验驱动脚本。正式实验必须把 `git status --short` 原样写入每次配置，不能只记录 commit hash，也不能把未提交状态描述成该 commit 的纯净版本。

当前未发现 `rgbd_tum`、YOLO detector 或批处理进程运行。

## 2. 当前语义检测模型

语义服务入口为 `yolov5_RemoveDynamic/detect_speedup_send.py`，内部使用本项目随附的 YOLOv5 代码，通过 `models.experimental.attempt_load()` 加载 YOLOv5s 权重。该子目录可解析出的 Git 提交为：

`d2e754b67bc08d3634df05932cc94d8c9314a7b1`

当前 Python 环境的 PyTorch 为 `2.4.1+cu121`。

仓库中存在两份内容不同的 YOLOv5s 权重：

| 路径 | SHA-256 | 当前使用者 |
|---|---|---|
| `yolov5_RemoveDynamic/yolov5s.pt` | `9ca9a642ad00fb151bd94ac1e25f491977ca29cdad96bddcaa126944173240a9` | Paper2 的 `_run_rgbd_with_yolo.sh`、`run_paper1.sh` |
| `yolov5_RemoveDynamic/weights/yolov5s.pt` | `3cb5c452360bc5c1dfd19ab0aca46f5e15a64af028846867310313a966cfe920` | `scripts/run_tum_rgbd_experiment.py` |

因此“当前模型版本”尚未被实验框架唯一固定。正式实验前必须选定一份权重并在配置中记录绝对路径和 SHA-256；否则不同脚本产生的检测结果不可直接公平比较。此项不要求修改模型或算法。

## 3. 四种配置能否真实运行

### 3.1 功能控制机制

语义模式由 `include/SemanticConfig.h::Mode()` 读取环境变量 `ORB_SLAM2_SEMANTIC_MODE`：

- `0`：关闭语义类别集合，`UseSemanticPipeline()==false`；
- `1`：启用当前帧语义类别与检测框，但 `UseDynamicAccumulation()==false`；
- `2`：启用当前帧语义和 MapPoint 时间证据累积。

ObjectDynamic 的反馈方式目前是编译期开关：

- `ENABLE_OBJECT_DYNAMIC_SHADOW_MODE`，默认 `1`；
- `ENABLE_OBJECT_DYNAMIC_ACTIVE_MODE`，默认 `0`，且 Active 要求 Shadow 同时开启。

### 3.2 配置结论

| 配置 | 能否真实运行 | 真实配置 | 对 SLAM 轨迹的实际作用 |
|---|---|---|---|
| ORB-SLAM2 | 可以 | `ORB_SLAM2_SEMANTIC_MODE=0`，建议编译时 Shadow=0、Active=0 | 动态/静态类别集合为空；不建立 YOLO socket，可作为本工程的基础 ORB-SLAM2 配置 |
| Semantic | 可以 | mode=1，Shadow=0、Active=0 | `Frame` 仍依据当前帧 person bbox 将框内 ORB 特征置为无效；不更新历史动态分数，属于单帧语义处理 |
| Temporal | 可以 | mode=2，Shadow=0、Active=0 | 在 Semantic 基础上更新 MapPoint 历史动态分数，并在 ORBmatcher/Tracking 中按阈值抑制；会真实改变匹配与轨迹，不只是日志观测 |
| Full | 可以 | mode=2，Shadow=1、Active=1 | 同时执行语义时间累积、ObjectDynamic 状态维护和 `DynamicMapFilter` 对 Tracking 候选关联的过滤 |

注意事项：

1. 当前 `Examples/RGB-D/rgbd_tum` 链接共享的 `lib/libORB_SLAM2.so`。连续构建不同编译宏会覆盖共享库；正式运行时必须按模式依次构建并立即完成该模式，或为二进制和共享库建立隔离副本。
2. Shadow/Active 不是运行时环境开关。仅改变 shell 脚本名称并不能改变已编译二进制的模式，必须核对构建目录的 `CMAKE_CXX_FLAGS`。
3. 现有 `run_paper1.sh` 名称不适合作为独立论文最终表格中的方法名；其实际默认是 mode=2，而不是 Semantic-only。
4. Temporal 与 Full 的差异不仅是 ObjectDynamic 状态输出：Full 的 Active 过滤在姿态优化前作用于候选 MapPoint 关联。

## 4. 时间一致性动态证据的源码位置

核心状态存储在 `include/MapPoint.h`：

- `mfSemanticDynamicScore`：累计动态证据；
- `mnSemanticDynamicLastFrame`：最近更新时间；
- `mnSemanticDynamicClassId`：相关类别。

核心更新位于：

- `src/MapPoint.cc::MapPoint::UpdateSemanticDynamicScore()`；
- `src/MapPoint.cc::MapPoint::ShouldSuppressSemanticDynamic()`。

更新行为为：根据帧间隔先乘以类别衰减系数；命中动态框时增加类别增量，未命中时继续衰减。阈值、增量和衰减参数来自：

- `include/SemanticConfig.h::DynamicScoreThresholdForClass()`；
- `DynamicScoreIncrementForClass()`；
- `DynamicScoreDecayForClass()`。

调用与轨迹影响位置：

- `src/ORBmatcher.cc::SearchByProjection()` 的多个重载：投影匹配前更新证据，达到阈值则跳过该 MapPoint；
- `src/Tracking.cc::CullSemanticDynamicMapPoints()`：优化后再次更新/判断，并清除当前帧关联；
- `src/Frame.cc` RGB-D Frame 构造：mode>=1 时根据当前帧动态框使对应特征无效，这是单帧 Semantic 路径，不是历史累积本身。

## 5. 动态地图点过滤的源码位置

这里存在两层不同机制，论文与实验必须明确区分。

### 5.1 MapPoint 时间证据抑制

- `src/ORBmatcher.cc`：达到动态证据阈值的投影 MapPoint 不参与匹配；
- `src/Tracking.cc::CullSemanticDynamicMapPoints()`：达到阈值的当前帧 MapPoint 关联被置空并标记 outlier。

### 5.2 ObjectDynamic Active 过滤

- 状态视图到点状态：`paper2_development/modules/ObjectDynamic/DynamicMapFilter.cc::UpdateMapView()`；
- 判断接口：`DynamicMapFilter::IsDynamicMapPoint()`；
- 当前帧过滤：`src/Tracking.cc::FilterCurrentFrameDynamicMapPoints()`；
- 局部地图候选过滤：`src/Tracking.cc::FilterLocalDynamicMapPoints()`；
- 插入流程：`src/Tracking.cc::TrackLocalMap()`，分别在 `UpdateLocalMap()` 前后及 `Optimizer::PoseOptimization()` 前执行。

Active 的真实行为是“移除当前 Tracking 帧/局部候选集合中的关联”，不是删除 `MapPoint` 对象、KeyFrame 观测或全局地图数据。

## 6. TUM walking 数据完整性

三个目标序列的 RGB、depth、列表、groundtruth 和实际使用的 association 均存在：

| 序列 | RGB 图像/列表 | Depth 图像/列表 | Groundtruth 行 | Association 行 | 结论 |
|---|---:|---:|---:|---:|---|
| `fr3_walking_xyz` | 859/859 | 833/833 | 2884 | 827 | 完整，可直接运行 |
| `fr3_walking_rpy` | 910/910 | 872/872 | 3062 | 866 | 完整，可直接运行 |
| `fr3_walking_halfsphere` | 1067/1067 | 1029/1029 | 3582 | 1021 | 完整，可直接运行 |

数据根目录为 `/home/djn/datasets/TUMRGBD/`。实际 association 使用项目内 `dataset_associations/fr3_walking_*_associate.txt`。Association 行数少于 RGB/depth 原始列表是时间戳配对后的正常结果，正式实验中的 `total_frame_count` 应定义为 association 有效行数，而不是 RGB 文件总数。

## 7. Bonn 数据集与 Precision/Recall/F1 审计

Bonn 数据集存在于：

`experiment_new/dataset/bonn_rgbd_dynamic/`

可见三个完整 TUM 格式序列：

| 序列 | RGB | Depth | Groundtruth | Association |
|---|---:|---:|---:|---:|
| `rgbd_bonn_person_tracking` | 580 | 580 | 583 | 580 |
| `rgbd_bonn_synchronous` | 332 | 332 | 333 | 332 |
| `rgbd_bonn_crowd` | 928 | 927 | 933 | 928 |

`experiment_new/scripts/run_bonn_experiment.py` 和 `evaluate_bonn.py` 只运行/汇总轨迹的 ATE、RPE 与 FPS，没有计算动态判别 Precision、Recall、F1。

仓库中的 `scripts/evaluate_dynamic_detection.py` 也不是 Bonn 动态真值评价。它：

1. 读取 TUM walking 序列的 YOLO person 检测；
2. 对 person 检测的短缺失段做人工规则补全，生成“帧级 reference dynamic”；
3. 将每帧是否为动态作为二分类对象；
4. 使用脚本内构造的 semantic/motion/temporal probability 计算 TP、FP、TN、FN。

因此该脚本的 Precision/Recall/F1 统计对象是“帧级是否存在动态 person 的派生二分类标签”，不是动态地图点、特征点、像素、检测区域或可靠的目标级人工真值；而且 reference 来自检测结果本身，不是 Bonn 标注。它不能作为 Bonn Precision/Recall/F1，也不能严谨声称为检测准确率。

当前结论：项目内没有可确认的 Bonn 动态地图点/特征点/像素/目标人工真值评价链。若没有外部人工标注或官方动态掩膜映射，Bonn Precision/Recall/F1 目前无法可靠实现，应标记为不可用。

## 8. 轨迹评价能力

`scripts/evaluate_tum_metrics.py` 可以直接计算并保存：

- ATE RMSE、mean、median、std、min、max；
- RPE translation RMSE、mean 等统计；
- RPE rotation RMSE、mean 等统计，单位 degree；
- 时间戳最大匹配差默认 0.02 s；
- 估计位置通过 SE(3) 刚体对齐到 groundtruth。

脚本使用 NumPy/SciPy 自行实现，不依赖 evo，当前可直接调用。系统环境中普通 Python 路径未安装 evo；`/tmp/paper2_evo_packages` 也未检测到可导入的 evo。因此正式实验应统一使用上述已验证脚本，或在实验开始前固定 evo 环境，但不能混用两套实现。

FPS 可从 `rgbd_tum` 日志的 mean tracking time 计算为 `1/mean_tracking_time`。这反映 SLAM Tracking 平均处理速率，不包含 YOLO 独立进程的端到端耗时；论文必须注明口径。如需端到端 FPS，应由实验 runner 记录 wall-clock time 与 association 帧数。

## 9. 可直接复用的实验脚本

### 9.1 推荐作为统一入口

- `scripts/run_tum_rgbd_experiment.py`：单次运行、YOLO socket、轨迹评价、runtime 输出；支持 `orb/hard/dynamic/full` 语义模式，但 Object Shadow/Active 仍取决于实际链接库的编译宏。
- `scripts/evaluate_tum_metrics.py`：统一 ATE/RPE 评价。
- `scripts/evaluate_tracking_success_rate.py`：已有跟踪覆盖统计逻辑，正式使用前需统一 total frames 定义。
- `scripts/summarize_semantic_stats.py`、`scripts/summarize_sequence_diagnostics.py`：可复用语义统计解析。

### 9.2 Paper2 shell 脚本

- `experiment_new/paper2/scripts/run_baseline.sh`；
- `run_shadow.sh`；
- `run_active.sh`；
- `_run_rgbd.sh`、`_run_rgbd_with_yolo.sh`。

这些脚本保留了单次运行接口和输出目录保护，但需要外部保证所传二进制/共享库确实由对应宏构建。`run_paper1.sh` 默认 mode=2，不应当用作 Semantic-only。

### 9.3 消融与参数脚本

- `experiment_new/independent_ablation_v3/evaluation/scripts/run_independent_ablation.py`：已有多配置、配置存档、失败保留和聚合框架，可借用结构；其 `object_level_map` 定义是 mode=1 + object map，并不等同于当前论文所需的 ObjectDynamic Shadow/Active 消融。
- `experiment_new/scripts/run_lambda_sensitivity_analysis.py`；
- `scripts/run_theta_sensitivity_analysis.py`。

正式批量前必须修正实验调度层面的并发隔离：每个运行使用唯一 socket，且禁止多个 batch scheduler 同时操作同一结果根目录。此前残留批处理已经证明默认共享 socket 会污染运行。

## 10. 最少需要增加的实验开关与日志

不需要改动核心算法公式或阈值。为完成可审计实验，最小工程改动建议如下。

### P0：正式运行前必须具备

1. **构建模式可验证标识**：在每次配置中写入 Shadow/Active 两个编译宏、二进制和 `libORB_SLAM2.so` 的 SHA-256。无需改算法；可由构建/runner 脚本完成。
2. **唯一 socket 与单实例锁**：每个 run 使用包含 PID/run_id 的 socket；结果根目录加锁，防止多个批处理并发。只改实验脚本。
3. **固定 YOLO 权重**：runner 显式接收权重路径并记录 SHA-256，所有配置使用同一份。只改实验脚本。
4. **运行状态记录**：在开始时写 `running`，正常结束写 `success`，崩溃/超时/中断写对应状态；不得用同一 run_id 自动重跑覆盖。只改实验脚本。
5. **统一帧数与耗时口径**：保存 association 总帧数、有效轨迹 pose 数、SLAM mean tracking time、端到端 wall time，并明确两种 FPS。只改实验/统计脚本。

### P1：核心消融解释所需的最小开关

1. **ObjectDynamic 运行时模式或严格隔离构建**：当前 Shadow/Active 是编译期开关。无需一定新增源码开关；使用三个隔离构建及独立共享库即可真实运行。若希望同一二进制切换，则需要最小运行时开关，但这属于后续代码变更，应先由用户批准。
2. **Semantic 与 Temporal 已可由 mode=1/2 区分**，无需新增算法开关。
3. **Temporal 是否反馈 Tracking 已有真实行为**：mode=2 的 MapPoint 分数阈值会在 ORBmatcher 和 Tracking 中抑制关联，所以可进行 ATE 消融，不应描述为只观测。

### P1：时间一致性论文指标所需日志

现有 `SemanticDynamicStatistics.txt` 只有每帧聚合字段：dynamic keypoints、dynamic map points、suppressed map points、dynamic/static/total objects；不能还原单个 MapPoint 的证据轨迹与状态切换。

若论文要真实报告达到阈值帧数、衰减曲线和 switching frequency，至少需要可选实验日志（不改变判断逻辑）：

- `frame_id, map_point_id, class_id, dynamic_hit, score_before, score_after, threshold, suppressed`；
- ObjectDynamic 状态事件已有部分日志，但若要完整统计，还需保证 Lost 事件和所有状态转换均输出；
- 每帧 Active 日志已有 `before_points, filtered_points, after_points`，可直接用于过滤统计。

### 当前无法可靠实现

- Bonn Precision/Recall/F1：缺少可确认的动态真值及对应评价脚本；
- 逐 MapPoint/逐目标动态准确率：当前数据集与日志没有相应人工真值；
- 将 `scripts/evaluate_dynamic_detection.py` 的派生帧标签当作真实检测精度：方法学上不成立。

## 11. P0 总结

- ORB-SLAM2、Semantic、Temporal、Full 四种配置均可由当前代码真实运行。
- Semantic/Temporal 的环境模式已存在；Full 需要 Active 编译构建，不能只靠运行脚本名切换。
- 三个 TUM walking 序列及 association/groundtruth 完整。
- 三个 Bonn 序列数据完整，但 Bonn Precision/Recall/F1 没有可靠真值评价链。
- 当前轨迹评价脚本支持所需 ATE 全部统计以及平移/旋转 RPE RMSE。
- 正式批量实验前最少应完善实验层的权重固定、构建哈希记录、唯一 socket、单实例锁和失败状态管理；这些都不需要修改核心算法。

本审计完成后停止，不启动批量实验，等待用户确认。
