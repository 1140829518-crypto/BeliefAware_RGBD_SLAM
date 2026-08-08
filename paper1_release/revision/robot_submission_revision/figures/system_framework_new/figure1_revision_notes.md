# Figure 1 Revision Notes

## 修改内容

1. 删除顶部 `Processing flow` 图例，减少论文双栏排版中的纵向空间占用。
2. 重新绘制为左到右流程：`RGB-D Input -> ORB-SLAM2 RGB-D Frontend -> Dynamic Evidence Update -> Backend Optimization -> Object-level Semantic Map -> Final Outputs`。
3. 将原 `Motion Consistency Analysis` 修改为 `Dynamic Evidence Update`，内部改为 `Semantic Observation / Temporal Decay / Evidence Accumulation`。
4. 将核心模块修改为 `Temporal Dynamic Evidence Model`，并突出显示 `Core Contribution`。内部包含 `Dynamic Evidence Score / λ Decay / γ Increment / θ Threshold / Dynamic Point Suppression`。
5. `Object-level Semantic Map` 增加 `Object Category / 3D Position / ID Association / Dynamic State`，突出动态状态管理。
6. `Final Outputs` 统一为 `Camera Trajectory / Feature Map / Dynamic Objects / Semantic Map`。
7. 颜色控制为三类低饱和度颜色：蓝色表示 ORB-SLAM2 RGB-D 流程，橙色表示语义检测流程，绿色表示动态证据建模流程。

## 与论文方法章节对应关系

- `ORB-SLAM2 RGB-D Frontend` 对应基础 RGB-D SLAM 的特征提取、匹配和位姿跟踪。
- `YOLOv5 Semantic Detection` 对应语义检测输入，提供类别、置信度和语义掩膜。
- `Dynamic Evidence Update` 对应当前实现中的语义观测命中、动态证据衰减和证据累积过程。
- `Temporal Dynamic Evidence Model` 对应动态证据分数 `s_t` 的跨帧衰减累积，参数含义与代码中的 `λ` 衰减、`γ` 增量、`θ` 阈值一致。
- `Object-level Semantic Map` 对应对象级语义地图和动态状态管理表达。

## 是否保持代码实现一致

保持一致。该图不再使用 `Motion Consistency Analysis` 或 `Dynamic Probability Model` 等容易被理解为运动概率融合/固定窗口模型的表述，而是改为与当前代码审计一致的动态证据衰减累积模型。图中未增加代码中不存在的新算法模块。

## 字体说明

论文要求推荐 Times New Roman 或 Arial。本机未安装 Times New Roman/Arial，绘图实际使用系统可用等效字体 `Liberation Serif`。图中文字字号不小于 8 pt，并按双栏插图可读性放大。

## 输出文件

- `figure1_system_framework.pdf`
- `figure1_system_framework.svg`
- `figure1_system_framework.eps`
- `figure1_system_framework.png`
