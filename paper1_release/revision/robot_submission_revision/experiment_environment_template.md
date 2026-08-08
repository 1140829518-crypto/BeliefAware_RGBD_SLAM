# 实验环境与评价指标模板

| Item | Configuration |
|---|---|
| CPU | Intel(R) Core(TM) i7-10870H CPU @ 2.20GHz; 8 cores/16 threads (from lscpu) |
| GPU | <mark>待补充</mark> |
| Memory | 7.6 GiB visible in current WSL environment (from free -h) |
| Operating System | Ubuntu 20.04.6 LTS on Linux 6.18.33.2-microsoft-standard-WSL2 |
| CUDA | <mark>待补充</mark> |
| OpenCV | 4.2.0 |
| SLAM Framework | ORB-SLAM2-derived RGB-D executable Examples/RGB-D/rgbd_tum; git commit not available |
| Semantic Detector | YOLOv5 detect_speedup_send.py with yolov5s.pt |
| Inference Device | CPU (--device cpu) |
| Input Resolution | 640 × 480 TUM RGB-D images; YOLO inference img-size 224 |
| Trajectory Evaluation Tool | experiment_new/independent_ablation_v3/evaluation/scripts/evaluate_tum_metrics.py |
| ATE Alignment Method | SE(3) rigid alignment; timestamp tolerance 0.02 s |
| RPE Definition | Adjacent associated poses; translational RMSE in m and rotational RMSE in deg |
| FPS Measurement Scope | End-to-end wall-clock FPS including YOLO startup/inference for semantic modes, SLAM tracking, shutdown and file output |
| Repeated Runs | 3 runs per sequence/configuration; 45 independent ablation runs total |

## 正文建议

实验在配置为Intel(R) Core(TM) i7-10870H CPU @ 2.20GHz、<mark>待补充</mark> GPU和7.6 GiB可见内存的计算机上进行，操作系统为Ubuntu 20.04.6 LTS on WSL2。系统基于ORB-SLAM2派生RGB-D框架实现，当前目录无法确认有效git提交号。语义检测模块采用YOLOv5 `detect_speedup_send.py` 和 `yolov5s.pt` 权重，并通过CPU完成推理。输入RGB-D图像分辨率为640×480，YOLO推理尺寸为224。ATE和RPE采用项目内 `evaluate_tum_metrics.py` 计算，其中ATE采用SE(3)刚体对齐，RPE按照相邻关联位姿统计。FPS统计范围为端到端运行时间，包括语义检测、SLAM跟踪、系统关闭和文件输出。除特别说明外，每组实验独立运行3次，结果以均值±标准差表示。

## Pose Missing Ratio定义

R_miss = (N_frame - N_pose) / N_frame

其中，N_frame表示输入图像总帧数，N_pose表示成功输出有效相机位姿的帧数，R_miss表示位姿缺失率。该指标不等同于严格意义上的系统失败概率。

## Switching Frequency定义说明

当前独立消融包中的Switching Frequency为基于 `SemanticDynamicStatistics.txt` 的帧级聚合代理指标：统计 `dynamic_objects > 0` 的帧级状态在相邻有效帧之间发生变化的次数，并除以有效相邻帧对数量。该实现不是目标ID级切换频率；目标进入/离开画面和多目标ID级汇总无法从当前日志严格确认。
