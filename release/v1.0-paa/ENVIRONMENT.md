# Recorded release environment

## Native system

| Component | Recorded version |
|---|---|
| OS | Ubuntu 20.04.6 LTS under WSL2 |
| Kernel | Linux 6.18.33.2-microsoft-standard-WSL2 x86_64 |
| C++ compiler | GCC/G++ 9.4.0 |
| CMake | 3.16.3 |
| OpenCV used by native build | 4.2.0 (`libopencv-dev 4.2.0+dfsg-5`) |
| Eigen | 3.3.7 (`libeigen3-dev 3.3.7-2`) |
| Boost | 1.71 (`libboost-dev 1.71.0.0ubuntu2`) |
| Pangolin | 0.8, locally installed |
| DBoW2 | bundled source |
| g2o | bundled source |

## Python/semantic environment

| Component | Recorded version |
|---|---|
| Python | 3.8.10 |
| NumPy | 1.24.4 |
| SciPy | 1.10.1 |
| Matplotlib | 3.7.5 |
| pandas | 2.0.3 |
| PyYAML | 5.3.1 |
| Pillow | 10.4.0 |
| Python OpenCV | 4.10.0 |
| PyTorch | 2.4.1+cu121 |
| torchvision | 0.19.1+cu121 |
| CUDA reported by PyTorch | 12.1 |
| cuDNN reported by PyTorch | 9.1.0 |

The dedicated runtime campaign records an Intel Core i7-10870H CPU and NVIDIA
RTX 3060 Laptop GPU. At release-audit time, NVML access from the sandbox was
blocked, so the installed NVIDIA driver version could not be re-queried. No
driver version is invented here.

The repository-level `environment.yml` freezes the Python analysis packages.
Native dependencies remain system packages and must be reproduced separately.
