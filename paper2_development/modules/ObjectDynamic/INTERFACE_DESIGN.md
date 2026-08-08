# ObjectDynamic Interface Design

设计基线：`paper2_development` 分支，提交 `92b5f2b`。本文只定义论文2模块与论文1冻结代码之间的数据边界，不要求修改 `src/`、`include/` 或论文1模块，也不包含算法实现。

## Existing ORB-SLAM2 Data Structures

### MapPoint

文件路径：

- `include/MapPoint.h`
- `src/MapPoint.cc`

类：`ORB_SLAM2::MapPoint`

关键成员：

| 成员/接口 | 数据形式 | 作用 |
|---|---|---|
| `mnId` | `long unsigned int` | 全局地图点 ID |
| `mWorldPos` | `cv::Mat`，3×1、`CV_32F` | 世界坐标系中的三维坐标；通过 `GetWorldPos()` 克隆读取，通过 `SetWorldPos()` 加锁写入 |
| `mObservations` | `std::map<KeyFrame*, size_t>` | 观测关键帧到该点在关键帧中特征索引的映射 |
| `mpRefKF` | `KeyFrame*` | 参考关键帧 |
| `nObs` | `int` | 观测计数；单目观测加 1，双目/RGB-D 观测可加 2 |
| `mnFirstKFid` / `mnFirstFrame` | ID | 地图点创建时的关键帧/普通帧来源 |
| `mnVisible` / `mnFound` | 计数 | 可见次数和成功匹配次数 |
| `mbBad` | `bool` | 地图点生命周期坏点标志 |
| `mpReplaced` | `MapPoint*` | 融合时替代当前点的地图点 |
| `mfSemanticDynamicScore` | `float` | 论文1已有动态证据分数 |
| `mnSemanticDynamicLastFrame` | Frame ID | 动态证据最近更新时间 |

坐标保存方式：`mWorldPos` 始终表示世界坐标系坐标。`GetWorldPos()` 在 `mMutexPos` 下返回克隆，适合作为 ObjectDynamic 的只读位置快照。

观测关键帧管理：`AddObservation()` 和 `EraseObservation()` 双向维护 MapPoint–KeyFrame 关系；`GetObservations()` 在锁内复制并返回 `KeyFrame* → feature index` 映射。删除关键帧观测可能使 `nObs <= 2`，继而触发 `SetBadFlag()`。

生命周期：地图点由 Tracking 或 LocalMapping 创建；加入 `Map` 后经历跟踪统计、LocalMapping 质量剔除和邻域融合。`SetBadFlag()` 清空观测、通知所有 KeyFrame 清除匹配并从 `Map` 容器移除；`Replace()` 将观测和统计迁移到替代点，并设置 `mpReplaced`。原对象内存不保证随容器移除立即释放，但论文2不得据此长期持有裸指针。

已有动态状态：`UpdateSemanticDynamicScore()`、`GetSemanticDynamicScore()` 和 `ShouldSuppressSemanticDynamic()` 已提供点级动态证据接口。它们属于论文1冻结逻辑；ObjectDynamic 只把分数作为可选输入证据，不写入或重定义该状态。

可扩展接口：不扩展 `MapPoint` 本体。由论文2适配器调用 `mnId`、`GetWorldPos()`、`GetObservations()`、`GetReferenceKeyFrame()`、`isBad()`、`GetReplaced()` 和 `GetSemanticDynamicScore()`，生成不含所有权的 `MapPointSnapshot`。快照至少包含 point ID、世界坐标、观测关键帧 ID、动态分数、坏点状态和替代点 ID。

### KeyFrame

文件：

- `include/KeyFrame.h`
- `src/KeyFrame.cc`

类：`ORB_SLAM2::KeyFrame`

关键成员：

| 成员/接口 | 作用 |
|---|---|
| `mnId`、`mnFrameId`、`mTimeStamp` | 关键帧 ID、来源 Frame ID 和时间戳 |
| `mvKeys`、`mvKeysUn` | 原始/去畸变关键点；索引与描述子、深度和地图点关联一致 |
| `mvuRight`、`mvDepth` | RGB-D/双目右目坐标与关键点深度 |
| `mDescriptors` | 每个关键点对应一行 ORB 描述子 |
| `mBowVec`、`mFeatVec` | 词袋和特征节点表示 |
| `Tcw`、`Twc`、`Ow` | 世界到相机位姿、逆位姿和世界坐标系相机中心；通过加锁 getter 读取 |
| `mvpMapPoints` | 与关键点索引对齐的 `MapPoint*` 数组 |
| `mConnectedKeyFrameWeights` | 共视关键帧及共享地图点权重 |
| `mbBad` | 关键帧坏帧状态 |

关键帧图像信息：KeyFrame 从 Frame 构造，冻结保存关键点、描述子、深度、标定参数、时间戳和 BoW 信息。当前类没有保存原始 RGB 图像或 YOLO 检测对象；对象检测必须由 Frame 侧适配器在当帧形成快照。

位姿保存：`SetPose(Tcw)` 同步计算 `Twc` 和相机中心；外部只读接口包括 `GetPose()`、`GetPoseInverse()`、`GetCameraCenter()`、`GetRotation()` 和 `GetTranslation()`。

地图点关联：`mvpMapPoints[index]` 与 `mvKeysUn[index]`、`mvDepth[index]` 对齐。通过 `GetMapPointMatches()`、`GetMapPoints()` 和 `GetMapPoint(index)` 获取，使用 `AddMapPoint()`、`EraseMapPointMatch()` 和 `ReplaceMapPointMatch()` 维护。

与 ObjectDynamic 关联方式：使用 `KeyFrameObservationSnapshot`，保存 keyframe ID、frame ID、时间戳、`Twc`/`Tcw` 快照，以及“object ID → MapPoint ID 列表/特征索引列表”的外部关联。ObjectDynamic 不向 KeyFrame 增加成员，不持有 KeyFrame 所有权，并在读取后检查 `isBad()`。

### Tracking and Frame Data Flow

当前帧数据流：

```text
RGB image + depth image + timestamp
  → Examples/RGB-D/rgbd_tum.cc
YOLO result text
  → MakeDetect_result / LoadBoundingBoxFromPython
  → vector<(bbox, class_id)>
  → System::TrackRGBD
  → Tracking::GrabImageRGBD
  → Frame(imGray, imDepth, timestamp, detect_result)
  → Frame::objects_cur_ + ORB features + per-keypoint depth
  → Tracking matching / pose optimization
  → Frame::mvpMapPoints
  → bbox membership and point-level dynamic evidence
  → ObjectDynamic observation adapter
```

Frame 关键输入/状态：

- `mTimeStamp`、`mnId`：时间与帧身份。
- `imDepth`、`mvDepth`：RGB-D 深度图和关键点深度。
- `mTcw`：Tracking 优化后的当前相机位姿。
- `mvKeys`、`mvKeysUn`、`mDescriptors`：ORB 观测。
- `mvpMapPoints`、`mvbOutlier`：当前特征到地图点的关联及几何外点标记。
- `objects_cur_`：由检测结果构造的 `Object` 列表；每项保存 bbox `vdetect_parameter` 和类别 `ndetect_class`。
- `vbInDynamic_mvKeys`：特征点是否位于动态检测区域。

动态点判断：Frame 构造时先提取 ORB，然后使用 `IsInDynamic()`/`IsInStatic()` 进行 bbox 区域判断；动态框内且非静态框内的关键点被置到无效坐标。Tracking 完成匹配与 `PoseOptimization()` 后调用 `CullSemanticDynamicMapPoints()`，对动态框内的已关联 MapPoint 更新论文1动态分数，超过阈值则从当前帧关联中清除。

ObjectDynamic 的数据入口应是只读的 `FrameObservationSnapshot`，在 Tracking 已获得有效位姿和地图点关联后构造。由于当前禁止修改 Tracking，第一阶段建议通过现有导出数据进行离线适配；未来在线接入需单独评审一个不改变论文1行为的桥接层。

## 1. ObjectState

ObjectState 表示跨帧对象轨迹的当前状态。它与 YOLO 检测、三维位置、地图点和关键帧的关系全部由论文2模块维护。

成员变量建议（概念设计，不在本任务中实现）：

```cpp
using ObjectId = std::uint64_t;
using MapPointId = std::uint64_t;
using KeyFrameId = std::uint64_t;

struct ObjectState {
    ObjectId object_id;
    int class_id;
    double timestamp;
    BoundingBox2D bounding_box;
    Pose3D object_pose;
    Vector3D velocity;
    double dynamic_probability;
    std::vector<MapPointId> associated_map_points;
    std::vector<KeyFrameId> observing_keyframes;
    TrackStatus status;
    std::uint64_t first_frame_id;
    std::uint64_t last_frame_id;
};
```

关联规则：

- YOLO 类别：保存内部 `class_id`，同时保留检测器原始类别/置信度作为 Observation 元数据，避免类别枚举耦合。
- Bounding Box：保存最近观测 bbox；历史 bbox 属于轨迹历史，不无限堆积在当前状态。
- 3D 位置：利用 bbox/mask 内有效深度、相机内参和 `Twc` 生成世界坐标观测；`object_pose` 及协方差由对象层维护。
- MapPoint 集合：保存稳定 `MapPointId`，可选维护一次性只读快照；不取得 `MapPoint*` 所有权。
- KeyFrame 观测：保存 keyframe ID、时间戳和观测摘要，用于运动估计与恢复；不修改 KeyFrame 的共视图。

## 2. MapPoint Association

### 方案 A：MapPoint 保存 object_id

做法：在 `MapPoint` 中增加对象 ID 或对象指针。

优点：点到对象查询直接；LocalMapping/Tracking 可快速访问所属对象。

缺点：必须修改论文1冻结类；对象重关联时要跨线程改写大量 MapPoint；点融合、替换和坏点流程均需同步迁移 object ID；单点可能存在多对象候选时表达能力弱；耦合 SLAM 核心和论文2生命周期。

结论：当前约束下不可采用。

### 方案 B：ObjectState 管理 MapPoint 列表

做法：每个 ObjectState 保存关联 MapPoint ID 或只读引用集合。

优点：不修改 MapPoint；对象状态聚合直观；按对象执行运动估计方便；实现规模较小。

缺点：反向查询成本高；对象竞争同一地图点时需额外冲突处理；MapPoint 被替换或置坏时列表可能过期；关联置信度和历史不易表达。

适用：早期原型和单一归属、低冲突场景。

### 方案 C：独立 Association Manager

做法：DynamicMapManager 内部维护独立关联表，以稳定 ID 连接 ObjectState、MapPointSnapshot 和 KeyFrameObservationSnapshot。

建议关系记录：

```text
AssociationRecord
  object_id
  map_point_id
  keyframe_id / frame_id
  confidence
  first_seen / last_seen
  association_state
  optional replacement_map_point_id
```

优点：完全隔离论文1代码；支持双向查询、多候选、置信度、历史、冲突解析和点替换迁移；可独立加锁、序列化和测试。

缺点：需要额外索引和一致性维护；必须处理 MapPoint/KeyFrame 生命周期事件或周期性快照清理；内存和实现复杂度较高。

推荐：**方案 C 为主，方案 B 作为 ObjectState 的缓存视图。** Association Manager 是关联事实的唯一来源；ObjectState 中的 `associated_map_points` 仅保存由 Manager 刷新的 ID 快照。这样不修改冻结类，同时为论文2的时空关联、恢复和实验审计保留完整信息。

生命周期约束：每次消费前检查 MapPoint/KeyFrame 是否 bad；若 `GetReplaced()` 非空，把关联迁移到替代点 ID 并保留迁移记录；禁止在异步模块中长期解引用裸指针。

## 3. MotionEstimator Interface Design

仅设计接口，不指定滤波或优化算法。

建议输入：

- `ObjectStateHistory`：按时间排序的对象状态快照。
- `ObjectObservation`：可选的新观测，包含时间戳、世界坐标位置、bbox、类别置信度及协方差。
- `MotionContext`：时间间隔、相机位姿质量和有效 MapPoint 统计。

建议输出：

- 下一时刻预测位置/姿态及预测时间戳。
- 估计速度及不确定性。
- 动态概率及其证据摘要。
- 预测是否有效、失败原因和建议搜索门限。

概念接口：

| 函数 | 参数 | 返回值 | 说明 |
|---|---|---|---|
| `Initialize` | `const ObjectState& initial_state` | `Status` | 初始化指定对象的运动状态 |
| `Predict` | `const ObjectStateHistory& history, double target_timestamp` | `MotionPrediction` | 预测目标时刻的位置、速度和协方差 |
| `Estimate` | `const ObjectStateHistory& history, const ObjectObservation& observation` | `MotionEstimate` | 基于历史和当前观测估计运动 |
| `EstimateDynamicProbability` | `const MotionEstimate&, const EvidenceSummary&` | `ProbabilityEstimate` | 融合运动与其他证据得到动态概率 |
| `Reset` | `ObjectId object_id` | `Status` | 清除指定对象的估计器内部状态 |

MotionEstimator 不修改 ObjectState；由 DynamicMapManager 验证返回值后提交状态更新。

## 4. DynamicMapManager Interface Design

职责：对象创建、更新、退休/删除、MapPoint 关联、对象级动态地图维护和恢复。这里“删除”默认是从活跃集合退休并保留轨迹摘要，不意味着删除 ORB-SLAM2 MapPoint。

概念类接口：

| 函数名称 | 参数 | 返回值 | 作用 |
|---|---|---|---|
| `ProcessFrame` | `const FrameObservationSnapshot& frame` | `FrameUpdateResult` | 单帧入口；组织预测、数据关联和状态提交 |
| `CreateObject` | `const ObjectObservation& observation` | `Result<ObjectId>` | 创建候选 ObjectState 并分配稳定 ID |
| `UpdateObject` | `ObjectId id, const ObjectObservation&, const MotionEstimate&` | `Status` | 更新 bbox、位置、速度、概率和观测时间 |
| `RetireObject` | `ObjectId id, RetirementReason reason` | `Status` | 将对象移出活跃集合并保存可恢复记录 |
| `AssociateObservations` | `const std::vector<ObjectObservation>&, const std::vector<MotionPrediction>&` | `AssociationResult` | 生成检测到对象的匹配、未匹配和冲突集合 |
| `AssociateMapPoints` | `ObjectId id, const std::vector<MapPointSnapshot>& candidates, const KeyFrameObservationSnapshot&` | `MapPointAssociationResult` | 更新对象–地图点关联记录及置信度 |
| `HandleMapPointLifecycle` | `const MapPointLifecycleSnapshot& event` | `Status` | 清理 bad 点或迁移 replaced 点关联 |
| `UpdateDynamicMap` | `const std::vector<ObjectState>& active_states` | `DynamicMapUpdate` | 生成当前动态对象集合和静态可用地图视图 |
| `RecoverObject` | `const ObjectObservation&, const std::vector<RetiredTrackSummary>&` | `Result<ObjectId>` | 在门控通过时恢复暂时丢失对象 |
| `GetObjectState` | `ObjectId id` | `Optional<ObjectStateSnapshot>` | 返回线程安全的对象状态快照 |
| `GetActiveObjects` | 无 | `std::vector<ObjectStateSnapshot>` | 返回活跃对象快照集合 |
| `GetStableMapView` | `double dynamic_threshold` | `StableMapView` | 返回排除高动态对象关联点后的只读地图视图 |

建议内部所有权：DynamicMapManager 拥有 ObjectState、MotionEstimator 实例和 Association Manager；ORB-SLAM2 的 Frame、MapPoint 与 KeyFrame 数据全部转换成值语义快照后再进入模块。模块不拥有也不删除任何论文1对象。

线程边界：`ProcessFrame()` 以单调时间戳串行提交对象状态；SLAM 线程提供快照后立即释放其锁。对外 getter 返回不可变快照，避免对象线程和 LocalMapping/LoopClosing 共享裸指针。
