# DS-SLAM six-sequence protocol audit

- Source: `baselines/DS-SLAM-master` (local tree; exact upstream revision is not verifiable because `.git` metadata is absent).
- Executable SHA-256: `1914b48c8492fe4b30fe2ad97b783382fb42cc137f481b0b5dc4de58fa15f4dd`.
- TUM3 configuration SHA-256: `e0bfd1294213b8b94ca06290fa60d63559488e1b0c7f8e2f80407cc4d7f5f2ea`.
- Bonn configuration: `experiment_new/dataset/bonn_rgbd_dynamic/Bonn.yaml`; it contains the ORB-SLAM2 camera, depth, ORB, and viewer keys consumed by DS-SLAM. Extra keys are ignored.
- SegNet model SHA-256: `df9b692ddfca0cae9c979465887aa1ed28a8480db46d86daf6b0fc638a11c2d0`.
- Evaluator: `scripts/evaluate_tum_metrics.py`, SHA-256 `cfdd35d556afcd5d080fe109396f5ffa7da1810a5e2c26a656c648216db24b13`.
- Dependencies: OpenCV 4.2; local Caffe/SegNet 1.0.0-rc3; Boost 1.71; ORB-SLAM2/Pangolin stack. `ldd` reports no unresolved shared library.
- TUM camera configuration: frozen DS-SLAM `TUM3.yaml`.
- Bonn camera configuration: frozen project `Bonn.yaml` with Bonn-specific calibration; TUM calibration is not reused.
- Associations: the same frozen project association files used by the internal campaign.
- Evaluator compatibility: full for trajectory metrics (ATE, RPE-t, RPE-r); TSR/PMR use association-frame coverage. DS-SLAM does not expose the internal final-inlier instrumentation, so final inliers are N/A.
- Runs: three predetermined runs per sequence; failures retained; no replacement and no best-run selection.
- Reuse: the already completed first three xyz/rpy runs use the same executable/config/model hashes and are copied into the new campaign directory and re-evaluated. The other 12 trials are new executions.
