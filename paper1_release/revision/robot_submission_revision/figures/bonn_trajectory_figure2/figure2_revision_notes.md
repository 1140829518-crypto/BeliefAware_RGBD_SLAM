# Figure 2 Bonn Trajectory Revision Audit

- Source manifest: `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/results/bonn_selected_sequences.csv`
- Run root: `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/results/bonn_runs`
- Output directory: `/home/djn/123/ORB_SLAM2_AddSemantic/robot_submission_revision/figures/bonn_trajectory_figure2`
- Font used: `Liberation Serif`
- Experiment data modified: No
- Experiment rerun: No
- Layout: three horizontal subplots for walking, sitting, and crowd.
- Line width: all trajectories are plotted with linewidth >= 2.0.

## Caption

中文：图2 Bonn RGB-D Dynamic Dataset不同方法轨迹估计结果

English: Fig.2 Trajectory comparison on the Bonn RGB-D Dynamic Dataset

## Data Sources

### walking
- Ground Truth: `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/dataset/bonn_rgbd_dynamic/rgbd_bonn_person_tracking/groundtruth.txt` (583 poses)
- ORB-SLAM3: `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/results/bonn_runs/walking/orb_slam3/CameraTrajectory.txt` (580 associated poses)
- DS-SLAM: `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/results/bonn_runs/walking/ds_slam/CameraTrajectory.txt` (580 associated poses)
- DynaSLAM: `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/results/bonn_runs/walking/dyna_slam/CameraTrajectory.txt` (574 associated poses)
- Ours: `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/results/bonn_runs/walking/ours/CameraTrajectory.txt` (580 associated poses)
### sitting
- Ground Truth: `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/dataset/bonn_rgbd_dynamic/rgbd_bonn_synchronous/groundtruth.txt` (333 poses)
- ORB-SLAM3: `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/results/bonn_runs/sitting/orb_slam3/CameraTrajectory.txt` (331 associated poses)
- DS-SLAM: `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/results/bonn_runs/sitting/ds_slam/CameraTrajectory.txt` (290 associated poses)
- DynaSLAM: `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/results/bonn_runs/sitting/dyna_slam/CameraTrajectory.txt` (54 associated poses)
- Ours: `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/results/bonn_runs/sitting/ours/CameraTrajectory.txt` (271 associated poses)
### crowd
- Ground Truth: `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/dataset/bonn_rgbd_dynamic/rgbd_bonn_crowd/groundtruth.txt` (933 poses)
- ORB-SLAM3: `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/results/bonn_runs/crowd/orb_slam3/CameraTrajectory.txt` (928 associated poses)
- DS-SLAM: `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/results/bonn_runs/crowd/ds_slam/CameraTrajectory.txt` (927 associated poses)
- DynaSLAM: `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/results/bonn_runs/crowd/dyna_slam/CameraTrajectory.txt` (626 associated poses)
- Ours: `/home/djn/123/ORB_SLAM2_AddSemantic/experiment_new/results/bonn_runs/crowd/ours/CameraTrajectory.txt` (841 associated poses)
