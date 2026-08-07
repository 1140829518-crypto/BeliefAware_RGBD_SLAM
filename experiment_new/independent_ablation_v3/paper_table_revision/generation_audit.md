# Generation Audit

## Output Directory

`/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/paper_table_revision`

## Source Files Used

- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/aggregated_results/ablation_results.csv`
- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/aggregated_results/statistical_summary.csv`
- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/aggregated_results/sequence_results.csv`
- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/aggregated_results/temporal_metrics.csv`
- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/aggregated_results/experiment_audit.md`

## Data Handling

- 原始数据是否被修改：否。
- 是否重新运行实验：否。
- 是否复用旧论文表格：否。
- 是否人工调整、插值、缩放或补造数据：否。
- 是否重新计算统计：否。论文表5直接读取 `ablation_results.csv` 中的均值±标准差字段；`sequence_results.csv` 和 `temporal_metrics.csv` 仅用于交叉检查45次独立运行证据链。

## Traceability

- 发现 `run_config.json` 数量：45。
- 运行状态统计：{'completed': 45}。
- `sequence_results.csv` 行数：45，其中数据行应为45。
- `temporal_metrics.csv` 行数：45，其中数据行应为45。

## Value Sources

- Baseline: `aggregated_results/ablation_results.csv` row `variant_key=baseline`; valid_runs=9, failed_runs=0.
- Semantic Mask: `aggregated_results/ablation_results.csv` row `variant_key=semantic_mask`; valid_runs=9, failed_runs=0.
- Temporal Consistency: `aggregated_results/ablation_results.csv` row `variant_key=temporal_consistency`; valid_runs=9, failed_runs=0.
- Object-level Semantic Map: `aggregated_results/ablation_results.csv` row `variant_key=object_level_map`; valid_runs=9, failed_runs=0.
- Full Model: `aggregated_results/ablation_results.csv` row `variant_key=full_model`; valid_runs=9, failed_runs=0.

论文表5各列来源如下：

- ATE (m)：`ATE_RMSE_mean_std`
- RPE (m)：`RPE_translation_RMSE_mean_std`
- FPS (frame/s)：`FPS_mean_std`
- Pose Missing Ratio：`Pose_Missing_Ratio_mean_std`
- Switching Frequency：`Switching_Frequency_mean_std`，但Baseline在论文表中显示为“—”，因为Baseline不输出动态目标状态，不参与该列比较。原始统计中的0值未修改。

## Missing Values

论文主表无NA数值列。Baseline的Switching Frequency按实验含义显示为“—”。F1-score和Temporal Consistency Score未进入论文主表，但保留在完整统计文件中。

## Cross-check Against Provided Values

未发现不一致。

## Best Methods by Mean Value

- ATE (m)：Temporal Consistency，均值 0.2424。
- RPE (m)：Full Model，均值 0.0244。
- FPS (frame/s)：Baseline，均值 14.0979。
- Pose Missing Ratio：Baseline，均值 0.2234。
- Switching Frequency：Full Model，均值 0.0216。Baseline不参与该列最优值判断。

## Consistency Result

表格可以追溯到45次独立运行。未发现源文件与指定交叉检查值不一致。需要注意：F1-score、逐目标概率方差和ID连续性指标缺少人工真值或逐目标日志，因此不进入论文主表。
