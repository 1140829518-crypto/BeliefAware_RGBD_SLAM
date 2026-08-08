#include "ObjectDynamicAdapter.h"

#include <cassert>
#include <cmath>

using ORB_SLAM2::Paper2::BoundingBox2D;
using ORB_SLAM2::Paper2::ObjectDynamicAdapter;
using ORB_SLAM2::Paper2::ObjectSnapshot;
using ORB_SLAM2::Paper2::ObjectState;
using ORB_SLAM2::Paper2::PoseMatrix4d;
using ORB_SLAM2::Paper2::SnapshotDetection;
using ORB_SLAM2::Paper2::StableMapView;
using ORB_SLAM2::Paper2::Vector3D;

namespace
{

ObjectSnapshot MakeSnapshot(std::uint64_t frame_id,
                            double timestamp,
                            double position_x)
{
    const PoseMatrix4d camera_pose = ObjectState::IdentityPose();
    ObjectSnapshot snapshot(frame_id, timestamp, camera_pose);
    SnapshotDetection detection(
        3, "person", BoundingBox2D(10.0 + position_x, 10.0,
                                    50.0 + position_x, 90.0),
        0.95, Vector3D(position_x, 0.0, 2.0));
    detection.AddMapPointId(100);
    detection.AddMapPointId(200);
    snapshot.AddDetection(detection);
    snapshot.AddMapPointId(300);
    return snapshot;
}

} // namespace

int main()
{
    // 1. Snapshot owns valid values and rejects duplicate MapPoint IDs.
    ObjectSnapshot first = MakeSnapshot(1, 1.0, 0.0);
    assert(first.IsValid());
    assert(first.detections.size() == 1);
    assert(first.detections[0].map_point_ids.size() == 2);
    assert(!first.detections[0].AddMapPointId(100));

    ObjectDynamicAdapter adapter(10);

    // 2. A single frame creates one active ObjectState and a stable view.
    StableMapView first_view = adapter.ProcessFrame(first);
    assert(first_view.snapshot_accepted);
    assert(first_view.frame_id == 1);
    assert(first_view.active_objects.size() == 1);
    const ObjectState::ObjectId object_id = first_view.active_objects[0].GetObjectId();
    assert(object_id == 10);
    assert(first_view.active_objects[0].GetObservationCount() == 1);
    assert(adapter.GetDynamicMapManager().GetObjectMapPoints(object_id).size() == 2);

    // 3. A second frame keeps the object ID and updates position, velocity, and history.
    ObjectSnapshot second = MakeSnapshot(2, 2.0, 1.0);
    StableMapView second_view = adapter.ProcessFrame(second);
    assert(second_view.snapshot_accepted);
    assert(second_view.active_objects.size() == 1);
    assert(second_view.active_objects[0].GetObjectId() == object_id);
    assert(second_view.active_objects[0].GetObservationCount() == 2);
    assert(std::fabs(second_view.active_objects[0].GetPosition().x - 1.0) < 1e-12);
    assert(std::fabs(second_view.active_objects[0].GetVelocity().x - 1.0) < 1e-12);

    // 4. Repeated consistent motion eventually appears in the dynamic view.
    StableMapView current_view = second_view;
    for(std::uint64_t frame_id = 3; frame_id <= 6; ++frame_id)
    {
        current_view = adapter.ProcessFrame(
            MakeSnapshot(frame_id, static_cast<double>(frame_id),
                         static_cast<double>(frame_id - 1)));
        assert(current_view.snapshot_accepted);
        assert(current_view.active_objects[0].GetObjectId() == object_id);
    }
    assert(current_view.dynamic_objects.size() == 1);
    assert(current_view.dynamic_objects[0].GetObjectId() == object_id);

    // Duplicate/out-of-order frames are rejected without changing the view.
    const StableMapView rejected = adapter.ProcessFrame(
        MakeSnapshot(6, 6.0, 5.0));
    assert(!rejected.snapshot_accepted);
    assert(rejected.active_objects.size() == 1);
    assert(rejected.active_objects[0].GetObjectId() == object_id);
    return 0;
}
