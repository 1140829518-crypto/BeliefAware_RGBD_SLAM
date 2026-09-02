# 图1～图4统一出版文件质量检查

- 本轮备份：`/home/djn/123/ORB_SLAM2_AddSemantic/experiments/final_paper/paper_figures_tables/backup/figures_six_format_20260814_141306`
- 每图统一格式：DRAWIO、EPS、SVG、EMF、TIF、PNG。
- 中文字体源：FZShuSong-Z01，7.5 pt；英文数字源：Times New Roman，7.5 pt。
- EMF文字由已确认SVG转换为矢量轮廓，不依赖Windows端字体替换；EMF不含整图位图记录。
- revision_preview目录中的PNG仅为历史预览，不是本轮PNG/EMF生成源。
- 视觉检查继承已经人工确认的正式版本；未重新设计图片。

## 图1 `fig1_system_framework`

- 数据/内容来源：方法框架示意；唯一正式源为根目录drawio
- DRAWIO：PASS；9202 byte；13个顶点对象，13条线对象；XML有效。
- EPS：VECTOR PASS；80760 byte；未发现整图位图操作符；中文字体=True；Times New Roman=True。
- SVG：VECTOR PASS；13482 byte；无image元素；中文字体声明=True；Times New Roman声明=True。
- EMF：VECTOR PASS；142204 byte；记录数=5946；位图记录=无。
- EMF字体：源文字为FZShuSong-Z01/Times New Roman，导出后为矢量轮廓；Windows Word无需替换字体。
- 400%检查：PASS；EMF重新矢量渲染宽度=3200px。
- TIF：PASS；538688 byte；3314×2392 px；DPI=600×600；模式=CMYK；纯白背景=True。
- PNG：PASS；280707 byte；3314×2392 px；模式=RGB。
- 内容边界：(500, 64, 2815, 2300)；裁切检查=PASS；文字重叠检查=PASS；图例压图=不适用；Grid=OFF。
- 最终状态：PASS

## 图2 `fig2_temporal_evidence`

- 数据/内容来源：机制示意，不使用实验数据
- DRAWIO：PASS；21106 byte；30个顶点对象，38条线对象；XML有效。
- EPS：VECTOR PASS；38953 byte；未发现整图位图操作符；中文字体=True；Times New Roman=True。
- SVG：VECTOR PASS；13455 byte；无image元素；中文字体声明=True；Times New Roman声明=True。
- EMF：VECTOR PASS；73848 byte；记录数=2886；位图记录=无。
- EMF字体：源文字为FZShuSong-Z01/Times New Roman，导出后为矢量轮廓；Windows Word无需替换字体。
- 400%检查：PASS；EMF重新矢量渲染宽度=3200px。
- TIF：PASS；222680 byte；2214×1448 px；DPI=600×600；模式=CMYK；纯白背景=True。
- PNG：PASS；137713 byte；2214×1448 px；模式=RGB。
- 内容边界：(17, 41, 2200, 1430)；裁切检查=PASS；文字重叠检查=PASS；图例压图=未发现；Grid=OFF。
- 最终状态：PASS

## 图3 `fig3_ate_comparison`

- 数据/内容来源：experiments/final_paper/02_tum_comparison/p2_comparison_summary.csv
- DRAWIO：PASS；28095 byte；45个顶点对象，46条线对象；XML有效。
- EPS：VECTOR PASS；55222 byte；未发现整图位图操作符；中文字体=True；Times New Roman=True。
- SVG：VECTOR PASS；19674 byte；无image元素；中文字体声明=True；Times New Roman声明=True。
- EMF：VECTOR PASS；209892 byte；记录数=7767；位图记录=无。
- EMF字体：源文字为FZShuSong-Z01/Times New Roman，导出后为矢量轮廓；Windows Word无需替换字体。
- 400%检查：PASS；EMF重新矢量渲染宽度=3200px。
- TIF：PASS；669688 byte；3536×1874 px；DPI=600×600；模式=CMYK；纯白背景=True。
- PNG：PASS；208181 byte；3536×1874 px；模式=RGB。
- 内容边界：(17, 40, 3523, 1856)；裁切检查=PASS；文字重叠检查=PASS；图例压图=未发现；Grid=OFF。
- 最终状态：PASS

## 图4 `fig4_mappoint_evidence`

- 数据/内容来源：experiments/final_paper/03_temporal_continuity/selected_mappoint_evidence.csv；Temporal / walking_xyz / MapPoint ID 254 / run_01 / 578条 / Frame 1–826
- DRAWIO：PASS；241490 byte；205个顶点对象，599条线对象；XML有效。
- EPS：VECTOR PASS；45695 byte；未发现整图位图操作符；中文字体=True；Times New Roman=True。
- SVG：VECTOR PASS；33985 byte；无image元素；中文字体声明=True；Times New Roman声明=True。
- EMF：VECTOR PASS；206604 byte；记录数=7230；位图记录=无。
- EMF字体：源文字为FZShuSong-Z01/Times New Roman，导出后为矢量轮廓；Windows Word无需替换字体。
- 400%检查：PASS；EMF重新矢量渲染宽度=3200px。
- TIF：PASS；460402 byte；3570×1832 px；DPI=600×600；模式=CMYK；纯白背景=True。
- PNG：PASS；206686 byte；3570×1832 px；模式=RGB。
- 内容边界：(17, 41, 3557, 1814)；裁切检查=PASS；文字重叠检查=PASS；图例压图=未发现；Grid=OFF。
- 最终状态：PASS

## 数据真实性专项检查

- 图3继续使用P2的12组mean/std、原柱高、原error bar和walking_rpy Full的`*`，未修改CSV。
- 图4继续使用Temporal / walking_xyz / MapPoint ID 254 / run_01的完整578条记录，Frame 1～826；无平滑、裁剪、抽样或异常点删除。

## 总结

- 总体状态：PASS
- EPS作为投稿矢量文件；TIF作为600 dpi CMYK印刷位图；EMF用于Word；DRAWIO/SVG保留编辑能力；PNG用于预览。
