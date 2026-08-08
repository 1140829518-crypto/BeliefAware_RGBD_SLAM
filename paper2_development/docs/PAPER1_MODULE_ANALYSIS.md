# 论文1模块分析

分析基线：提交 `195eb01`（`paper2_development` 分支）。本文仅记录论文1冻结代码的实现位置、调用关系和可复用接口，不改变其实现。

## 论文1已有模块

| 模块 | 代码位置 | 作用 | 论文对应 |
|---|---|---|---|
| YOLO Detection Interface | `yolov5_RemoveDynamic/detect_speedup_send.py`；`Examples/RGB-D/rgbd_tum.cc` | 外部 YOLO 进程执行检测；RGB-D 示例通过 Unix domain socket 请求并接收每帧检测框，将字符串解析成 `bbox + class_id` 后传入 SLAM | 语义目标检测输入 |
| Detection Transport | `Examples/RGB-D/rgbd_tum.cc`：`MakeDetect_result()`、`LoadBoundingBoxFromPython()`、`LoadBoundingBox()` | 接收或读取检测结果，并转换为 `vector<pair<vector<double>, int>>` | 检测器与 SLAM 的数据接口 |
| Semantic Detection Ingress | `src/System.cc`：`System::TrackRGBD()`；`src/Tracking.cc`：`Tracking::GrabImageRGBD()`；`src/Frame.cc`：RGB-D `Frame` 构造函数 | 将检测框沿 System → Tracking → Frame 传递，并为当前帧构造 `Object` 集合 | 语义信息注入跟踪线程 |
| Semantic Region Processing | `src/Frame.cc`：`IsPixelInBox()`、`IsPixelInDynamicBox()`、`IsPixelInStaticBox()`、`IsInDynamic()`、`IsInStatic()` | 判断特征点是否落入动态/静态检测框；动态框内且不在静态框内的特征点被标记，并将坐标置为 `(-100,-100)` 以阻止后续使用 | 语义区域过滤与动态特征点剔除 |
| Dynamic Category Policy | `include/SemanticConfig.h`：`DynamicObjectClasses()`、`StaticObjectClasses()`、`IsDynamicObjectClass()`、`IsStaticObjectClass()` | 集中定义类别策略。当前动态类为 `3`（person），静态/低动态分组为 `1、2` | 类别先验和动态类别判定 |
| Detection Class Mapping | `Examples/RGB-D/rgbd_tum.cc`：`LoadBoundingBoxFromPython()`、`LoadBoundingBox()` | 将检测标签映射为内部类别：person→3，部分家具/电器→1，chair/car→2 | YOLO 类别到论文类别的映射 |
| Dynamic Evidence Score | `include/MapPoint.h`；`src/MapPoint.cc`：`UpdateSemanticDynamicScore()`、`GetSemanticDynamicScore()`、`ShouldSuppressSemanticDynamic()` | 每个地图点维护动态分数和最后更新帧；动态命中时加分，按帧间隔指数衰减，并按类别阈值决定是否抑制 | 时间一致性动态证据累积 |
| Evidence Parameters | `include/SemanticConfig.h`：`DynamicScore*ForClass()` | 提供阈值、增量和衰减系数。person 默认阈值 1.0、增量 3.0、衰减 0.85；其他类默认阈值 3.0、增量 1.0、衰减 0.95；支持环境变量覆盖 | 动态证据模型参数化 |
| Dynamic Point Suppression | `src/Tracking.cc`：`CullSemanticDynamicMapPoints()` | 检查当前帧关联的 MapPoint；动态框命中后更新分数，超过阈值则标记外点并从当前帧关联中置空 | 达阈值动态地图点抑制 |
| Semantic Statistics | `src/Tracking.cc`：`SaveSemanticDynamicStatistics()`；`src/System.cc`：同名转发接口 | 记录每帧动态特征点、动态地图点、被抑制地图点及目标数量 | 论文实验统计输出 |
| MapPoint Management | `include/MapPoint.h`、`src/MapPoint.cc`；`include/Map.h`、`src/Map.cc` | 管理地图点坐标、观测、描述子、可见/找到计数、坏点状态，以及地图容器中的添加和移除 | 点级地图表示与生命周期 |
| MapPoint Quality Culling | `src/LocalMapping.cc`：`MapPointCulling()` | 根据坏点标志、找到率和关键帧观测数淘汰新建的低质量地图点 | 局部地图质量控制 |
| KeyFrame Management | `include/KeyFrame.h`、`src/KeyFrame.cc`；`include/Map.h`、`src/Map.cc` | 管理关键帧位姿、特征、MapPoint 关联、共视关系、坏帧状态和地图容器 | 关键帧图与地图维护 |
| KeyFrame Culling | `src/LocalMapping.cc`：`KeyFrameCulling()` | 当关键帧中超过 90% 的有效地图点可被至少三个其他关键帧观测时，将其判为冗余 | 关键帧冗余抑制 |
| Semantic Object Landmark | `include/SemanticObject.h`、`src/SemanticObject.cc`；`src/Tracking.cc`：`UpdateSemanticObjectMap()`；`src/Map.cc`：`AddOrFuseSemanticObject()` | 将静态/低动态目标框中心反投影到世界坐标，按类别和三维距离关联或融合，维护观察次数和平均位置 | 已有对象级语义地图雏形 |

## 关键调用链

```text
YOLO Python detector
  → Unix socket / detection text
  → Examples/RGB-D/rgbd_tum.cc
  → System::TrackRGBD
  → Tracking::GrabImageRGBD
  → Frame(detect_result)
  → bbox-based feature filtering
  → Tracking::CullSemanticDynamicMapPoints
  → MapPoint::UpdateSemanticDynamicScore
  → current-frame MapPoint suppression
```

地图管理主链为：

```text
Tracking::CreateNewKeyFrame
  → LocalMapping::ProcessNewKeyFrame / CreateNewMapPoints
  → Map::AddKeyFrame / AddMapPoint
  → LocalMapping::MapPointCulling / KeyFrameCulling
  → MapPoint::SetBadFlag / KeyFrame::SetBadFlag
  → Map::EraseMapPoint / EraseKeyFrame
```

## 实现边界与论文2接口注意事项

1. 当前没有独立的像素级 semantic mask 数据结构或分割处理函数。所谓语义 mask 实际由矩形检测框充当区域掩膜，边界判断在 `src/Frame.cc` 完成。
2. 检测器运行在外部 Python/YOLO 工程中，核心 C++ 只消费检测框和内部类别编号；这适合作为论文2检测适配器的输入边界。
3. `MapPoint` 的动态状态只有 `mfSemanticDynamicScore` 和 `mnSemanticDynamicLastFrame`，没有对象 ID、速度或轨迹归属。
4. `UpdateSemanticDynamicScore(false, ...)` 支持非动态命中的额外衰减，但在当前代码中未发现以 `false` 调用；现有主流程只在动态框命中时调用，帧间时间一致性由下次命中时按 `frameGap` 衰减体现。
5. `CullSemanticDynamicMapPoints()` 只移除当前帧中的关联并标记外点，不直接调用 `MapPoint::SetBadFlag()`，因此是跟踪级抑制，不是永久删除地图点。
6. 已有 `SemanticObject` 仅按“类别相同 + 三维中心距离阈值”融合，具备对象 ID、类别、位置和观察次数，但没有速度、运动模型、轨迹预测、显式动态概率或恢复状态。
7. 论文2的 ObjectDynamic 模块应通过适配接口读取论文1输出，避免直接修改上述冻结实现。
