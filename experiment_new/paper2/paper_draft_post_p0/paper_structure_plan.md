# 《基于目标级动态建模与时间一致性约束的动态环境视觉SLAM方法》论文结构规划

## 一、论文定位与叙事主线

本文按独立投稿论文组织，不采用“在既有工作上扩展”的叙事。全文围绕以下问题展开：动态环境中的单帧语义区域不能稳定表达对象随时间变化的运动状态；若直接依据不稳定判定过滤地图点候选，又可能削弱有效静态约束。为此，本文在ORB-SLAM2框架中引入目标级动态状态建模，以跨帧关联、几何—时间运动证据、动态概率和生命周期维护对象状态，并通过Shadow与Active两种模式区分“状态估计”和“状态反馈”。

推荐全文逻辑链为：

```text
动态场景定位问题
→ 逐帧几何/语义判断及直接过滤的局限
→ 目标级时间一致性状态建模
→ ObjectSnapshot与跨帧关联
→ 几何—时间运动评分与概率更新
→ 生命周期管理和StableMapView
→ Shadow观测与Active候选过滤
→ TUM RGB-D定位、覆盖率和在线状态实验
→ 方法有效范围与Active局限
```

## 二、模板前置内容

### 中文题名

基于目标级动态建模与时间一致性约束的动态环境视觉SLAM方法

题名应准确反映“目标级状态建模”和“时间一致性”，不使用“高精度”“鲁棒”等尚无统计检验支持的修饰语。

### 作者与单位

按模板填写作者姓名、单位全称、城市和邮政编码。通信作者、基金项目、中图分类号、文献标志码及稿件编号等信息以期刊投稿系统的最新要求为准，不在当前草稿中虚构。

### 中文摘要

采用“目的—方法—结果—结论”四部分结构，建议控制为一个完整摘要段落或按模板要求加粗分项标识。

#### 目的

- 说明动态目标特征会干扰基于静态场景假设的视觉SLAM。
- 指出单帧语义判断缺少跨帧目标状态，直接过滤又可能损失有效静态约束。
- 给出目标：建立目标级时间一致性动态状态，并分析其两种利用方式。

#### 方法

- YOLO仅作为语义观测输入。
- ObjectSnapshot保存帧、检测、有效三维位置和MapPoint ID快照。
- ObjectAssociation保持跨帧object ID。
- MotionEstimator利用有效三维位置形成几何—时间运动评分。
- person初始概率为0.7，语义只用于初始化。
- 动态概率更新为

  \[
  P_t=0.8P_{t-1}+0.2S_{motion}.
  \]

- DynamicMapManager维护Static、PotentialDynamic、Dynamic、Lost和Recovered状态。
- Shadow仅生成StableMapView；Active过滤Tracking动态候选MapPoint，不删除地图点。

#### 结果

仅使用TUM RGB-D的3个真实序列：

|序列|Shadow ATE RMSE/m|Active ATE RMSE/m|
|---|---:|---:|
|fr3_walking_xyz|0.571050|0.598146|
|fr3_walking_rpy|0.882434|0.229810|
|fr3_walking_halfsphere|0.447759|0.426866|

结果段必须同时说明Active在walking_rpy上的低ATE伴随tracked frames下降与tracking gap episodes增加，不能据此判断完整序列性能全面提升。

#### 结论

- 目标级关联和生命周期管理可形成连续对象动态状态。
- Shadow在当前3组单次实验中表现出可用的状态建模结果和较低轨迹误差。
- Active具有场景依赖性，应结合轨迹覆盖率和跟踪间断评价。
- 不写统计显著性结论，除非后续补充重复实验和统计检验。

### 关键词

建议为：视觉SLAM；动态场景；目标级动态建模；时间一致性；目标关联；地图点候选过滤。

### 英文题名与摘要

英文题名建议：`Visual SLAM in Dynamic Environments Based on Object-level Dynamic Modeling and Temporal Consistency Constraints`。

英文摘要应与中文摘要信息逐项对应，采用`Objective`、`Method`、`Result`、`Conclusion`结构，数值、单位和限制性说明保持一致；`Key words`与中文关键词一一对应。

## 0 引言

### 0.1 动态环境视觉SLAM背景

写作内容：

- 视觉SLAM的基本任务和静态场景假设。
- 行人等运动对象对特征匹配、位姿优化和地图稳定性的影响。
- 动态信息估计与动态信息反馈是两个不同问题：状态要可靠，反馈还需避免损失约束。

建议在本段引用ORB-SLAM2及动态SLAM综述或代表性工作，形成问题背景，不展开本文技术细节。

### 0.2 现有方法及不足

按3类方法形成连续论证：

1. 基于几何运动一致性的方法：依据多视图几何、光流、重投影误差或运动模型识别异常运动；优点是不依赖预定义类别，局限是依赖运动可观测性和匹配质量，缺少目标语义理解。
2. 基于语义信息的方法：利用检测或分割定位潜在动态类别；优点是具有类别和空间范围，局限是通常采用单帧判断，易受漏检、遮挡和框抖动影响，缺少跨帧目标状态。
3. 动态点过滤方法：在匹配、优化或建图环节排除动态候选；可能减少运动干扰，但误判会削弱有效静态约束，影响跟踪连续性。

每类只描述文献中实际存在的技术路线；具体引用待文献检索后补充，不虚构作者、方法名或结果。

### 0.3 本文切入点

强调本文研究对象不是“检测某一帧中哪些像素为动态”，而是“维护具有跨帧标识、运动历史和生命周期的对象动态状态”。说明语义给出对象创建时的动态倾向，几何—时间证据决定后续概率变化。

### 0.4 主要贡献

建议压缩为3条，以利摘要和结论呼应：

1. 构建目标级跨帧关联与生命周期管理框架，通过object ID和Static、PotentialDynamic、Dynamic、Lost、Recovered状态维护对象时间状态。
2. 构建语义先验初始化、几何—时间证据更新机制；使用`position_valid`隔离无效深度，并通过指数平滑形成动态概率。
3. 构建StableMapView及Shadow/Active两种动态信息利用模式，将状态估计与Tracking候选过滤分离，便于分析主动反馈的收益和风险。

引言末段简述全文结构：第1节相关工作，第2节方法，第3节实验，第4节结论。

## 1 相关工作

本章承担文献定位，不重复方法章节公式。所有比较必须有真实文献来源。

### 1.1 动态环境视觉SLAM

写作内容：

- 概述动态场景对前端跟踪与后端地图的影响。
- 归纳基于几何约束、运动分割、鲁棒估计等路线。
- 分析仅依赖运动一致性在目标静止、相机快速运动、遮挡或弱纹理条件下的限制。
- 引出需要在几何观测之外建立对象实体和时间状态。

### 1.2 语义辅助SLAM

写作内容：

- 介绍目标检测或语义分割向SLAM提供类别和区域信息的常见方式。
- 区分“语义输入”“动态状态估计”“动态观测处理”三个层次。
- 指出逐帧类别掩膜不等于对象级动态状态，类别为潜在动态也不表示每帧都在运动。
- 明确本文YOLO只提供检测观测，不将检测性能作为贡献或评价对象。

### 1.3 目标级动态建模

写作内容：

- 综述目标跟踪、对象级地图、运动状态和生命周期管理等相关方向。
- 讨论跨帧ID、状态历史、丢失与恢复对时序稳定性的作用。
- 说明本文关注轻量、可独立于ORB-SLAM2核心对象所有权的数据结构与在线状态更新。
- 不声称不存在的全局数据关联、联合BA、目标三维包围盒或轨迹预测优化。

### 1.4 小结与本文区别

用一段总结研究空缺：几何方法缺少对象语义实体，逐帧语义方法缺少时间状态，直接过滤存在约束损失风险。自然引出第2节，不把本文描述为其他论文的延续。

## 2 方法

### 2.1 系统框架

#### 2.1.1 总体组成

描述ORB-SLAM2、YOLO语义输入和ObjectDynamic模块的关系。建议放置“系统总体框架图”（图1）：

```text
RGB-D帧 → YOLO检测 → ObjectSnapshot → ObjectAssociation
→ MotionEstimator → DynamicMapManager → StableMapView
→ Shadow统计 / Active候选过滤 → Tracking
```

图注需明确YOLO只提供语义检测；Shadow路径不反馈Tracking；Active路径反馈DynamicMapFilter。

#### 2.1.2 数据边界与在线调用时机

- ObjectSnapshot为值语义快照，不持有Frame、KeyFrame或MapPoint裸指针。
- Tracking成功后、关键帧判断前构建快照并调用Adapter。
- ObjectDynamic保存MapPoint ID关联，不拥有地图点对象。

### 2.2 目标级动态建模

#### 2.2.1 ObjectSnapshot与三维观测

写入frame id、timestamp、camera pose、class、bbox、confidence、position、`position_valid`和MapPoint ID。给出bbox中心及反投影公式。

重点说明：中心深度无效时`position_valid=false`；默认零向量不是有效世界原点；无效位置不进入三维代价和速度估计。不要描述框内深度中值、深度聚类或三维包围盒。

建议图2为“有效/无效三维观测处理流程”。

#### 2.2.2 ObjectAssociation

在本节集中放置4项关联代价：

\[
C_{sem}=\mathbb I(c_i\ne c_j),
\]

\[
C_{iou}=1-\operatorname{IoU}(B_i,B_j),
\]

\[
C_{2D}=\operatorname{clip}\left(\frac{\|\mathbf u_i-\mathbf u_j\|}{100},0,1\right),
\]

\[
C_{3D}=\operatorname{clip}\left(\frac{\|\mathbf p_i-\mathbf p_j\|}{2.0},0,1\right).
\]

三维有效时：

\[
C=0.35C_{sem}+0.30C_{iou}+0.15C_{2D}+0.20C_{3D}.
\]

三维无效时移除3D项并对其余权重重新归一化。最大匹配代价为0.70，候选按代价升序进行一对一贪心分配。必须如实称为贪心关联，不写Hungarian算法或全局最优。

#### 2.2.3 ObjectState

列出object ID、类别、bbox、三维位置及有效性、速度、运动方向、动态概率、生命周期、关联MapPoint ID、时间戳和观测次数。说明新对象为PotentialDynamic；person初始动态概率0.7，其他类别0.5。

### 2.3 时间一致性动态状态估计

#### 2.3.1 MotionEstimator

给出速度：

\[
\mathbf v_t=\frac{\mathbf p_t-\mathbf p_{t-1}}{\Delta t}.
\]

说明时间间隔要求`1e-6 < Δt ≤ 10 s`，任一位置无效时本次估计失败且不制造零速度。

依次给出：

\[
S_v=1-\exp(-\|\mathbf v_t\|/0.5),
\]

\[
S_h=\exp(-\|\mathbf v_t-\mathbf v_{t-1}\|/0.5),
\]

以及方向一致性、0.5/0.5一致性加权和

\[
S_{geo}=\operatorname{clip}(S_vS_c,0,1),\qquad
S_{motion}=S_{geo}.
\]

必须强调运动评分中没有逐帧固定语义项。

#### 2.3.2 动态概率更新

本节放置核心公式：

\[
P_t=0.8P_{t-1}+0.2S_{motion}.
\]

解释：语义只确定初始化倾向；有效的几何运动及历史一致性驱动概率变化。可用静止person示例`0.7→0.56→0.448`解释其不会仅由类别永久锁定Dynamic。

#### 2.3.3 生命周期管理

建议图3为真实在线状态机，包含：

- Static：`P≥0.50`进入PotentialDynamic；
- PotentialDynamic：person在`P≥0.60`进入Dynamic，其他对象在`P≥0.70`进入Dynamic；`P≤0.30`进入Static；
- Dynamic：`P<0.50`退回PotentialDynamic；
- 未观测：进入Lost；
- Lost连续3次重新匹配：进入Recovered；
- Recovered下一次观测：按概率进入Static、PotentialDynamic或Dynamic。

明确恢复确认第1、2次仍保持Lost，第3次进入Recovered。状态机图与伪代码应对应`ObjectDynamicAdapter::ProcessFrame()`和`DynamicMapManager`的在线调用顺序。

### 2.4 动态信息利用

#### 2.4.1 StableMapView

说明视图包含active、dynamic和recovered对象，其中dynamic是active中状态为Dynamic的子集。视图用于隔离ObjectDynamic内部状态与Tracking消费者。

#### 2.4.2 Shadow模式

只运行状态估计并输出StableMapView和日志，不反馈匹配、位姿优化和地图结构。论文不能将Shadow的轨迹差异解释为动态点过滤直接作用。

#### 2.4.3 Active模式

说明DynamicMapFilter建立`MapPoint ID→Object ID→Dynamic State`关系，在`TrackLocalMap()`中：

1. 过滤当前帧已有动态关联；
2. `UpdateLocalMap()`后抑制局部地图动态候选；
3. `SearchLocalPoints()`后、位姿优化前再次防御性过滤。

统一使用“候选过滤”“关联抑制”，禁止使用“删除地图点”。代码不删除全局MapPoint、KeyFrame观测，也不修改原有语义状态。

#### 2.4.4 算法伪代码

给出从ObjectSnapshot输入到StableMapView输出的主流程伪代码，分支标明Shadow直接输出、Active更新过滤器。伪代码不加入源码没有的卡尔曼滤波、匈牙利匹配、轨迹预测或联合优化。

## 3 实验结果与分析

### 3.1 实验设置

#### 3.1.1 数据集

列出TUM RGB-D的`fr3_walking_xyz`、`fr3_walking_rpy`、`fr3_walking_halfsphere`，说明选择动态行人场景。数据路径不写入论文正文。

#### 3.1.2 实验平台与实现细节

需要从实际机器补录且核验：CPU、GPU、内存、Ubuntu、编译器、OpenCV、CUDA/PyTorch版本。当前材料不足，不填占位数值。记录ORB特征参数、YOLO权重和运行模式时必须与正式实验日志一致。

#### 3.1.3 对比方法

- Baseline：基础ORB-SLAM2配置；
- Semantic：启用语义动态处理、不启用ObjectDynamic反馈的对比配置；
- Shadow：启用ObjectDynamic，仅观测状态；
- Active：启用ObjectDynamic和DynamicMapFilter候选过滤。

正文、图例、表格统一使用上述名称，不出现项目开发过程中的历史称谓。

#### 3.1.4 评价指标

- ATE RMSE与ATE mean；
- RPE translation与RPE rotation；
- Tracked Frames和KeyFrames；
- Tracking gap episodes代理指标；
- Detections、Valid/Invalid 3D、Dynamic transitions、Recovered events；
- Active的filtered MapPoints和frames with filtering。

明确evo参数完全一致：`evo_ape tum --align`，RPE分别使用`trans_part`和`angle_deg`。说明gap episodes是日志代理，而非Tracking内部LOST状态计数。

### 3.2 定位精度分析

#### 3.2.1 四方法ATE比较

放置主表（表1）：`Sequence × Baseline/Semantic/Shadow/Active`的ATE RMSE。数据来自`trajectory_comparison_post_p0.csv`，不得手工改写不利结果。

重点分析：

- Shadow的真实ATE为0.571050、0.882434和0.447759 m；
- Active为0.598146、0.229810和0.426866 m；
- walking_xyz中Shadow优于Active；
- walking_rpy的Active低ATE伴随tracked frames下降和gap增加；
- walking_halfsphere的Active轨迹覆盖同样下降。

#### 3.2.2 RPE与轨迹覆盖

放置RPE表（表2）及tracked frames/KeyFrames表（表3），使局部误差与轨迹完整性共同呈现。Active walking_rpy不得只报告0.229810 m而省略371个tracked frames和19个gap episodes。

#### 3.2.3 轨迹与误差可视化

建议图4为ATE柱状图，图5为估计轨迹与真值对比。若没有现成轨迹图，应基于已保存轨迹生成，不新增实验；所有图使用同一对齐参数。

### 3.3 动态状态分析

#### 3.3.1 三维观测有效性

放置Valid/Invalid 3D统计（表4或图6），解释无效观测仍可提供二维/语义关联信息，但不参与3D代价与运动估计。

#### 3.3.2 Dynamic状态时间变化

使用`dynamic_objects_over_time`曲线（图7），分析对象动态状态随帧变化。说明dynamic object-frame sum是逐帧动态对象数之和，不等同于独立目标数量，也不是检测准确率。

#### 3.3.3 Lost/Recovered在线行为

报告3个Shadow序列分别出现32、34、44次Recovered事件，证明在线恢复路径可达。这里的“验证”限于软件路径与日志事件，不声称恢复识别准确率，因为没有目标级GT。

### 3.4 Active策略分析

#### 3.4.1 过滤数量与时间分布

放置Active filtered MapPoints时间曲线（图8）和汇总表：walking_xyz过滤754点/10帧，walking_rpy过滤244点/10帧，walking_halfsphere过滤64点/44帧。

#### 3.4.2 Shadow与Active对比

放置Shadow vs Active图（图9），联合ATE、RPE、tracked frames和gaps讨论。说明候选过滤可能减少动态干扰，也可能移除有效定位约束；现有结果显示其效果具有场景依赖性。

#### 3.4.3 负面结果与有效性边界

- walking_xyz：Active ATE较Shadow增加4.74%，轨迹覆盖相同；
- walking_rpy：Active ATE数值降低，但轨迹覆盖明显下降且有19个gaps；
- walking_halfsphere：Active ATE略低，但RPE上升、轨迹覆盖下降且有8个gaps。

不得用“全面提升”概括Active。指出当前仅单次运行，尚无方差和显著性检验。

### 3.5 本章小结

用事实总结：Shadow在3个序列中获得给定ATE，目标生命周期和Recovered路径在线可达；Active反馈呈场景依赖。避免重复方法章节和引入新结论。

## 4 结论

结论按“工作—结果—局限—展望”组织：

1. 总结目标级动态建模框架及跨帧关联、生命周期管理。
2. 总结语义先验初始化和几何—时间证据概率更新，强调无效3D隔离。
3. 总结Shadow在3个TUM RGB-D动态序列中的真实结果，避免统计显著性措辞。
4. 指出Active候选过滤具有场景依赖，轨迹覆盖下降时ATE不能单独代表整体性能。
5. 展望可包括更可靠的对象三维位置、关联策略、过滤置信机制和重复实验；不得把尚未实现内容写成本文方法。

## 三、公式、图表与数据布置总表

|内容|建议位置|来源|
|---|---|---|
|bbox中心与反投影|2.2.1|`BuildObjectDynamicSnapshot()`|
|4项关联代价及权重|2.2.2|`ObjectAssociation::ComputeAssociationCost()`|
|速度、speed score、稳定性|2.3.1|`MotionEstimator::Estimate()`|
|`S_motion=S_geo`|2.3.1|`MotionEstimator::Estimate()`|
|`P_t=0.8P_(t-1)+0.2S_motion`|2.3.2|`MotionEstimator::Estimate()`|
|生命周期阈值与恢复路径|2.3.3|`DynamicMapManager`、Adapter|
|总体框架图|2.1.1|源码在线数据流|
|状态机图|2.3.3|在线真实状态转换|
|ATE主表|3.2.1|post-P0 comparison CSV|
|RPE/覆盖表|3.2.2|post-P0 comparison CSV|
|3D有效性与状态统计|3.3|post-P0 runtime statistics CSV|
|Active过滤统计|3.4|post-P0 runtime statistics CSV|

## 四、版式实施建议

- 标题按`0 引言、1 相关工作、2 方法、3 实验结果与分析、4 结论`编号；下级标题采用`2.1`、`2.1.1`格式，避免层级过深。
- 图表按正文首次出现顺序编号，正文必须先引用后出现；图题、表题提供中英文对照。
- 图片制作分辨率不低于300 dpi；坐标轴、图例和单位在缩放后仍可辨识。
- 变量首次出现时解释含义和单位；标量、向量、矩阵的字体格式在排版阶段统一。
- 公式居中、按全文或章节连续编号，正文用“式（x）”引用；公式后的标点符合句法。
- 数值与单位之间留适当空格，单位采用国际单位制，如`0.571050 m`、`0.5 s`。
- 参考文献按模板规定格式著录，中英文文献字段、作者、卷期页码和DOI逐项核对；本规划不生成未经核验的参考文献。
- 中文摘要与英文摘要的目的、方法、结果、结论及数值必须完全对应。
