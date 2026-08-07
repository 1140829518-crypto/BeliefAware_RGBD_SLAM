# Independent Ablation v1

This directory contains a fresh ablation attempt generated without modifying or
overwriting previous experiment results. Each completed run has its own command,
configuration, logs, trajectories, timing and evaluation files.

Variants:

- Baseline: semantic mode 0, object map 0.
- Semantic Mask: semantic mode 1, object map 0.
- Temporal Consistency: semantic mode 2, object map 0.
- Object-level Semantic Map: semantic mode 1, object map 1. This is an independent
  run, but object mapping depends on semantic detections in the current binary.
- Full Model: semantic mode 2, object map 1.
