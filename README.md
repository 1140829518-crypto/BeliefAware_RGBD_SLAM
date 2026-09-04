# BeliefAware_RGBD_SLAM

Official implementation of:

**Belief-Aware Persistent Landmark Modeling with Reliability-Adaptive Measurement Selection for Dynamic RGB-D SLAM**

This repository provides the source code, experimental configurations, dataset association files, and evaluation tools for the proposed belief-aware RGB-D SLAM framework.

The repository corresponds to the current manuscript version (Manuscript3).


## Overview

Dynamic objects introduce significant challenges to RGB-D SLAM systems because incorrect observations may be incorporated into the persistent map and degrade long-term localization accuracy.

This repository implements a belief-aware persistent landmark modeling framework that maintains temporal states directly on persistent SLAM MapPoints.

Instead of performing only frame-level dynamic filtering, the proposed framework treats persistent landmarks as carriers of temporal dynamic states and jointly models:

- dynamic probability
- uncertainty evolution
- temporal evidence accumulation
- reliability-aware measurement adaptation

The estimated landmark states are continuously updated and used to regulate the contribution of observations during SLAM optimization.


## Manuscript Version

This repository corresponds to the manuscript:

**Belief-Aware Persistent Landmark Modeling with Reliability-Adaptive Measurement Selection for Dynamic RGB-D SLAM**

The released code, configurations, and evaluation scripts correspond to the experiments reported in this manuscript.



## Main Features

- Persistent MapPoint-level belief representation
- Temporal evidence accumulation on landmark states
- Dynamic probability and uncertainty estimation
- Reliability-adaptive measurement weighting
- RGB-D SLAM evaluation pipeline
- Reproducible experiment configurations and scripts


## Repository Structure
src/ Core SLAM implementation
include/ Header files
Examples/ Running examples
scripts/ Experiment and evaluation scripts
experiment_new/ Experimental configurations
experiments/ Analysis and visualization tools
dataset_associations/ Dataset association files
Thirdparty/ Third-party dependencies



## Requirements

The system has been tested under:

- Ubuntu 20.04
- ROS Noetic
- C++14
- OpenCV
- Eigen
- Pangolin



## Installation  

Clone the repository:

```bash
git clone https://github.com/1140829518-crypto/BeliefAware_RGBD_SLAM.git

cd BeliefAware_RGBD_SLAM

Build the system:
chmod +x build.sh

./build.sh

## Dataset Preparation

The experiments in this repository use public RGB-D datasets, including:
TUM RGB-D Dataset
Bonn RGB-D Dynamic Dataset

Dataset download links:

- TUM RGB-D Dataset:
  https://vision.in.tum.de/data/datasets/rgbd-dataset

- Bonn RGB-D Dynamic Dataset:
  https://www.ipb.uni-bonn.de/data/rgbd-dynamic-dataset/

The datasets are not redistributed in this repository because they are provided and maintained by their original authors.
Please download the datasets from their official sources and configure the dataset paths before running experiments.
The repository provides dataset association files, configuration examples, and evaluation procedures required for reproducing the reported experiments.

## Repository Structure

| Directory | Description |
|---|---|
| `src/` | Core SLAM implementation |
| `include/` | Header files |
| `Examples/` | Running examples |
| `scripts/` | Experiment and evaluation scripts |
| `experiment_new/` | Experimental configurations |
| `experiments/` | Analysis and visualization tools |
| `dataset_associations/` | Dataset association files |
| `Thirdparty/` | Third-party dependencies |

To reproduce the reported results:

1. Download the required public RGB-D datasets.
2. Configure dataset paths.
3. Compile the SLAM system.
4. Run experiment scripts.
5. Evaluate results.
All algorithmic parameters, uncertainty settings, dynamic thresholds, and evaluation protocols used in the manuscript are included in this repository.

## Release
The official reproducible release is available at:
https://github.com/1140829518-crypto/BeliefAware_RGBD_SLAM/releases/tag/v1.0.0

## Citation
If you use this repository in your research, please cite:
Citation information will be added after publication.

## License
This project is released for academic research purposes.


