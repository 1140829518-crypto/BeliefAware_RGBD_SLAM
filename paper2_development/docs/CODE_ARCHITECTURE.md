# ORB-SLAM2 AddSemantic Code Architecture

分析基线：`paper2_development` 分支，提交 `3de17c5`。本文记录论文1冻结代码的运行链路和论文2可采用的外部扩展点，不修改现有 SLAM 算法。

## System Entry

| 文件路径 | 函数名称 | 作用 |
|---|---|---|
| `Examples/RGB-D/rgbd_tum.cc` | `main()` | RGB-D 离线运行入口；读取关联文件、RGB/深度图像，初始化检测 socket 和 SLAM 系统，逐帧调用 `TrackRGBD()` |
| `Examples/RGB-D/rgbd_tum.cc` | `ORB_SLAM2::System SLAM(...)` | 使用词典、相机配置和 `System::RGBD` 传感器类型创建系统 |
| `src/System.cc` / `include/System.h` | `System::System()` | 加载词典与配置，创建 Map、KeyFrameDatabase、Tracking、LocalMapping、LoopClosing、Viewer，并启动后台线程 |
| `src/System.cc` / `include/System.h` | `System::TrackRGBD()` | 检查传感器类型与系统状态，将 RGB、深度、时间戳和检测结果转交 Tracking |
| `src/Tracking.cc` / `include/Tracking.h` | `Tracking::GrabImageRGBD()` | 灰度化与深度尺度转换，构造当前 Frame，随后进入 `Track()` 主跟踪流程 |

主调用链：

```text
Examples/RGB-D/rgbd_tum.cc::main
  → System::System
  → per frame: System::TrackRGBD
  → Tracking::GrabImageRGBD
  → Frame RGB-D constructor
  → Tracking::Track
```

## Tracking

文件与类：

- 文件：`include/Tracking.h`、`src/Tracking.cc`
- 主类：`ORB_SLAM2::Tracking`
- 帧结构：`include/Frame.h`、`src/Frame.cc` 中的 `ORB_SLAM2::Frame`
- 匹配器：`include/ORBmatcher.h`、`src/ORBmatcher.cc` 中的 `ORB_SLAM2::ORBmatcher`
- 优化器：`include/Optimizer.h`、`src/Optimizer.cc` 中的 `ORB_SLAM2::Optimizer`

| 环节 | 关键函数 | 作用 |
|---|---|---|
| 跟踪状态机 | `Tracking::Track()` | 按初始化、恒速模型、参考关键帧、局部地图和重定位状态组织跟踪流程 |
| 特征提取 | RGB-D `Frame::Frame()`、`Frame::ExtractORB()` | 在 Frame 构造期间调用 ORBextractor 生成关键点和描述子 |
| 参考帧匹配 | `Tracking::TrackReferenceKeyFrame()`、`ORBmatcher::SearchByBoW()` | 使用词袋约束匹配当前帧和参考关键帧 |
| 运动模型匹配 | `Tracking::TrackWithMotionModel()`、`ORBmatcher::SearchByProjection()` | 按上一帧和速度模型投影匹配地图点 |
| 局部地图匹配 | `Tracking::TrackLocalMap()`、`Tracking::SearchLocalPoints()`、`ORBmatcher::SearchByProjection()` | 更新局部关键帧/地图点，并搜索当前帧可见的局部地图点 |
| 位姿优化 | `Optimizer::PoseOptimization()` | 固定 MapPoint，优化当前 Frame 位姿并标记几何外点 |
| 动态区域预过滤 | RGB-D `Frame::Frame()`、`Frame::IsInDynamic()`、`Frame::IsInStatic()` | 特征提取后检查检测框；动态框内且不在静态框内的关键点被标记并移出有效图像范围 |
| 动态地图点过滤 | `Tracking::CullSemanticDynamicMapPoints()` | 在参考帧、运动模型和局部地图位姿优化后检查动态证据阈值，从当前帧关联中抑制地图点 |

动态点接口位于 Frame 和 Tracking 两层：Frame 处理检测框到特征点的区域过滤；Tracking 处理已关联 MapPoint 的证据更新与当前帧抑制。

## LocalMapping

- 文件：`include/LocalMapping.h`、`src/LocalMapping.cc`
- 类：`ORB_SLAM2::LocalMapping`

| 环节 | 关键函数 | 作用 |
|---|---|---|
| 建图线程入口 | `LocalMapping::Run()` | 消费 Tracking 插入的关键帧，依次执行处理、剔除、建点、融合、局部优化和关键帧剔除 |
| 关键帧处理 | `LocalMapping::ProcessNewKeyFrame()` | 计算 BoW，建立 KeyFrame–MapPoint 观测，更新地图点描述子、法向和深度，并加入 Map |
| 新地图点创建 | `LocalMapping::CreateNewMapPoints()` | 与共视关键帧进行极线约束匹配和三角化，创建并登记新 MapPoint |
| 地图点质量维护 | `LocalMapping::MapPointCulling()` | 按坏点状态、找到率、年龄和观测数量淘汰近期地图点 |
| 邻域融合 | `LocalMapping::SearchInNeighbors()` | 与相邻关键帧投影融合重复地图点，并更新描述子、法向和深度 |
| 局部优化 | `Optimizer::LocalBundleAdjustment()` | 优化局部关键帧位姿和局部地图点位置 |
| 关键帧管理 | `LocalMapping::KeyFrameCulling()` | 当关键帧 90% 以上有效地图点具有足够冗余观测时将其剔除 |

## MapPoint

- 文件：`include/MapPoint.h`、`src/MapPoint.cc`
- 类：`ORB_SLAM2::MapPoint`
- 容器管理：`include/Map.h`、`src/Map.cc` 中的 `ORB_SLAM2::Map`

MapPoint 数据结构维护世界坐标、参考关键帧、关键帧观测表、代表描述子、平均观测方向、尺度距离范围、可见/找到计数、坏点和替换关系，以及论文1加入的语义动态状态。

| 类型 | 变量/函数 | 作用 |
|---|---|---|
| 几何状态 | `mWorldPos`、`GetWorldPos()`、`SetWorldPos()` | 保存和访问世界坐标 |
| 观测状态 | `mObservations`、`AddObservation()`、`EraseObservation()` | 维护 KeyFrame 与特征索引的观测关系 |
| 生命周期 | `SetBadFlag()`、`isBad()`、`Replace()` | 从关键帧和 Map 中解除坏点，或融合替换重复点 |
| 描述与尺度 | `ComputeDistinctiveDescriptors()`、`UpdateNormalAndDepth()` | 更新代表描述子、法向和有效观测距离 |
| 跟踪质量 | `IncreaseVisible()`、`IncreaseFound()`、`GetFoundRatio()` | 维护地图点可跟踪性统计 |
| 动态分数 | `mfSemanticDynamicScore` | 论文1的地图点动态证据累计值 |
| 时间状态 | `mnSemanticDynamicLastFrame` | 最近一次动态证据更新的 Frame ID |
| 动态接口 | `UpdateSemanticDynamicScore()`、`GetSemanticDynamicScore()`、`ShouldSuppressSemanticDynamic()` | 更新/读取动态证据并执行阈值判断 |

`Map::AddMapPoint()` 和 `Map::EraseMapPoint()` 负责全局容器中的登记与移除；`LocalMapping` 负责主要的点质量维护。

## Semantic Detection

| 文件 | 接口 | 输入 | 输出/保存内容 |
|---|---|---|---|
| `yolov5_RemoveDynamic/detect_speedup_send.py` | 外部 YOLO 检测进程 | RGB 图像流 | 经 Unix socket 发送检测框、类别和置信度文本 |
| `Examples/RGB-D/rgbd_tum.cc` | `MakeDetect_result()` | socket 文件描述符 | 每帧 `vector<pair<vector<double>, int>>` |
| `Examples/RGB-D/rgbd_tum.cc` | `LoadBoundingBoxFromPython()` | 单个检测文本片段 | `[left, top, right, bottom]` 与内部 `class_id` |
| `Examples/RGB-D/rgbd_tum.cc` | `LoadBoundingBox()` | 离线检测结果文件 | 同样的 bbox/类别结构；当前主流程使用 socket 接口 |
| `src/Frame.cc` / `include/Frame.h` | RGB-D `Frame` 构造函数 | 检测结果容器 | 每个检测被保存为当前帧 `objects_cur_` 中的 `Object` |
| `src/Frame.cc` | `IsPixelInDynamicBox()`、`IsPixelInStaticBox()` | 像素坐标与 `objects_cur_` | bbox 区域归属及 box ID |
| `include/SemanticConfig.h` | `IsDynamicObjectClass()`、`IsStaticObjectClass()` | 内部类别编号 | 动态/静态类别判定 |

当前实现没有像素级 segmentation mask；矩形 bbox 被用作区域掩膜。类别映射在 RGB-D 示例入口完成，内部约定 person 为动态类 `3`，静态/低动态分组为 `1、2`。类别和 bbox 保存在 Frame 的 `Object` 实例中。

## Dynamic Evidence Module

- 文件：`include/MapPoint.h`、`src/MapPoint.cc`、`include/SemanticConfig.h`、`src/Tracking.cc`
- 类：`MapPoint`、`Tracking`
- 核心函数：`MapPoint::UpdateSemanticDynamicScore()`、`MapPoint::ShouldSuppressSemanticDynamic()`、`Tracking::CullSemanticDynamicMapPoints()`

算法流程：

```text
current Frame detections
  → test associated keypoint against dynamic/static bbox
  → dynamic-only bbox hit
  → MapPoint::UpdateSemanticDynamicScore(true, frameId, classId)
  → decay old score by lambda^(frame gap)
  → add class-dependent evidence increment
  → compare with class-dependent threshold
  → mark current association as outlier and clear it when threshold is reached
```

动态证据更新公式对应实现为：

```text
score ← score × decay^(current_frame - last_update_frame)
if dynamic_hit:
    score ← score + increment
else:
    score ← score × decay
suppress ⇔ score ≥ threshold
```

默认参数集中在 `include/SemanticConfig.h`：person 使用阈值 `1.0`、增量 `3.0`、衰减 `0.85`；其他类别默认阈值 `3.0`、增量 `1.0`、衰减 `0.95`，部分参数可由环境变量覆盖。

实现边界：当前主流程只发现动态命中时调用 `UpdateSemanticDynamicScore(true, ...)`，没有发现 `false` 调用；非命中额外衰减分支已定义但未接入。抑制只作用于当前 Frame 的 MapPoint 关联，不直接永久删除 Map 中的 MapPoint。

## Paper2 Extension Points

论文2应在 `paper2_development/modules/ObjectDynamic/` 中独立实现，通过适配器读取冻结系统的输出，避免修改 `src/`、`include/` 和 `Examples/`。

建议扩展边界：

1. **Detection Adapter**：消费现有 `bbox + class_id`，未来可转换像素级 mask，但不改变论文1 Frame。
2. **Frame Observation Adapter**：组合时间戳、相机位姿、深度、bbox 和可选 MapPoint 观测，生成论文2对象观测。
3. **ObjectState**：在 `SemanticObject` 现有对象 ID/类别/位置基础上独立维护速度、动态概率和轨迹状态。
4. **MotionEstimator**：在世界坐标系估计对象运动并预测短时轨迹，显式补偿相机运动。
5. **DynamicMapManager**：完成对象关联、对象地图更新、遮挡恢复和静态/动态地图视图管理。
6. **Offline First**：先通过导出的检测、位姿和语义对象文件进行离线验证；在线接入另行设计构建目标和兼容层。

论文1冻结代码是只读基线。任何未来在线集成都应先形成接口文档和回退方案，再通过论文2专用适配层接入。
