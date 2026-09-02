# Frame-Temporal implementation map

- Configuration entry: `SemanticConfig::Mode()`; Semantic=1, MapPoint-Temporal=2, Frame-Temporal=3.
- Semantic observation: YOLO detections become `Frame::objects_cur_`; dynamic/static policy is in `SemanticConfig.h`.
- Existing persistent state: `MapPoint::mfSemanticDynamicScore` and `mnSemanticDynamicLastFrame`.
- Existing update: `MapPoint::UpdateSemanticDynamicScore`; class-specific increment, frame-gap decay and threshold.
- Measurement selection: projection candidates in `ORBmatcher.cc` and final current-frame culling in `Tracking::CullSemanticDynamicMapPoints`.
- Frame-Temporal state: `FrameTemporalBaseline` owns one image-plane `CV_32F` EMA map. It has no MapPoint-ID container and never calls `MapPoint::UpdateSemanticDynamicScore` in mode 3.
- Logging: projection rows contain frame ID, real MapPoint ID, pixel, semantic observation, selected temporal state and score. MapPoint IDs are output identifiers only, never Frame-Temporal memory keys.
- Runner/evaluation: `scripts/run_tum_rgbd_experiment.py`, `scripts/evaluate_tum_metrics.py`, and the isolated runner in this directory.
