# ObjectDynamic 模块设计

## ObjectDynamic模块设计

目标：为第二篇论文“Object-level Spatio-temporal Dynamic SLAM”提供独立的对象级时空动态建模层。模块位于 `paper2_development/modules/ObjectDynamic/`，通过适配器消费论文1冻结代码提供的检测、位姿、深度和地图点信息，不直接修改论文1实现。

## ObjectState

职责：保存一个对象在当前时刻的统一状态，并作为关联、预测和地图更新的数据单元。

建议字段：

- `object_id`：跨帧稳定的对象标识。
- `category`：语义类别及可选置信度。
- `position`：世界坐标系中的三维位置及可选协方差。
- `velocity`：世界坐标系中的线速度及可选协方差。
- `dynamic_probability`：对象处于动态状态的概率。
- `last_observed_frame`：最后观测帧，用于失配和恢复。
- `observation_count`：累计有效观测数。
- `track_status`：候选、稳定跟踪、暂时丢失、恢复或终止。

基本行为：

- 用新观测更新状态及不确定性。
- 保存有限长度的时间历史。
- 根据动态概率阈值提供静态、可疑动态、动态三态判定。

## MotionModel

功能：

- motion estimation：利用连续对象观测、相机位姿与时间戳估计对象运动。
- trajectory prediction：在短时检测缺失时预测对象位置和搜索门限。

建议接口：

- `Initialize(ObjectState, Observation)`
- `Predict(timestamp) -> PredictedState`
- `Update(Observation) -> ObjectState`
- `Innovation(Observation) -> residual/covariance`
- `Reset(ObjectState)`

设计要求：

- 运动模型与具体滤波器解耦，首个实现可使用常速度模型。
- 明确相机运动补偿，所有对象状态统一到世界坐标系。
- 输出预测不确定性，供对象关联门控和恢复机制使用。
- 不把类别先验直接等同于真实运动，语义只作为动态概率的一项证据。

## DynamicMapManager

功能：

- object-map association：将当前帧对象观测与已有 `ObjectState` 关联。
- dynamic map update：更新对象状态、动态概率以及对象关联的地图元素状态。
- recovery mechanism：处理短时遮挡、漏检、错误动态判定和对象重新出现。

建议内部流程：

```text
Detection/Depth/Pose observations
  → coordinate normalization
  → motion prediction
  → association gating and assignment
  → ObjectState update
  → dynamic probability fusion
  → static/dynamic map-view generation
  → lost-track recovery or retirement
```

建议接口：

- `ProcessFrame(FrameObservation)`：执行预测、关联和状态更新。
- `Associate(observations, predictions)`：结合类别、三维距离、投影重叠和运动残差进行匹配。
- `UpdateDynamicProbability(ObjectState, Evidence)`：融合语义、几何与时间证据。
- `GetStaticMapView()`：向定位模块提供排除可信动态对象后的地图视图。
- `GetDynamicObjects()`：返回当前动态对象集合及轨迹。
- `RecoverLostObjects()`：在预测门限内执行重关联。
- `RetireStaleObjects()`：超时后终止对象轨迹，但保留可审计历史。

恢复机制原则：

- 暂时未观测不立即删除对象，进入预测状态并逐步降低置信度。
- 重新观测需同时通过类别、空间门控和运动一致性检验。
- 被误判为动态的稳定对象可在持续静态证据下恢复到静态地图视图。
- 动态对象停止运动后设置滞回区间，避免静态/动态状态频繁切换。

## 与论文1冻结代码的接口边界

输入适配层可读取：检测框和类别、RGB-D 深度、相机位姿、帧 ID/时间戳、MapPoint 观测以及已有 `SemanticObject` 输出。所有适配代码仍属于本模块；论文1的 `src/`、`include/` 和 `Examples/` 保持冻结。

首阶段只定义数据结构与离线接口，不接入论文1运行链路。未来需要在线接入时，应先形成独立设计评审和兼容层方案，再决定是否在新的论文2构建目标中连接。
