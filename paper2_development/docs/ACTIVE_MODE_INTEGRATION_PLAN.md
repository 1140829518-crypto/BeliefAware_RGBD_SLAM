# Active Mode Integration Plan

本文基于 `paper2_development` 分支的 ObjectDynamic、DynamicMapFilter 和 Tracking Shadow Mode，设计 Active Mode 的最小接入方案。本次只进行代码分析和补丁规划，不修改 `src/`、`include/` 或现有算法。

Active Mode 的边界是：根据对象级状态生成当前帧可用的 MapPoint 过滤视图，但不修改 MapPoint 本体、不从全局 Map 删除点、不改变 LocalMapping 数据结构。首版采用上一接受帧的对象状态作为当前帧先验，避免当前位姿估计和当前对象三维运动估计形成循环依赖。

## Current MapPoint Flow

### 1. Tracking 主数据流

```text
initial tracking
  → mCurrentFrame.mvpMapPoints 获得初始关联
  → TrackLocalMap()
      → UpdateLocalMap()
          → UpdateLocalKeyFrames()
          → UpdateLocalPoints()
      → SearchLocalPoints()
          → isInFrustum()
          → ORBmatcher::SearchByProjection()
          → 新匹配写入 mCurrentFrame.mvpMapPoints
      → Optimizer::PoseOptimization(&mCurrentFrame)
      → paper1 CullSemanticDynamicMapPoints()
      → 更新 IncreaseFound() 和 mnMatchesInliers
  → NeedNewKeyFrame()
  → CreateNewKeyFrame()
  → LocalMapping::InsertKeyFrame()
```

### 2. 关键函数和遍历位置

| 文件 | 函数 | MapPoint 遍历及作用 |
|---|---|---|
| `src/Tracking.cc` | `Tracking::TrackReferenceKeyFrame()` | 将参考关键帧 BoW 匹配结果写入 `mCurrentFrame.mvpMapPoints`，调用 `PoseOptimization()`，之后遍历关联点剔除外点并统计有效地图匹配 |
| `src/Tracking.cc` | `Tracking::TrackWithMotionModel()` | 清空当前关联，通过上一帧投影匹配写入 `mvpMapPoints`，执行初始位姿优化，再遍历外点和有效观测 |
| `src/Tracking.cc` | `Tracking::TrackLocalMap()` | 串联局部地图更新、投影匹配和最终位姿优化；优化后遍历当前 Frame 全部关联点，更新 found 统计、内点数和跟踪成功判定 |
| `src/Tracking.cc` | `Tracking::UpdateLocalKeyFrames()` | 遍历 `mCurrentFrame.mvpMapPoints`，用每个点的 KeyFrame 观测为局部关键帧投票；坏点从当前 Frame 清空 |
| `src/Tracking.cc` | `Tracking::UpdateLocalPoints()` | 遍历局部关键帧的 MapPoint 匹配，去重并将有效点加入 `mvpLocalMapPoints` |
| `src/Tracking.cc` | `Tracking::SearchLocalPoints()` | 第一遍处理当前 Frame 已有关联，设置 visible/last-seen；第二遍遍历 `mvpLocalMapPoints`，做坏点检查和视锥判断；最后调用投影匹配 |
| `src/ORBmatcher.cc` | `ORBmatcher::SearchByProjection(Frame&, const vector<MapPoint*>&, float)` | 遍历视锥内局部 MapPoint，执行论文1点级动态证据更新、投影窗口搜索和描述子选择，将匹配写入 `F.mvpMapPoints[bestIdx]` |
| `src/Tracking.cc` | `Tracking::CullSemanticDynamicMapPoints()` | 位姿优化后遍历当前 Frame MapPoint，更新论文1动态框证据；达到阈值时仅从当前 Frame 清空关联并标记 outlier |
| `src/Tracking.cc` | `Tracking::NeedNewKeyFrame()` | 遍历当前 Frame 深度点，统计已跟踪/未跟踪近点，参与关键帧决策 |
| `src/Tracking.cc` | `Tracking::CreateNewKeyFrame()` | 从当前 Frame 构造 KeyFrame；遍历 RGB-D 深度点，保留已有有效 MapPoint或创建新点并写入当前 Frame/KeyFrame/Map |
| `src/LocalMapping.cc` | `LocalMapping::ProcessNewKeyFrame()` | 遍历新关键帧 MapPoint，补充观测、法向和描述子，更新共视连接并加入 Map |
| `src/MapPoint.cc` | `MapPoint::SetBadFlag()`、`Replace()` | 永久修改观测关系、KeyFrame 关联和全局 Map；Active Mode 首版不得调用 |

`Optimizer::PoseOptimization()` 读取 `Frame::mvpMapPoints` 并为非空关联建立重投影边。因本任务要求尽量只改 Tracking，首版不修改 Optimizer：进入该函数前从当前 Frame 视图中清空动态对象关联点，即可保证它们不进入位姿优化。

### 3. MapPoint 投影匹配细节

`SearchLocalPoints()` 的局部地图点来源是 `UpdateLocalPoints()` 生成的 `mvpLocalMapPoints`。每个候选点先经过：

1. `mnLastFrameSeen` 去重；
2. `isBad()` 检查；
3. `mCurrentFrame.isInFrustum()` 视锥、尺度和观测方向检查；
4. `ORBmatcher::SearchByProjection()` 的投影窗口、描述子距离、尺度和左右目误差检查；
5. 论文1 `UpdateSemanticDynamicScore()` 与阈值抑制。

成功候选写入与特征索引对齐的 `mCurrentFrame.mvpMapPoints`。最终 `PoseOptimization()` 直接使用这些非空关联。因此 Active Mode 最有效且修改最小的控制点，是在投影匹配前过滤候选，并在优化前进行一次防御性清理。

## Candidate Integration Points

### 方案 A：匹配阶段过滤

做法：在局部点进入 `ORBmatcher::SearchByProjection()` 前，以 `pMP->mnId` 调用 `DynamicMapFilter::IsDynamicMapPoint()`；动态点不参与本帧投影匹配。对初始跟踪已经写入 `mCurrentFrame.mvpMapPoints` 的点，在最终优化前同样按 ID 清空。

优点：

- 动态对象点不会形成新的特征匹配和重投影约束。
- 不需要修改 `MapPoint`，也不永久删除地图内容，Recovered 后可重新使用。
- 直接作用于位姿估计输入，论文2对象级过滤贡献清晰。

缺点：

- 依赖上一帧 StableMapView，存在一帧时延。
- object–point 关联漏检时无法过滤；误关联会降低静态约束数。
- 若直接修改 ORBmatcher，会扩大代码范围并与论文1逻辑耦合。

论文2贡献：对象级时空状态转化为几何前端的可逆约束选择，而不是永久删点。

结论：推荐，但通过 Tracking 侧候选向量和当前 Frame 关联过滤实现，不修改 ORBmatcher。

### 方案 B：优化阶段降低权重

做法：保留动态对象 MapPoint 的重投影边，但在 `Optimizer::PoseOptimization()` 中按状态降低信息矩阵权重或使用额外鲁棒核。

优点：

- 不是硬过滤，误判时仍保留少量几何信息。
- 可以研究对象动态概率到连续权重的映射。

缺点：

- 必须修改 Optimizer 接口和实现，超出最小修改范围。
- 需要把对象状态传入 g2o 边，增加数据耦合和参数敏感性。
- 与现有 Huber/outlier 机制及论文1抑制叠加后难以归因。

论文2贡献：可形成概率加权优化扩展，但应作为后续独立消融，不适合作为首个 Active Mode。

结论：首版不采用。

### 方案 C：局部地图选择阶段过滤

做法：`UpdateLocalPoints()` 生成 `mvpLocalMapPoints` 后，在 Tracking 内创建本帧候选视图，排除 Dynamic MapPoint ID，再交给 `SearchLocalPoints()`。

优点：

- 过滤发生在视锥计算和描述子搜索前，可减少计算量。
- 不修改 ORBmatcher、MapPoint 或 LocalMapping。
- 只改变当前 Tracking 候选视图，全局 Map 保持完整。

缺点：

- 只过滤局部候选不足以处理初始跟踪阶段已存在于 `mCurrentFrame.mvpMapPoints` 的动态点。
- 不应直接从持久的 `mvpLocalMapPoints` 删除后影响可视化或后续诊断；建议使用临时 filtered vector。

论文2贡献：构建对象状态驱动的稳定局部地图视图。

结论：推荐与方案 A 组合。

### 方案 D：关键帧插入阶段处理

做法：在 `NeedNewKeyFrame()` 或 `CreateNewKeyFrame()` 前清理动态对象关联点，避免写入新 KeyFrame。

优点：

- 可减少动态关联进入后续 LocalMapping 和局部 BA。
- 修改可以限制在 Tracking。

缺点：

- 位姿优化已经使用了动态点，无法改善当前帧位姿。
- 若直接从 KeyFrame/Map 删除，会破坏恢复机制并触及论文1/LocalMapping。
- 清空点会改变近点统计和关键帧创建时机，影响范围较大。

论文2贡献：适合作为稳定关键帧输出策略，但不是前端动态鲁棒性的首要实现。

结论：首版只保证过滤后的当前 Frame 自然传入关键帧，不增加额外永久处理。

### 推荐方案

采用 **A + C 的 Tracking 侧可逆过滤**：

1. 在 `TrackLocalMap()` 开始、`UpdateLocalMap()` 前，过滤初始跟踪已写入 `mCurrentFrame.mvpMapPoints` 的动态 ID，避免其参与局部关键帧投票。
2. `UpdateLocalMap()` 完成后，对 `mvpLocalMapPoints` 生成非动态候选副本，再执行 `SearchLocalPoints()`；或者在 `SearchLocalPoints()` 的两个 Tracking 侧循环中跳过动态 ID。
3. `PoseOptimization()` 前再次检查 `mCurrentFrame.mvpMapPoints`，作为防御性屏障。
4. 不调用 `SetBadFlag()`，不从 Map/KeyFrame 删除点，不修改 MapPoint 动态成员。
5. Recovered 或不在过滤索引中的 ID 正常进入匹配和优化。

## Dynamic Filtering Strategy

### 1. Active Mode 数据流

```text
previous accepted StableMapView
  ↓
DynamicMapFilter::UpdateMapView()
  ↓
Object ID → MapPoint ID → Static/Dynamic/Recovered
  ↓
Tracking current-frame and local-map candidate decision
  ↓
only non-Dynamic MapPoints remain in mCurrentFrame.mvpMapPoints
  ↓
Optimizer::PoseOptimization()
  ↓
paper1 evidence/culling for remaining and unassociated points
  ↓
successful current-frame ObjectDynamicAdapter::ProcessFrame()
  ↓
new StableMapView updates filter for the next frame
```

### 2. 输入、处理、输出

| 项目 | 内容 |
|---|---|
| 输入 | 上一成功帧的 `StableMapView`、当前 Frame 初始 MapPoint 关联、局部 MapPoint 候选及 `MapPoint::mnId` |
| 判断 | `mDynamicMapFilter.IsDynamicMapPoint(static_cast<MapPointId>(pMP->mnId))` |
| 输出 | 当前帧可用的稳定 MapPoint 关联和过滤后的局部投影候选；可选过滤计数日志 |
| 不变内容 | MapPoint 世界坐标、观测、bad/replaced 状态、全局 Map、KeyFrame 和论文1动态分数 |
| 恢复 | `Recovered` 返回 false，不再过滤；地图点因从未永久删除而可重新匹配 |

### 3. 时序原则

当前 Shadow Mode 的 `ProcessFrame()` 在 `TrackLocalMap()` 成功之后、`NeedNewKeyFrame()` 之前运行。因此刚生成的 StableMapView 不可能影响同一次已经完成的 PoseOptimization。首版 Active Mode 应明确使用 `t-1` 的对象地图先验处理帧 `t`。

若未来希望使用当前帧检测，需要把 2D ObjectAssociation/预测阶段与依赖当前最终位姿的 3D 状态更新拆开，而不是简单把完整 `ProcessFrame()` 移到优化前。否则会出现：当前位姿决定对象世界运动，对象动态状态又决定当前位姿输入的循环依赖。

### 4. 状态规则

- `Dynamic`：当前帧视图中清空或跳过该 MapPoint 关联。
- `Recovered`：允许重新参与投影、匹配和优化。
- `Static`：保持 ORB-SLAM2 原流程。
- 未知/过期 ID：`DynamicMapFilter` 默认返回 Static，保持保守兼容。
- Lost object 的旧动态点：由 Filter 的过期策略短期保留最后状态；阈值必须通过实验确定，不能无限期屏蔽。

## Paper1 Compatibility

### 1. 两种机制的职责

| 内容 | 论文1 MapPoint Dynamic Evidence | 论文2 Object Dynamic Map Filter |
|---|---|---|
| 判断单位 | 单个 MapPoint | 跨帧 ObjectState 及其 MapPoint ID 集合 |
| 数据来源 | 当前投影/特征是否落入语义动态框，时间累积与衰减 | 对象关联、三维运动、动态概率、生命周期和恢复 |
| 作用阶段 | ORBmatcher 匹配时更新分数；优化后 Tracking culling | 优化前构造可逆的稳定 MapPoint 视图 |
| 地图操作 | 当前 Frame 抑制，MapPoint 保存点级分数 | 不改 MapPoint，不永久删除，通过 ID 过滤与恢复 |

### 2. 推荐执行顺序

```text
ObjectDynamic filter from previous StableMapView
  → 排除已确认 Dynamic object 的关联点
  → ORBmatcher 对剩余候选执行原论文1证据更新与匹配
  → PoseOptimization 使用剩余关联
  → CullSemanticDynamicMapPoints 对剩余点执行论文1阈值抑制
```

这样可避免重复过滤：已被论文2对象级过滤的点不再进入 ORBmatcher，也不会在该帧再次积累论文1证据；论文1继续作为未关联点、新对象点及对象模型漏检的 fallback。首版不能在论文2判断 Dynamic 后再调用 `UpdateSemanticDynamicScore(true)`，否则会把同一对象证据重复计入点级状态。

### 3. 共存模式

- `Paper1 Baseline`：Shadow/Active 开关关闭，编译和执行路径保持论文1行为。
- `Paper2 Shadow`：Adapter 和 Filter 更新状态，但不改变候选点。
- `Paper2 Active`：上一帧 Filter 只修改当前帧/局部候选视图，论文1处理其余点。
- `Paper2 Object-only Ablation`：可配置关闭论文1点级抑制，用于证明对象级贡献；不应删除论文1代码。

必须分别记录 `paper1_suppressed`、`paper2_filtered` 和二者未实际重复作用的数量，避免实验统计把同一点重复计数。

## Minimal Patch Plan

本节为后续实现计划，本次不执行。

### 1. 预计修改文件

| 文件 | 预计修改 | 是否首版必需 |
|---|---|---|
| `include/Tracking.h` | 包含/声明 DynamicMapFilter；增加 Active Mode 状态和 Tracking 私有辅助接口 | 是 |
| `src/Tracking.cc` | 更新 Filter、过滤当前关联和局部候选、输出统计、Reset 清理 | 是 |
| `src/ORBmatcher.cc` | 无修改；继续处理 Filter 放行的候选 | 否 |
| `src/LocalMapping.cc` | 无修改 | 否 |
| `src/MapPoint.cc` / `include/MapPoint.h` | 无修改；只读取公开 `mnId` | 否 |

### 2. 新增变量建议

```text
Paper2::DynamicMapFilter mDynamicMapFilter
bool mbObjectDynamicActiveMode
std::size_t mnObjectDynamicFilteredCurrentPoints
std::size_t mnObjectDynamicFilteredLocalPoints
Paper2::StableMapView mObjectDynamicStableMapView  // 已有 Shadow 成员
```

编译开关建议：

```text
ENABLE_OBJECT_DYNAMIC_ACTIVE_MODE=0  // 默认关闭
```

Active 开关必须依赖 Shadow/Adapter 可用；关闭时不得执行 Filter 查询或改变容器。未来应由正规构建配置编译 ObjectDynamic 源文件，替代当前 Shadow 首版在 `Tracking.cc` 中纳入 `.cc` 的临时方式。

### 3. 新增接口建议

| 接口 | 参数 | 返回值 | 作用 |
|---|---|---|---|
| `UpdateDynamicMapFilter()` | `const StableMapView&` | `bool` | 仅在 Adapter 接受新帧后更新 Filter，并清理过期 ID |
| `FilterCurrentFrameMapPoints()` | `Frame&` | 过滤数量 | 遍历 `mvpMapPoints`，按 ID 清空 Dynamic 关联并同步 `mvbOutlier=false`；不修改 MapPoint |
| `BuildStableLocalMapPointView()` | `const vector<MapPoint*>&` | filtered vector | 返回非 Dynamic 候选副本，保留原 `mvpLocalMapPoints` |
| `IsObjectDynamicMapPoint()` | `const MapPoint*` | `bool` | 集中处理空指针、ID 转换和 Active 开关 |
| `ResetObjectDynamicActiveState()` | 无 | void | System Reset 时清空 Filter 和统计 |

### 4. `TrackLocalMap()` 最小调用顺序

```text
if Active:
    FilterCurrentFrameMapPoints(mCurrentFrame)

UpdateLocalMap()

if Active:
    stableLocalPoints = BuildStableLocalMapPointView(mvpLocalMapPoints)
    SearchLocalPoints(stableLocalPoints)  // 或临时交换候选容器
else:
    SearchLocalPoints()

if Active:
    FilterCurrentFrameMapPoints(mCurrentFrame)  // 防御性检查

Optimizer::PoseOptimization(&mCurrentFrame)
CullSemanticDynamicMapPoints()
...原有内点统计与成功判定...
```

为保持修改最小，可给 `SearchLocalPoints()` 增加可选候选参数，或新增 `SearchStableLocalPoints()`；不建议临时原地删除 `mvpLocalMapPoints`，因为该成员还用于地图显示和诊断。

### 5. 当前帧结束时更新

保持现有 Shadow 调用位置：成功跟踪后、`NeedNewKeyFrame()` 前调用 Adapter。随后：

```text
mObjectDynamicStableMapView = mObjectDynamicAdapter.ProcessFrame(snapshot)
if snapshot_accepted:
    mDynamicMapFilter.UpdateMapView(mObjectDynamicStableMapView)
    mDynamicMapFilter.ClearExpiredPoints()
```

该更新从下一帧开始生效。若 Adapter 拒绝快照，不推进 Filter 帧号或过期计数。

### 6. 关键帧策略

首版不额外修改 `NeedNewKeyFrame()` 或 `CreateNewKeyFrame()`。因为 Dynamic 点已经在最终优化前从当前 Frame 关联中移除，已有动态关联不会随 Frame 拷贝进入新 KeyFrame。新 RGB-D 深度点创建仍保持原逻辑，避免改变地图生成策略；是否阻止动态 bbox 内新点创建应作为方案 D 的独立后续实验。

## Risk Analysis

| 风险 | 影响 | 控制措施 |
|---|---|---|
| 一帧状态延迟 | 快速出现/启动运动的对象可能在首帧进入优化 | 使用 MotionEstimator 预测和合理状态阈值；未来拆分预关联与后验状态更新，不形成闭环 |
| object–MapPoint 误关联 | 静态约束被错误过滤，跟踪点数下降 | 深度/mask 一致性门控、多帧确认、最小静态内点保护和 Active 自动旁路 |
| 过滤后有效点少于跟踪阈值 | `mnMatchesInliers` 降低，引发 LOST 或更多关键帧 | 在执行过滤前估计剩余点数；低于安全阈值时降级为 Shadow 或只过滤高置信 Dynamic 对象 |
| 论文1与论文2重复处理 | 动态证据/统计被重复计算，贡献不清 | 对象级先过滤；论文1仅处理剩余点；分开记录统计并做消融 |
| Recovered 点无法重新进入 | 地图恢复机制失效 | 绝不 `SetBadFlag()` 或删除 KeyFrame 观测；Recovered/Static 查询直接放行 |
| Lost 状态长期残留 | 点被过久屏蔽 | 使用 `ClearExpiredPoints()`，按帧龄清理；记录清理数量并评估阈值 |
| MapPoint ID 替换 | Filter 保存旧 ID，替换点未继承状态 | 首版未知新 ID 默认 Static；未来在 Tracking 的 `CheckReplacedInLastFrame()` 后发布 ID replacement 事件 |
| Reset 后旧索引污染 | 新地图可能复用从 0 开始的 MapPoint ID | `Tracking::Reset()` 同步调用 Filter `Clear()` 和 Adapter reset |
| 与 LocalMapping 并发 | MapPoint 在读取 ID 时可能被置 bad/replaced | 保持现有 Map mutex 范围；查询前检查空/bad，不保存指针，不让 LocalMapping访问 Filter |
| 候选向量原地修改 | 影响可视化、统计或下一阶段复用 | 为投影匹配生成临时 filtered vector；只清理当前 Frame 中明确要排除的关联 |
| Active 代码关闭不彻底 | 论文1基线发生性能或结果变化 | 编译期开关默认关闭；关闭时跳过成员、查询、日志与容器复制；运行回归比较轨迹和 ATE |
| 当前 Filter 只提供布尔硬判定 | 阈值附近对象状态抖动 | 依赖 DynamicMapManager 多帧状态机；连续权重方案留给后续方案 B |

### 验证建议

1. 单元测试：Static/Dynamic/Recovered、同点冲突、过期、Reset 和 ID replacement 模拟。
2. 关闭 Active 与论文1冻结版本逐帧回归，确认调用和轨迹在正常并发波动范围内一致。
3. Shadow 与 Active 使用相同检测输入，记录每帧过滤点数、剩余内点、跟踪状态和耗时。
4. 运行静态 TUM 序列，验证误过滤率和 ATE 不退化。
5. 运行动态 TUM/Bonn 序列，对比 ATE/RPE、跟踪成功率、对象 ID 连续性和恢复延迟。
6. 消融比较 Paper1-only、Paper2 Shadow、Paper2 Active、Paper2 object-only，明确对象级过滤增益。

结论：首版 Active Mode 应只修改 `Tracking.h` 和 `Tracking.cc`，在 `TrackLocalMap()` 中以之前一帧的 DynamicMapFilter 结果过滤当前 Frame 已有关联及局部投影候选，并在 `PoseOptimization()` 前设置防御性过滤屏障。该方案无需修改 ORBmatcher、Optimizer、MapPoint 或 LocalMapping，不永久删除地图点，能够让 Recovered 点重新参与 SLAM，并保持论文1作为未关联点的补充动态证据机制。
