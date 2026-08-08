# ObjectDynamic

`ObjectDynamic` 模块用于第二篇论文“Object-level Spatio-temporal Dynamic RGB-D SLAM”。当前目录只建立代码与接口骨架，不包含算法实现，也不接入论文1冻结的 SLAM 核心代码。

## 1. ObjectState

规划维护单个对象的时空状态：

- object id
- category
- position
- velocity
- dynamic probability

对应骨架：`ObjectState.h`、`ObjectState.cc`。

## 2. MotionEstimator

规划提供：

- object motion estimation
- trajectory prediction

对应骨架：`MotionEstimator.h`、`MotionEstimator.cc`。

## 3. DynamicMapManager

规划负责：

- object-map association
- dynamic map update
- map recovery

对应骨架：`DynamicMapManager.h`、`DynamicMapManager.cc`。

## 开发边界

模块后续实现应保持在 `paper2_development/modules/ObjectDynamic/` 内。需要使用论文1的检测、位姿、深度或地图输出时，通过论文2适配接口读取，不直接修改论文1模块。
