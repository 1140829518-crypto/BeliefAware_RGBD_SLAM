# Project Organization Plan

Current branch: `paper2_development`

Goal: separate Paper1 materials from future Paper2 development files while keeping shared SLAM code in the repository root.

This is a planning document only. No files have been moved yet.

Inventory verified on 2026-08-08. Neither `paper1_release/` nor the root-level
`paper2_development/` directory currently exists, so the planned destinations
do not conflict with existing paths.

## Non-Move Rules

The following shared code and shared configuration paths must remain in the repository root:

| Original path | Planned action | Reason |
|---|---|---|
| `src/` | keep in root | Shared ORB-SLAM2 and semantic RGB-D SLAM implementation |
| `include/` | keep in root | Shared public headers |
| `Examples/` | keep in root | Shared executable examples and camera YAML files |
| `lib/` | keep in root | Shared build/library output location |
| `cmake_modules/` | keep in root | Shared CMake modules |
| `Vocabulary/` | keep in root | Shared ORB vocabulary path |
| `Thirdparty/` | keep in root | Shared third-party dependencies |
| `build/` | keep in root | Existing local build directory; ignored by git |
| `dataset_associations/` | keep in root | Shared TUM association files used by scripts |
| `experiment_new/` | keep in root | Explicitly requested to remain at root |
| `CMakeLists.txt` | keep in root | Shared build entry |
| `build.sh` | keep in root | Shared build script |
| `build_ros.sh` | keep in root | Shared ROS build script |
| `Dependencies.md` | keep in root | Shared dependency note |
| `README.md` | keep in root | Root project entry; update after confirmed move |

## Directories To Create After Confirmation

| New path | Purpose |
|---|---|
| `paper1_release/` | Paper1 release materials |
| `paper1_release/figures/` | Paper1 figure outputs and figure source data |
| `paper1_release/tables/` | Paper1 tables and table conversion outputs |
| `paper1_release/experiments/` | Paper1 experiment summaries/results outside `experiment_new/` |
| `paper1_release/manuscript/` | Paper1 draft, LaTeX, Word and submission files |
| `paper1_release/revision/` | Robot-journal revision/submission support files |
| `paper1_release/trajectories/` | Paper1 TUM/Bonn trajectory outputs and ATE/RPE archives |
| `paper1_release/scripts/` | Paper1-only plotting/helper scripts that are not shared SLAM code |
| `paper2_development/` | Paper2 development workspace |
| `paper2_development/experiments/` | Future Paper2 experiments |
| `paper2_development/figures/` | Future Paper2 figures |
| `paper2_development/results/` | Future Paper2 results |
| `paper2_development/docs/` | Future Paper2 documents |
| `paper2_development/modules/` | Future Paper2 new algorithm modules |
| `paper2_development/modules/ObjectDynamic/` | Reserved module example for Paper2 |

## Planned Moves For Paper1 Release

### Figure Data, Plotting And Figure Source Files

| Original path | New path | Classification reason |
|---|---|---|
| `Paper_Figure_Data/` | `paper1_release/figures/Paper_Figure_Data/` | Paper1 Matplotlib/figure data |
| `Paper_Figure_Plot （初稿最终图片）/` | `paper1_release/figures/Paper_Figure_Plot_初稿最终图片/` | Paper1 figure plotting scripts and outputs |
| `Paper_Figure_Visio（初稿最终系统框架图片）/` | `paper1_release/figures/Paper_Figure_Visio_初稿最终系统框架图片/` | Paper1 Fig.1 system framework source |
| `paper_figs_fr3/` | `paper1_release/figures/paper_figs_fr3/` | Paper1 generated figure set |
| `paper_figs_fr3_tuned3/` | `paper1_release/figures/paper_figs_fr3_tuned3/` | Paper1 generated figure set |
| `paper_figs_fr3_tuned4/` | `paper1_release/figures/paper_figs_fr3_tuned4/` | Paper1 generated figure set |
| `paper_figs_standard/` | `paper1_release/figures/paper_figs_standard/` | Paper1 generated figure set |
| `dynamic_detection_compare.png` | `paper1_release/figures/dynamic_detection_compare.png` | Paper1 detection visualization figure |
| `dynamic_probability_curve.png` | `paper1_release/figures/dynamic_probability_curve.png` | Paper1 temporal/dynamic probability figure |
| `dynamic_ratio_curve.png` | `paper1_release/figures/dynamic_ratio_curve.png` | Paper1 robustness figure |
| `lambda_analysis.png` | `paper1_release/figures/lambda_analysis.png` | Paper1 lambda sensitivity figure |

### Tables And Paper Text

| Original path | New path | Classification reason |
|---|---|---|
| `evaluation_tables/` | `paper1_release/tables/evaluation_tables/` | Paper1 evaluation tables |
| `paper_tables_text/` | `paper1_release/tables/paper_tables_text/` | Paper1 Word/Markdown table conversions |
| `dynamic_detection_results.csv` | `paper1_release/tables/dynamic_detection_results.csv` | Paper1 dynamic detection summary |
| `dynamic_ratio_test.csv` | `paper1_release/tables/dynamic_ratio_test.csv` | Paper1 dynamic-ratio robustness summary |
| `lambda_analysis.csv` | `paper1_release/tables/lambda_analysis.csv` | Paper1 lambda sensitivity summary |
| `lambda_analysis_by_sequence.csv` | `paper1_release/tables/lambda_analysis_by_sequence.csv` | Paper1 lambda sensitivity per-sequence summary |
| `table_format_check.txt` | `paper1_release/tables/table_format_check.txt` | Paper1 Word table-format audit |

### Manuscript, LaTeX And Submission Files

| Original path | New path | Classification reason |
|---|---|---|
| `paper_draft/` | `paper1_release/manuscript/paper_draft/` | Paper1 Markdown draft |
| `paper_latex/` | `paper1_release/manuscript/paper_latex/` | Paper1 LaTeX project |
| `paper_materials/` | `paper1_release/manuscript/paper_materials/` | Paper1 supporting manuscript materials |
| `paper_ready_outputs_v2/` | `paper1_release/manuscript/paper_ready_outputs_v2/` | Paper1 generated manuscript/figure output |
| `paper_ready_outputs_v3/` | `paper1_release/manuscript/paper_ready_outputs_v3/` | Paper1 generated manuscript/figure output |
| `paper_ready_outputs_v4/` | `paper1_release/manuscript/paper_ready_outputs_v4/` | Paper1 generated manuscript/figure output |
| `paper_ready_outputs_v5/` | `paper1_release/manuscript/paper_ready_outputs_v5/` | Paper1 generated manuscript/figure output |
| `paper_ready_outputs_v6/` | `paper1_release/manuscript/paper_ready_outputs_v6/` | Paper1 generated manuscript/figure output |
| `paper_ready_outputs_v7/` | `paper1_release/manuscript/paper_ready_outputs_v7/` | Paper1 generated manuscript/figure output |
| `paper_ready_outputs_v8/` | `paper1_release/manuscript/paper_ready_outputs_v8/` | Paper1 generated manuscript/figure output |
| `paper_ready_outputs_v9/` | `paper1_release/manuscript/paper_ready_outputs_v9/` | Paper1 generated manuscript/figure output |
| `paper_ready_outputs_v10/` | `paper1_release/manuscript/paper_ready_outputs_v10/` | Paper1 generated manuscript/figure output |
| `paper_ready_outputs_v11/` | `paper1_release/manuscript/paper_ready_outputs_v11/` | Paper1 generated manuscript/figure output |
| `paper_ready_outputs_v12/` | `paper1_release/manuscript/paper_ready_outputs_v12/` | Paper1 generated manuscript/figure output |
| `paper_ready_outputs_v13/` | `paper1_release/manuscript/paper_ready_outputs_v13/` | Paper1 generated manuscript/figure output |
| `paper_ready_outputs_v14/` | `paper1_release/manuscript/paper_ready_outputs_v14/` | Paper1 generated manuscript/figure output |
| `paper_ready_outputs_v15/` | `paper1_release/manuscript/paper_ready_outputs_v15/` | Paper1 generated manuscript/figure output |
| `paper_ready_outputs_v16/` | `paper1_release/manuscript/paper_ready_outputs_v16/` | Paper1 generated manuscript/figure output |
| `robot_submission_revision/` | `paper1_release/revision/robot_submission_revision/` | Robot-journal revision/submission package |
| `my_paper.docx` | `paper1_release/manuscript/my_paper.docx` | Paper1 manuscript file |
| `mypaper.docx` | `paper1_release/manuscript/mypaper.docx` | Paper1 manuscript file |
| `mypaper-IEEE  RCAR.docx` | `paper1_release/manuscript/mypaper-IEEE  RCAR.docx` | Related paper manuscript file |
| `修订版 - 副本.docx` | `paper1_release/manuscript/修订版 - 副本.docx` | Paper1 revised Word manuscript |
| `修订版 - 副本_表格三线表.docx` | `paper1_release/manuscript/修订版 - 副本_表格三线表.docx` | Paper1 table-formatted manuscript |
| `结果.odt` | `paper1_release/manuscript/结果.odt` | Paper1/result document |

### Experiment Results And Trajectories Outside `experiment_new/`

| Original path | New path | Classification reason |
|---|---|---|
| `TUM_trajectory_results/` | `paper1_release/experiments/TUM_trajectory_results/` | Paper1 TUM trajectory results |
| `TUM_fr3_walking_xyz_results/` | `paper1_release/experiments/TUM_fr3_walking_xyz_results/` | Paper1 TUM sequence result |
| `TUM_fr3_walking_half_results/` | `paper1_release/experiments/TUM_fr3_walking_half_results/` | Paper1 TUM sequence result |
| `TUM_fr3_walking_static_results/` | `paper1_release/experiments/TUM_fr3_walking_static_results/` | Paper1 TUM sequence result |
| `TUM_fr3_sitting_static_results/` | `paper1_release/experiments/TUM_fr3_sitting_static_results/` | Paper1 TUM sequence result |
| `standard_eval_results/` | `paper1_release/experiments/standard_eval_results/` | Paper1 evaluation results |
| `standard_eval_results_with_candidates/` | `paper1_release/experiments/standard_eval_results_with_candidates/` | Paper1 evaluation results |
| `standard_runs/` | `paper1_release/experiments/standard_runs/` | Paper1 run outputs |
| `YOLO_runs/` | `paper1_release/experiments/YOLO_runs/` | Paper1 YOLO run outputs |
| `baseline_runs_missing/` | `paper1_release/experiments/baseline_runs_missing/` | Paper1 baseline run outputs |
| `baseline_runs_retry/` | `paper1_release/experiments/baseline_runs_retry/` | Paper1 baseline run outputs |
| `baseline_runs_retry2/` | `paper1_release/experiments/baseline_runs_retry2/` | Paper1 baseline run outputs |
| `baseline_runs_retry3_patched/` | `paper1_release/experiments/baseline_runs_retry3_patched/` | Paper1 baseline run outputs |
| `baseline_runs_retry4_patched/` | `paper1_release/experiments/baseline_runs_retry4_patched/` | Paper1 baseline run outputs |
| `orbslam3_runs_missing/` | `paper1_release/experiments/orbslam3_runs_missing/` | Paper1 baseline run outputs |
| `results/` | `paper1_release/experiments/results/` | Paper1 root experiment outputs |
| `DS_SLAM_trajectory/` | `paper1_release/trajectories/DS_SLAM_trajectory/` | Paper1 trajectory output |
| `Dyna_SLAM_trajectory/` | `paper1_release/trajectories/Dyna_SLAM_trajectory/` | Paper1 trajectory output |
| `ORB_SLAM2_trajectory/` | `paper1_release/trajectories/ORB_SLAM2_trajectory/` | Paper1 trajectory output |
| `ORB_SLAM3_trajectory/` | `paper1_release/trajectories/ORB_SLAM3_trajectory/` | Paper1 trajectory output |
| `Semantic_Hard_Remove_trajectory/` | `paper1_release/trajectories/Semantic_Hard_Remove_trajectory/` | Paper1 trajectory output |
| `ate轨迹图half/` | `paper1_release/trajectories/ate轨迹图half/` | Paper1 ATE trajectory figure archive |
| `ate轨迹图sstatic/` | `paper1_release/trajectories/ate轨迹图sstatic/` | Paper1 ATE trajectory figure archive |
| `ate轨迹图wstatic/` | `paper1_release/trajectories/ate轨迹图wstatic/` | Paper1 ATE trajectory figure archive |
| `ate轨迹图xyz/` | `paper1_release/trajectories/ate轨迹图xyz/` | Paper1 ATE trajectory figure archive |
| `ORB_dwp_ATE.zip` | `paper1_release/trajectories/ORB_dwp_ATE.zip` | Paper1 ATE archive |
| `YOLO_dwp_ATE.zip` | `paper1_release/trajectories/YOLO_dwp_ATE.zip` | Paper1 ATE archive |
| `YOLO_xyz_RPE_angle.zip` | `paper1_release/trajectories/YOLO_xyz_RPE_angle.zip` | Paper1 RPE archive |
| `YOLO_xyz_RPE_trans.zip` | `paper1_release/trajectories/YOLO_xyz_RPE_trans.zip` | Paper1 RPE archive |
| `CameraTrajectory.txt` | `paper1_release/trajectories/CameraTrajectory.txt` | Root trajectory artifact |
| `KeyFrameTrajectory.txt` | `paper1_release/trajectories/KeyFrameTrajectory.txt` | Root trajectory artifact |

### Paper1 Helper Scripts Outside Shared Script Directory

| Original path | New path | Classification reason |
|---|---|---|
| `plot_trajectory_ate.py` | `paper1_release/scripts/plot_trajectory_ate.py` | Paper1 plotting helper |
| `my_plot.py` | `paper1_release/scripts/my_plot.py` | Paper1 plotting/helper script |

### Version And Reproduction Notes

Current git status shows `REPRODUCTION.md` and `VERSION_HISTORY.md` as deleted, with renamed Chinese files present. This likely came from a manual rename in the working tree.

| Original/current path | New path | Classification reason |
|---|---|---|
| `REPRODUCTION(复现实验说明).md` | `paper1_release/REPRODUCTION.md` | Paper1 reproduction note; restore canonical name inside release folder |
| `VERSION_HISTORY( 版本说明).md` | `paper1_release/VERSION_HISTORY.md` | Paper1 version note; restore canonical name inside release folder |

## Items Requiring Confirmation Before Moving

| Path | Proposed action | Reason |
|---|---|---|
| `scripts/` | keep in root for now | Contains shared experiment/evaluation entry points; moving could break reproduction commands |
| `experiment_new/` | keep in root | Explicitly requested not to move |
| `dataset_associations/` | keep in root | Explicitly requested not to move |
| `yolov5_RemoveDynamic/` | keep in root | External detector dependency; large and currently ignored by git |
| `baselines/` | keep in root | External baseline dependency; not requested for movement |
| `rgbd_dataset_freiburg3_walking_static/` | keep in root | Dataset-like directory; avoid moving dataset inputs unless explicitly requested |
| `server_socket` and `.orb_*.sock` | leave untouched / ignored | Runtime IPC artifacts; not part of paper release organization |
| `REPRODUCTION.md` / `VERSION_HISTORY.md` deleted status | handle during confirmed move | Need to avoid accidentally losing canonical tracked file history |

### Bonn Result Boundary

- Bonn outputs below `YOLO_runs/` move together with `YOLO_runs/` into
  `paper1_release/experiments/YOLO_runs/`.
- Bonn data, results, figures, tables and scripts below `experiment_new/` stay
  in the root-level `experiment_new/`, as explicitly required.
- Bonn figures/tables already contained in `paper_latex/`,
  `paper_tables_text/` and `robot_submission_revision/` move with those planned
  Paper1 directories.

## README Update Planned After Confirmation

After file movement is confirmed and completed, update root `README.md` with:

- `paper1_tce_release`: frozen Paper1 release branch and tag `paper1_submission_v1.0`.
- `paper2_development`: active Paper2 development branch.
- `paper1_release/`: location of Paper1 manuscript, figures, tables and release artifacts.
- `paper2_development/`: location for new Paper2 experiments, figures, results, docs and modules.
- Note that shared SLAM code remains in root (`src/`, `include/`, `Examples/`, `Thirdparty/`, etc.).

## Git Operations Planned After Confirmation

1. Create directories listed above.
2. Move files using `git mv` where files are tracked; use `mv` for ignored/untracked artifacts.
3. Update `README.md`.
4. Run `git status`.
5. Commit:

```bash
git commit -m "Organize project structure for paper1 release and paper2 development"
```

No push will be performed.

## Confirmation Gate

Stop after generating this plan. Do not create directories, move files, update
`README.md`, or commit until the user explicitly confirms this plan.
