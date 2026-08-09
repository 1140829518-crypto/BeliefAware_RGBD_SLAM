# Paper2 Batch Experiment Run Guide

## 运行前准备

1. 检查 `configs/tum_sequences.yaml` 中四个序列的数据集和 association 路径。
2. 准备 Baseline、Paper1、Shadow 和 Active 对应的已编译可执行文件。
3. Paper1、Shadow 和 Active 若依赖语义检测服务，应在运行前独立启动该服务。
4. 确认默认结果目录有足够磁盘空间。

批量脚本只调用已有 `run_baseline.sh`、`run_paper1.sh`、`run_shadow.sh` 和 `run_active.sh`，不会构建工程、修改源码或改变算法开关。

## 运行全部实验

在项目根目录执行：

```bash
experiment_new/paper2/scripts/run_all_tum.sh
```

如四种方法使用不同的预编译程序，可在执行前设置：

```bash
PAPER2_BASELINE_BINARY=/path/to/baseline/rgbd_tum \
PAPER2_PAPER1_BINARY=/path/to/paper1/rgbd_tum \
PAPER2_SHADOW_BINARY=/path/to/shadow/rgbd_tum \
PAPER2_ACTIVE_BINARY=/path/to/active/rgbd_tum \
experiment_new/paper2/scripts/run_all_tum.sh
```

可通过 `PAPER2_RESULTS_ROOT=/path/to/results` 更改结果根目录。批量运行采用严格失败策略：任一实验失败时停止，修复问题后重新执行；已有结果目录不会被覆盖。

## 结果保存位置

每次实验使用包含序列名和时间戳的运行名，目录结构为：

```text
experiment_new/paper2/results/<method>/<sequence>_<timestamp>/
├── run.log
├── CameraTrajectory.txt
├── KeyFrameTrajectory.txt
└── 其他程序输出
```

`run.log` 记录模式、序列、配置路径、开始时间、输出路径以及程序标准输出。轨迹文件由现有 RGB-D 程序写入同一结果目录。

## 填写论文结果表

1. 对 `CameraTrajectory.txt` 使用统一工具计算 ATE RMSE 和 RPE。
2. 从运行日志或计时统计提取 FPS、Tracking Lost 和 Filtered Points。
3. 将结果填写到 `results/RESULT_TABLE_TEMPLATE.md` 对应的 Sequence/Method 行。
4. 多次运行时保留每次原始结果，并在论文表格中报告均值和标准差。
5. 填表时记录结果目录、Git commit、评估命令和指标单位，确保结果可复现。
