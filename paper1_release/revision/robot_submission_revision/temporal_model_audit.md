# 时间一致性模型静态审计报告

审计对象：

- 项目根目录：`/home/djn/123/ORB_SLAM2_AddSemantic`
- 论文修订目录：`/home/djn/123/ORB_SLAM2_AddSemantic/robot_submission_revision`

审计方式：仅做静态代码、配置、脚本和结果目录检查；未修改源码；未重新运行 SLAM 实验；未修改任何实验结果。

## 1. 最终分类

**Final Classification: D：代码实现与论文描述均不完全一致，需要重新定义。**

理由如下：

1. 主算法中确实存在一个由 `ORB_SLAM2_DYNAMIC_LAMBDA` 控制的指数衰减系数，默认值为普通动态类别 `0.95`、person 类 `0.85`。该系数参与 `MapPoint` 的语义动态分数跨帧累积，并最终影响匹配和 Tracking 中的动态点抑制。
2. 主算法中未发现固定长度时间窗口 `N` 参与动态概率计算。实验运行配置中也明确写明 `window_size: not configurable in current binary`。
3. 论文方法章节写有 `p_t^o=\alpha p_t^s+(1-\alpha)p_t^m` 和 `p_t=\lambda p_{t-1}+(1-\lambda)p_t^o`。但代码中未发现语义概率 `p_t^s`、运动概率 `p_t^m` 的显式融合权重 `alpha`，也未发现运动一致性概率进入主动态状态判定的调用链。
4. 论文第 4.5 节的 `N=1,3,5,10,15` 时间窗口敏感性结果来自脚本按已有结果生成的派生曲线，不是通过改变主程序固定窗口参数得到的真实 SLAM 运行结果。

## 2. 关键变量审计

| 变量/概念 | 文件路径 | 行号 | 默认值 | 是否可配置 | 参与计算 | 是否影响最终动态状态 |
|---|---|---:|---|---|---|---|
| `ORB_SLAM2_SEMANTIC_MODE` | `include/SemanticConfig.h` | 18-31 | 未设置时为 `2` | 是，环境变量 | 控制语义模式：0/1/2 | 是。`Mode() >= 2` 时启用动态累积 |
| `UseDynamicAccumulation()` | `include/SemanticConfig.h` | 39-42 | `Mode() >= 2` | 间接由 `ORB_SLAM2_SEMANTIC_MODE` 控制 | 决定是否启用语义动态分数累积 | 是 |
| `kDynamicScoreDecay` | `include/SemanticConfig.h` | 54 | `0.95` | 可被 `ORB_SLAM2_DYNAMIC_LAMBDA` 覆盖 | 普通动态类别的动态分数衰减系数 | 是 |
| `kPersonDynamicScoreDecay` | `include/SemanticConfig.h` | 60 | `0.85` | 可被 `ORB_SLAM2_DYNAMIC_LAMBDA` 覆盖 | person 类动态分数衰减系数 | 是 |
| `ORB_SLAM2_DYNAMIC_LAMBDA` | `include/SemanticConfig.h` | 90-98 | 普通类 `0.95`，person 类 `0.85` | 是，环境变量 | 覆盖动态分数衰减系数，范围裁剪到 `[0,0.999]` | 是 |
| `kDynamicScoreIncrement` | `include/SemanticConfig.h` | 53 | `1.0` | 否 | 动态框命中时普通类加分 | 是 |
| `kPersonDynamicScoreIncrement` | `include/SemanticConfig.h` | 59 | `3.0` | 否 | 动态框命中时 person 类加分 | 是 |
| `kDynamicScoreThreshold` | `include/SemanticConfig.h` | 52 | `3.0` | 否 | 普通类别动态抑制阈值 | 是 |
| `kPersonDynamicScoreThreshold` | `include/SemanticConfig.h` | 58 | `1.0` | 否 | person 类动态抑制阈值 | 是 |
| `mfSemanticDynamicScore` | `include/MapPoint.h` | 333-335 | `0.0` | 否 | 保存每个 `MapPoint` 的跨帧语义动态分数 | 是 |
| `mnSemanticDynamicLastFrame` | `include/MapPoint.h` | 333-335 | `0` | 否 | 保存上次更新帧号，用于计算帧间隔 | 是 |
| `alpha` | `src/SemanticObject.cc` | 70-76 | `1/(mnObservedCount+1)` | 否 | 仅用于对象级语义地图中心位置滑动均值更新 | 否，不是语义/运动概率融合权重 |
| `tau` | `src/PnPsolver.cc` | 1445-1484 | 局部临时变量 | 否 | PnP 求解内部数学变量 | 否，不是动态判定阈值 |
| `windowSize` | `include/ORBmatcher.h`, `src/ORBmatcher.cc` | `include/ORBmatcher.h:166-169`, `src/ORBmatcher.cc:585-620` | 初始化搜索窗口默认 `10` | 函数参数 | ORB 初始化/匹配搜索窗口 | 否，不是时间一致性窗口 |
| `mlpTemporalPoints` | `include/Tracking.h`, `src/Tracking.cc` | `include/Tracking.h:486`, `src/Tracking.cc:767-779` | 空列表 | 否 | ORB-SLAM2 临时 MapPoint 管理 | 否，不是动态概率历史缓存 |

## 3. 证据表

| 证据 | 文件路径 | 行号 | 代码/配置内容 | 说明 |
|------|----------|------:|---------------|------|
| 语义模式默认启用动态累积 | `include/SemanticConfig.h` | 18-31 | `if(!env) return 2;` | 未设置环境变量时默认 `Mode=2` |
| 动态累积开关 | `include/SemanticConfig.h` | 39-42 | `return Mode() >= 2;` | 只有模式 2 才启用时间累积 |
| lambda-like 衰减默认值 | `include/SemanticConfig.h` | 52-60 | `kDynamicScoreDecay = 0.95f`, `kPersonDynamicScoreDecay = 0.85f` | 代码中的 lambda 实际是动态分数衰减系数 |
| lambda 可由环境变量覆盖 | `include/SemanticConfig.h` | 90-98 | `EnvFloat("ORB_SLAM2_DYNAMIC_LAMBDA", defaultDecay)` | 可配置，但不是 yaml 参数 |
| 动态分数状态变量 | `include/MapPoint.h` | 333-335 | `mfSemanticDynamicScore`, `mnSemanticDynamicLastFrame` | 每个 MapPoint 保存一个累计分数和上次更新帧 |
| 指数衰减/累积实现 | `src/MapPoint.cc` | 383-392 | `score *= pow(decay, frameGap); if(hit) score += inc; else score *= decay;` | 等价于指数记忆的分数更新，但不是论文中的归一化概率递推公式 |
| 动态阈值判定 | `src/MapPoint.cc` | 407-413 | `score >= DynamicScoreThresholdForClass(classId)` | 该阈值是最终动态抑制条件之一 |
| 匹配前动态点跳过 | `src/ORBmatcher.cc` | 105-116 | 更新分数后 `continue` | 超阈值 MapPoint 不参与后续投影匹配 |
| 运动模型匹配阶段跳过 | `src/ORBmatcher.cc` | 1784-1795 | 更新分数后 `continue` | 动态分数影响跟踪匹配 |
| 局部地图匹配阶段跳过 | `src/ORBmatcher.cc` | 1974-1985 | 更新分数后 `continue` | 动态分数影响局部地图匹配 |
| Tracking 侧最终剔除 | `src/Tracking.cc` | 1587-1630 | `mvbOutlier[i] = true; mvpMapPoints[i] = NULL;` | 超阈值 MapPoint 被设为外点并移除 |
| 位姿优化后调用动态剔除 | `src/Tracking.cc` | 1272-1276 | `PoseOptimization(); CullSemanticDynamicMapPoints();` | 参考关键帧跟踪后执行剔除 |
| 位姿优化后调用动态剔除 | `src/Tracking.cc` | 1457-1462 | `PoseOptimization(); CullSemanticDynamicMapPoints();` | 运动模型跟踪后执行剔除 |
| 局部地图优化后调用动态剔除 | `src/Tracking.cc` | 1525-1531 | `PoseOptimization(); CullSemanticDynamicMapPoints();` | 局部地图跟踪后执行剔除 |
| 统计日志不包含动态概率序列 | `src/Tracking.cc` | 1713-1723 | 输出 `dynamic_keypoints`, `dynamic_map_points`, `suppressed_map_points`, `dynamic_objects`, `static_objects`, `total_objects` | 未输出每目标 `p_t` 或历史窗口 |
| 消融脚本不设置 lambda | `experiment_new/independent_ablation_v3/evaluation/scripts/run_independent_ablation.py` | 305-310 | 只设置 `ORB_SLAM2_SEMANTIC_MODE`, `ORB_SLAM2_OBJECT_MAP`, 输出路径等 | 45 次独立消融未显式改变 lambda |
| 消融运行配置声明窗口不可配置 | `experiment_new/independent_ablation_v3/evaluation/scripts/run_independent_ablation.py` | 323-324 | `"window_size": "not configurable in current binary"` | 明确说明主程序没有可配置窗口 |
| Full Model 配置 | `experiment_new/independent_ablation_v3/runs/full_model/fr3_walking_xyz/run_02/run_config.json` | 6-11 | `semantic_mode=2`, `object_map_enabled=true`, `window_size not configurable`, `lambda default...` | Full Model 启用动态累积和对象地图，但未设置窗口 |
| lambda 真实运行入口 | `scripts/run_tum_rgbd_experiment.py` | 97, 115-116 | `--dynamic-lambda`; `env["ORB_SLAM2_DYNAMIC_LAMBDA"] = ...` | 存在真实改变 lambda 的运行入口 |
| lambda 分析默认是离线估计 | `scripts/analyze_lambda_sensitivity.py` | 4-10, 119-143, 326-338 | 默认复用旧结果并插值；只有 `--run-slam` 才跑 SLAM | 当前 `lambda_analysis.csv` 不能直接证明真实 lambda 多配置运行 |
| 时间窗口结果由公式生成 | `experiment_new/scripts/generate_experiment_new.py` | 376-402 | 使用 `stability_gain`, `delay_penalty`, `fps_penalty` 生成 `N` 表 | `N=1,3,5,10,15` 不是主程序窗口参数真实运行 |
| 时间窗口图只读取派生 CSV | `experiment_new/scripts/prepare_paper_figures.py` | 153-169 | 读取 `time_window_sensitivity.csv` 作图 | 后处理制图，不改变算法输出 |
| 论文写入固定时间窗口 N | `paper_latex/sections/experiment.tex` | 58-69 | `N=1,3,5,10,15`，并分析窗口影响 | 与主程序“窗口不可配置”矛盾 |
| 论文方法写 alpha 融合 | `paper_latex/sections/method.tex` | 19-27 | `p_t^o=\alpha p_t^s+(1-\alpha)p_t^m`; `p_t=\lambda...` | 未在主代码中找到对应 alpha/运动概率融合实现 |

## 4. 对公式和调用链的判断

### 4.1 是否存在 `p_t = lambda * p_{t-1} + (1 - lambda) * p_t^o`

未发现完全等价实现。

代码中的实际形式更接近：

```text
score_t = score_{last} * decay^(frameGap)
if dynamic_hit:
    score_t = score_t + increment
else:
    score_t = score_t * decay
dynamic = score_t >= threshold
```

其中 `decay` 由 `DynamicScoreDecayForClass(classId)` 返回，可被 `ORB_SLAM2_DYNAMIC_LAMBDA` 覆盖。因此可以称为“指数衰减的动态证据累积分数”，但不应严格称为“归一化动态概率递推”。

### 4.2 是否存在固定长度历史缓存

未发现主算法中用于时间一致性动态概率计算的 `deque`、`queue`、`vector history`、`pop_front`、`max_history`、`window_size` 或 `recent N frames`。

发现的相关但不属于时间一致性窗口的结构：

- `include/Tracking.h:373-375` 中的 `queue<vector<Object>>` 等为注释代码，未启用；
- `include/Tracking.h:486` 的 `mlpTemporalPoints` 是 ORB-SLAM2 临时地图点列表，与动态概率历史窗口无关；
- `ORBmatcher` 中的 `windowSize` 和 `Search in a window` 是特征匹配搜索窗口，不是时间窗口。

### 4.3 如果存在窗口 N，它保存什么、是否影响主程序输出

未发现主算法中的窗口 `N`。因此：

- 不存在保存动态概率/检测结果/目标状态/特征状态/目标 ID 历史的固定窗口；
- `N` 不参与动态概率计算；
- `N` 不与 lambda 同时作用；
- 改变论文或后处理脚本中的 `N` 不会改变当前 C++ 主程序输出。

### 4.4 第 3.5 节 `N=1,3,5,10,15` 来源

`N=1,3,5,10,15` 出现在论文和后处理结果中，但未在主程序配置或真实运行目录中发现对应运行证据。

具体判断：

- `experiment_new/results/time_window_sensitivity.csv` 存在 `N=1,3,5,10,15` 数值；
- 其生成脚本 `experiment_new/scripts/generate_experiment_new.py:376-402` 根据已有 Ours 结果乘以 `stability_gain`、`delay_penalty`、`fps_penalty` 生成表格；
- 未发现 `N1/N3/N5/N10/N15` 的运行目录；
- `independent_ablation_v3` 的 `run_config.json` 明确写 `window_size: not configurable in current binary`；
- 因此这些结果应判定为派生/模拟敏感性数据，不是固定时间窗口主算法实验。

### 4.5 lambda 是否真实存在

lambda-like 参数真实存在，但含义是动态分数衰减 `decay`：

- 默认普通类别：`0.95`
- 默认 person 类：`0.85`
- 可由环境变量 `ORB_SLAM2_DYNAMIC_LAMBDA` 覆盖并裁剪到 `[0,0.999]`
- 在独立消融 `v3` 脚本中未显式设置，因此使用默认值；
- 项目存在真实运行入口 `scripts/run_tum_rgbd_experiment.py --dynamic-lambda`；
- `scripts/analyze_lambda_sensitivity.py` 默认不真实跑 SLAM，而是离线插值；只有传入 `--run-slam` 才会真实运行多 lambda 配置。

当前未发现 `lambda_0.1`、`lambda_0.3`、`lambda_0.5`、`lambda_0.7`、`lambda_0.8`、`lambda_0.9`、`lambda_0.95` 对应真实运行目录。因此现有 `lambda_analysis.csv` 不应作为真实多 lambda SLAM 实验直接写入论文，除非补跑并保存对应配置与日志。

## 5. alpha 和 tau 审计

### alpha

未发现论文中“语义与运动概率融合权重”的 `alpha` 在主算法动态判定链路中实现。

唯一相关命中是 `src/SemanticObject.cc:70-76`：

```text
alpha = 1.0 / (mnObservedCount + 1)
mWorldCenter = (1.0 - alpha) * mWorldCenter + alpha * worldCenter
```

该 `alpha` 是对象级语义地图中 3D 中心位置的增量均值更新权重，不是 `p_t^s` 与 `p_t^m` 的融合权重，不影响动态状态阈值判定。

### tau

未发现名为 `tau` 的动态阈值参数。`src/PnPsolver.cc` 中的 `tau` 是 PnP 求解内部临时数学变量，与动态目标判别无关。

真实动态阈值为：

- `kDynamicScoreThreshold = 3.0`
- `kPersonDynamicScoreThreshold = 1.0`

二者位于 `include/SemanticConfig.h:52,58`，不是通过配置文件设置。

## 6. 论文与代码不一致位置

| 论文/材料位置 | 当前描述 | 审计判断 | 风险 |
|---|---|---|---|
| `paper_latex/sections/method.tex:19-27` | 语义概率和运动概率通过 `alpha` 融合，再用 `lambda` 做概率递推 | 代码未实现该 `alpha` 融合，也未发现运动概率 `p_t^m` 进入判定链 | 高 |
| `paper_latex/sections/method.tex:29-35` | 根据动态概率定义权重 `w_i=1-p_i` 并进入优化目标 | 代码实际是超过阈值后剔除/置 outlier，不是连续权重进入优化目标 | 高 |
| `paper_latex/sections/experiment.tex:58-69` | 时间窗口 `N=1,3,5,10,15` 敏感性实验 | 主程序无可配置窗口，现有 N 结果由后处理脚本生成 | 高 |
| `experiment_new/final_submission/final_experiment_section.md:52-56` | N 会影响动态概率累积范围，并据此分析 ATE/Smoothness/FPS | 缺少对应真实运行配置与日志 | 高 |
| `paper_draft/4_method.md:7,13` | 运动一致性概率参与当前帧动态观测 | 未在主代码中发现运动概率计算及融合到动态状态判定 | 中-高 |
| `paper_latex/sections/conclusion.tex:5` | 参数敏感性实验说明适当增大时间窗口有助于提高轨迹平滑性 | 若保留为真实实验结论，会被审稿人质疑 | 高 |

## 7. 风险最低的修改方案

### 可以仅改文字的部分

1. 方法章节应把模型从“语义/运动概率融合 + 归一化概率递推 + 连续权重优化”改为“基于语义检测命中的 MapPoint 动态证据指数衰减累积”。
2. 将 `lambda` 的含义写成“动态证据衰减系数”而不是严格的概率递推权重。建议公式：

```text
s_t =
    lambda^(Delta t) s_{t-1} + gamma_c,  if hit dynamic semantic region
    lambda^(Delta t+1) s_{t-1},          otherwise

dynamic if s_t >= theta_c
```

其中 `gamma_c` 是类别相关增量，`theta_c` 是类别相关阈值。当前代码默认值：

| 参数 | 普通动态类别 | person 类 | 来源 |
|---|---:|---:|---|
| `gamma_c` | 1.0 | 3.0 | `kDynamicScoreIncrement`, `kPersonDynamicScoreIncrement` |
| `lambda` | 0.95 | 0.85 | `kDynamicScoreDecay`, `kPersonDynamicScoreDecay` |
| `theta_c` | 3.0 | 1.0 | `kDynamicScoreThreshold`, `kPersonDynamicScoreThreshold` |

3. 将“动态权重 `w_i=1-p_i` 进入优化目标”改为“当动态证据分数超过类别阈值时，在匹配和 Tracking 中抑制该 MapPoint”。这样与 `ORBmatcher.cc` 和 `Tracking.cc` 调用链一致。
4. 对 `alpha` 和 `tau` 的描述应删除或改为“本文实现中未显式设置语义/运动融合权重，动态判定阈值采用类别相关阈值 `theta_c`”。

### 必须重跑实验的部分

1. 如果论文继续保留“时间窗口敏感性分析 N=1,3,5,10,15”，必须先在主算法中实现可配置固定时间窗口，并对每个 N 真实运行 SLAM，保存对应 `run_config.json`、命令、日志和轨迹结果。不能只改图题。
2. 如果论文改为“lambda 敏感性分析”，必须使用 `scripts/analyze_lambda_sensitivity.py --run-slam` 或等价真实批处理方式，让 `ORB_SLAM2_DYNAMIC_LAMBDA` 对 `0.1,0.3,0.5,0.7,0.8,0.9,0.95` 分别真实生效，并保存每个 lambda 的运行目录、配置、日志和评估结果。当前默认生成的 `lambda_analysis.csv` 不能作为真实运行证据。
3. 如果论文继续声称“YOLO+运动一致性”参与本文方法，需要实现或定位运动一致性概率进入动态判定的代码路径，并用日志输出可追踪指标；否则应弱化为“语义动态证据累积”。

## 8. 对 A/B/C/D 的逐项判断

| 选项 | 判断 | 说明 |
|---|---|---|
| A. 同时使用指数递推权重 lambda 和固定时间窗口 N | 否 | 主算法有 lambda-like 衰减，但没有固定窗口 N |
| B. 仅使用指数递推权重 lambda，不使用固定窗口 N | 不完全成立 | 代码确实只使用 lambda-like 衰减，不使用 N；但论文描述还包含 alpha、运动概率融合、连续概率权重和窗口实验，与实现不一致 |
| C. 仅使用固定滑动窗口 N，不使用指数递推权重 lambda | 否 | 未发现主算法固定窗口；发现 lambda-like 衰减 |
| D. 代码实现与论文描述均不完全一致，需要重新定义 | 是 | 这是最符合审计证据的分类 |

## 9. 论文动作建议

建议优先采取“低风险修订”：

1. 删除或暂缓第 4.5 节“时间窗口参数敏感性分析”的真实实验表述和图表，除非补跑真实窗口实验。
2. 将第 3.3 节模型改写为“动态证据分数指数衰减累积模型”，用 `s_t` 而非 `p_t` 表示当前实现。
3. 参数表报告真实值：普通类 `lambda=0.95, gamma=1.0, theta=3.0`；person 类 `lambda=0.85, gamma=3.0, theta=1.0`。
4. 若需要参数敏感性实验，建议改为真实 `lambda` 敏感性分析，并补跑 `ORB_SLAM2_DYNAMIC_LAMBDA=0.1,0.3,0.5,0.7,0.8,0.9,0.95`。不能复用当前离线插值曲线。
5. 把“运动一致性概率融合”的表述改为“现有实现主要依据语义检测区域和跨帧动态证据累积进行动态点抑制”；若保留运动一致性，需要补充实际代码和实验日志。

## 10. 终端结论摘要

```text
Final Classification: D
Lambda Used: Yes
Window N Used: No
Alpha Value: Not implemented for semantic-motion probability fusion; unrelated object-map averaging alpha exists as 1/(mnObservedCount+1)
Lambda Value: default 0.95 for non-person dynamic classes, 0.85 for person; overridable by ORB_SLAM2_DYNAMIC_LAMBDA
Tau Value: No tau variable for dynamic decision; actual thresholds are 3.0 for non-person dynamic classes and 1.0 for person
Main Evidence: include/SemanticConfig.h:52-60,90-98; src/MapPoint.cc:383-413; src/ORBmatcher.cc:105-116,1784-1795,1974-1985; src/Tracking.cc:1587-1630; run_config.json records window_size not configurable
Paper Action Required: redefine the method as exponential dynamic-score accumulation, remove or rerun the window-N sensitivity experiment, and avoid claiming alpha/motion-probability fusion unless implemented and logged
```

