# Experiment Configs

本目录用于保存论文2实验清单和参数说明，不用于自动修改源码或编译宏。

每组正式实验建议记录：

- 实验名称及 run name；
- Git commit 和 tag；
- 可执行文件路径及校验值；
- Shadow/Active 编译开关；
- 数据集、association 和相机 settings；
- YOLO 模型、检测结果或 socket 配置；
- ObjectDynamic 参数与消融项；
- 重复运行次数和随机性说明。

相机 YAML 等已有公共配置保持原位置，实验清单只引用其路径，避免产生未经说明的重复配置。
