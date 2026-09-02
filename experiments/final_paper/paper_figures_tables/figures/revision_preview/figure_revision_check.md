# 图2～图4预览检查

## 本阶段范围

- 仅生成图2、图3、图4的PNG预览。
- 未覆盖 `figures/` 中已有的正式drawio、SVG、EPS或TIF文件。
- 未修改实验CSV、论文正文或算法，也未重新运行实验。

## 统一样式检查

- 中文渲染字体：`FZShuSong-Z01`，7.5 pt，由 `/home/djn/.local/share/fonts/FZSSK.TTF` 显式加载。
- 英文、数字及坐标刻度：Times New Roman，7.5 pt。
- 背景：纯白、不透明。
- Grid：OFF。
- 坐标轴：黑色实线；上、右边框隐藏。
- 正式600 dpi CMYK导出：本阶段未执行，等待人工确认预览。

## 图2 时间一致性动态证据更新示意

- 文件：`fig2_temporal_evidence_preview.png`
- 像素尺寸：843 × 563 px。
- 数据性质：机制示意，不使用实验数据，未增加新算法含义。
- 图例：时序动态证据、动态判定阈值、动态观测，位于坐标区左上方空白区域。
- 坐标轴：横轴“帧编号”，纵轴“动态证据”。
- 证据衰减标注：保留，箭头未遮挡图例或曲线关键点。
- 颜色与线型：绿色实线、红色虚线、蓝色圆点。
- Grid：OFF；背景：white；图内标题：无。
- 人工目检：未发现图例压线、文字裁切或重叠。

## 图3 不同配置ATE RMSE比较

- 文件：`fig3_ate_comparison_preview.png`
- 像素尺寸：1 329 × 720 px。
- 数据来源：`experiments/final_paper/02_tum_comparison/p2_comparison_summary.csv`。
- 横轴：“序列”（FZShuSong-Z01）；纵轴：`ATE RMSE/m`（Times New Roman）。
- 序列名和方法名保留英文；图例位于绘图区上方。
- 柱色：ORB-SLAM2蓝、Semantic橙、Temporal绿、Full红。
- 误差棒：黑色、统一线宽。
- 柱顶显示3位小数的mean与±std；walking_rpy的Full保留`*`。
- walking_rpy相邻数值标签仅做垂直错位排版，未改变任何数值。
- Grid：OFF；背景：white；图内标题：无。
- 人工目检：未发现图例、数值或误差棒互相遮挡。

### P2读取值核对

| Sequence | Method | Mean | Std |
|---|---|---:|---:|
| walking_xyz | ORB-SLAM2 | 0.835129026 | 0.222270174 |
| walking_xyz | Semantic | 0.504875897 | 0.055832324 |
| walking_xyz | Temporal | 0.562268041 | 0.082441359 |
| walking_xyz | Full | 0.538911446 | 0.042123627 |
| walking_rpy | ORB-SLAM2 | 1.164328650 | 0.152317846 |
| walking_rpy | Semantic | 0.749207411 | 0.035709288 |
| walking_rpy | Temporal | 0.756381005 | 0.058432875 |
| walking_rpy | Full | 0.465345095 | 0.395890499 |
| walking_halfsphere | ORB-SLAM2 | 0.644461647 | 0.072637222 |
| walking_halfsphere | Semantic | 0.329266379 | 0.177199782 |
| walking_halfsphere | Temporal | 0.356206538 | 0.215750874 |
| walking_halfsphere | Full | 0.443035265 | 0.209125910 |

核对结果：与P2源CSV完全一致，绘图时未手工覆盖数据。

## 图4 代表地图点动态证据变化

- 文件：`fig4_mappoint_evidence_preview.png`
- 像素尺寸：1 340 × 704 px。
- 数据来源：`experiments/final_paper/03_temporal_continuity/selected_mappoint_evidence.csv`。
- 固定筛选：method=`Temporal`、sequence=`fr3_walking_xyz`、map_point_id=`254`、run_id=`run_01`。
- 使用记录数：578条；帧范围：1～826；帧顺序单调递增。
- 绘制方式：全部578条证据记录按原值连接；无平滑、无裁剪、无抽样、无异常点删除。
- 动态观测：175条实际`dynamic_hit`记录，全部显示为蓝色小圆点。
- 状态切换：由相邻记录的实际状态变化计算，共5处，显示为紫色空心圆。
- `suppressed`字段：源CSV完整保留，筛选结果中为true的记录共202条；本图不绘制Suppressed标记，未修改源数据。
- 已删除右上角序列/MapPoint/person文字。
- 图例：时序动态证据、动态判定阈值、动态观测、状态切换，位于绘图区左上方空白区域。
- 坐标轴：横轴“帧编号”，纵轴“动态证据”。
- Grid：OFF；背景：white；图内标题：无。
- 人工目检：未发现图例压线、文字裁切或高密度marker造成的不可辨识重叠。

## 结论

三张预览均满足本轮内容、字体、颜色、坐标轴、图例和数据真实性要求，可提交人工确认。正式EPS/TIF/CMYK/600 dpi文件尚未生成。
