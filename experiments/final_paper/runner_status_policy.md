# Experiment Runner Status Policy

适用范围：后续 P2–P8 及对 P1 的重新汇总。该政策只规定实验工程状态，不改变 SLAM、语义、动态证据或评价算法。

## 1. 两类状态必须独立

每个固定 `run_id` 必须同时记录：

### `raw_process_status`

表示外层 runner 实际观察到的进程退出情况，不根据输出文件反向改写。

| 值 | 定义 |
|---|---|
| `exit_0` | runner 观察到退出码 0 |
| `exit_N` | runner 观察到非零退出码 N，例如 `exit_130` |
| `timeout` | runner 的明确超时机制触发 |
| `killed` | 观察到进程被信号终止或负 return code，但无法可靠映射为普通 exit code |
| `unknown` | runner 没有取得可信退出结果 |

退出码字段应同时原样保存。存在合法轨迹、评价文件或完成标志，均不得把 `exit_130` 篡改为 `exit_0`。

### `experiment_completion_status`

表示该 run 的实验产物是否满足预定义完整性证据，与进程退出码独立。

| 值 | 定义 |
|---|---|
| `completed` | 同时满足完成标志、非空轨迹、成功评价，且没有明确致命错误证据 |
| `incomplete` | 缺少至少一个必要完成证据，但未检测到明确致命错误 |
| `invalid` | 检测到 segmentation fault、OOM、明确 timeout 等致命错误，或产物明确损坏 |

## 2. `completed` 的最低证据

必须同时满足：

1. SLAM 日志包含正常完成标志。目前 RGB-D 实验要求至少出现 `trajectory saved!` 与 `semantic dynamic statistics saved!`；
2. `CameraTrajectory.txt` 存在且非空；
3. `eval/metrics.json` 存在且非空，评价脚本正常生成指标；
4. 合并检查 runner、SLAM、YOLO 日志，未发现明确的 segmentation fault、OOM 或 timeout 错误。

`completed` 不意味着完整轨迹覆盖。轨迹只覆盖少量帧时仍可能完成程序流程，因此必须另外报告 `trajectory_valid_poses`、TSR、PMR 和 tracking gaps。

## 3. 合法组合示例

以下组合都可能真实出现，禁止合并为单一“success”：

| raw_process_status | experiment_completion_status | 含义 |
|---|---|---|
| `exit_0` | `completed` | 进程和产物均正常 |
| `exit_0` | `incomplete` | 进程返回 0，但必要产物缺失 |
| `exit_130` | `completed` | 外层记录非零退出，但产物证据显示实验流程完成；需审计 runner 生命周期 |
| `timeout` | `incomplete` | 超时且产物不完整 |
| `killed` | `invalid` | 被终止并存在明确损坏/致命证据 |
| `unknown` | `completed` | 外层状态丢失，但完成证据充分；仍不得推断 exit code |

## 4. 统计纳入规则

每份汇总必须同时给出：

- `n_total`：所有固定 run_id；
- `n_raw_exit_0`：原始进程退出为 0 的数量；
- `n_completed`、`n_incomplete`、`n_invalid`；
- `n_legal_evaluation`：具有非空轨迹且评价 JSON 可解析的数量；
- `raw_exit_0_rate` 与 `experiment_completion_rate`。

指标使用规则：

- ATE/RPE：只纳入 `has_legal_evaluation=1` 的 run，并明确样本数；不自动要求 `raw_process_status=exit_0`，也不把缺失评价填为 0；
- TSR/PMR/tracking gaps：对所有固定 run_id 计算；轨迹缺失时 valid poses 为 0，仍保留该 run；
- FPS/runtime：只纳入有可靠计时记录的 run，并报告实际样本数；
- 不剔除异常值，不使用额外重跑替换失败 run_id。

若论文表格只采用 `completed` 子集，必须另做一张汇总并明确筛选条件，不能覆盖全 run 汇总。

## 5. P1 历史数据处理

P1 的 `p1_run_config.json` 中原 `status` 和 `return_code` 是历史原始记录，不修改。重新汇总时：

- `original_status` 原样复制历史 `status`；
- `exit_code` 原样复制历史退出码；
- `raw_process_status` 从历史状态/退出码推导；
- `experiment_completion_status` 从现存日志和产物重新审计；
- 证据写入 `completion_evidence`，便于复核。

因此 rpy run_01/run_03 可以同时保持 `exit_130` 与 `completed`，不存在退出码洗白。

## 6. 后续 runner 要求

P2–P8 runner 应在 run 创建时写：

```text
raw_process_status=unknown
experiment_completion_status=incomplete
```

进程结束后先原样写退出信息，再独立执行产物审计。若 runner 自身在写最终状态前消失，后处理器只能将 raw 状态记为 `unknown`，不得依据完成文件猜测 `exit_0`。

每次运行还应保留唯一 socket、单实例锁、终端合并日志、SLAM 日志、YOLO 日志、轨迹、评价 JSON 和实际配置快照。
