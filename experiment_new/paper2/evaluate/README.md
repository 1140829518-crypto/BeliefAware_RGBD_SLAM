# Evaluation

本目录用于论文2轨迹及对象动态结果评估。

建议对所有模式统一计算：

- ATE RMSE、mean、median；
- translational/rotational RPE；
- Tracking success rate；
- 每帧耗时及峰值内存；
- Object ID continuity；
- dynamic classification precision/recall；
- map recovery delay 和恢复成功率。

评估程序应只读取 `results/` 中的日志与轨迹，不覆盖原始输出。Baseline、Paper1、Shadow、Active 和各消融项必须使用同一时间戳关联与评估参数。
