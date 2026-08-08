#include "ObjectState.h"

#include <cassert>
#include <cmath>

using ORB_SLAM2::Paper2::BoundingBox2D;
using ORB_SLAM2::Paper2::ObjectLifecycleState;
using ORB_SLAM2::Paper2::ObjectState;
using ORB_SLAM2::Paper2::PoseMatrix4d;
using ORB_SLAM2::Paper2::Vector3D;

int main()
{
    ObjectState object = ObjectState::Create(
        42, 3, "person", BoundingBox2D(10.0, 20.0, 50.0, 100.0),
        0.90, Vector3D(1.0, 2.0, 3.0), 1.0);

    assert(object.GetObjectId() == 42);
    assert(object.GetClassId() == 3);
    assert(object.GetObservationCount() == 1);
    assert(object.GetLifecycleState() == ObjectLifecycleState::PotentialDynamic);

    object.UpdateState(3, "person", BoundingBox2D(12.0, 20.0, 52.0, 100.0),
                       0.95, Vector3D(1.2, 2.0, 3.0), 1.1);
    object.UpdateVelocity(Vector3D(2.0, 0.0, 0.0));
    object.SetDynamicProbability(0.8);
    object.SetLifecycleState(ObjectLifecycleState::Dynamic);

    assert(object.GetObservationCount() == 2);
    assert(std::fabs(object.GetPosition().x - 1.2) < 1e-12);
    assert(std::fabs(object.GetMotionDirection().x - 1.0) < 1e-12);
    assert(std::fabs(object.GetDynamicProbability() - 0.8) < 1e-12);
    assert(object.GetLifecycleState() == ObjectLifecycleState::Dynamic);

    PoseMatrix4d pose = ObjectState::IdentityPose();
    pose[3] = 4.0;
    pose[7] = 5.0;
    pose[11] = 6.0;
    object.UpdatePose(pose);
    assert(std::fabs(object.GetPosition().z - 6.0) < 1e-12);

    assert(object.AddMapPoint(100));
    assert(!object.AddMapPoint(100));
    assert(object.HasMapPoint(100));
    assert(object.RemoveMapPoint(100));
    assert(!object.HasMapPoint(100));
    return 0;
}
