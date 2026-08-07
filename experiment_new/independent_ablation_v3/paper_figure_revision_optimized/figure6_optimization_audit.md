# Figure 6 Optimization Audit

## Original Figure Paths

- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/paper_figure_revision/figure6_ablation.pdf`
- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/paper_figure_revision/figure6_ablation.eps`
- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/paper_figure_revision/figure6_ablation.svg`
- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/paper_figure_revision/figure6_ablation.png`

## Generation Script

`/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/paper_figure_revision_optimized/generate_figure6_optimized.py`

No original standalone plotting script was found in the previous figure directory, so this optimized script regenerates the figure from the saved data files.

## Data Files Used

- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/paper_figure_revision/figure6_ablation_data.csv`
- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/aggregated_results/ablation_results.csv`
- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/aggregated_results/statistical_summary.csv`
- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/aggregated_results/temporal_metrics.csv`

## Optimization Operations

- Removed the in-panel text `Baseline excluded` from subplot (d).
- Kept the Baseline `N/A` marker in subplot (d).
- Kept Baseline excluded from switching-frequency best-value comparison.
- Reduced the top legend font size from 8.5 pt to 7.5 pt, a reduction of approximately 11.8%.
- Reduced legend handle length to 1.05, handle-text padding to 0.35, column spacing to 0.85, border axes padding to 0.05, and label spacing to 0.2.
- Compressed the top legend area by changing the figure legend anchor to `(0.5, 0.998)` and the tight-layout rectangle to `(0, 0, 1, 0.965)`.

## Data Handling

- Modified experiment data: no.
- Re-ran experiments: no.
- Changed bar heights: no.
- Changed error bars: no.
- Changed method order: no.
- Changed colors or hatches: no.
- Overwrote original figure files: no.

## Baseline N/A Handling

Baseline still appears as `N/A` in subplot (d). Its source switching-frequency value remains 0 in the data files, but it is not plotted as a valid zero-height bar and is not included in the best-value comparison.

## Output Files, Size and DPI

- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/paper_figure_revision_optimized/figure6_ablation_optimized.pdf`: 35559 bytes
- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/paper_figure_revision_optimized/figure6_ablation_optimized.eps`: 125117 bytes
- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/paper_figure_revision_optimized/figure6_ablation_optimized.svg`: 118914 bytes
- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/paper_figure_revision_optimized/figure6_ablation_optimized.png`: 556913 bytes; 4257 x 3143 px, dpi=(599.9988, 599.9988)
- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/paper_figure_revision_optimized/figure6_ablation_double_column_optimized.pdf`: 35559 bytes
- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/paper_figure_revision_optimized/figure6_ablation_double_column_optimized.eps`: 125131 bytes
- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/paper_figure_revision_optimized/figure6_ablation_double_column_optimized.svg`: 118914 bytes
- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/paper_figure_revision_optimized/figure6_ablation_double_column_optimized.png`: 556913 bytes; 4257 x 3143 px, dpi=(599.9988, 599.9988)
- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/paper_figure_revision_optimized/figure6_ablation_single_column_optimized.pdf`: 35560 bytes
- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/paper_figure_revision_optimized/figure6_ablation_single_column_optimized.eps`: 124983 bytes
- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/paper_figure_revision_optimized/figure6_ablation_single_column_optimized.svg`: 118764 bytes
- `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/independent_ablation_v3/paper_figure_revision_optimized/figure6_ablation_single_column_optimized.png`: 450214 bytes; 2291 x 3023 px, dpi=(599.9988, 599.9988)

## Font

The optimized figure uses `Nimbus Roman`, matching the available serif font used by the previous generated Figure 6.

## Data Consistency

No data differences were introduced by the optimization. The same `figure6_ablation_data.csv` and `ablation_results.csv` values were used.

## Suggested Caption

中文：

图6 不同消融配置下的系统性能比较。（a）绝对轨迹误差；（b）相对位姿误差；（c）位姿缺失率；（d）动态状态切换频率。柱高表示多次独立实验结果的均值，误差棒表示标准差。Baseline不输出动态目标状态，因此不参与动态状态切换频率的比较。

English:

Fig. 6 Performance comparison under different ablation configurations. (a) Absolute trajectory error; (b) relative pose error; (c) pose missing ratio; (d) dynamic-state switching frequency. Bars indicate the mean values of independent runs, and error bars denote the standard deviations. The Baseline does not output dynamic object states and is therefore excluded from the comparison of switching frequency.
