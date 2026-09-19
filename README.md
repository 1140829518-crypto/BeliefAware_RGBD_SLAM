# BeliefAware_RGBD_SLAM

Official implementation of:

**Persistent MapPoint-Level Temporal Evidence Fusion for RGB-D SLAM in Dynamic Environments**

This repository provides the source code, experimental configurations, dataset association files, evaluation tools, and reproducibility package for the proposed belief-aware RGB-D SLAM framework.

The repository corresponds to the manuscript submitted to **Pattern Analysis and Applications (Springer)**.

---

# Overview

Dynamic objects introduce significant challenges to RGB-D SLAM systems because unreliable observations may be incorporated into the persistent map and degrade long-term localization accuracy.

This repository implements a belief-aware persistent landmark modeling framework that maintains temporal states directly on persistent SLAM MapPoints.

Different from approaches that only perform frame-level dynamic filtering, the proposed framework models persistent landmarks as carriers of temporal dynamic states and jointly considers:

- dynamic probability estimation
- uncertainty evolution
- temporal evidence accumulation
- reliability-aware measurement adaptation

The estimated landmark states are continuously updated and used to regulate the contribution of observations during SLAM optimization.

---

# Manuscript Information

This repository corresponds to the manuscript:

**Persistent MapPoint-Level Temporal Evidence Fusion for RGB-D SLAM in Dynamic Environments**

The released source code, configurations, and evaluation scripts correspond to the experiments reported in the manuscript.

The exact reproducible version is archived as:

**v1.0-paa-final**

---

# Main Features

- Persistent MapPoint-level belief representation
- Temporal evidence accumulation on landmark states
- Dynamic probability estimation
- Uncertainty-aware landmark modeling
- Reliability-adaptive measurement selection
- RGB-D SLAM evaluation pipeline
- Reproducible experiment configurations
- Frozen evaluation protocols and scripts

---

# Repository Structure

| Directory | Description |
|---|---|
| `src/` | Core SLAM implementation |
| `include/` | Header files |
| `Examples/` | Running examples and configuration files |
| `scripts/` | Experiment execution and evaluation scripts |
| `experiment_new/` | Experimental configurations |
| `experiments/` | Analysis and visualization tools |
| `dataset_associations/` | Dataset association files |
| `Thirdparty/` | Third-party dependencies |
| `release/v1.0-paa/` | Reproducibility release documents and audit files |

---

# Requirements

The system has been tested under:

- Ubuntu 20.04 LTS
- ROS Noetic
- GCC 9
- C++14
- OpenCV
- Eigen
- Pangolin

For semantic dynamic modules, additional dependencies are documented in the release package.

---

# Installation

Clone the repository:

```bash
git clone https://github.com/1140829518-crypto/BeliefAware_RGBD_SLAM.git

cd BeliefAware_RGBD_SLAM

Build the system:
chmod +x build.sh

./build.sh


Dataset Preparation

The experiments use public RGB-D datasets:

TUM RGB-D Dataset
Bonn RGB-D Dynamic Dataset

Dataset download links:

TUM RGB-D Dataset:

https://vision.in.tum.de/data/datasets/rgbd-dataset

Bonn RGB-D Dynamic Dataset:

https://www.ipb.uni-bonn.de/data/rgbd-dynamic-dataset/

The datasets are not redistributed in this repository because they are provided and maintained by their original authors.

Users should download the datasets from the official sources and configure the dataset paths before running experiments.

This repository provides:

dataset association files
configuration examples
evaluation procedures
experiment scripts

required for reproducing the reported results.


Reproduce Experiments

To reproduce the reported experiments:

Download the required public RGB-D datasets.
Configure dataset paths.
Compile the SLAM system.
Run the provided experiment scripts.
Evaluate results using the provided evaluation tools.

All algorithmic parameters, uncertainty settings, dynamic thresholds, and evaluation protocols used in the manuscript are included in this repository and the reproducibility release.

Reproducibility Release

The official reproducibility release corresponding to this manuscript is:

v1.0-paa-final

Release page:

https://github.com/1140829518-crypto/BeliefAware_RGBD_SLAM/releases/tag/v1.0-paa-final

The release package contains:

source code
experiment configurations
evaluation scripts
dataset association files
environment documentation
frozen binaries
SHA256 manifests for protected artifacts

The released version corresponds exactly to the experimental configurations and evaluation protocols used for the manuscript.

External DS-SLAM comparison results are provided as OUR RUN, with provenance limitations documented in the release audit files.


Citation

If you use this repository in your research, please cite the associated manuscript:

Persistent MapPoint-Level Temporal Evidence Fusion for RGB-D SLAM in Dynamic Environments

Citation information will be updated after publication.


License

This project is released for academic research purposes.

Please refer to the included license file for details.




