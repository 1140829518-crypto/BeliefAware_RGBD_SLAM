# Independent Ablation Authenticity Audit

Generated: 2026-07-29T23:07:31

## Answers

1. Five groups independently run: yes; completed run count = 45.
2. Results copied from other configurations: no copying is performed by this runner.
3. Manual interpolation or scaling: none.
4. Same data and evaluation protocol: yes for all attempted runs.
5. Full Model module configuration: semantic_mode=2 and object_map=1 in every Full Model run_config.
6. Object-level map independent run: independent process run, but not a pure object-only module; current binary requires semantic detections for object map updates.
7. Baseline true FPS: yes, computed from wall-clock runtime and associated input frames.
8. Failed or incomplete runs: 0.
9. Metrics supporting dynamic-decision continuity: frame-level switching frequency, label fluctuation proxy and temporal consistency score when SemanticDynamicStatistics exists.
10. Metrics not supporting original strong conclusions: F1, probability variance and ID continuity are unavailable without additional labels/logs.
11. Full Model best comprehensive performance: best ATE=Temporal Consistency, best RPE=Full Model, best Pose Missing Ratio=Baseline, best TCS=Baseline. Do not claim Full Model is best unless these values support it.
12. Recommended paper conclusion: state that temporal modeling improves available continuity proxies, while localization accuracy and pose coverage show a trade-off.
13. Recommended additional runs: add target-level dynamic labels and per-target probability/ID logging, then rerun detection metrics.

## Failed Runs

- None.

## Summary

- Baseline: ATE 0.8485 ± 0.2689, RPE 0.0588 ± 0.0304, FPS 14.0979 ± 3.1163, Pose Missing Ratio 0.2234 ± 0.1872, TCS 1.0000 ± 0.0000
- Semantic Mask: ATE 0.5701 ± 0.2328, RPE 0.0558 ± 0.0341, FPS 13.3753 ± 1.0619, Pose Missing Ratio 0.3211 ± 0.3044, TCS 0.9623 ± 0.0101
- Temporal Consistency: ATE 0.2424 ± 0.2317, RPE 0.0296 ± 0.0105, FPS 13.0124 ± 0.8745, Pose Missing Ratio 0.4211 ± 0.4176, TCS 0.9609 ± 0.0111
- Object-level Semantic Map: ATE 0.5620 ± 0.2708, RPE 0.0598 ± 0.0432, FPS 11.8681 ± 1.1552, Pose Missing Ratio 0.2312 ± 0.1625, TCS 0.9637 ± 0.0081
- Full Model: ATE 0.2660 ± 0.2902, RPE 0.0244 ± 0.0074, FPS 12.4740 ± 1.5840, Pose Missing Ratio 0.4615 ± 0.4045, TCS 0.9638 ± 0.0077
