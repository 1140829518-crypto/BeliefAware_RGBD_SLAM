# Metric Definitions

- ATE RMSE: root mean square translational absolute trajectory error after SE(3)
  alignment to TUM ground truth. Lower is better.
- RPE translation RMSE: adjacent-pose translational relative pose error. Lower is better.
- RPE rotation RMSE: adjacent-pose rotational relative pose error in degrees. Lower is better.
- FPS: associated input frames divided by measured wall-clock runtime for the whole run.
  It includes YOLO startup/inference when semantic mode is enabled, SLAM tracking,
  shutdown and file output.
- Pose Missing Ratio: `1 - valid output poses / associated input RGB-D frames`.
  Lower is better. This measures trajectory-output incompleteness and is not a
  strict probability of system failure.
- Trajectory Smoothness: mean norm of the second-order finite difference of estimated
  translation. Lower is smoother, but smoother is not necessarily more accurate.
- Dynamic-state Switching Frequency: frame-level aggregate proxy computed from
  transitions of `dynamic_objects > 0` in `SemanticDynamicStatistics.txt`, divided
  by valid adjacent frame pairs. Lower indicates fewer frame-level dynamic/static
  state toggles. The current logs do not provide target-level IDs, so target-level
  switching cannot be calculated.
- Frame-to-frame Label Fluctuation: aggregate proxy computed as the mean absolute
  change of normalized dynamic-keypoint counts between adjacent frames. Lower means
  less frame-to-frame fluctuation. This is not pixel-, feature-match-, or target-ID
  label fluctuation.
- Temporal Consistency Score: `1 - Label Fluctuation`, clipped to [0, 1]. It measures
  continuity only and does not measure classification correctness.
- Precision, Recall and F1-score: Not available for this independent ablation because
  this repository does not contain per-frame/object human ground-truth dynamic labels
  for these newly generated runs.
- Dynamic Probability Variance and Mean Probability Change: Not available because the
  current binary does not output per-target dynamic probability sequences.
- ID Switches and Average Track Length: Not available because the current output does
  not contain reliable target IDs over time.
