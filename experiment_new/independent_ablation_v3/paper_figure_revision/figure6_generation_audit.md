# Figure 6 Generation Audit

## Output Directory

`/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/paper_figure_revision`

## Source CSV Files

- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/aggregated_results/ablation_results.csv`
- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/aggregated_results/statistical_summary.csv`
- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/aggregated_results/sequence_results.csv`
- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/aggregated_results/temporal_metrics.csv`

## Data Columns Used

- Subplot (a): `ATE_RMSE_mean`, `ATE_RMSE_std` from `ablation_results.csv`.
- Subplot (b): `RPE_translation_RMSE_mean`, `RPE_translation_RMSE_std` from `ablation_results.csv`.
- Subplot (c): `Pose_Missing_Ratio_mean`, `Pose_Missing_Ratio_std` from `ablation_results.csv`.
- Subplot (d): `Switching_Frequency_mean`, `Switching_Frequency_std` from `ablation_results.csv`; Baseline is excluded from this comparison.

## Plotted Values

| Variant | ATE (m) | RPE (m) | Pose Missing Ratio | Switching Frequency |
|---|---:|---:|---:|---:|
| Baseline | 0.8485 ± 0.2689 | 0.0588 ± 0.0304 | 0.2234 ± 0.1872 | N/A in plot |
| Semantic Mask | 0.5701 ± 0.2328 | 0.0558 ± 0.0341 | 0.3211 ± 0.3044 | 0.0367 ± 0.0253 |
| Temporal Consistency | 0.2424 ± 0.2317 | 0.0296 ± 0.0105 | 0.4211 ± 0.4176 | 0.0259 ± 0.0201 |
| Object-level Semantic Map | 0.5620 ± 0.2708 | 0.0598 ± 0.0432 | 0.2312 ± 0.1625 | 0.0388 ± 0.0165 |
| Full Model | 0.2660 ± 0.2902 | 0.0244 ± 0.0074 | 0.4615 ± 0.4045 | 0.0216 ± 0.0217 |

## Baseline Switching Frequency Handling

Baseline has `Switching_Frequency_mean=0` in the source CSV because it does not output semantic dynamic-object states. In subplot (d), Baseline is shown as N/A with a hatched empty marker and is not considered for the best value.

## Missing Values

No missing values were found in the four plotted source metrics. Baseline switching frequency is intentionally displayed as N/A in the figure because the raw zero is not semantically comparable.

## Data Consistency Check

No inconsistency was found between the source CSV values and the provided cross-check values.

## Original Data Handling

- Modified original experiment files: no.
- Re-ran experiments: no.
- Interpolated, scaled, or manually adjusted data: no.
- Generated new files only under the output directory above.

## Fonts

Requested fonts Times New Roman and SimSun were not available in the runtime environment. The figure uses `Nimbus Roman` as the serif replacement for English and numeric text. No external fonts were downloaded.

## Output Image Size and DPI

- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/paper_figure_revision/figure6_ablation.png`: 4257 x 3148 px, saved at 600 dpi target.
- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/paper_figure_revision/figure6_ablation_single_column.png`: 3315 x 3027 px, saved at 600 dpi target.
- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/paper_figure_revision/figure6_ablation_double_column.png`: 4257 x 3148 px, saved at 600 dpi target.

PDF, EPS and SVG files were saved as vector outputs. PNG outputs were saved with a 600 dpi target.

## Suggested Caption

中文：图6 不同消融配置下的性能比较。（a）绝对轨迹误差；（b）相对位姿误差；（c）位姿缺失率；（d）动态状态切换频率。

English: Fig.6 Performance comparison under different ablation configurations. (a) Absolute trajectory error; (b) relative pose error; (c) pose missing ratio; (d) dynamic-state switching frequency.

Supplement: 图中柱高和误差棒分别表示多次独立实验结果的均值和标准差。Baseline不输出动态目标状态，因此不参与动态状态切换频率的比较。
