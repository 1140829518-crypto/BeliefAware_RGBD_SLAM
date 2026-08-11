/*
Paper2 Object-level Dynamic SLAM Module

Purpose:
Value-semantic snapshots for future ORB-SLAM2 integration.

Author:
Dong Jianing

Branch:
paper2_development
*/

#ifndef PAPER2_OBJECT_DYNAMIC_OBJECT_SNAPSHOT_H
#define PAPER2_OBJECT_DYNAMIC_OBJECT_SNAPSHOT_H

#include "ObjectState.h"

#include <cstdint>
#include <string>
#include <vector>

namespace ORB_SLAM2
{
namespace Paper2
{

struct SnapshotDetection
{
    int class_id;
    std::string class_name;
    BoundingBox2D bbox;
    double confidence;
    Vector3D position_3d;
    bool position_valid;
    std::vector<ObjectState::MapPointId> map_point_ids;

    SnapshotDetection();
    SnapshotDetection(int class_id_value,
                      const std::string &class_name_value,
                      const BoundingBox2D &bbox_value,
                      double confidence_value,
                      const Vector3D &position_3d_value,
                      bool position_valid_value = true);

    bool AddMapPointId(ObjectState::MapPointId map_point_id);
    bool IsValid() const;
};

// This DTO owns only values. It stores no raw pointers or ORB-SLAM2 references.
struct ObjectSnapshot
{
    std::uint64_t frame_id;
    double timestamp;
    PoseMatrix4d camera_pose;
    std::vector<SnapshotDetection> detections;
    std::vector<ObjectState::MapPointId> map_point_ids;

    ObjectSnapshot();
    ObjectSnapshot(std::uint64_t frame_id_value,
                   double timestamp_value,
                   const PoseMatrix4d &camera_pose_value);

    void AddDetection(const SnapshotDetection &detection);
    bool AddMapPointId(ObjectState::MapPointId map_point_id);
    bool IsValid() const;
};

} // namespace Paper2
} // namespace ORB_SLAM2

#endif // PAPER2_OBJECT_DYNAMIC_OBJECT_SNAPSHOT_H
