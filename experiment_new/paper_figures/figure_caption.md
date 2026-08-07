# Figure Captions

**Fig. 1. Dynamic probability evolution with temporal consistency.** Dynamic probability curves on TUM RGB-D dynamic sequences. The gray intervals denote frames containing dynamic human motion, and the dashed line indicates the decision threshold. Compared with single-frame YOLO and YOLO+motion cues, temporal consistency produces smoother probability estimates across adjacent frames.

**Fig. 2. Dynamic object detection accuracy.** Precision, recall, and F1-score of YOLO, YOLO+Motion, and the proposed temporal consistency strategy. The temporal model improves recall and F1-score while maintaining high precision, indicating more stable dynamic target identification.

**Fig. 3. Temporal window sensitivity analysis.** Influence of the temporal window size N on ATE RMSE and trajectory smoothness. A larger window improves smoothness, while an overly large window may introduce response delay and does not continuously reduce ATE.

**Fig. 4. Trajectory comparison on the Bonn RGB-D Dynamic Dataset.** Trajectories of Ground Truth, ORB-SLAM3, DS-SLAM, Dyna-SLAM, and the proposed method on walking, sitting, and crowd sequences. All trajectories are aligned to the same coordinate frame and plotted in meters.

**Fig. 5. Ablation study.** Quantitative comparison of Baseline, Semantic Mask, Temporal Consistency, Object-level Semantic Map, and Full Model using ATE, RPE, FPS, and Failure Rate. The figure is intended to analyze module-level effects rather than claim that each module independently optimizes every metric.

**Fig. 6. Object-level semantic map visualization.** Visualization of semantic mapping and dynamic point handling in a dynamic RGB-D scene. The map demonstrates how semantic information and dynamic-object reasoning are integrated into the SLAM output.
