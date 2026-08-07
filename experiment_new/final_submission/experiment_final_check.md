# 投稿前最终实验检查

检查对象：`experiment_new/final_submission/`

## 1. pending 数据检查

结论：未发现 pending 数据进入 final_submission。

已明确排除以下非投稿结果文件：

- `experiment_new/results/bonn_dataset_comparison.csv`：旧 Bonn 模板，包含 `pending_dataset`。
- `experiment_new/results/real_robot_experiment_manifest.csv`：真实机器人采集清单，仍为 `pending`。
- `experiment_new/tables/table_bonn_dataset_comparison.tex`：旧模板表。
- `experiment_new/tables/table_real_robot_manifest.tex`：采集清单表。

## 2. 模板文件检查

结论：final_submission 中未纳入 Bonn 模板表和真实机器人 pending 表。最终表格仅保留：

- Table1_TUM_ATE_RPE.tex
- Table2_Bonn_Dynamic_Results.tex
- Table3_Dynamic_Detection_Accuracy.tex
- Table4_Parameter_Sensitivity.tex
- Table5_Ablation.tex

## 3. 实验描述夸大检查

结论：未发现禁用夸大表述。

正文采用了审慎表述，例如：

- “不是单纯追求每一项误差指标最低”
- “动态环境下具有更稳定运行趋势”
- “在轨迹精度、局部运动稳定性和实时性之间取得较好的折中”

## 4. 贡献实验支撑检查

- 贡献1 时间一致性概率递推：由动态概率曲线、动态检测准确率、窗口参数敏感性和失败案例分析支撑。
- 贡献2 对象级语义建图：由语义地图展示和消融实验支撑，但定量支撑偏弱，建议论文中表述为地图表达和对象管理能力增强。
- 贡献3 动态 SLAM 鲁棒性：由 TUM ATE/RPE、Bonn 动态数据集、动态比例鲁棒性和轨迹稳定性分析支撑。

## 5. 最终投稿包内容

- `final_experiment_section.md`：第4章实验最终版本。
- `final_tables/`：5个投稿表格。
- `final_figures/`：6个投稿图片。
- `experiment_final_check.md`：本文档。

## 6. 注意事项

- 消融实验中 Full Model 并非所有指标优于 Baseline，论文中不应宣称每个模块单独提升定位精度。
- Bonn crowd 序列中 Dyna-SLAM 的 ATE 略低于本文方法，论文中应强调综合性能和稳定性，而非单项 ATE 全面领先。
- 对象级语义建图目前主要是定性展示，若作为强贡献，后续建议补充对象级地图质量评价。
