# Paper Figure Plot

This directory contains Matplotlib scripts for generating paper figures from
`Paper_Figure_Data/`. The scripts only read prepared data and do not modify
experiment results.

## Run

```bash
python3 Paper_Figure_Plot/scripts/plot_all.py
```

Outputs are saved under:

```text
Paper_Figure_Plot/output/
```

Each figure is exported as EPS, PDF, and 600 dpi PNG. The EPS files requested
for submission are:

- `output/Fig2.eps`
- `output/Fig3.eps`
- `output/Fig4.eps`
- `output/Fig5.eps`
- `output/Fig6.eps`

## Style

- Font priority: Times New Roman, Liberation Serif, Nimbus Roman, DejaVu Serif.
- Current system does not provide Times New Roman, so Matplotlib uses
  `Liberation Serif`.
- Figures use grayscale colors, line styles, hatches, and non-default styling
  for print readability.
- Axes include variable names and units where applicable.

## Figure Sources

### Fig2

Data source:

`Paper_Figure_Data/Fig2_Trajectory/{walking,sitting,crowd}/`

The Bonn trajectory files include:

- `gt.txt`
- `orbslam3.txt`
- `dsslam.txt`
- `dynaslam.txt`
- `ours.txt`

The script keeps the true method name `ORB-SLAM3`; it does not relabel it as
ORB-SLAM2. Estimated trajectories are associated by timestamp and aligned to
ground truth for plotting.

### Fig3

Data source:

`Paper_Figure_Data/Fig3_Dynamic_Evidence/dynamic_evidence.csv`

The current data do not contain raw motion-score probabilities. The figure
plots the available dynamic evidence score column and dynamic-state background
only; it does not plot or fabricate `motion_score`.

### Fig4

Data source:

`Paper_Figure_Data/Fig4_Detection_Performance/detection_metrics.csv`

The figure plots grouped bars for Precision, Recall, and F1-score.

### Fig5

Data source:

`Paper_Figure_Data/Fig5_Parameter_Analysis/lambda_analysis.csv`

The figure contains four panels:

- (a) ATE
- (b) RPE
- (c) FPS
- (d) Switching Frequency

### Fig6

Data source:

`Paper_Figure_Data/Fig6_Ablation/ablation_results.csv`

The figure contains four panels:

- (a) ATE
- (b) RPE
- (c) Pose Missing Ratio
- (d) Switching Frequency

Baseline is marked as `N/A` in the switching-frequency panel because it does
not output dynamic object states for this comparison.
