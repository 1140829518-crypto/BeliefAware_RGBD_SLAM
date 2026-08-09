# Paper2 Experiment Status

该文件用于记录论文2实验进度。实验结果应由运行脚本生成，不在此处手工复制或覆盖。

## 已完成实验

- [ ] Baseline
- [ ] Paper1
- [ ] Shadow
- [ ] Active
- [ ] 消融实验

当前仅完成实验框架及统一序列配置，尚未登记正式论文实验结果。

## 待完成实验

- 在 `fr3_sitting_static` 上依次运行 Baseline、Paper1、Shadow 和 Active。
- 在 `fr3_walking_xyz` 上依次运行四种模式。
- 在 `fr3_walking_rpy` 上依次运行四种模式。
- 在 `fr3_walking_static` 上依次运行四种模式。
- 完成无恢复机制、无运动一致性和完整模型等消融对比。
- 汇总 ATE、RPE、运行耗时以及多次运行的均值和标准差。

## 运行命令

统一配置调用（推荐）：

```bash
experiment_new/paper2/scripts/run_baseline.sh fr3_walking_static baseline_01
experiment_new/paper2/scripts/run_paper1.sh fr3_walking_static paper1_01
experiment_new/paper2/scripts/run_shadow.sh fr3_walking_static shadow_01
experiment_new/paper2/scripts/run_active.sh fr3_walking_static active_01
```

原有显式路径接口继续可用：

```bash
experiment_new/paper2/scripts/run_active.sh \
  Vocabulary/ORBvoc.txt \
  Examples/RGB-D/TUM3.yaml \
  rgbd_dataset_freiburg3_walking_static \
  rgbd_dataset_freiburg3_walking_static/associate.txt \
  active_01
```

## 结果位置

默认结果目录：

```text
experiment_new/paper2/results/<mode>/<run-name>/
```

每次运行保存 `run.log`、`CameraTrajectory.txt` 和 `KeyFrameTrajectory.txt`；程序产生的其他统计文件保存在同一目录。可通过 `PAPER2_RESULTS_ROOT` 指定另一个结果根目录。
