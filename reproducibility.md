# PAA reproducibility guide

## 1. Scope

This guide reproduces the evaluated V3 `BELIEF_ONLY` and V4
`GEOMETRY_PROTECTED` configurations on three TUM RGB-D and three Bonn RGB-D
Dynamic sequences and evaluates TUM-format trajectories. It also documents
how to evaluate trajectories produced by the local DS-SLAM external baseline.

The release does not contain datasets, model weights, generated trajectories,
raw logs, compiled binaries, or the local DS-SLAM source tree. The DS-SLAM
results in the paper are **OUR RUN** results; the exact upstream revision of
that local tree was not verifiable.

## 2. Tested environment

The frozen campaigns used Ubuntu 20.04/WSL2, GCC 9.4.0, CMake 3.16.3,
Python 3.8.10, OpenCV 4.2.0, Eigen 3.3.7, Boost 1.71, and a locally installed
Pangolin. DBoW2 and g2o are bundled. The dedicated runtime campaign used an
Intel Core i7-10870H and NVIDIA RTX 3060 Laptop GPU; runtime conclusions are
hardware-specific.

Create the Python analysis environment with:

```bash
conda env create -f environment.yml
conda activate orb-slam2-paper2-paa
```

Semantic modes also require the externally acquired YOLOv5 inference tree and
weights expected by `scripts/run_tum_rgbd_experiment.py`. Install that tree's
own pinned requirements and place `yolov5s.pt` under its `weights/` directory.
These assets are not redistributed here.

## 3. Native build

Install OpenCV, Eigen3, Boost, Pangolin, CMake, and a C++14 compiler, then run:

```bash
chmod +x build.sh
./build.sh
```

Expected outputs are `Examples/RGB-D/rgbd_tum` and `lib/libORB_SLAM2.so`.
Extract or place the ORB vocabulary at `Vocabulary/ORBvoc.txt` before running.
Builds are environment-sensitive; compare hashes only when reproducing the
frozen environment described in `RESULTS.md`.

## 4. Dataset acquisition

Download datasets from their official project pages and keep them outside the
repository:

- TUM RGB-D benchmark: `fr3_walking_xyz`, `fr3_walking_static`, and
  `fr3_walking_rpy`.
- Bonn RGB-D Dynamic Dataset: `rgbd_bonn_person_tracking`,
  `rgbd_bonn_synchronous`, and `rgbd_bonn_crowd`.

Each sequence directory must contain `rgb/`, `depth/`, and `groundtruth.txt`.
TUM association files are provided in `dataset_associations/`. For Bonn,
generate or retain `associate.txt` inside each sequence without changing the
association protocol. Use `configs/Bonn.yaml`; do not substitute TUM
intrinsics. See `configs/sequences.example.yml` for the path convention.

## 5. Frozen method configurations

V3 and V4 must use semantic method `belief-active`, MapPoint ownership,
persistent uncertainty, belief and reliability enabled, and both legacy
temporal weighting and hard rejection disabled. They differ only in:

```text
V3: ORB_SLAM2_MEASUREMENT_POLICY=BELIEF_ONLY
V4: ORB_SLAM2_MEASUREMENT_POLICY=GEOMETRY_PROTECTED
```

The complete exported environment is documented in `configs/methods.env`.
Do not edit algorithm parameters or thresholds for reproduction.

## 6. Reproduction entry point

First print the complete plan without executing SLAM:

```bash
./reproduce_paa_results.sh --plan
```

To execute V3 and V4 (three predetermined runs per method/sequence):

```bash
TUM_ROOT=/datasets/TUMRGBD \
BONN_ROOT=/datasets/bonn_rgbd_dynamic \
OUTPUT_ROOT=/outputs/orb_slam2_paa \
YOLO_DEVICE=0 \
./reproduce_paa_results.sh --run internal
```

Run only one method with `--run v3` or `--run v4`. Existing successful output
directories are not silently replaced by this entry point.

To evaluate already generated DS-SLAM trajectories using the same evaluator:

```bash
TUM_ROOT=/datasets/TUMRGBD \
BONN_ROOT=/datasets/bonn_rgbd_dynamic \
DS_SLAM_RESULTS_ROOT=/outputs/dsslam_six_sequence/runs \
OUTPUT_ROOT=/outputs/orb_slam2_paa \
./reproduce_paa_results.sh --run dsslam-eval
```

This command evaluates DS-SLAM outputs; it does not claim to reconstruct the
unverifiable upstream DS-SLAM revision.

## 7. Evaluator

For one trajectory:

```bash
./evaluation/evaluate_trajectory.sh \
  /path/to/groundtruth.txt \
  /path/to/CameraTrajectory.txt \
  /path/to/evaluation_output
```

The underlying evaluator is `scripts/evaluate_tum_metrics.py`. It performs
timestamp association with a default 0.02 s tolerance, rigid SE(3) alignment
for ATE, and frame-to-frame RPE. TSR and PMR are coverage metrics produced by
the experiment summaries and must use the same association-frame denominator.

## 8. Provenance and non-selection rules

- Use three predetermined runs per method-sequence cell.
- Retain failures and incomplete trajectories.
- Do not select the best run.
- Record dataset, association, settings, executable, library, and evaluator
  hashes in every run manifest.
- Do not compare heavily instrumented accuracy runs with lightweight runtime
  runs as if their timing conditions were identical.
- Treat low trajectory coverage as a limitation when interpreting ATE/RPE.

Authoritative hashes and result locations are listed in `RESULTS.md`.
