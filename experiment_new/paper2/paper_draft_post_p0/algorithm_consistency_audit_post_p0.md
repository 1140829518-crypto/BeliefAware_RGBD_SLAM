# Paper2 Post-P0 算法一致性审计

审计基准：Git commit `7489083942e8c1ad83b0a7f0f4eca27ef1cb256b`。

|源码文件|函数/位置|论文描述|一致性检查|
|---|---|---|---|
|`src/Tracking.cc`|`BuildObjectDynamicSnapshot()`|从当前帧复制frame id、timestamp、camera pose、检测框、类别、三维位置有效性和框内MapPoint ID|一致。快照为值语义，不保存ORB-SLAM2裸指针|
|`src/Tracking.cc`|`BackProjectSemanticObjectCenter()`|只使用bbox中心像素有效深度反投影|一致。不得描述为框内中值、聚类或鲁棒三维中心|
|`ObjectSnapshot.h/.cc`|`SnapshotDetection`|显式保存`position_valid`|一致。默认构造为false；正常带参接口可显式传入|
|`ObjectState.h/.cc`|构造、`UpdateState()`、`IsPositionValid()`|对象状态持续保存3D有效性|一致。默认对象false，观测更新传播该标志|
|`ObjectAssociation.cc`|`ComputeAssociationCost()`|有效3D使用四项代价；无效3D跳过3D项并重归一化|一致。无效零占位不进入3D distance cost|
|`ObjectAssociation.cc`|`AssociationWeights()`、构造函数|权重0.35/0.30/0.15/0.20，最大代价0.70，2D尺度100 px，3D尺度2.0|一致|
|`ObjectAssociation.cc`|`AssociateObjects()`|候选按代价升序一对一贪心匹配并保持object ID|一致。不是Hungarian或全局最优匹配|
|`MotionEstimator.cc`|`Estimate()`位置检查|前后任一位置无效则返回`InvalidPosition`，不估计速度|一致。不得写成无效位置产生零速度|
|`MotionEstimator.cc`|`Estimate()`|`S_motion=S_geo`|一致。源码不存在`0.5*S_geo+0.5*S_sem`|
|`ObjectState.cc`|对象构造|person (`class_id=3`)初始化`P0=0.7`，其他类别0.5|一致。语义先验仅用于初始化|
|`MotionEstimator.cc`|概率更新|`P_t=0.8P_(t-1)+0.2S_motion`|一致。仅在有效运动估计后应用|
|`DynamicMapManager.cc`|构造、`CheckTransition()`|Static/PotentialDynamic/Dynamic阈值0.30/0.50/0.70，person进入Dynamic阈值0.60|一致。person阈值仍是类别相关状态参数，应在论文中公开|
|`ObjectDynamicAdapter.cc`|`ProcessFrame()`|Lost重新匹配时在线调用`RecoverObject()`|一致。修复前“未接入在线路径”的描述已失效|
|`DynamicMapManager.cc`|`RecoverObject()`|连续三次匹配确认后进入Recovered|一致。前两次保持Lost；第三次转Recovered并重置计数|
|`DynamicMapManager.cc`|`CheckTransition()` Recovered分支|Recovered后续观测按概率进入Dynamic、Static或PotentialDynamic|一致。Recovered不是永久状态|
|`ObjectDynamicAdapter.cc`|`BuildStableMapView()`|active、dynamic、recovered对象形成值语义视图|一致。dynamic是active中状态为Dynamic的子集|
|`src/Tracking.cc`|`Track()` Shadow宏分支|Shadow调用Adapter并记录StableMapView，不反馈Tracking|一致。不得把Shadow的ATE变化归因于主动过滤|
|`src/Tracking.cc`|`TrackLocalMap()`、过滤辅助函数|Active清除当前帧动态关联并从局部候选向量排除动态MapPoint|一致。行为是association/candidate filtering|
|`src/Tracking.cc`|`FilterCurrentFrameDynamicMapPoints()`|只把当前Frame中的指针槽位置空|一致。不调用MapPoint删除接口|
|`src/Tracking.cc`|`FilterLocalDynamicMapPoints()`|从本次Tracking的`mvpLocalMapPoints`候选向量擦除条目|一致。不删除Map、MapPoint或KeyFrame观测|

## 重点结论

### 1. Person动态先验

当前实现同时保留person初始概率0.7和进入Dynamic阈值0.60，但不再把semantic prior逐帧加入motion score。论文应表述为“类别提供初始化倾向，几何—时间证据驱动后续概率变化”，不得使用修复前的等权语义—几何运动公式。

### 2. `position_valid`

无效深度与有效世界原点已由布尔标志区分。关联阶段移除3D项并重新归一化；运动阶段拒绝本次估计。论文不得再描述默认零向量进入3D代价或速度计算。

### 3. Recovered在线路径

`ObjectDynamicAdapter::ProcessFrame()` 已调用 `DynamicMapManager::RecoverObject()`。真实在线状态经过三次连续重新匹配才到达Recovered，post-P0真实实验也记录了Recovered事件。论文不得再写“RecoverObject仅存在于测试或未接入Tracking路径”。

### 4. Active真实行为

Active不会从全局地图删除MapPoint，也不会修改MapPoint生命周期。它只在当前Tracking帧中解除动态关联，并从本次局部地图候选列表中排除动态点。推荐术语为“动态MapPoint候选抑制”或“Tracking关联过滤”，避免“删除动态地图点”“清除动态地图”等表述。

## 实验描述一致性

post-P0论文实验数据只引用`experiment_new/paper2/results/post_p0/`中的新Shadow/Active结果。Active walking_rpy的低ATE伴随tracked frames降至371和19个gap episodes，必须与误差数值同时报告。Shadow相对Paper1三序列ATE降低属于单次实验事实，不构成统计显著性结论。

