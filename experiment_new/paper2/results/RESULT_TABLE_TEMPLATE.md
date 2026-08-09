# Paper2 Experiment Result Table

该模板用于汇总论文2的定量实验结果。每一行对应一次序列与方法组合；重复实验可增加行或在汇总行中填写均值和标准差。

| Sequence | Method | ATE RMSE | RPE trans | RPE rot | FPS | Tracking Lost | Filtered Points |
|---|---|---:|---:|---:|---:|---:|---:|
| fr3_sitting_static | baseline | — | — | — | — | — | — |
| fr3_sitting_static | paper1 | — | — | — | — | — | — |
| fr3_sitting_static | shadow | — | — | — | — | — | — |
| fr3_sitting_static | active | — | — | — | — | — | — |
| fr3_walking_xyz | baseline | — | — | — | — | — | — |
| fr3_walking_xyz | paper1 | — | — | — | — | — | — |
| fr3_walking_xyz | shadow | — | — | — | — | — | — |
| fr3_walking_xyz | active | — | — | — | — | — | — |
| fr3_walking_rpy | baseline | — | — | — | — | — | — |
| fr3_walking_rpy | paper1 | — | — | — | — | — | — |
| fr3_walking_rpy | shadow | — | — | — | — | — | — |
| fr3_walking_rpy | active | — | — | — | — | — | — |
| fr3_walking_static | baseline | — | — | — | — | — | — |
| fr3_walking_static | paper1 | — | — | — | — | — | — |
| fr3_walking_static | shadow | — | — | — | — | — | — |
| fr3_walking_static | active | — | — | — | — | — | — |

## Recording Notes

- ATE RMSE、RPE trans 和 RPE rot 应注明单位，并使用同一评估工具和参数。
- FPS 采用完整有效跟踪区间的平均值。
- Tracking Lost 记录跟踪丢失次数；在论文中明确计数定义。
- Filtered Points 记录 Active Mode 过滤点数，可同时保存总数和每帧均值。
- 每个结果应可追溯到对应结果目录、Git commit、二进制文件和运行日志。
