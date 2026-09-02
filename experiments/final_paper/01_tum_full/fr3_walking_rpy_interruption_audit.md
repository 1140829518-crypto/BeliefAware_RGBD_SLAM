# fr3_walking_rpy Interrupted Run Audit

本审计为只读取证，不修改算法、参数、轨迹或评价数据。`run_01` 和 `run_03` 的 `p1_run_config.json` 保留调度层记录的 `interrupted` 状态；以下同时报告目录中实际产物。

## Audit scope

检查来源：

- `terminal.log`、`slam.log`、`yolo.log`；
- `p1_run_config.json` 中的状态和退出码；
- `CameraTrajectory.txt`、`KeyFrameTrajectory.txt`、`SemanticDynamicStatistics.txt`；
- `eval/metrics.json` 和 `eval/metrics.txt`；
- 唯一 socket 路径与 P1 文件锁；
- 只读 `dmesg --ctime`。

没有单独的 Python stderr 文件：P1 将 Python runner stdout/stderr 合并写入 `terminal.log`，而 runner 又将 SLAM 输出写入 `slam.log`。

## Per-run findings

| run_id | recorded status | recorded exit_code | last processed input frame | trajectory valid poses | termination reason | algorithm related | runner related | system related |
|---|---|---:|---:|---:|---|---|---|---|
| run_01 | interrupted | 130 | 850 progress marker; input loop reached the sequence tail | 503 | Metadata was manually marked interrupted after an earlier monitor no longer saw the expected foreground process. However, artifacts prove the child runner completed normally. Exact reason for the parent/monitor discrepancy is unknown. | No evidence | Likely metadata/monitor lifecycle inconsistency; not conclusively attributable | Unknown |
| run_03 | interrupted | 130 | 850 progress marker; input loop reached the sequence tail | 160 | Same evidence pattern as run_01: the child runner completed normally while parent metadata was later marked interrupted. Exact reason is unknown. | No evidence | Likely metadata/monitor lifecycle inconsistency; not conclusively attributable | Unknown |

`last_processed_frame` uses the last explicit `[RGBD_TUM] frame` progress line. Logging occurs every 25 frames, so 850 is not evidence that the 866-frame input stopped at 850. Normal shutdown immediately follows, showing that the input loop reached completion.

## Evidence: run_01

- `terminal.log` ends with `completed fr3_walking_rpy full` and contains a complete metrics report.
- `slam.log` ends with:
  - `trajectory saved!`;
  - `semantic objects saved!`;
  - `semantic dynamic statistics saved!`.
- `eval/metrics.json` exists; the evaluator matched 501 poses to ground truth.
- `CameraTrajectory.txt` contains 503 valid TUM-format poses.
- `KeyFrameTrajectory.txt` contains 222 poses.
- YOLO created the unique socket `/tmp/orbslam2_p1_fr3_walking_rpy_01_111842.sock`, accepted one connection, and ended with `C++ socket disconnected; stopping detection` after SLAM shutdown.
- No `timeout`, segmentation fault, OOM, traceback, socket bind conflict, or abnormal YOLO termination was found.

Relevant excerpt:

```text
trajectory saved!
semantic objects saved!
semantic dynamic statistics saved!
matches: 501
ATE RMSE [m]: 0.708897
completed fr3_walking_rpy full
```

## Evidence: run_03

- `terminal.log` ends with `completed fr3_walking_rpy full` and contains a complete metrics report.
- `slam.log` contains all normal save markers.
- `eval/metrics.json` exists; the evaluator matched 158 poses to ground truth.
- `CameraTrajectory.txt` contains 160 valid poses.
- `KeyFrameTrajectory.txt` contains 77 poses.
- YOLO used `/tmp/orbslam2_p1_fr3_walking_rpy_03_111842.sock` and ended only after C++ disconnected.
- No `timeout`, segmentation fault, OOM, traceback, socket bind conflict, or abnormal YOLO termination was found.

Relevant excerpt:

```text
trajectory saved!
semantic objects saved!
semantic dynamic statistics saved!
matches: 158
ATE RMSE [m]: 0.036664
completed fr3_walking_rpy full
```

## Requested failure checks

| Check | run_01 | run_03 |
|---|---|---|
| Experiment script actively terminated SLAM | No evidence | No evidence |
| Timeout | No evidence | No evidence |
| Socket conflict | No evidence; unique socket connected | No evidence; unique socket connected |
| Process killed | Parent metadata uses synthetic exit code 130, but no child kill evidence | Same |
| Segmentation fault | Not present | Not present |
| Tracking lost caused program exit | No; program reached normal shutdown | No; program reached normal shutdown |
| OOM | No OOM evidence in run logs or accessible dmesg excerpt | No OOM evidence in run logs or accessible dmesg excerpt |
| YOLO failure | No; normal disconnect after C++ completion | No; normal disconnect after C++ completion |
| Result directory conflict | No evidence | No evidence |
| Lock conflict | No; both were created by the single lock owner | No; both were created by the single lock owner |
| User/system interruption | Exact parent-process event is unknown | Exact parent-process event is unknown |

The accessible kernel log contains recurring WSL `dxg` query errors but no line tying those messages to either run, and no OOM-killer or segmentation-fault evidence. They must not be used as a causal explanation.

## Comparison

The two runs share the same *metadata discrepancy*, not the same SLAM failure location:

- both child executions processed the sequence and shut down normally;
- both saved all expected output classes and completed evaluation;
- both were later labeled `interrupted` at the outer P1 metadata level;
- they produced very different tracking coverage (503 versus 160 poses), which is a real stochastic tracking outcome and must remain in the data.

## Conclusion

There is no evidence that either run was interrupted by an algorithm crash, timeout, socket conflict, OOM, YOLO exception, or tracking-lost exit. The precise outer-runner lifecycle event cannot be reconstructed and is therefore **unknown**. The most defensible description is: **recorded status is interrupted, while the child SLAM and evaluator artifacts show normal completion**. The final CSV preserves `status=interrupted`, does not count either run in `n_success`, and may include their accuracy metrics only because the trajectories and evaluator outputs are valid; `n_legal_evaluation` makes that distinction explicit.
