# Paper2 Belief Evaluation

This experiment isolates four runtime configurations while using the same
ObjectDynamic-active binary and the existing TUM RGB-D runner.

```bash
python3 experiment_new/paper2_belief_eval/run_belief_ablation.py
```

Results are never overwritten by default and use:

```text
output/<method>/<sequence>/run_<id>/
```

Each successful run contains `CameraTrajectory.txt`, `eval/metrics.json`,
`belief_evolution.csv`, `slam.log`, and `run_config.json`. The aggregate
`output/summary.csv` is regenerated without changing raw run outputs.

For a minimal validation:

```bash
python3 experiment_new/paper2_belief_eval/run_belief_ablation.py \
  --methods baseline full_model --runs 1
```
