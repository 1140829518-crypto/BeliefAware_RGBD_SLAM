# P4 MapPoint级动态状态人工标注规范（V2）

## 必须结合时间上下文

人工判断中心帧中的人体是否真实运动时，必须同时查看对应 `*_context.png`。context从左至右仅包含前2帧、前1帧、当前帧、后1帧和后2帧，不含任何算法状态。

## 标签定义

- `Dynamic`：中心帧中实际处于运动状态的人体像素，在 `*_gt.png` 标为255。
- `Static`：明确静止背景，或结合相邻帧可以确认处于静止状态的目标；GT保持0。
- `Ignore`：无法从时间上下文可靠判断运动状态、严重遮挡、人体边缘、投影或深度异常区域，在 `*_ignore.png` 标为255。

## 禁止事项

1. 禁止使用YOLO检测框、Semantic/Temporal输出、score、state、threshold或suppression生成GT。
2. 禁止直接使用矩形检测框代替像素级人体mask。
3. preview中的青色小圆仅表示MapPoint投影，不编码预测状态。
4. person类别不自动等于Dynamic。
5. 不得改变PNG尺寸、文件名或0/255编码。

后续评价将统一添加固定2像素边界ignore band；人工标注不得根据算法结果调整边界规则。
