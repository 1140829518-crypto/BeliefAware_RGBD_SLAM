/*
Paper2 Object-level Dynamic SLAM Module

Purpose:
Object-level spatio-temporal dynamic modeling.

Author:
Dong Jianing

Branch:
paper2_development
*/

#ifndef PAPER2_OBJECT_DYNAMIC_OBJECT_STATE_H
#define PAPER2_OBJECT_DYNAMIC_OBJECT_STATE_H

#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace ORB_SLAM2
{
namespace Paper2
{

struct BoundingBox2D
{
    double left;
    double top;
    double right;
    double bottom;

    BoundingBox2D();
    BoundingBox2D(double left_value, double top_value,
                  double right_value, double bottom_value);
};

struct Vector3D
{
    double x;
    double y;
    double z;

    Vector3D();
    Vector3D(double x_value, double y_value, double z_value);
};

typedef std::array<double, 16> PoseMatrix4d;

enum class ObjectLifecycleState
{
    Static,
    PotentialDynamic,
    Dynamic,
    Lost,
    Recovered
};

// Self-contained object state. It has no ownership of ORB-SLAM2 objects.
class ObjectState
{
public:
    typedef std::uint64_t ObjectId;
    typedef std::uint64_t MapPointId;

    ObjectState();
    ObjectState(ObjectId object_id,
                int class_id,
                const std::string &class_name,
                const BoundingBox2D &bbox,
                double confidence,
                const Vector3D &position,
                double timestamp,
                bool position_valid = true);
    ~ObjectState();

    static ObjectState Create(ObjectId object_id,
                              int class_id,
                              const std::string &class_name,
                              const BoundingBox2D &bbox,
                              double confidence,
                              const Vector3D &position,
                              double timestamp,
                              bool position_valid = true);

    void UpdateState(int class_id,
                     const std::string &class_name,
                     const BoundingBox2D &bbox,
                     double confidence,
                     const Vector3D &position,
                     double timestamp,
                     bool position_valid = true);
    void UpdatePose(const PoseMatrix4d &pose);
    void UpdateVelocity(const Vector3D &velocity);
    void SetDynamicProbability(double probability);
    void SetLifecycleState(ObjectLifecycleState state);

    bool AddMapPoint(MapPointId map_point_id);
    bool RemoveMapPoint(MapPointId map_point_id);
    bool HasMapPoint(MapPointId map_point_id) const;

    ObjectId GetObjectId() const;
    int GetClassId() const;
    const std::string &GetClassName() const;
    const BoundingBox2D &GetBoundingBox() const;
    double GetConfidence() const;
    const Vector3D &GetPosition() const;
    bool IsPositionValid() const;
    const PoseMatrix4d &GetPose() const;
    const Vector3D &GetVelocity() const;
    const Vector3D &GetMotionDirection() const;
    double GetDynamicProbability() const;
    ObjectLifecycleState GetLifecycleState() const;
    const std::vector<MapPointId> &GetAssociatedMapPoints() const;
    double GetTimestamp() const;
    std::uint64_t GetObservationCount() const;

    static PoseMatrix4d IdentityPose();

private:
    static double ClampProbability(double value);
    static Vector3D Normalize(const Vector3D &value);

    ObjectId object_id_;
    int class_id_;
    std::string class_name_;

    BoundingBox2D bbox_;
    double confidence_;

    Vector3D position_;
    bool position_valid_;
    PoseMatrix4d pose_;

    Vector3D velocity_;
    Vector3D motion_direction_;

    double dynamic_probability_;
    ObjectLifecycleState state_;

    std::vector<MapPointId> associated_map_points_;

    double timestamp_;
    std::uint64_t observation_count_;
};

} // namespace Paper2
} // namespace ORB_SLAM2

#endif // PAPER2_OBJECT_DYNAMIC_OBJECT_STATE_H
