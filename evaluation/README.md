# Evaluation

`evaluate_trajectory.sh` is the public wrapper around the authoritative
`scripts/evaluate_tum_metrics.py` evaluator. It accepts TUM-format ground truth
and estimated trajectories and writes `metrics.json`, `metrics.txt`, and plots.

The frozen evaluator SHA-256 is recorded in `../RESULTS.md`. Do not change its
timestamp tolerance or metric definitions when reproducing the paper.

TSR is valid trajectory poses divided by association frames; PMR is `1-TSR`.
Those coverage metrics are summarized by the experiment pipeline rather than
invented from ATE matches.
