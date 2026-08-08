/*
Paper2 Object-level Dynamic SLAM Module

Purpose:
Value-semantic snapshots for future ORB-SLAM2 integration.

Author:
Dong Jianing

Branch:
paper2_development
*/

#include "ObjectSnapshot.h"

#include <algorithm>
#include <cmath>

namespace ORB_SLAM2
{
namespace Paper2
{

namespace
{

bool IsFiniteVector(const Vector3D &value)
{
    return std::isfinite(value.x) && std::isfinite(value.y) && std::isfinite(value.z);
}

bool IsFinitePose(const PoseMatrix4d &pose)
{
    for(std::size_t index = 0; index < pose.size(); ++index)
    {
        if(!std::isfinite(pose[index]))
            return false;
    }
    return true;
}

bool AddUniqueMapPointId(std::vector<ObjectState::MapPointId> *ids,
                         ObjectState::MapPointId map_point_id)
{
    if(ids == NULL)
        return false;
    if(std::find(ids->begin(), ids->end(), map_point_id) != ids->end())
        return false;
    ids->push_back(map_point_id);
    return true;
}

} // namespace

SnapshotDetection::SnapshotDetection()
    : class_id(-1), class_name("unknown"), bbox(), confidence(0.0), position_3d()
{
}

SnapshotDetection::SnapshotDetection(int class_id_value,
                                     const std::string &class_name_value,
                                     const BoundingBox2D &bbox_value,
                                     double confidence_value,
                                     const Vector3D &position_3d_value)
    : class_id(class_id_value),
      class_name(class_name_value),
      bbox(bbox_value),
      confidence(confidence_value),
      position_3d(position_3d_value)
{
}

bool SnapshotDetection::AddMapPointId(ObjectState::MapPointId map_point_id)
{
    return AddUniqueMapPointId(&map_point_ids, map_point_id);
}

bool SnapshotDetection::IsValid() const
{
    return class_id >= 0
        && !class_name.empty()
        && std::isfinite(confidence)
        && confidence >= 0.0
        && confidence <= 1.0
        && std::isfinite(bbox.left)
        && std::isfinite(bbox.top)
        && std::isfinite(bbox.right)
        && std::isfinite(bbox.bottom)
        && bbox.right > bbox.left
        && bbox.bottom > bbox.top
        && IsFiniteVector(position_3d);
}

ObjectSnapshot::ObjectSnapshot()
    : frame_id(0), timestamp(0.0), camera_pose(ObjectState::IdentityPose())
{
}

ObjectSnapshot::ObjectSnapshot(std::uint64_t frame_id_value,
                               double timestamp_value,
                               const PoseMatrix4d &camera_pose_value)
    : frame_id(frame_id_value),
      timestamp(timestamp_value),
      camera_pose(camera_pose_value)
{
}

void ObjectSnapshot::AddDetection(const SnapshotDetection &detection)
{
    detections.push_back(detection);
}

bool ObjectSnapshot::AddMapPointId(ObjectState::MapPointId map_point_id)
{
    return AddUniqueMapPointId(&map_point_ids, map_point_id);
}

bool ObjectSnapshot::IsValid() const
{
    if(!std::isfinite(timestamp) || !IsFinitePose(camera_pose))
        return false;
    for(std::size_t index = 0; index < detections.size(); ++index)
    {
        if(!detections[index].IsValid())
            return false;
    }
    return true;
}

} // namespace Paper2
} // namespace ORB_SLAM2
