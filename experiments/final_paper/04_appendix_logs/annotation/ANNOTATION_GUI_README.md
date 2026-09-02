# P4人工GT本地标注工具

## 启动

在项目根目录执行：

```bash
python3 scripts/p4_annotation_gui.py
```

无界面检查120帧文件和mask格式：

```bash
python3 scripts/p4_annotation_gui.py --check
```

首次使用前可在无界面模式初始化进度表：

```bash
python3 scripts/p4_annotation_gui.py --initialize-progress
```

依赖：Python 3、Tkinter、Pillow、OpenCV和NumPy。工具读取：

- `selected_frames_v2.csv`
- `annotation_v2/<sequence>/frame_XXXX_{rgb,context,gt,ignore}.png`

工具**不会读取**MapPoint预测状态、Semantic/Temporal结果、dynamic score、threshold或suppression字段。

## 标注方式

- `G`：GT图层，绿色半透明预览；
- `I`：Ignore图层，黄色半透明预览；
- `E`：切换当前图层的橡皮擦；
- `B`：画笔；
- `M`：多边形；逐点单击轮廓，按Enter闭合填充，Esc取消；
- `Z`：撤销；
- `S`：保存；
- `N`或右方向键：保存并进入下一帧；
- `P`或左方向键：进入上一帧；有未保存内容时会询问；
- `+`/`-`：调整画笔直径。

左键拖动使用画笔。多边形模式下左键逐点添加顶点。默认启动为GT画笔模式。

界面顶部显示五帧context，顺序为前2、前1、当前、后1、后2。主体只显示原始RGB及人工mask半透明覆盖。

## 文件安全

- 已有GT和Ignore会在重新打开时恢复，不会初始化覆盖。
- 保存前强制将mask二值化为0/255。
- 保存文件为与RGB相同尺寸的单通道8-bit PNG。
- 使用临时文件校验成功后原子替换目标mask。
- “标注完成”状态及像素计数写入 `annotation_progress.csv`。
- 标注完成复选框需要按`S`或“保存并下一张”后才写入进度文件。

本工具不计算TP/FP/FN、Precision、Recall或F1。
