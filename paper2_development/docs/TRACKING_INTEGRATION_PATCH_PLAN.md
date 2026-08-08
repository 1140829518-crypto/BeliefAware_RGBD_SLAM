# Tracking Integration Patch Plan

本文基于 `paper2_development` 分支当前实现，给出 `ObjectDynamicAdapter` 接入 ORB-SLAM2 Tracking 的后续补丁方案。本次仅分析和设计，不修改 `src/`、`include/` 或现有算法。

## 1. 现有数据流

```text
RGB image + registered depth + timestamp
                 +
external YOLO detections
                 ↓
System::TrackRGBD()
                 ↓
Tracking::GrabImageRGBD()
                 ↓
Frame RGB-D constructor
                 ↓
Tracking::Track()
                 ↓
TrackLocalMap()
                 ↓
NeedNewKeyFrame() / CreateNewKeyFrame()
                 ↓
LocalMapping::InsertKeyFrame() → LocalMapping::Run()
```

| 阶段 | 文件 | 类 | 关键函数 | 当前作用 |
|---|---|---|---|---|
| RGB-D 分发 | `src/System.cc`、`include/System.h` | `System` | `TrackRGBD()` | 校验 RGB-D 模式，处理定位模式和复位，将图像、深度、时间戳及检测结果交给 Tracking |
| 当前帧输入 | `src/Tracking.cc`、`include/Tracking.h` | `Tracking` | `GrabImageRGBD()` | 灰度化 RGB 图像、转换深度尺度，构造 `mCurrentFrame`，随后调用 `Track()` |
| Frame 构造 | `src/Frame.cc`、`include/Frame.h` | `Frame` | RGB-D `Frame` 构造函数 | 保存检测对象、提取 ORB、按语义框标记/移除特征、计算 RGB-D 深度并初始化 MapPoint 槽位 |
| 主跟踪 | `src/Tracking.cc` | `Tracking` | `Track()` | 初始化或估计初始位姿，跟踪局部地图，确认跟踪状态，维护运动模型并决定是否创建关键帧 |
| 局部地图跟踪 | `src/Tracking.cc` | `Tracking` | `TrackLocalMap()` | 更新局部关键帧/点、投影搜索、最终位姿优化、论文1动态点抑制及内点统计 |
| 关键帧创建 | `src/Tracking.cc` | `Tracking` | `NeedNewKeyFrame()`、`CreateNewKeyFrame()` | 检查建图负载与跟踪质量；从当前 Frame 创建 KeyFrame、创建 RGB-D 近点并提交 LocalMapping |
| 局部建图 | `src/LocalMapping.cc`、`include/LocalMapping.h` | `LocalMapping` | `Run()`、`ProcessNewKeyFrame()` | 异步处理关键帧队列，更新 MapPoint 观测、共视图和地图，执行局部 BA 与剔除 |

## 2. `Tracking::Track()` 流程

`Track()` 持有 `mpMap->mMutexMapUpdate`，主要流程如下：

1. `NO_IMAGES_YET` 转为 `NOT_INITIALIZED`。
2. 未初始化时调用 `StereoInitialization()`（RGB-D 与双目）或 `MonocularInitialization()`；初始化失败则提前返回。
3. 已初始化时根据状态、运动模型和运行模式，从 `TrackReferenceKeyFrame()`、`TrackWithMotionModel()`、`Relocalization()` 中选择初始位姿估计路径。
4. 初始估计成功后调用 `TrackLocalMap()`，获得最终局部地图匹配与优化位姿。
5. 依据 `bOK` 将 `mState` 更新为 `OK` 或 `LOST`，更新 FrameDrawer。
6. `bOK=true` 时更新相机恒速模型、相机显示位姿、临时 MapPoint，并执行 `NeedNewKeyFrame()`；满足条件时调用 `CreateNewKeyFrame()`。
7. 清理外点，保存 `mLastFrame` 和相对位姿轨迹。

需要注意：初始化分支成功后不会进入同一轮 `else` 中的常规 `bOK` 流程。因此第一版接入应明确规定“初始化帧只建立适配器基准或跳过”，不能假设每次 `Track()` 都会经过常规提交点。

## 3. `TrackLocalMap()` 流程

```text
UpdateLocalMap()
  → SearchLocalPoints()
  → Optimizer::PoseOptimization(&mCurrentFrame)
  → CullSemanticDynamicMapPoints()
  → UpdateSemanticObjectMap()（配置启用时）
  → 更新 MapPoint found 统计和 mnMatchesInliers
  → 跟踪成功阈值判断
```

最终 `PoseOptimization()` 之后，`mCurrentFrame.mTcw`、`mvpMapPoints`、`mvbOutlier` 和局部地图匹配最完整。紧随其后的 `CullSemanticDynamicMapPoints()` 会执行论文1点级动态证据更新，并可能从当前 Frame 清空需抑制的动态 MapPoint。因此：

- 对象级 MapPoint ID 快照应在最终 `PoseOptimization()` 后、论文1 culling 前采集。
- `ObjectDynamicAdapter::ProcessFrame()` 不应在这里直接调用，因为 `TrackLocalMap()` 仍可能以匹配数不足返回失败，而且同一帧还存在不进入 `TrackLocalMap()` 的降级路径。
- 不应在 `TrackReferenceKeyFrame()` 或 `TrackWithMotionModel()` 的每次优化后提交，否则同一 Frame 会重复累积动态概率和生命周期计数。

## 4. 当前 Frame 可用数据

| 快照字段 | 当前来源 | 转换要求 |
|---|---|---|
| `frame_id` | `mCurrentFrame.mnId` | 转为 `std::uint64_t` |
| `timestamp` | `mCurrentFrame.mTimeStamp` | 转为 `double`，保持严格递增检查 |
| `camera_pose` | `mCurrentFrame.mTcw` | 当前保存的是 `Tcw`；必须约定 Adapter 快照使用 `Tcw` 还是 `Twc`，并统一转换到 `PoseMatrix4d` |
| bbox | `mCurrentFrame.objects_cur_[i]->vdetect_parameter` | 校验至少四项、坐标有限且面积为正 |
| class ID | `mCurrentFrame.objects_cur_[i]->ndetect_class` | 通过统一类别表生成 `class_name` |
| confidence | 当前 `Object` 不保存 | 不得伪造；未来须从入口 DTO 补齐，或在缺失策略下显式使用中性值并禁用置信度门控 |
| detection 3D position | bbox 中心/稳健深度 + 相机位姿 | 从 RGB-D 深度获得相机系点，再通过 `Twc = Tcw.inv()` 转成世界坐标；需过滤无效深度和边缘背景 |
| MapPoint IDs | `mCurrentFrame.mvpMapPoints[k]->mnId` | 仅采集非空、非 bad、非 outlier 且特征位于检测区域的点；只复制 ID，不保存指针 |

`Frame::objects_cur_` 保存 `shared_ptr<Object>`，但 `ObjectSnapshot` 必须在 Tracking 线程内完成值复制。任何 `Object*`、`MapPoint*`、`Frame&` 或 OpenCV 矩阵引用都不得跨入 ObjectDynamic。

## 5. YOLO 检测结果来源

YOLO 推理由 SLAM 核心外部完成。当前 RGB-D 示例 `Examples/RGB-D/rgbd_tum.cc` 通过 `MakeDetect_result()` 从检测进程 socket 接收结果，`LoadBoundingBoxFromPython()` 将文本转换为 `pair<vector<double>, int>`，之后调用：

```text
System::TrackRGBD(imRGB, imD, timestamp, detect_result)
  → Tracking::GrabImageRGBD(..., detect_result)
  → Frame(..., detect_result)
  → Frame::objects_cur_
```

现有传输结构只稳定保留 bbox 和内部 class ID。检测文本虽然包含 confidence，但 `pair<vector<double>, int>` 和 `Object` 均没有独立 confidence 字段，当前链路会丢失该信息。未来正式补丁若要求真实 confidence，应先设计向后兼容的检测 DTO；本阶段的 Tracking 接入不得修改 YOLO 或论文1接口，也不得把假定值描述为真实置信度。

## 6. 推荐插入方案

### 6.1 两阶段接入

推荐采用“快照采集 + 单次提交”两阶段方案。

#### 阶段 A：采集最终关联快照

- 修改文件（未来）：`src/Tracking.cc`
- 函数：`Tracking::TrackLocalMap()`
- 插入位置：`Optimizer::PoseOptimization(&mCurrentFrame)` 之后，`CullSemanticDynamicMapPoints()` 之前
- 操作：调用一个只读转换辅助函数，例如 `BuildObjectSnapshotCandidate(mCurrentFrame)`
- 结果：覆盖保存本帧候选 `ObjectSnapshot`，但不调用 `ProcessFrame()`

该位置能在论文1移除动态点之前读取最终位姿和有效 feature–MapPoint 对应。采集过程只复制标量、固定大小数组和 ID。

#### 阶段 B：单次处理对象状态

- 修改文件（未来）：`src/Tracking.cc`
- 函数：`Tracking::Track()`
- 插入位置：常规跟踪分支中 `bOK` 已由 `TrackLocalMap()` 返回值确定之后，进入 `if(bOK)` 后；位于 `NeedNewKeyFrame()` / `CreateNewKeyFrame()` 之前
- 调用：`mObjectDynamicAdapter.ProcessFrame(mPendingObjectSnapshot)`
- 输出：缓存本帧 `StableMapView`

这是 `ProcessFrame()` 的推荐唯一在线调用点。原因是：

1. 当前帧最终位姿已经优化且跟踪结果已确认。
2. 每个成功输入帧只提交一次，避免概率和生命周期重复累计。
3. 调用发生在关键帧创建之前，未来可让 `StableMapView` 为关键帧/建图策略提供只读决策依据。
4. 第一阶段应采用 shadow mode，只记录输出，不改变当前帧匹配、位姿或关键帧内容。

若 `bOK=false`，第一版不调用 `ProcessFrame()`，避免用不可靠位姿更新对象运动；另设一次“frame missed”接口是后续需求，不能用无检测的有效快照代替，因为那会把跟踪失败误解释为所有对象未匹配。纯定位或没有进入 `TrackLocalMap()` 但最终定位成功的路径，应构造带质量标志的降级快照；现有 `ObjectSnapshot` 尚无质量字段，正式补丁前应补充设计。

### 6.2 初始化帧策略

RGB-D 初始化成功帧已有位姿和初始 MapPoint，但 `Track()` 会在初始化分支结束后绕过常规 `bOK` 块。建议首版：

- 初始化成功帧只构造初始快照并调用一次 Adapter，作为 object ID 基准；或
- 明确跳过初始化帧，从下一正常帧开始处理。

推荐前者，但必须设置独立的 `processed_frame_id` 防重。若初始化帧的对象三维位置质量不足，则采用后者并记录跳过原因。

## 7. 未来补丁的修改清单

本次不执行下列修改。实际接入时建议最小变更如下：

### 修改文件

| 文件 | 计划修改 |
|---|---|
| `include/Tracking.h` | 前向声明/包含适配器接口；声明快照构造辅助函数、Adapter 所有权、待提交快照、StableMapView 和防重状态 |
| `src/Tracking.cc` | 在 `TrackLocalMap()` 采集候选快照；在 `Track()` 的成功单次提交点调用 `ProcessFrame()`；Reset 时清理 Adapter 状态 |
| 主工程构建文件 | 仅在论文2构建开关启用时编译 ObjectDynamic 源文件并添加 include 路径；默认关闭以保持论文1基线 |

`System.cc`、`Frame.cc` 和 `LocalMapping.cc` 第一阶段无需修改。`System` 继续负责原有输入；转换在 Tracking 内完成；LocalMapping 不直接持有 Adapter。

### 新增变量建议

```text
std::unique_ptr<Paper2::ObjectDynamicAdapter> mpObjectDynamicAdapter
Paper2::ObjectSnapshot mPendingObjectSnapshot
Paper2::StableMapView mStableMapView
bool mbHasPendingObjectSnapshot
bool mbObjectDynamicEnabled
unsigned long mnLastObjectDynamicFrameId
```

建议 Adapter 由 `Tracking` 独占，原因是 `ProcessFrame()` 当前会修改内部 ObjectAssociation、MotionEstimator 和 DynamicMapManager 状态，不应被 Tracking 与 LocalMapping 两线程同时调用。若需要向 LocalMapping 发布视图，只传不可变副本或版本化消息。

### 辅助函数建议

| 函数 | 参数 | 返回值 | 职责 |
|---|---|---|---|
| `BuildObjectSnapshotCandidate` | `const Frame&` | `bool` | 校验位姿和检测，完成值复制、3D 反投影及 MapPoint ID 采集 |
| `ConvertCameraPose` | `const cv::Mat& Tcw` | `PoseMatrix4d` | 固定并记录坐标系约定，拒绝空或非 4×4 位姿 |
| `EstimateDetectionPosition3D` | Frame、bbox | `Vector3D` + validity | 使用 bbox 内稳健深度而非单个中心像素，转换到世界坐标 |
| `CollectDetectionMapPointIds` | Frame、bbox | ID vector | 过滤空、bad、outlier 和背景深度不一致点，去重 ID |
| `ProcessPendingObjectSnapshot` | 无 | `StableMapView`/状态 | 检查开关与 Frame ID，保证每帧最多调用一次 `ProcessFrame()` |

## 8. 调用流程

```text
System::TrackRGBD
  → Tracking::GrabImageRGBD
      → construct Frame (bbox/class copied to objects_cur_)
      → Tracking::Track
          → initial pose tracking
          → Tracking::TrackLocalMap
              → final PoseOptimization
              → BuildObjectSnapshotCandidate        [只读采集]
              → paper1 CullSemanticDynamicMapPoints
              → inlier statistics / return bOK
          → if bOK
              → ProcessPendingObjectSnapshot
                  → ObjectDynamicAdapter::ProcessFrame [每帧一次]
                      → ObjectAssociation
                      → ObjectState update
                      → MotionEstimator
                      → DynamicMapManager
                      → StableMapView
              → NeedNewKeyFrame / CreateNewKeyFrame
          → save last frame and trajectory
```

第一阶段 `StableMapView` 仅用于日志、可视化和离线评估。不得据此修改当前 `mCurrentFrame.mvpMapPoints`，否则会与论文1 `CullSemanticDynamicMapPoints()` 形成双重抑制，并改变冻结基线。

## 9. MapPoint 与 LocalMapping 边界

Tracking 只把 MapPoint 的稳定 `mnId` 写入 `SnapshotDetection::map_point_ids`。ObjectDynamic 使用自身的 `Object ID → MapPoint ID list`，不修改 `MapPoint`，也不持有指针。

第一阶段 LocalMapping 无调用点。原因是 `LocalMapping` 异步执行 `ProcessNewKeyFrame()`、地图点创建/替换、局部 BA 与剔除；让它直接访问 Adapter 会引入锁顺序、对象状态竞争和悬空引用风险。未来若需同步建图变化，应发布只包含 KeyFrame ID、MapPoint ID、替换/失效事件的单向值语义队列，ObjectDynamic 在自己的所有者线程消费。

## 10. 风险与控制措施

| 风险 | 后果 | 控制措施 |
|---|---|---|
| 同帧多次调用 Adapter | 动态概率、观测次数和恢复计数被重复更新 | 只在 `Track()` 单点提交；以 `mnLastObjectDynamicFrameId` 和 Adapter 自身顺序校验双重防重 |
| `Tcw`/`Twc` 混用 | 对象世界速度方向和大小错误 | 在转换函数名、文档和单元测试中固定约定；用已知位姿测试相机系到世界系转换 |
| bbox 中心深度无效或落在背景 | 3D 位置跳变，产生虚假动态证据 | 使用 bbox 内 mask/中心区域的深度中值、有效比例和离群值过滤；无可靠 3D 时不更新运动证据 |
| confidence 在当前链路丢失 | 关联权重含义不真实 | 扩展 DTO 前显式标为 unavailable；不得伪称固定值是真实检测置信度 |
| 论文1先移除动态 MapPoint | 对象关联点不足 | 在最终优化后、论文1 culling 前采集 ID；保留 shadow mode 对比 |
| 跟踪失败被当作对象消失 | 所有对象错误转 Lost | 失败帧使用独立 tracking-missed 语义；不能提交“空检测有效帧”模拟失败 |
| 初始化/重定位路径不经过推荐点 | 漏帧或状态不连续 | 为初始化和降级定位路径定义显式策略；记录 snapshot quality 和跳过原因 |
| MapPoint 被 LocalMapping 替换或删除 | Adapter 内 ID 过期 | 仅保存 ID；未来消费替换/失效事件或按关键帧周期校验，不跨线程保存指针 |
| Tracking 持有地图锁时处理开销过大 | 实时性下降并阻塞 LocalMapping | 快照采集保持 O(feature/object) 的轻量复制；必要时将纯 ObjectDynamic 计算移交单消费者队列并按帧号发布结果 |
| Adapter 状态未随 System Reset 清理 | 新序列帧号/时间戳被拒绝，旧对象污染新地图 | Reset 路径重建 Adapter 或增加明确 `Reset()` 接口；与 Map reset 同步执行 |
| StableMapView 同时被多线程读取/写入 | 数据竞争 | Tracking 作为唯一写者；向其他线程发布不可变副本并使用独立 mutex/消息队列 |

## 11. 实施顺序

1. 增加独立的快照转换单元测试，覆盖位姿约定、无效深度、bbox 边界和 MapPoint ID 去重。
2. 增加论文2编译开关，默认关闭；确认关闭时论文1轨迹与统计不变。
3. 以 shadow mode 接入 `TrackLocalMap()` 快照采集和 `Track()` 单次提交，不反馈 Tracking/LocalMapping。
4. 验证初始化、正常跟踪、纯定位、重定位、LOST 和 Reset 路径的帧序列。
5. 记录每帧调用次数、耗时、检测数、对象 ID、动态概率和 StableMapView 大小。
6. 通过 TUM/Bonn 序列验证 object ID 连续性与轨迹后，再单独评审 Active mode 的过滤/恢复反馈补丁。

结论：`ObjectDynamicAdapter::ProcessFrame()` 的主调用应位于 `Tracking::Track()` 中最终跟踪成功之后、`NeedNewKeyFrame()` 之前；`TrackLocalMap()` 只负责在最终位姿优化后、论文1动态点抑制前构造候选值语义快照。该设计可以保证单帧只更新一次对象状态，同时保留最完整的 MapPoint 关联信息，并让第一阶段接入对论文1冻结算法保持只读。
