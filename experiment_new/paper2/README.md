# Paper2 Experiment Framework

该目录用于第二篇论文“Object-level Spatio-temporal Dynamic RGB-D SLAM”的实验管理。实验脚本只调用已经编译好的程序，并保存运行日志和程序输出的轨迹；不会修改源码、切换分支、改变编译宏或自动构建工程。

## Directory Layout

```text
experiment_new/paper2/
├── scripts/    # 运行入口
├── configs/    # 实验配置与清单说明
├── results/    # 本地运行结果（默认不提交）
└── evaluate/   # 评估说明及后续评估脚本
```

每次运行默认输出到：

```text
results/<experiment>/<run-name>/
├── run.log
├── CameraTrajectory.txt
├── KeyFrameTrajectory.txt
└── SemanticDynamicStatistics.txt
```

当对应模式启用对象语义地图时，还可能生成 `SemanticObjects.txt`。

## Prerequisites

运行脚本需要以下四个输入：

1. ORB vocabulary 文件；
2. RGB-D settings 文件；
3. TUM 格式序列目录；
4. RGB/Depth association 文件。

Paper1、Shadow 和 Active 实验若启用语义流水线，还要求 YOLO 检测服务已经由用户独立启动。脚本不会启动或管理检测服务。

通用调用形式：

```bash
experiment_new/paper2/scripts/run_<mode>.sh \
  Vocabulary/ORBvoc.txt \
  Examples/RGB-D/TUM3.yaml \
  /path/to/rgbd_sequence \
  /path/to/associate.txt \
  optional_run_name
```

可用环境变量：

- `PAPER2_RESULTS_ROOT`：覆盖默认结果根目录。
- `ORB_SLAM2_SOCKET_PATH`：语义检测 Unix socket。
- `PAPER2_BASELINE_BINARY`、`PAPER2_PAPER1_BINARY`、`PAPER2_SHADOW_BINARY`、`PAPER2_ACTIVE_BINARY`：为各实验指定预先编译的可执行文件。
- `PAPER2_SEMANTIC_MODE`：覆盖 Paper1/Shadow/Active 脚本默认使用的语义模式 `2`。

## 1. Baseline Experiment

入口：`scripts/run_baseline.sh`。

- 设置 `ORB_SLAM2_SEMANTIC_MODE=0`。
- 使用原始几何 Tracking 路径，不连接 YOLO socket。
- 用于报告 ORB-SLAM2 baseline 的轨迹和运行日志。

## 2. Paper1 Experiment

入口：`scripts/run_paper1.sh`。

- 默认设置 `ORB_SLAM2_SEMANTIC_MODE=2`。
- 使用论文1点级 Dynamic Evidence 与动态点抑制。
- 应使用论文1冻结构建或明确记录对应 commit 的二进制文件。

## 3. Shadow Experiment

入口：`scripts/run_shadow.sh`。

- 使用已启用 `ENABLE_OBJECT_DYNAMIC_SHADOW_MODE`、但关闭 Active Mode 的预编译程序。
- ObjectDynamic 只观察并输出状态，不反馈 Tracking。
- 重点记录 Object ID、动态状态日志、ATE/RPE 和运行时间开销。

## 4. Active Experiment

入口：`scripts/run_active.sh`。

- 使用已启用 `ENABLE_OBJECT_DYNAMIC_ACTIVE_MODE=1` 的预编译程序。
- DynamicMapFilter 使用上一接受帧的对象状态过滤当前 Tracking 候选。
- 脚本本身不会打开宏或重新编译；通过 `PAPER2_ACTIVE_BINARY` 指定正确二进制。

## 5. Ablation Experiments

消融实验复用上述脚本和已准备好的不同二进制/运行配置，建议至少包含：

- Paper1-only；
- ObjectDynamic Shadow；
- Active without recovery；
- Active without motion consistency；
- Active full model。

每个消融项必须使用独立 `run_name`，并在 `configs/` 中记录 commit、编译开关、数据集、检测输入和参数。运行脚本不得通过文本替换或其他方式自动修改代码。

## Reproducibility Rules

- 同组对比使用相同 vocabulary、settings、association 和检测结果。
- 保存运行命令、Git commit、二进制路径和环境变量。
- 每种模式至少重复运行多次，报告均值和标准差。
- `results/` 默认忽略运行产物；正式论文结果应经审核后复制到明确的发布目录。
- ATE/RPE 评估在 `evaluate/` 中独立完成，运行脚本不修改轨迹。
