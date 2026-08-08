# Paper2 Algorithm Design

论文方向：**Object-level Spatio-temporal Dynamic RGB-D SLAM**。

设计基线：`paper2_development` 分支，提交 `5577157`。本文给出数学模型与算法流程设计，不包含实现，不改变论文1冻结代码。符号、接口和数据所有权遵循 `CODE_ARCHITECTURE.md`、`PAPER2_SYSTEM_FRAMEWORK.md` 与 `ObjectDynamic/INTERFACE_DESIGN.md`。

## 1. Overall Framework

```text
RGB-D Input
    ↓
YOLO Object Detection
    ↓
Object Association
    ↓
Object State Estimation
    ↓
Motion Consistency Analysis
    ↓
Dynamic Map Management
    ↓
ORB-SLAM2 Optimization
    ↓
Stable Dynamic Semantic Map
```

1. **RGB-D Input**：提供同步 RGB、深度和时间戳；深度与内参将二维对象观测提升为三维观测。
2. **YOLO Object Detection**：输出语义类别、置信度和 Bounding Box。当前 bbox 作为对象区域；模型允许未来使用 mask，但不依赖该扩展。
3. **Object Association**：综合语义、二维重叠、三维距离和运动预测，将当前检测与历史轨迹匹配并保持 object ID。
4. **Object State Estimation**：在世界坐标系维护对象位置、姿态、速度、动态概率、关联 MapPoint 和观测 KeyFrame。
5. **Motion Consistency Analysis**：区分相机运动造成的表观变化与对象自身运动，检查速度、方向、预测残差及时间连续性。
6. **Dynamic Map Management**：管理对象生命周期，隔离可信动态对象关联点，并验证动态目标离开后的背景地图。
7. **ORB-SLAM2 Optimization**：概念上使用稳定地图视图完成位姿与局部地图优化。当前设计不改动论文1优化器；未来接入必须使用论文2专用适配层。

框架采用双层地图视图：底层 ORB-SLAM2 地图保持论文1行为；论文2维护对象状态和关联记录，并输出不改变底层所有权的 `StableMapView`。

## 2. Object-level State Representation

对第 \(i\) 个对象，在时刻 \(t\) 定义状态：

\[
\mathcal{S}_t^i =
\left\{o^i, c_t^i, \mathbf{T}_{wo,t}^i, \mathbf{p}_t^i,
\mathbf{v}_t^i, P_{D,t}^i, \mathcal{M}_t^i,
\mathcal{K}_t^i, q_t^i\right\}.
\]

- \(o^i\)：跨帧稳定的 object ID。
- \(c_t^i\)：语义类别及类别置信度分布。
- \(\mathbf{T}_{wo,t}^i \in SE(3)\)：对象坐标系到世界坐标系的位姿；bbox 无法提供完整朝向时，旋转分量可标记为未观测。
- \(\mathbf{p}_t^i \in \mathbb{R}^3\)：对象在世界坐标系中的代表位置。
- \(\mathbf{v}_t^i \in \mathbb{R}^3\)：对象世界坐标速度。
- \(P_{D,t}^i \in [0,1]\)：对象动态置信度。
- \(\mathcal{M}_t^i\)：关联 MapPoint ID 集合。
- \(\mathcal{K}_t^i\)：观测该对象的 KeyFrame ID/Frame ID 集合或有限历史。
- \(q_t^i\)：生命周期状态，属于 Static、PotentialDynamic、Dynamic、Lost、Recovered。

显式表示不确定性时，定义最小状态向量：

\[
\mathbf{x}_t^i =
\begin{bmatrix}(\mathbf{p}_t^i)^\top & (\mathbf{v}_t^i)^\top\end{bmatrix}^{\top},
\qquad \mathbf{\Sigma}_t^i = \operatorname{Cov}(\mathbf{x}_t^i).
\]

对象三维观测由 bbox 内稳健深度统计得到相机坐标点 \(\mathbf{z}_{c,t}^j\)，再变换到世界坐标：

\[
\mathbf{z}_{w,t}^j = \mathbf{T}_{wc,t}\,\mathbf{z}_{c,t}^j.
\]

### 与论文1 MapPoint Dynamic Evidence 的区别

论文1状态附着于单个 MapPoint，核心变量为动态分数和最后更新帧；它根据点是否落入动态 bbox 累积或衰减，并在当前 Frame 中抑制超过阈值的点。

论文2状态附着于跨帧对象，联合语义、三维位置、速度、预测误差、关联点集合和生命周期。MapPoint 仅作为对象观测和地图关联证据。论文1点级分数可作为输入特征 \(e_{mp,t}^i\)，但不直接等同于对象动态概率，也不决定对象生命周期。

## 3. Object Association

当前时刻 YOLO 检测集合：

\[
\mathcal{D}_t = \left\{d_t^j\right\}_{j=1}^{N_t},
\qquad d_t^j = \{b_t^j, c_t^j, s_t^j,
\mathbf{z}_{w,t}^j, \mathbf{R}_t^j\},
\]

其中 \(b_t^j\) 为 bbox，\(c_t^j\) 为类别，\(s_t^j\) 为检测置信度，\(\mathbf{z}_{w,t}^j\) 为三维位置，\(\mathbf{R}_t^j\) 为观测协方差。历史对象由 MotionEstimator 预测出 bbox、三维位置与位置协方差。

语义类别代价：

\[
C_{sem}(i,j) =
\begin{cases}
0, & c^i = c_t^j,\\
1 - \pi(c_t^j|i), & \text{允许兼容类别时},\\
\infty, & \text{类别门控失败时}.
\end{cases}
\]

二维 bbox 和图像中心代价：

\[
C_{iou}(i,j)=1-\operatorname{IoU}(\widehat b_t^i,b_t^j),
\qquad
C_{2d}(i,j)=\frac{\|\widehat{\mathbf u}_t^i-\mathbf u_t^j\|_2}
{\sqrt{W^2+H^2}}.
\]

三维位置一致性采用马氏距离：

\[
C_{3d}(i,j)=\sqrt{
(\mathbf z_{w,t}^j-\widehat{\mathbf p}_t^i)^\top
(\widehat{\mathbf\Sigma}_{p,t}^i+\mathbf R_t^j)^{-1}
(\mathbf z_{w,t}^j-\widehat{\mathbf p}_t^i)}.
\]

对通过类别、时间间隔和空间距离门控的候选对，定义匹配代价：

\[
C_{ij}=w_{sem}C_{sem}+w_{iou}C_{iou}
+w_{2d}C_{2d}+w_{3d}\bar C_{3d},
\]

\[
w_{sem}+w_{iou}+w_{2d}+w_{3d}=1,\qquad w_k\ge0.
\]

缺失深度时移除三维项并重新归一化其余权重，不能把缺失深度当作零距离。类别不兼容、时间间隔过大或 \(C_{3d}>\tau_{3d}\) 的候选置为无穷大；对有限代价矩阵执行一对一分配，仅接受 \(C_{ij}<\tau_{assoc}\) 的匹配。

跨帧 ID 规则：已匹配检测继承 object ID；未匹配检测先建立候选轨迹，连续确认后分配新 ID；未匹配轨迹在有限窗口内进入 Lost 并保留 ID；重新出现时同时通过类别、三维预测、IoU/图像位置和时间门控才恢复原 ID。Association Manager 保存每次匹配代价、置信度和冲突，ObjectState 的关联列表仅为快照。

## 4. Spatio-temporal Dynamic Evidence

对象级证据包括：运动显著性 \(e_{m,t}^i\)、连续运动一致性 \(e_{c,t}^i\) 和语义稳定证据 \(e_{s,t}^i\)。

静态世界假设下的三维残差：

\[
r_{s,t}^i=\sqrt{
(\mathbf z_{w,t}^i-\mathbf p_{t-1}^i)^\top
(\mathbf\Sigma_{p,t-1}^i+\mathbf R_t^i)^{-1}
(\mathbf z_{w,t}^i-\mathbf p_{t-1}^i)}.
\]

运动证据映射：

\[
e_{m,t}^i=\sigma(k_m(r_{s,t}^i-\tau_m)),
\qquad \sigma(x)=\frac{1}{1+e^{-x}}.
\]

运动一致性结合方向和速度稳定性：

\[
e_{c,t}^i=
\eta_d\frac{1+\cos(\mathbf v_t^i,\mathbf v_{t-1}^i)}{2}
+\eta_v\exp\left(-\frac{\|\mathbf v_t^i-\mathbf v_{t-1}^i\|^2}{2\sigma_v^2}\right),
\]

其中 \(\eta_d+\eta_v=1\)。速度低于最小可观测阈值时不使用方向项，避免零速度方向不稳定。

最近 \(L\) 帧类别一致率及语义证据：

\[
\kappa_{s,t}^i=\frac{1}{L}\sum_{\ell=0}^{L-1}
\mathbb I(c_{t-\ell}^i=\widehat c_t^i),
\qquad e_{s,t}^i=\kappa_{s,t}^i\pi_D(\widehat c_t^i).
\]

语义先验只能调节证据，不能单独把对象判为动态。

使用 log-odds 更新动态概率：

\[
L_{t-1}^i=\log\frac{P_{D,t-1}^i}{1-P_{D,t-1}^i},
\qquad \rho_t^i=\exp(-\lambda\Delta t_i).
\]

\[
L_t^i=\rho_t^iL_{t-1}^i
+\alpha_m(2e_{m,t}^i-1)
+\alpha_c(2e_{c,t}^i-1)g_v^i
+\alpha_s(2e_{s,t}^i-1)
+\alpha_p(2e_{mp,t}^i-1),
\]

\[
P_{D,t}^i=\sigma(L_t^i).
\]

\(g_v^i\) 为速度可观测性门控；\(e_{mp,t}^i\) 是论文1点级动态证据在对象关联点上的稳健汇总，是可选项且权重 \(\alpha_p\) 必须通过消融实验验证。无新观测时只执行衰减 \(L_t^i=\rho_t^iL_{t-1}^i\)，使置信度逐渐回到中性。

采用双阈值避免状态抖动：

\[
P_{D,t}^i\ge\tau_{high}\Rightarrow Dynamic,
\qquad P_{D,t}^i\le\tau_{low}\Rightarrow Static,
\qquad \tau_{low}<\tau_{high}.
\]

中间区域保持 PotentialDynamic 或沿用上一稳定状态。论文1执行“点命中—分数累积—当前帧抑制”；论文2执行“相机运动补偿—对象关联—多证据概率更新—生命周期与地图恢复”。

## 5. Motion Estimation

MotionEstimator 输入连续对象状态和当前三维观测，输出速度、运动方向、预测位置及不确定性。

基础两帧速度：

\[
\widetilde{\mathbf v}_t^i=
\frac{\mathbf p_t^i-\mathbf p_{t-1}^i}{t_t-t_{t-1}}.
\]

时间窗加权速度：

\[
\mathbf v_t^i=
\frac{\sum_{k=1}^{K}\omega_k
(\mathbf p_{t-k+1}^i-\mathbf p_{t-k}^i)/(t_{t-k+1}-t_{t-k})}
{\sum_{k=1}^{K}\omega_k},\qquad \omega_k\ge0.
\]

运动方向与常速度预测：

\[
\mathbf d_t^i=\frac{\mathbf v_t^i}{\|\mathbf v_t^i\|},
\quad \|\mathbf v_t^i\|>v_{min},
\qquad
\widehat{\mathbf p}_{t+1|t}^i=\mathbf p_t^i+\mathbf v_t^i\Delta t.
\]

接口同时输出预测协方差 \(\widehat{\mathbf\Sigma}_{p,t+1|t}^i\)。具体滤波器留待实现与实验选择。

预测残差满足以下门控才视为运动一致：

\[
(\mathbf r_{pred,t}^i)^\top
(\widehat{\mathbf\Sigma}_{p,t|t-1}^i+\mathbf R_t^i)^{-1}
\mathbf r_{pred,t}^i<\chi^2_{3,\gamma},
\quad
\mathbf r_{pred,t}^i=\mathbf z_{w,t}^i-\widehat{\mathbf p}_{t|t-1}^i.
\]

同时检查速度方向、幅值变化和时间间隔。门控失败不直接等同于动态：它也可能来自错误关联、深度异常或模型失效，应先降低关联置信度或触发轨迹重初始化。

## 6. Dynamic Map Management

对象生命周期：

```text
Static
  ↓ sustained ambiguous/motion evidence
Potential Dynamic
  ↓ P_D ≥ τ_high for confirmation window
Dynamic
  ↓ missing observations
Lost
  ↓ gated re-association
Recovered
  ├─→ Dynamic
  ├─→ Potential Dynamic
  └─→ Static
```

- 新对象先进入 PotentialDynamic，经过最小确认帧数后进入 Static 或 Dynamic。
- Static 只有连续运动证据满足条件才转为 PotentialDynamic。
- Dynamic 在 \(P_D\le\tau_{low}\) 且持续静止时先回到 PotentialDynamic，再经验证进入 Static。
- 活跃对象连续未匹配可进入 Lost；超过最大恢复时间后进入 Retired 归档状态。Retired 不删除论文1地图数据。
- Recovered 是短暂验证状态，恢复原 ID 后按新证据进入稳定状态。

DynamicMapManager 输出三类地图视图：

1. **Stable**：未关联动态对象，或通过多帧静态验证的地图点。
2. **Quarantined**：关联 PotentialDynamic/Dynamic 对象的点；暂不进入稳定视图，但不从论文1 Map 删除。
3. **RecoveryCandidate**：动态对象离开或关联失效后，等待背景重验证的点/区域。

动态对象关联点执行逻辑隔离而非整框硬删除。MapPoint 出现 bad/replaced 时，独立关联表清理或迁移 ID，并保留审计记录。

### 动态目标离开后的静态地图恢复

恢复采用“保留—重观测—验证—激活”：

1. 保留动态对象最后占据区域、关联点和背景恢复候选，不永久删除底层 MapPoint。
2. 对象离开后，从后续 RGB-D 帧收集该区域的深度、重投影和静态特征观测。
3. 候选背景点通过多帧重投影误差、深度一致性、相机运动补偿和多关键帧观测检验。
4. 连续 \(N_{recover}\) 帧满足静态条件后逐步提高恢复置信度，超过 \(\tau_{recover}\) 才加入 StableMapView。
5. 旧点与新背景不一致时继续隔离，允许 LocalMapping 新生成的稳定点替代其地图作用；ObjectDynamic 不直接写入或删除论文1 MapPoint。

稳定地图视图定义为：

\[
\mathcal M_{stable,t}=\left\{m_k\in\mathcal M\mid
P_D(o(m_k))<\tau_{map}\land q_{assoc}(m_k)>\tau_a\right\}
\cup\mathcal M_{recovered,t}.
\]

未关联对象且通过常规 SLAM 质量检查的点默认属于稳定候选。

## 7. Difference From Paper1

| 内容 | 论文1 | 论文2 |
|---|---|---|
| 对象单位 | MapPoint | Object |
| 状态身份 | 点 ID，无跨帧对象轨迹 | 稳定 object ID 与生命周期 |
| 动态判断 | 点级 bbox 命中和阈值判断 | 对象级语义、三维运动、预测残差和时间一致性融合 |
| 时间模型 | Dynamic Evidence 分数累积/衰减 | 带时间戳、不确定性和运动预测的时空概率模型 |
| 运动表达 | 无对象速度与轨迹 | 世界坐标速度、方向、预测位置和运动一致性 |
| 关联机制 | 当前帧特征/MapPoint 与 bbox 区域关系 | 跨帧类别、IoU、二维位置、三维位置与预测联合关联 |
| 地图处理 | 当前帧 MapPoint 抑制 | Stable/Quarantined/RecoveryCandidate 管理与恢复 |
| 遮挡/漏检 | 无显式对象恢复状态 | Lost–Recovered 生命周期和门控重关联 |
| MapPoint 关系 | 动态状态保存在 MapPoint | 独立 Association Manager 管理对象–点–关键帧关系 |
| 论文1复用 | 本体算法 | 冻结基线；点级分数仅作可选辅助证据 |

## 8. Algorithm Pipeline

输入：RGB-D frame、时间戳、相机标定、YOLO detections 和只读 SLAM 快照。

输出：稳定动态语义地图、对象状态/轨迹，以及隔离和恢复候选视图。

```text
Algorithm ObjectLevelSpatioTemporalDynamicSLAM
Input: RGB image I_t, depth image D_t, timestamp t, detections Det_t,
       SLAM snapshot F_t, previous object states S_(t-1)
Output: stable map M_stable,t, updated object states S_t

1:  O_t ← BuildObjectObservations(Det_t, D_t, K, F_t.camera_pose)
2:  Pred_t ← MotionEstimator.PredictAll(S_(t-1), t)
3:  C_t ← BuildAssociationCost(Pred_t, O_t,
                               semantic, IoU, image distance, 3D distance)
4:  A_t, U_obs, U_track ← GatedOneToOneAssignment(C_t)
5:  for each matched pair (object_i, observation_j) in A_t do
6:      motion_i ← MotionEstimator.Estimate(history_i, observation_j)
7:      points_i ← SelectMapPointSnapshots(F_t, observation_j.region)
8:      assoc_i ← AssociationManager.Update(object_i, points_i, F_t)
9:      evidence_i ← ComputeSpatioTemporalEvidence(
                        motion_i, semantic_history_i, assoc_i)
10:     P_D,i ← DecayedLogOddsUpdate(P_D,i, evidence_i, Δt_i)
11:     S_t^i ← UpdateObjectState(S_(t-1)^i, observation_j,
                                  motion_i, P_D,i, assoc_i)
12: end for
13: for each unmatched observation in U_obs do
14:     CreatePotentialObjectTrack(observation)
15: end for
16: for each unmatched track in U_track do
17:     DecayDynamicProbability(track, Δt)
18:     PredictOrMarkLost(track)
19: end for
20: Recover eligible Lost objects using semantic + 3D + motion gates
21: Apply lifecycle transitions with hysteresis and confirmation windows
22: DynamicMapManager.QuarantineAssociations(dynamic objects)
23: DynamicMapManager.ValidateRecoveryCandidates(new RGB-D observations)
24: M_stable,t ← DynamicMapManager.GetStableMapView()
25: Use M_stable,t as conceptual stable constraints for SLAM optimization
26: Return M_stable,t and S_t
```

第 25 步是论文2目标接口，不表示当前冻结 ORB-SLAM2 已接入该视图。在线集成属于后续阶段，必须保持可关闭、可回退并单独验证。

## Design Validation Plan

- 消融三维关联、IoU 和语义项，评估 ID switch。
- 对比点级辅助证据 \(e_{mp}\) 开/关，验证其对象级增益。
- 分析时间衰减、双阈值和确认窗口对状态抖动的影响。
- 对比无恢复、立即恢复和多帧验证恢复对稳定地图精度的影响。
- 分析 bbox 深度统计、对象位置噪声和相机位姿误差的敏感性。
