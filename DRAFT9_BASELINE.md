# Draft 9 experiment baseline

This file freezes the source and experiment-script baseline used for the
PAA/PRL extension experiments. Generated results, datasets, model weights,
build directories, and local baseline binaries are deliberately excluded from
Git and are identified by path and hash where applicable.

## Freeze identity

- Freeze date: 2026-08-23 (Asia/Shanghai)
- Parent commit: `92733684846a6c578d409b127a4271876ea27077`
- Branch at freeze: `main`
- Baseline commit: the commit containing this file
- Scope: tracked project source, the three Draft 9 tracked modifications, and
  the current final-paper Python experiment scripts
- Excluded: `experiments/`, `experiment_new/`, `results/`, build directories,
  datasets, model weights, `baselines/`, SAM assets, logs, sockets, and `.save`
  files

## Draft 9 semantic defaults

The values below were read from `include/SemanticConfig.h` at freeze time.

| Parameter | Normal dynamic class | Person |
|---|---:|---:|
| Dynamic score threshold | 3.0 | 2.0 |
| Evidence increment | 1.0 | 1.0 |
| Evidence decay | 0.95 | 0.90 |

The active dynamic class set is person-only (`class_id=3`). Main experiments
must not override these values. Sensitivity runs must parse their defaults from
the checked-out `SemanticConfig.h` and record the parsed values per run.

## Main configuration contract

| Configuration | SemanticMode | Object map | Shadow | Active |
|---|---:|---:|---:|---:|
| ORB-SLAM2 | 0 | 0 | 0 | 0 |
| Semantic | 1 | 0 | 0 | 0 |
| Temporal | 2 | 0 | 0 | 0 |
| Full | 2 | 1 | 1 | 1 |

DynaSLAM and DS-SLAM are external baselines and are not part of these four
configurations or their repetition count.

## Key file SHA-256 at freeze

| File | SHA-256 |
|---|---|
| `CMakeLists.txt` | `7e6b59c51cd20a91bc3a78c1beb416c0eca3fc1e704f7ab0a015c916f5711e3a` |
| `Examples/RGB-D/rgbd_tum.cc` | `847842553fd84fbb872ee5b10d498c862a4198e5508df28b548fef3f0fd03524` |
| `include/SemanticConfig.h` | `487ceb5957c8cc90a27ade8211f9187e747f14ec90ff05d5ac4a39635b177630` |
| `include/Tracking.h` | `e39a0346b6e534c13fcc740ceda30064763424de9207883055424fc58af87031` |
| `src/Tracking.cc` | `a249570078f18f149bbc485e8f6ee2dfa64c3668d9f92fd9f15126cd0c1231f0` |
| `src/MapPoint.cc` | `bdacedc9a3ceb6d8cfde21970a14de2745f888bf7ffdc7d6813a40e3791db786` |
| `src/ORBmatcher.cc` | `15356eb8300d04a7676167603467e8344ed5c94167ae25096a79568f920298ea` |
| `scripts/run_tum_rgbd_experiment.py` | `3dc70d9fa853a7ef13ff3ff2c74b59ff4938b730ba06c6fb82762487b6482377` |
| `scripts/evaluate_tum_metrics.py` | `cfdd35d556afcd5d080fe109396f5ffa7da1810a5e2c26a656c648216db24b13` |
| `Examples/RGB-D/TUM3.yaml` | `3c6e1782dfe35feb782d430348ce40923ee99de998748633e9b6821cdfc2ce67` |
| `dataset_associations/fr3_walking_xyz_associate.txt` | `ab704a8160ae078e63de1b3f84498ebe2cfcf1561713f0ba9f73ea6d205c8fa0` |
| `dataset_associations/fr3_walking_rpy_associate.txt` | `34e8fb45667449f11d853de05f3a3eab9748c5559fc093e7004644b4c70607f3` |
| `dataset_associations/fr3_walking_halfsphere_associate.txt` | `82cba27e140ddb5c6b84039bf22ae91e04524ba841293449f7a96836f997c347` |
| `yolov5_RemoveDynamic/weights/yolov5s.pt` | `3cb5c452360bc5c1dfd19ab0aca46f5e15a64af028846867310313a966cfe920` |
| `Examples/RGB-D/rgbd_tum` | `58e463c75c25fc2c3268bb9bd053f8084d0736a6b45a0bb5ddf5b855d1e1373c` |
| `lib/libORB_SLAM2.so` | `771e36dad152ef0b82c4e9be2280da1e59823fb98b23cf01f6a3d2b5e8ad2f10` |

## Evaluation rules

- Main configurations use six TUM RGB-D sequences and five fixed repetitions.
- Failed or interrupted attempts are retained and never replaced silently.
- ATE/RPE must always be reported with TSR/PMR and trajectory coverage.
- A short trajectory after tracking failure is not considered a better result.
- Runtime excludes the first 30 processed frames only from timing aggregates;
  all frames remain in trajectory, ATE, RPE, TSR, PMR, and SF evaluation.
- DynaSLAM results are not paper-eligible unless the complete Mask R-CNN
  weights and semantic execution path are verified and recorded.
