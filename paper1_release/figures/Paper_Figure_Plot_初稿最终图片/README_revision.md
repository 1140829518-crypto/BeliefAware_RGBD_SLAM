# Paper Figure Plot Revision

## Revision Scope

This revision only updates Matplotlib plotting code and visual style under
`Paper_Figure_Plot/scripts/`. No experiment data were modified, no SLAM program
was rerun, and no unavailable data columns were fabricated.

## Unified Style

The shared style file `scripts/plot_style.py` was updated with:

- White figure and axes background.
- No grid lines: `axes.grid=False`, and every plotting script explicitly calls `ax.grid(False)`.
- Font priority: Times New Roman, Liberation Serif, Nimbus Roman, DejaVu Serif.
- Current system font fallback: Liberation Serif.
- Axis label size: 10.5 pt.
- Tick label size: 9 pt.
- Legend size: 9 pt.
- Curve linewidth: 1.5.
- Axis linewidth: 1.0.
- Output formats retained: EPS, PDF, and 600 dpi PNG.

## Figure Updates

### Fig2

Script: `scripts/plot_fig2.py`

Data source: `Paper_Figure_Data/Fig2_Trajectory/`

Updates:

- Kept Bonn method name `ORB-SLAM3` from `orbslam3.txt`; it is not relabeled as ORB-SLAM2.
- Removed grid lines.
- Used color-coded trajectories:
  - Ground Truth: black
  - ORB-SLAM3: red
  - DS-SLAM: blue
  - DynaSLAM: green
  - Ours: orange
- Kept three subplots: (a) walking, (b) sitting, (c) crowd.
- Axis labels: X (m), Z (m).

### Fig3

Script: `scripts/plot_fig3.py`

Data source: `Paper_Figure_Data/Fig3_Dynamic_Evidence/dynamic_evidence.csv`

Updates:

- Removed gray filled background.
- Plotted only available dynamic evidence score data.
- Did not plot or synthesize missing motion-score data.
- Dynamic state is shown on a secondary y-axis.
- If a threshold column is present in future data, it will be drawn as a red dashed line; no threshold is fabricated.

### Fig4

Script: `scripts/plot_fig4.py`

Data source: `Paper_Figure_Data/Fig4_Detection_Performance/detection_metrics.csv`

Updates:

- Reorganized grouped bars by metric: Precision, Recall, F1-score.
- Method colors:
  - YOLO: blue
  - YOLO+Motion: orange
  - Temporal/Ours: green
- Added numeric value labels.
- Removed grid lines.

### Fig5

Script: `scripts/plot_fig5.py`

Data source: `Paper_Figure_Data/Fig5_Parameter_Analysis/lambda_analysis.csv`

Updates:

- Four panels retained: (a) ATE, (b) RPE, (c) FPS, (d) Switching Frequency.
- X-axis label changed to `Decay coefficient λ`.
- Different metrics use different colors.
- Removed grid lines.

### Fig6

Script: `scripts/plot_fig6.py`

Data source: `Paper_Figure_Data/Fig6_Ablation/ablation_results.csv`

Updates:

- Four panels retained: (a) ATE, (b) RPE, (c) Pose Missing Ratio, (d) Switching Frequency.
- Different ablation methods use different colors.
- Method labels retained as Baseline, Semantic Mask, Temporal Consistency, Object Map, and Full Model.
- Error bars represent standard deviation.
- Mean ± std labels are added above bars.
- Baseline is marked as N/A in Switching Frequency because it does not output dynamic object states.

## Regeneration Command

```bash
cd /home/djn/123/ORB_SLAM2_AddSemantic/
python3 Paper_Figure_Plot/scripts/plot_all.py
```

## Output Files

All regenerated figures are saved under:

```text
Paper_Figure_Plot/output/
```

Required EPS files:

- `Fig2.eps`
- `Fig3.eps`
- `Fig4.eps`
- `Fig5.eps`
- `Fig6.eps`

PDF and 600 dpi PNG versions are also generated for each figure.
