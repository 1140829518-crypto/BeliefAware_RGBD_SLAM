# Fig.1 System Framework Generation Notes

## Files

- `Fig1_System_Framework.vsdx`: editable Visio source generated from Visio XML shapes.
- `Fig1_System_Framework.pdf`: vector preview exported from SVG.
- `Fig1_System_Framework.png`: 600 dpi raster preview exported from SVG.

## Method Correspondence

- RGB-D Input corresponds to image and depth input.
- ORB-SLAM2 RGB-D Frontend contains only Feature Extraction, Feature Matching, and Pose Tracking.
- YOLOv5 Semantic Detection contains Object Category, Confidence, and Semantic Mask.
- Semantic Observation feeds semantic evidence into the temporal model.
- Temporal Dynamic Evidence Model is visually highlighted as the core contribution and contains Dynamic Evidence Score, λ Decay, γ Increment, θ Threshold, and Dynamic State Decision.
- Dynamic Point Suppression contains Dynamic Point Removal, Feature Filtering, Matching Constraint, and Tracking Constraint.
- Backend Optimization contains Local Mapping, Loop Closing, and Graph Optimization.
- Object-level Semantic Map contains Object Category, 3D Position, Object Observation Association, and Dynamic State.
- Final Outputs contain Camera Trajectory, Static/Dynamic Map Points, and Object-level Semantic Information.

## Compliance Check

- Editable VSDX source is retained.
- No raster screenshot is embedded as the Visio content.
- The figure does not include Kalman Filter, Optical Flow, Transformer, Object ID Tracking, ID Association, Re-identification, or Dynamic Object Tracking.
- `ID Association` was deliberately not used; the map module uses `Object Observation Association`.
- White background, no gradient, no shadow.
- Text is in English and uses Times New Roman in the Visio font declaration.
