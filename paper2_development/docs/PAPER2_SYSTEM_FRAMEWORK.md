# Paper2 System Framework

论文方向：**Object-level Spatio-temporal Dynamic RGB-D SLAM**。

本文描述第二篇论文的概念算法框架。当前阶段只定义层次、数据契约和输出，不实现算法，不修改论文1冻结系统。

## 1. 输入层

### RGB-D

输入同步 RGB 图像、深度图像和时间戳。RGB 图像用于 ORB 特征和目标检测；深度图提供关键点及对象区域的尺度信息。相机标定参数用于反投影，SLAM 位姿用于将相机坐标观测转换到世界坐标系。

### YOLO检测

YOLO 输出每帧目标的类别、置信度和 Bounding Box。论文1现有接口经 Unix socket 将检测文本转换为 `bbox + class_id`。论文2输入适配层将其转换为不依赖论文1内部类的 `ObjectObservation`。

```text
RGB frame ───────────────┐
Depth frame ─────────────┼─→ Frame Observation Adapter
Timestamp ───────────────┤
YOLO bbox/class/score ───┘
```

## 2. SLAM层

### Tracking

Tracking 构造当前 Frame，提取 ORB 特征，执行参考关键帧/运动模型/局部地图匹配，通过位姿优化得到 `Tcw`，并保留当前特征到 MapPoint 的关联。论文1的 bbox 动态点过滤和 Dynamic Evidence Score 继续保持原行为。

论文2只读输出：

- Frame ID 与时间戳
- 优化后的相机位姿
- 去畸变特征位置和深度
- 有效 MapPoint 关联
- YOLO bbox 与类别
- 论文1点级动态证据（可选对比输入）

### LocalMapping

LocalMapping 处理新关键帧、创建和融合 MapPoint、执行局部 BA，并剔除低质量地图点和冗余关键帧。论文2不参与其内部优化，只通过快照同步点/关键帧生命周期结果。

### MapPoint

MapPoint 提供世界坐标、观测关键帧、跟踪质量、坏点/替换状态和论文1动态分数。ObjectDynamic 使用稳定 ID 和值语义快照，不取得 MapPoint 所有权。

```text
Tracking Frame snapshot
       │
       ├── camera pose / timestamp
       ├── detection observations
       └── MapPoint snapshots
                    ↑
       LocalMapping lifecycle snapshots
```

## 3. Object Dynamic层

### ObjectState

保存跨帧对象身份和当前状态：对象 ID、类别、bbox、世界坐标姿态、速度、动态概率、关联 MapPoint ID、观测 KeyFrame ID 和轨迹状态。ObjectState 不写入论文1的 Frame、MapPoint 或 KeyFrame。

### MotionEstimator

消费 ObjectState 历史和当前观测，输出下一时刻预测位置、估计速度、运动不确定性和动态概率证据。运动估计必须在世界坐标系中显式补偿相机运动。

### DynamicMapManager

作为对象层协调器：

- 将检测观测与已有对象状态关联。
- 创建、更新、退休和恢复 ObjectState。
- 通过独立 Association Manager 维护 Object–MapPoint–KeyFrame 关系。
- 处理 MapPoint bad/replaced 事件的关联清理或迁移。
- 根据动态概率生成动态对象地图和稳定地图视图。

对象层概念流程：

```text
FrameObservationSnapshot
  → object observation construction
  → MotionEstimator prediction
  → object association
  → ObjectState update
  → MapPoint association update
  → dynamic probability update
  → active / lost / recovered state transition
  → stable map view
```

## 4. 输出

系统目标输出为稳定动态环境地图，包括：

- 相机轨迹与当前定位状态。
- 静态、可信 MapPoint 构成的稳定地图视图。
- 具有稳定 object ID 的对象级语义地图。
- 动态对象当前位置、速度、轨迹和动态概率。
- 暂时丢失及恢复对象的状态记录。
- 对象–MapPoint–KeyFrame 关联及置信度，支持实验审计。

## 分层数据流

```text
Input Layer
  RGB-D + timestamp + YOLO detections
                    │
                    ▼
Frozen SLAM Layer
  Tracking → Frame pose/feature association
  LocalMapping → KeyFrame/MapPoint lifecycle
                    │ read-only snapshots
                    ▼
Paper2 Object Dynamic Layer
  ObjectState ↔ MotionEstimator
       ↕
  DynamicMapManager + Association Manager
                    │
                    ▼
Output Layer
  stable map + dynamic object trajectories + recovery state
```

## 开发边界

第一阶段采用离线快照/导出数据验证接口。未来若需要在线运行，应新增论文2专用适配器和构建入口，并单独评审线程模型、数据所有权和回退路径；不得直接改变论文1 Tracking、LocalMapping 或 MapPoint 的冻结行为。
