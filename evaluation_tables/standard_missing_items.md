# Missing Standard Experiment Items

| Sequence | Method | Status | Dataset | Association | Notes |
| --- | --- | --- | --- | --- | --- |
| fr3_walking_xyz | Hard Remove | needs_run | /home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz | /home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz/associate.txt | Run with ORB_SLAM2_SEMANTIC_MODE=1 |
| fr3_walking_xyz | Dynamic Score | needs_run | /home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz | /home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz/associate.txt | Run ablation with dynamic accumulation and without reporting object-map contribution |
| fr3_walking_xyz | Full Method | candidate_existing | /home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz | /home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_xyz/associate.txt | Existing semantic trajectory; verify run setting before final paper use |
| fr3_walking_rpy | Hard Remove | needs_run | /home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_rpy | dataset_associations/fr3_walking_rpy_associate.txt | Run with ORB_SLAM2_SEMANTIC_MODE=1 |
| fr3_walking_rpy | Dynamic Score | needs_run | /home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_rpy | dataset_associations/fr3_walking_rpy_associate.txt | Run ablation with dynamic accumulation |
| fr3_walking_rpy | Full Method | needs_run | /home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_rpy | dataset_associations/fr3_walking_rpy_associate.txt | Run full method |
| fr3_walking_halfsphere | Hard Remove | needs_run | /home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_halfsphere | /home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_halfsphere/associate.txt | Run with ORB_SLAM2_SEMANTIC_MODE=1 |
| fr3_walking_halfsphere | Dynamic Score | needs_run | /home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_halfsphere | /home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_halfsphere/associate.txt | Run ablation with dynamic accumulation |
| fr3_walking_halfsphere | Full Method | candidate_existing | /home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_halfsphere | /home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg3_walking_halfsphere/associate.txt | Existing semantic trajectory; verify naming and run setting before final paper use |
| fr3_walking_static | Dynamic Score | needs_run | rgbd_dataset_freiburg3_walking_static | rgbd_dataset_freiburg3_walking_static/associate.txt | Need separate Dynamic Score ablation trajectory if object-map contribution must be isolated |
| fr1_xyz | ORB-SLAM2 | needs_run | /home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg1_xyz | dataset_associations/fr1_xyz_associate.txt | Dataset found; run ORB-SLAM2 baseline |
| fr1_xyz | Hard Remove | needs_run | /home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg1_xyz | dataset_associations/fr1_xyz_associate.txt | Dataset found; run hard remove |
| fr1_xyz | Dynamic Score | needs_run | /home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg1_xyz | dataset_associations/fr1_xyz_associate.txt | Dataset found; run Dynamic Score |
| fr1_xyz | Full Method | needs_run | /home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg1_xyz | dataset_associations/fr1_xyz_associate.txt | Dataset found; run Full Method |
| fr1_desk | ORB-SLAM2 | needs_run | /home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg1_desk | dataset_associations/fr1_desk_associate.txt | Dataset found; run ORB-SLAM2 baseline |
| fr1_desk | Hard Remove | needs_run | /home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg1_desk | dataset_associations/fr1_desk_associate.txt | Dataset found; run hard remove |
| fr1_desk | Dynamic Score | needs_run | /home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg1_desk | dataset_associations/fr1_desk_associate.txt | Dataset found; run Dynamic Score |
| fr1_desk | Full Method | needs_run | /home/djn/datasets/TUMRGBD/rgbd_dataset_freiburg1_desk | dataset_associations/fr1_desk_associate.txt | Dataset found; run Full Method |
