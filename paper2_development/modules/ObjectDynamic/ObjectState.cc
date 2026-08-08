/*
Paper2 Object-level Dynamic SLAM Module

Purpose:
Object-level spatio-temporal dynamic modeling.

Author:
Dong Jianing

Branch:
paper2_development
*/

#include "ObjectState.h"

#include <algorithm>
#include <cmath>

namespace ORB_SLAM2
{
namespace Paper2
{

BoundingBox2D::BoundingBox2D()
    : left(0.0), top(0.0), right(0.0), bottom(0.0)
{
}

BoundingBox2D::BoundingBox2D(double left_value, double top_value,
                             double right_value, double bottom_value)
    : left(left_value), top(top_value), right(right_value), bottom(bottom_value)
{
}

Vector3D::Vector3D() : x(0.0), y(0.0), z(0.0)
{
}

Vector3D::Vector3D(double x_value, double y_value, double z_value)
    : x(x_value), y(y_value), z(z_value)
{
}

ObjectState::ObjectState()
    : object_id_(0),
      class_id_(-1),
      class_name_("unknown"),
      bbox_(),
      confidence_(0.0),
      position_(),
      pose_(IdentityPose()),
      velocity_(),
      motion_direction_(),
      dynamic_probability_(0.5),
      state_(ObjectLifecycleState::PotentialDynamic),
      timestamp_(0.0),
      observation_count_(0)
{
}

ObjectState::ObjectState(ObjectId object_id,
                         int class_id,
                         const std::string &class_name,
                         const BoundingBox2D &bbox,
                         double confidence,
                         const Vector3D &position,
                         double timestamp)
    : object_id_(object_id),
      class_id_(class_id),
      class_name_(class_name),
      bbox_(bbox),
      confidence_(ClampProbability(confidence)),
      position_(position),
      pose_(IdentityPose()),
      velocity_(),
      motion_direction_(),
      dynamic_probability_(0.5),
      state_(ObjectLifecycleState::PotentialDynamic),
      timestamp_(timestamp),
      observation_count_(1)
{
    pose_[3] = position.x;
    pose_[7] = position.y;
    pose_[11] = position.z;
}

ObjectState::~ObjectState()
{
}

ObjectState ObjectState::Create(ObjectId object_id,
                                int class_id,
                                const std::string &class_name,
                                const BoundingBox2D &bbox,
                                double confidence,
                                const Vector3D &position,
                                double timestamp)
{
    return ObjectState(object_id, class_id, class_name, bbox,
                       confidence, position, timestamp);
}

void ObjectState::UpdateState(int class_id,
                              const std::string &class_name,
                              const BoundingBox2D &bbox,
                              double confidence,
                              const Vector3D &position,
                              double timestamp)
{
    class_id_ = class_id;
    class_name_ = class_name;
    bbox_ = bbox;
    confidence_ = ClampProbability(confidence);
    position_ = position;
    timestamp_ = timestamp;
    ++observation_count_;

    pose_[3] = position.x;
    pose_[7] = position.y;
    pose_[11] = position.z;
}

void ObjectState::UpdatePose(const PoseMatrix4d &pose)
{
    pose_ = pose;
    position_ = Vector3D(pose_[3], pose_[7], pose_[11]);
}

void ObjectState::UpdateVelocity(const Vector3D &velocity)
{
    velocity_ = velocity;
    motion_direction_ = Normalize(velocity);
}

void ObjectState::SetDynamicProbability(double probability)
{
    dynamic_probability_ = ClampProbability(probability);
}

void ObjectState::SetLifecycleState(ObjectLifecycleState state)
{
    state_ = state;
}

bool ObjectState::AddMapPoint(MapPointId map_point_id)
{
    if(HasMapPoint(map_point_id))
        return false;
    associated_map_points_.push_back(map_point_id);
    return true;
}

bool ObjectState::RemoveMapPoint(MapPointId map_point_id)
{
    const std::vector<MapPointId>::iterator it =
        std::find(associated_map_points_.begin(), associated_map_points_.end(), map_point_id);
    if(it == associated_map_points_.end())
        return false;
    associated_map_points_.erase(it);
    return true;
}

bool ObjectState::HasMapPoint(MapPointId map_point_id) const
{
    return std::find(associated_map_points_.begin(), associated_map_points_.end(), map_point_id)
           != associated_map_points_.end();
}

ObjectState::ObjectId ObjectState::GetObjectId() const { return object_id_; }
int ObjectState::GetClassId() const { return class_id_; }
const std::string &ObjectState::GetClassName() const { return class_name_; }
const BoundingBox2D &ObjectState::GetBoundingBox() const { return bbox_; }
double ObjectState::GetConfidence() const { return confidence_; }
const Vector3D &ObjectState::GetPosition() const { return position_; }
const PoseMatrix4d &ObjectState::GetPose() const { return pose_; }
const Vector3D &ObjectState::GetVelocity() const { return velocity_; }
const Vector3D &ObjectState::GetMotionDirection() const { return motion_direction_; }
double ObjectState::GetDynamicProbability() const { return dynamic_probability_; }
ObjectLifecycleState ObjectState::GetLifecycleState() const { return state_; }
const std::vector<ObjectState::MapPointId> &ObjectState::GetAssociatedMapPoints() const
{
    return associated_map_points_;
}
double ObjectState::GetTimestamp() const { return timestamp_; }
std::uint64_t ObjectState::GetObservationCount() const { return observation_count_; }

PoseMatrix4d ObjectState::IdentityPose()
{
    PoseMatrix4d pose = {{0.0, 0.0, 0.0, 0.0,
                          0.0, 0.0, 0.0, 0.0,
                          0.0, 0.0, 0.0, 0.0,
                          0.0, 0.0, 0.0, 0.0}};
    pose[0] = 1.0;
    pose[5] = 1.0;
    pose[10] = 1.0;
    pose[15] = 1.0;
    return pose;
}

double ObjectState::ClampProbability(double value)
{
    if(value < 0.0)
        return 0.0;
    if(value > 1.0)
        return 1.0;
    return value;
}

Vector3D ObjectState::Normalize(const Vector3D &value)
{
    const double norm = std::sqrt(value.x * value.x + value.y * value.y + value.z * value.z);
    if(norm <= 1e-12)
        return Vector3D();
    return Vector3D(value.x / norm, value.y / norm, value.z / norm);
}

} // namespace Paper2
} // namespace ORB_SLAM2
