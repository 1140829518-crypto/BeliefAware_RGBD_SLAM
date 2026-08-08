# 投稿前重点修订审计报告

## 文件状态

1. 修改后的Word文件路径：`/home/djn/123/ORB_SLAM2_AddSemantic/robot_submission_revision/《机器人》(12)_重点修订版.docx`。
2. 原始Word是否被修改：否。源文件 `/mnt/e/研/My_Research/Paper/《机器人》.docx` 未覆盖，修订版仅保存到项目内 `robot_submission_revision/`。
3. 参考模板读取情况：已读取 `/mnt/e/研/My_Research/Paper/《机器人》写作模板_word版（推荐）.docx` 的文本和表格结构，用于核对基本表题/图题习惯；未覆盖模板。
4. 压缩结构检查：`unzip -t` 未发现压缩数据错误。
5. LibreOffice headless PDF转换：命令长时间未返回，已终止；建议作者用Word/WPS人工打开确认最终分页。

## 表1拆分结果

- 已在Word副本中将原表1拆分为表1(a) ATE和表1(b) RPE两个Word原生表格。
- 同步生成：`table1_ate.csv`、`table1_rpe.csv`、`table1_ate.tex`、`table1_rpe.tex`。
- 表1(a)和表1(b)最终数据：与用户给定原论文数据一致，均保留4位小数。
- 表1是否使用三线表：OpenXML中设置为顶线、表头下横线和底线，无竖线。
- 自动检查：旧式 `0.0092/0.0055` 合并单元格文本已不存在。

## 表5重构结果

- 已在Word副本中重构表5为Word原生三线表。
- 同步生成：`table5_ablation.csv`、`table5_ablation.tex`。
- 表5保留指标：ATE、RPE、FPS、Pose Missing Ratio、Switching Frequency。
- 表5未放入F1-score。
- Baseline的Switching Frequency显示为“—”，不参与最优值判断。
- 表5是否存在断词：表头使用完整短语，未主动插入断词或换行。

## 图6重排结果

- Word中的旧图6图片已替换为 `figure6_ablation_revised.png`。
- 同步生成：`figure6_ablation_revised.pdf/.eps/.svg/.png`。
- 图6使用的数据：`experiment_new/independent_ablation_v3/aggregated_results/ablation_results.csv`。
- 是否修改均值或标准差：否。
- 子图标题是否移至下方：是，修订图中(a)–(d)子图标题位于各子图下方居中。
- 是否删除“Baseline excluded”：是。
- 是否保留“N/A”：是，保留于图像中Baseline的Switching Frequency位置。
- PNG尺寸：4290 × 3044 px，600 dpi。

## 图7调整结果

- 图7原标题：`图7 对象级语义地图可视化结果` / `Fig.7 Visualization of the object-level semantic map`。
- 图7新标题：`图7 动态目标及语义动态点可视化结果` / `Fig.7 Visualization of dynamic objects and semantic dynamic points`。
- 已删除或弱化的结论：完整静态场景结构和动态目标三维信息、对象空间位置及运动状态直接记录、完整分层三维表达、长期地图维护能力已由图7证明等表述。
- 新正文强调：动态目标检测区域和语义动态点可为动态特征降权/过滤以及后续对象信息管理提供语义观测。

## 实验环境与评价指标

- 已新增“3.1 实验环境与评价指标”内容和实验平台表。
- 成功识别的配置：CPU i7-10870H、可见内存7.6 GiB、Ubuntu 20.04.6 LTS on WSL2、OpenCV 4.2.0、YOLOv5 + yolov5s.pt、CPU推理、输入640×480/YOLO img-size 224、evaluate_tum_metrics.py、ATE SE(3)对齐、RPE相邻位姿、端到端FPS、每组3次重复。
- 未能确认的配置：GPU、CUDA、有效git提交号、投稿作者/基金等，见 `unresolved_information.md`。
- Pose Missing Ratio定义来源：独立消融包 `metric_definitions.md`，定义为 `R_miss = (N_frame - N_pose) / N_frame`。
- Switching Frequency定义来源：独立消融包 `metric_definitions.md`，为基于 `dynamic_objects > 0` 的帧级聚合代理指标；目标ID级正式定义仍需补充。

## 正文同步调整

- 表1引用已改为“表1(a)和表1(b)”。
- 表5、图6和图7说明已改为定量结果、性能对比以及动态目标及语义动态点可视化结果。
- F1实验和消融实验已增加区分说明：表3检测F1不用于表5。
- `Failure Rate` 已替换为 `Pose Missing Ratio` 相关表述。
- 未发现“Full Model最佳综合性能”字样。
- 未发现“Baseline excluded”在正文XML文本中残留。

## 最终检查

- 表1是否仍有ATE/RPE写在同一个单元格：未发现。
- 表5是否有Pose Missing Ratio和Switching Frequency断词：未主动断词；建议Word中最终打开确认列宽。
- 表格是否仍存在竖线：新生成的表1和表5不含竖线。
- 图6是否仍有“Baseline excluded”：未发现。
- 图7是否仍称为对象级语义地图可视化结果：未发现旧图7标题。
- 是否存在编造环境信息：未确认项均保留为“待补充”。
- 是否覆盖原始论文：否。
- 当前仍存在影响投稿的硬问题：需要作者用Word/WPS打开修订版做最终分页、跨页和版式检查；GPU、CUDA、git提交号、基金/通信作者信息需人工补充。
