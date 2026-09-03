# BeliefAware_RGBD_SLAM

Official implementation of:

**Belief-Aware Persistent Landmark Modeling with Reliability-Adaptive Measurement Selection for Dynamic RGB-D SLAM**

This repository provides the source code, experimental configurations, and evaluation tools for the proposed belief-aware RGB-D SLAM framework.


## Overview

Dynamic objects introduce significant challenges to RGB-D SLAM systems because incorrect observations may be incorporated into the persistent map and degrade long-term localization accuracy.

This repository implements a belief-aware persistent landmark modeling framework that maintains temporal states directly on persistent SLAM MapPoints.

The proposed framework jointly models:

- dynamic probability
- uncertainty evolution
- temporal evidence accumulation
- reliability-aware measurement selection

Different from conventional frame-level dynamic filtering approaches, the proposed method performs temporal reasoning on persistent landmark identities and adaptively regulates their contribution during SLAM optimization.


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


Dataset Preparation

The experiments are evaluated on public RGB-D datasets, including:

TUM RGB-D Dataset
Bonn RGB-D Dynamic Dataset

Please download the datasets from their official sources and configure the dataset paths before running experiments.

Reproduce Experiments

The released package contains the implementation, configuration files, experiment scripts, and evaluation tools required to reproduce the results reported in the paper.

Typical reproduction procedure:

Prepare the RGB-D datasets.
Modify dataset paths in the configuration files.
Compile the SLAM system.
Run the provided experiment scripts.
Evaluate results using the provided evaluation tools.

All experimental parameters and configurations are provided in this repository.

Release

The official reproducible release is available at:

https://github.com/1140829518-crypto/BeliefAware_RGBD_SLAM/releases/tag/v1.0.0

Citation

If you use this repository in your research, please cite:
Citation information will be added after publication.

License

This project is released for academic research purposes.
