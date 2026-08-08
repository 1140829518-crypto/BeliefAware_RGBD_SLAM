# 未解决信息清单

- GPU型号：`nvidia-smi` 返回 GPU access blocked，无法确认。应在实际实验机器上查询；Word位置：实验环境表。
- CUDA版本：当前无法确认有效CUDA运行时版本。应在实验机器上查询 `nvcc --version`、驱动/CUDA日志或PyTorch CUDA运行信息；Word位置：实验环境表。
- 有效git提交号：当前 `.git` 目录不可作为有效仓库读取，独立实验 `run_config.json` 也记录为 not available。应提供源码提交号或版本标签；Word位置：实验环境表。
- 通信作者、基金、作者单位英文规范写法等投稿信息：当前任务未提供。应由作者按《机器人》模板填写；Word位置：首页/脚注/基金项目。
- Switching Frequency目标级正式定义：当前代码输出为基于 `dynamic_objects > 0` 的帧级聚合代理指标，不含目标ID。若论文需要目标级公式，应补充代码实现或标注协议；Word位置：评价指标定义。
- 图7真实三维对象级语义地图证据：当前未确认包含对象ID、三维包围框、类别、动态/静态状态的完整三维地图图像。因此本文修订版采用“动态目标及语义动态点可视化结果”；Word位置：图7标题及分析段落。
- LibreOffice headless PDF转换验证：转换命令长时间未返回，被终止。docx压缩结构已通过 `unzip -t` 检查，但建议作者用Microsoft Word/WPS打开后再人工检查分页、跨页表题和图题位置。
