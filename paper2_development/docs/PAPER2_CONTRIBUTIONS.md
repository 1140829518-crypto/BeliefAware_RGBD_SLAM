# Paper2 Contributions

论文方向：**Object-level Spatio-temporal Dynamic RGB-D SLAM**。

以下贡献建立在论文1冻结的 MapPoint-level Dynamic Evidence 基线上，重点转向对象级运动建模、跨帧关联和地图恢复，避免重复论文1的点级证据累积与当前帧抑制。

## Contribution 1: Object-level spatio-temporal state and association model

提出面向动态 RGB-D SLAM 的对象级时空状态表示，以稳定 object ID 联合建模语义类别、三维位置、对象位姿、速度、动态概率、关联 MapPoint 和观测 KeyFrame。设计融合语义兼容性、二维 IoU、图像空间距离、三维马氏距离和运动预测的一对一关联代价，在相机运动补偿后的世界坐标系中保持跨帧对象身份，并通过 Lost–Recovered 门控重关联处理短时遮挡和漏检。

与论文1的区别：论文1以单个 MapPoint 为动态证据单位，没有跨帧对象身份、速度或对象轨迹；本贡献的核心是对象状态与跨帧数据关联，而非复用点级阈值判断。

## Contribution 2: Object-level spatio-temporal dynamic evidence fusion

提出对象级时空动态概率模型，在 log-odds 空间融合静态世界假设下的三维运动残差、连续速度方向/幅值一致性、语义类别稳定性和可选的点级辅助证据，并按真实时间间隔执行指数遗忘。通过不确定性门控、双阈值滞回和连续确认窗口，区分真实对象运动、相机运动、深度噪声与错误关联。

与论文1的区别：论文1主要根据 MapPoint 的动态框命中进行分数加权与衰减；本贡献以对象轨迹为单位，显式引入世界坐标运动估计、预测一致性、语义稳定性和概率不确定性。

## Contribution 3: Recoverable dynamic semantic map management

提出不破坏底层 ORB-SLAM2 地图所有权的可恢复对象地图管理机制。独立 Association Manager 维护 Object–MapPoint–KeyFrame 关系，将地图划分为 Stable、Quarantined 和 RecoveryCandidate 视图；动态对象关联点先逻辑隔离而非永久删除。对象离开后，通过多帧重投影、深度一致性、相机运动补偿和关键帧观测验证逐步恢复背景地图，并利用 Static–PotentialDynamic–Dynamic–Lost–Recovered 生命周期抑制状态抖动。

与论文1的区别：论文1侧重超过动态阈值后的当前帧点抑制；本贡献进一步解决动态对象生命周期、遮挡重关联、地图隔离以及动态目标离开后的静态地图恢复问题。

## Concise Summary

1. 对象级状态与跨帧多模态关联。
2. 融合运动、时间和语义一致性的对象级动态概率模型。
3. 支持隔离、重关联和背景恢复的可恢复动态语义地图管理。
