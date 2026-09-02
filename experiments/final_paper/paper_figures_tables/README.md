# Paper figures and tables

## Font status

FONT_MISSING = NO

Times New Roman和FZShuSong-Z01均已安装。图1正式文件已使用FZShuSong-Z01重新导出并完成字体嵌入检查。本次任务未重新导出图2～图4，它们的字体状态应以各自后续质量检查为准。

## Figure quality audit

| 图 | TIF像素 | DPI | 模式 | 600 dpi | 轴标签/说明 | 数据来源 |
|---|---:|---:|---|---|---|---|
| fig1_system_framework | 3314×2392 | 600×600 | CMYK | PASS | 无坐标轴 | 方法框架示意；依据当前源码，不含实验数据 |
| fig2_temporal_evidence | 2010×1367 | 600×600 | CMYK | PASS | 示意时间轴与阈值 | 机制示意；观测序列仅为示意，不是实验结果 |
| fig3_ate_comparison | 4014×2130 | 600×600 | CMYK | PASS | Sequence；ATE RMSE/m | 02_tum_comparison/p2_comparison_summary.csv |
| fig4_mappoint_evidence | 4014×2070 | 600×600 | CMYK | PASS | Frame ID；Dynamic evidence | 03_temporal_continuity/selected_mappoint_evidence.csv |

- 所有TIF均由SVG/Matplotlib按最终物理尺寸直接栅格化到600 dpi，不是仅修改DPI元数据；均为CMYK。
- 图3用填充纹理区分方法，图4用线型和标记区分状态，因此不依赖颜色作为唯一信息。图例位于上方或右上空白区；自动布局后未覆盖柱体主区域。
- 图1为双栏宽流程图；图2为单栏宽示意图；图3、图4为双栏宽坐标图。预览PNG为300 dpi。
- 图题未烘焙进图像，统一存于captions.md。

## Figure mapping

- 图1：方法/系统框架；drawio可继续编辑。
- 图2：方法/时间证据机制；drawio可继续编辑。
- 图3：实验/定位精度；Full在walking_rpy的星号须配合图注说明低轨迹覆盖。
- 图4：实验/时间连续性；使用P3既定客观选点结果。选择规则：曾进入动态状态、不同观测帧数最多、并列取最小MapPoint ID。

## Table sources

- 表1：`01_tum_full/experiment_environment.json`。
- 表2：P2经审计的四种真实配置定义。
- 表3、表4：`02_tum_comparison/p2_comparison_summary.csv`。
- 表5：`03_temporal_continuity/p3_temporal_continuity_summary.csv`。

## Completeness and limitations

- 所有实验图均来自既有真实数据；图2明确为机制示意图。未生成Bonn、Precision、Recall或F1图表。
- P3伴随ATE/RPE未用于图3或主性能表。
- 表1字段均可由环境JSON获得；未编造缺失硬件信息。
- 可直接插入Word：EPS或TIF；PNG仅供预览。可继续编辑：图1、图2的drawio，以及全部SVG。
- 灰度可辨性通过纹理、线型和点型设计保证；最终排版仍建议在Word目标尺寸下人工目检一次。
