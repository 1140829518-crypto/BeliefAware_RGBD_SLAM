# 论文2开发规范

## 适用范围

本规范适用于第二篇论文“Object-level Spatio-temporal Dynamic SLAM”的全部新增工作。论文1代码视为冻结基线；论文2功能通过独立模块和适配层扩展。

## 目录约定

| 内容 | 目录 | 说明 |
|---|---|---|
| 新增代码 | `paper2_development/modules/` | 所有论文2算法、数据结构、适配器和模块测试代码 |
| 实验 | `paper2_development/experiments/` | 实验配置、运行入口、数据清单和可复现命令 |
| 结果 | `paper2_development/results/` | 结构化指标、日志摘要和实验结果 |
| 图片 | `paper2_development/figures/` | 论文2绘图脚本、绘图数据和导出图片 |
| 论文与文档 | `paper2_development/docs/` | 设计、实验协议、论文草稿和开发说明 |

对象级动态模块统一放入：

```text
paper2_development/modules/ObjectDynamic/
```

## 冻结边界

禁止直接修改论文1冻结代码及公共路径，尤其包括：

- `src/`
- `include/`
- `Examples/`
- `lib/`
- `Vocabulary/`
- `experiment_new/`
- `paper1_release/`

如论文2需要消费论文1数据，应在 `paper2_development/modules/` 内创建适配器，不在冻结类中直接加入论文2状态或逻辑。确需改变公共构建或运行入口时，必须先提交接口设计文档，说明兼容性、回退方案和对论文1复现的影响，再单独评审。

## 开发流程

1. 先在模块文档中定义输入、输出、坐标系、时间基准和状态生命周期。
2. 新功能以独立、可测试的组件实现，不隐式依赖论文1内部可变状态。
3. 实验配置与代码分离；每次实验记录提交号、数据集、参数、随机种子和运行命令。
4. 原始结果写入 `results/`，绘图脚本从结构化结果生成 `figures/`，禁止手工改图代替数据修正。
5. 所有动态判断应区分语义先验、几何运动证据和时间一致性证据。
6. 合入前检查 `git diff`，确认冻结目录没有改动。

## 版本与复现

- 基线标签：`paper2_start_v1.0`。
- 基线标签说明：`Start paper2 development based on paper1 frozen version`。
- 实验报告必须记录其基于的 Git commit 和配置文件。
- 大型数据集、模型权重和运行缓存继续遵循 `.gitignore`，不得混入源码提交。

## 提交检查清单

- 新代码是否全部位于 `paper2_development/modules/`？
- 实验、结果、图片和文档是否进入对应目录？
- 是否未修改论文1冻结路径？
- 是否说明接口、参数和失败/恢复行为？
- 是否提供最小可复现实验或测试？
- `git status` 和提交内容是否仅包含本次任务文件？
