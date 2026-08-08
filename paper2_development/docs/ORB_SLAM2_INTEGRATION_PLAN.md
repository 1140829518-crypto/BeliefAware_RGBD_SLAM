# ORB-SLAM2 Integration Plan

设计基线：`paper2_development` 分支，提交 `88d7d45`。

本文只描述 ObjectDynamic 与 ORB-SLAM2 的集成方案，不修改现有代码。论文1的 `System`、`Tracking`、`LocalMapping`、`MapPoint`、语义检测和点级 Dynamic Evidence 均视为冻结模块。未来实现必须通过论文2适配层、值语义快照和可关闭开关接入。

## System Entry

### 现有 RGB-D 数据流

```text
RGB-D images + timestamp + YOLO detection text
  → Examples/RGB-D/rgbd_tum.cc::main
  → System::TrackRGBD
  → Tracking::GrabImageRGBD
  → Frame RGB-D constructor
  → Tracking::Track
  → Tracking::CreateNewKeyFrame / LocalMapping::InsertKeyFrame
  → LocalMapping::Run
  → MapPoint creation, observation, fusion and culling
```

| 阶段 | 文件 | 类 | 关键函数 | 作用 |
|---|---|---|---|---|
| RGB-D 入口 | `Examples/RGB-D/rgbd_tum.cc` | 无 | `main()`、`MakeDetect_result()` | 读取 RGB/深度/时间戳，从 YOLO socket 获取检测结果并逐帧调用 SLAM |
| 系统构造 | `src/System.cc`、`include/System.h` | `ORB_SLAM2::System` | `System::System()` | 创建 Map、Tracking、LocalMapping、LoopClosing、Viewer，并启动 LocalMapping 等线程 |
| RGB-D 分发 | 同上 | `System` | `System::TrackRGBD()` | 处理定位模式/复位请求，将图像、深度、时间戳和检测容器传入 Tracking；保存当前跟踪状态及 MapPoint/KeyPoint 快照 |
| 当前帧构造 | `src/Tracking.cc`、`include/Tracking.h` | `ORB_SLAM2::Tracking` | `Tracking::GrabImageRGBD()` | 灰度化、深度尺度转换，构造 `mCurrentFrame` 并调用 `Track()` |
| 帧内数据 | `src/Frame.cc`、`include/Frame.h` | `ORB_SLAM2::Frame` | RGB-D 构造函数、`ExtractORB()`、`ComputeStereoFromRGBD()` | 保存检测对象，提取 ORB，计算特征深度并初始化特征–MapPoint 关联 |
| 跟踪 | `src/Tracking.cc` | `Tracking` | `Track()`、`TrackReferenceKeyFrame()`、`TrackWithMotionModel()`、`TrackLocalMap()` | 完成匹配、位姿优化、动态点过滤、状态判断和关键帧决策 |
| 关键帧提交 | `src/Tracking.cc` | `Tracking` | `CreateNewKeyFrame()` | 从当前 Frame 构造 KeyFrame，为 RGB-D 近点创建 MapPoint，并插入 LocalMapping 队列 |
| 局部建图 | `src/LocalMapping.cc`、`include/LocalMapping.h` | `ORB_SLAM2::LocalMapping` | `Run()`、`ProcessNewKeyFrame()`、`CreateNewMapPoints()` | 处理关键帧观测、创建/融合/剔除 MapPoint，运行局部 BA 和关键帧剔除 |
| 地图点状态 | `src/MapPoint.cc`、`include/MapPoint.h` | `ORB_SLAM2::MapPoint` | 构造函数、`AddObservation()`、`SetBadFlag()`、`Replace()` | 保存世界坐标、ID、关键帧观测、坏点/替换关系及论文1点级动态分数 |

### System 层未来职责

ObjectDynamic 不应直接拥有 ORB-SLAM2 指针。推荐新增论文2专用 `ObjectDynamicBridge`，由未来的论文2运行入口或可选 System 侧协调器持有：

- 接收每帧 `FrameObservationSnapshot`。
- 调用 `ObjectAssociation`、`MotionEstimator` 和 `DynamicMapManager`。
- 输出只读 `StableMapView`、对象轨迹和诊断信息。
- 在 paper2 开关关闭时完全旁路，保证论文1行为和结果可复现。

当前阶段可先在主工程外通过导出结果做离线集成，不需要改动 `System`。

## Tracking Integration

### 候选插入位置比较

| 插入位置 | 可用数据 | 优点 | 问题 | 结论 |
|---|---|---|---|---|
| Frame 创建后 | bbox、类别、深度、ORB 特征；位姿尚未估计 | 最早取得检测和深度 | 无可靠世界坐标；`mvpMapPoints` 尚未匹配 | 仅适合构造原始检测快照 |
| 特征提取后 | 关键点、描述子、bbox 区域标志 | 可做 2D bbox–feature 候选 | 特征提取发生在 Frame 构造内部；仍无当前位姿/稳定 MapPoint 关联 | 不作为主更新点 |
| 位姿估计前 | 初始位姿预测和部分匹配 | 可尝试用上一帧预测门控 | 相机位姿误差会污染对象三维运动；关联还会被优化改变 | 不推荐提交对象状态 |
| 每次 `PoseOptimization()` 后 | 优化位姿、当前 MapPoint 匹配和外点标志 | 可生成世界坐标对象观测与点关联 | 参考帧、运动模型和局部地图路径都调用，直接更新会造成同帧重复累计 | 只抓取/覆盖候选快照 |
| 最终 `TrackLocalMap()` 优化后 | 本帧最完整的局部地图匹配和最终位姿 | 适合对象三维状态与 MapPoint 关联 | 论文1紧接着调用动态点 culling，会清空部分动态点 | 推荐在 culling 前抓取快照 |
| `Tracking::Track()` 中 `bOK` 后 | 已确认最终跟踪状态、位姿和本帧结果 | 可保证每帧 ObjectDynamic 只提交一次 | 若此时才读取，动态关联点可能已被论文1清空 | 推荐消费此前抓取的快照并提交状态 |

### 推荐方案：两阶段、单次提交

#### 插入函数 A：最终姿态后的快照捕获

推荐逻辑位置：`Tracking::TrackLocalMap()` 内最终
`Optimizer::PoseOptimization(&mCurrentFrame)` 之后、
`CullSemanticDynamicMapPoints()` 之前。

输入：

- `mCurrentFrame.mnId`、`mTimeStamp`、`mTcw`。
- `objects_cur_` 的 bbox/class。
- `mvKeysUn`、`mvDepth`、`mvpMapPoints`、`mvbOutlier`。
- MapPoint 的 `mnId`、`GetWorldPos()`、`isBad()`、`GetReplaced()` 和论文1动态分数。

处理：只构造值语义 `FrameObservationSnapshot`，不更新对象状态、不保存裸指针。

输出：包含对象检测、世界坐标候选、有效 MapPoint ID 和质量标志的本帧候选快照。

原因：这是本帧局部地图位姿优化后的最完整关联，同时尚未被论文1 culling 清空动态点。

影响：只读复制会增加有限开销，但不改变位姿、外点或地图。需要保证同一 Frame ID 的后一次快照覆盖前一次，防止多个跟踪路径重复。

#### 插入函数 B：对象状态单次提交

推荐逻辑位置：`Tracking::Track()` 中 `TrackLocalMap()` 返回并确定 `bOK` 之后、`NeedNewKeyFrame()`/`CreateNewKeyFrame()` 之前。

处理：

1. 若 `bOK=true`，将最终相机位姿写入候选快照并调用一次 `ObjectDynamicBridge::ProcessFrame()`。
2. 若 `bOK=false`，不得使用不可靠世界位姿创建三维对象；只向 Manager 发送“未可靠观测/跟踪丢失”事件。
3. 保存由 DynamicMapManager 产生的对象状态和 `StableMapView`，供下一帧或未来论文2专用优化入口使用。

原因：这一位置对每个输入帧执行一次，避免 `TrackReferenceKeyFrame()`、`TrackWithMotionModel()` 和 `TrackLocalMap()` 中多次 `PoseOptimization()` 导致动态概率重复更新。

影响：Shadow 模式下只产生对象结果，不影响 Tracking。Active 模式若要让稳定点参与当前帧优化，需要更复杂的“预测视图先验”；第一版建议将本帧结果用于下一帧，避免对象状态与当前位姿形成未控制的循环依赖。

### 无 `TrackLocalMap()` 场景

纯定位、重定位或局部地图不可用时，若最终位姿仍成功，可在相应最后一次 `PoseOptimization()` 后生成降级快照，并标记 `snapshot_quality=DEGRADED`。降级快照可更新 2D 关联和 Lost 计数，但三维运动证据应降低权重。

## YOLO Interface

### 检测结果产生位置

- 文件：`yolov5_RemoveDynamic/detect_speedup_send.py`
- 关键位置：NMS 后遍历 `for *xyxy, conf, cls in reversed(det)`。
- 发送文本格式包含：`left/top/right/bottom`、类别名称和格式化 confidence，例如 `class:person 0.79`，多检测以 `*` 分隔。
- Unix socket 默认路径由 `ORB_SLAM2_SOCKET_PATH` 控制。

### 当前 C++ 传输链

```text
YOLO result string
  → rgbd_tum.cc::MakeDetect_result
  → LoadBoundingBoxFromPython
  → pair<vector<double>, int>
  → System::TrackRGBD
  → Tracking::GrabImageRGBD
  → Frame RGB-D constructor
  → shared_ptr<Object> in Frame::objects_cur_
```

当前保存内容：

- bbox：保存在 `vector<double>`，预期前四项为 left、top、right、bottom。
- class：字符串在 `LoadBoundingBoxFromPython()` 中映射到内部整数，随后保存在 `Object::ndetect_class`。
- confidence：Python 发送文本中存在，但 C++ 解析结果类型只有 `pair<bbox, class_id>`，`Object` 也没有 confidence 字段，因此 **confidence 当前被解析链丢弃**。

### 传入 ObjectAssociation 的设计

适配器将每个有效检测转换为论文2 `Detection`：

```text
Detection.class_id   ← internal class id
Detection.class_name ← parsed YOLO label or class-id mapping
Detection.bbox       ← first four validated bbox coordinates
Detection.confidence ← parsed YOLO confidence; unavailable时使用“缺失”策略
Detection.position_3d← robust bbox-depth observation transformed by Twc
```

第一阶段离线集成应直接解析原始 YOLO 文本或保存完整检测文件以保留 confidence。未来在线接口不得用固定数值冒充真实 confidence；应显式携带 `has_confidence` 或定义缺失默认值并在关联权重中禁用该项。

输入校验必须包括 bbox 长度/边界、类别合法性、confidence 范围、深度有效比例和时间戳对齐。

## ObjectDynamic Pipeline

完整目标数据流：

```text
RGB-D Frame
  ↓
Semantic Detection
  ↓
ObjectAssociation
  ↓
ObjectState Update
  ↓
MotionEstimator
  ↓
DynamicMapManager
  ↓
StableMapView / object tracks
  ↓
Tracking / LocalMapping (optional paper2 active mode)
```

| 步骤 | 输入 | 处理 | 输出 |
|---|---|---|---|
| RGB-D Frame | RGB、depth、timestamp、标定 | Frame 构造、ORB 提取、深度对齐 | 图像观测、关键点深度、Frame ID |
| Semantic Detection | RGB 图像 | YOLO 检测与 NMS | bbox、class、confidence |
| Snapshot Adapter | 检测、`Tcw/Twc`、深度、特征/MapPoint | 校验检测；稳健估计 bbox 三维中心；把 MapPoint/KeyFrame 转为 ID 快照 | `FrameObservationSnapshot`、论文2 `Detection` 集合 |
| ObjectAssociation | 历史 ObjectState、当前 Detection | 语义、IoU、2D 中心和 3D 距离加权一对一匹配 | matches、未匹配轨迹、未匹配检测；匹配对象保持 ID |
| ObjectState Update | 匹配及观测 | 更新 bbox、类别、置信度、世界位置、时间和观测数 | 当前对象状态候选 |
| MotionEstimator | 同 ID 的前后 ObjectState | 计算速度、方向、速度/方向/历史一致性分数；平滑动态概率 | `MotionEstimate` 和更新对象状态 |
| MapPoint Association | bbox/mask 区域、有效 feature–MapPoint 快照 | 写入独立 `Object ID → MapPoint ID` 索引，去重并处理 replaced/bad ID | 对象关联点集合 |
| DynamicMapManager | 当前对象、匹配状态、动态概率、点关联 | 生命周期转换、多帧恢复、active/lost/recovered 分类 | 对象地图、Stable/Quarantined/RecoveryCandidate 视图 |
| Tracking/Mapping | StableMapView | Shadow 模式仅记录；Active 模式用稳定点约束下一帧/论文2优化 | 更稳定定位与地图；必须可回退论文1路径 |

建议处理顺序中，MotionEstimator 应使用 `ObjectAssociation` 保持的同一 object ID；DynamicMapManager 是对象状态与点关联的唯一所有者，其他线程只获取副本。

## MapPoint Association

### 数据模型

不修改 `MapPoint`。使用 DynamicMapManager 已实现的独立索引：

```text
ObjectState::ObjectId
  → set<ObjectState::MapPointId>
```

关联事实保存在 Manager；ObjectState 的 `associated_map_points` 是同步缓存。不得把 `MapPoint*` 跨线程保存在 ObjectDynamic 中。

### Tracking 侧关联流程

在推荐的“最终位姿后、论文1 culling 前”快照点：

1. 对每个已匹配 object ID 取得当前 bbox。
2. 遍历与 `mvKeysUn` 索引对齐的 `mvpMapPoints`。
3. 仅接受非空、非 `mvbOutlier`、非 bad 的 MapPoint。
4. 检查关键点是否位于对象 bbox（未来可替换为 mask），并结合深度一致性降低框内背景点误关联。
5. 读取 `pMP->mnId`，调用快照适配器记录 `(object_id, map_point_id, frame_id, confidence)`。
6. 单线程提交阶段再调用 `DynamicMapManager::AssociateMapPoint()`；不要在遍历 SLAM 指针时修改 Manager。

若 `GetReplaced()` 非空，Association Manager 将旧 ID 迁移为替代点 ID；若 `isBad()`，移除对象关联但保留历史记录。论文1已经在 Frame 构造期预过滤动态框特征，因此动态对象的有效关联点可能偏少，必须同时使用 bbox 深度三维中心，不能假设每个对象都有足量 MapPoint。

### LocalMapping 侧关联流程

第一阶段不建议 LocalMapping 直接调用 ObjectDynamic：LocalMapping 与 Tracking 并发，直接共享 Manager 会增加锁竞争和裸指针生命周期风险。

未来需要同步建图变化时，使用单向事件/快照队列：

- `ProcessNewKeyFrame()` 完成后：发布 KeyFrame ID、时间戳和有效 MapPoint ID/feature index 快照。
- `CreateNewMapPoints()`/`SearchInNeighbors()` 后：发布新点和 replaced 点 ID 事件。
- `MapPointCulling()` 或 `MapPoint::SetBadFlag()` 结果：通过周期性 Map 快照或统一 lifecycle event 发布 bad ID。
- Local BA 后：必要时发布更新后的 MapPoint 世界坐标快照；ObjectDynamic 不持有优化中的地址。

ObjectDynamic 消费队列并调用 `AssociateMapPoint()`/`RemoveMapPoint()`，LocalMapping 不等待对象模块返回。若不增加事件桥，离线阶段可按 KeyFrame 周期扫描只读 Map 快照并比较 ID 差异。

## Paper1 Compatibility

### 模型比较

| 项目 | 论文1 | 论文2 |
|---|---|---|
| 动态单位 | MapPoint | 跨帧 ObjectState |
| 核心状态 | `mfSemanticDynamicScore`、最后更新帧 | object ID、3D 状态、速度、motion score、动态概率、生命周期 |
| 证据来源 | 动态 bbox 内的点级命中 | 对象关联、世界坐标运动、方向/历史一致性、语义和点集合 |
| 地图操作 | 当前 Frame 中抑制超过阈值的 MapPoint | 独立 ID 关联、对象生命周期、逻辑隔离与多帧恢复 |
| 代码所有权 | ORB-SLAM2/论文1类 | `paper2_development/modules/ObjectDynamic/` |

### 可复用模块

- RGB-D 读取、时间戳与相机标定。
- YOLO 检测进程、bbox 和 class（confidence 需补全接口）。
- Tracking 优化后的相机位姿。
- Frame 的特征、深度和临时 MapPoint 匹配。
- MapPoint ID、世界坐标、观测、bad/replaced 状态。
- 论文1点级动态分数可作为可选辅助证据和对比基线。

### 必须独立的模块

- ObjectAssociation 的跨帧 object ID 管理。
- ObjectState 的对象级位置、速度和动态概率。
- MotionEstimator 的运动一致性估计。
- DynamicMapManager 的生命周期、独立点关联与恢复。
- StableMapView 及对象级实验输出。

### 共存模式

1. **Paper1 Baseline**：ObjectDynamic 完全关闭，结果必须与冻结版本一致。
2. **Paper2 Shadow**：论文1照常跟踪/建图，ObjectDynamic 只读快照并输出对象结果，不反馈 SLAM。用于验证 ID、速度、概率和性能开销。
3. **Paper2 Active**：ObjectDynamic 输出 StableMapView，论文2专用入口将其用于下一帧匹配/优化；必须可运行时关闭并回退 Baseline。
4. **Ablation**：分别关闭点级辅助证据、对象运动证据、恢复机制，避免把论文1贡献重复计入论文2。

不建议同时让论文1点级 culling 和论文2对象级隔离对同一观测重复累计或重复删除。Shadow 阶段保持论文1行为；Active 阶段需明确策略优先级，推荐底层 MapPoint 不永久删除、论文2只产生过滤视图。

## Implementation Steps

以下为后续实施顺序，本次不执行：

1. **离线适配验证**：从现有输出构造 `Detection`、位姿和 MapPoint ID 快照，验证 ObjectDynamic 四个模块和数据格式。
2. **定义桥接 DTO**：在论文2模块中定义 `FrameObservationSnapshot`、`MapPointSnapshot`、`KeyFrameSnapshot` 和 lifecycle event；所有类型使用值语义。
3. **补全检测契约**：为论文2入口保留 YOLO class name、confidence 和 bbox 校验结果；不覆盖论文1旧接口。
4. **Tracking Shadow Hook**：实现两阶段快照/单次提交，默认关闭；确认同一 Frame ID 只更新一次。
5. **LocalMapping Observer**：使用非阻塞事件队列同步 MapPoint new/bad/replaced 和 KeyFrame 观测，不让 LocalMapping 等待对象模块。
6. **对象结果导出**：输出 object ID、状态、速度、概率、关联点和恢复计数，先验证轨迹与状态机。
7. **StableMapView Shadow Evaluation**：生成但不应用稳定视图，与论文1有效点集合做差异统计。
8. **Active Integration**：仅在论文2专用构建/运行开关下，把上一帧稳定视图用于下一帧匹配或新关键帧点选择；逐项评估 ATE/RPE、IDF1、动态识别和运行时间。
9. **回退与回归**：开关关闭时运行论文1复现实验，确认轨迹、统计与冻结版本一致。

## Risk Analysis

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| YOLO confidence 在 C++ 链路丢失 | 关联与状态置信度缺少真实输入 | 论文2 DTO 显式保留 confidence；缺失时禁用对应权重，不伪造观测 |
| 同帧多次 `PoseOptimization()` | 动态概率和 observation_count 重复更新 | 快照可覆盖，按 Frame ID 只提交一次 |
| 位姿和对象运动循环依赖 | 错误位姿造成错误对象运动，反向过滤又恶化位姿 | 先 Shadow；Active 使用上一帧稳定视图并保留最小几何内点回退 |
| 论文1在 Frame 构造时预过滤动态特征 | 动态对象 MapPoint 数量不足 | 对象三维位置使用稳健 bbox 深度；点关联作为辅助而非唯一观测 |
| culling 后 MapPoint 关联被清空 | 无法建立动态对象点集合 | 在最终优化后、culling 前捕获 ID 快照 |
| Tracking/LocalMapping 并发 | 数据竞争、锁等待、悬空指针 | 值语义快照、单向非阻塞队列；ObjectDynamic 不持有裸指针 |
| MapPoint bad/replaced | Object ID→point ID 索引过期 | 处理 lifecycle event 或周期快照；迁移 replaced ID、清除 bad ID |
| Tracking 丢失或重定位 | 世界坐标对象速度突变 | 标记降级快照，暂停高权重运动更新，重定位后重新确认轨迹 |
| bbox 包含背景 | 背景 MapPoint 被关联动态对象 | 加深度一致性、关联置信度、多帧确认；不整框永久删除 |
| Lost 单帧误恢复 | object ID switch 或错误地图恢复 | 使用 DynamicMapManager 多帧恢复计数和三维/语义门控 |
| 额外 YOLO/对象处理延迟 | 破坏 Tracking 实时性 | 异步检测时间戳对齐、预算队列、性能统计和超时降级 |

## Acceptance Criteria for Future Integration

- Paper1 Baseline 开关关闭时，冻结代码路径与结果不变。
- 每个 RGB-D Frame 至多提交一次对象状态更新。
- ObjectDynamic 不保存 MapPoint/KeyFrame 裸指针，不拥有或删除 ORB-SLAM2 对象。
- Tracking 丢失、检测缺失和深度无效都有显式降级策略。
- LocalMapping 不阻塞等待 ObjectDynamic。
- confidence、坐标系、时间戳和 ID 生命周期均可追踪。
- 所有 Active 模式改动具备 Shadow 对照、消融实验和运行时回退。
