#include "DynamicMapFilter.h"

#include <cassert>

using ORB_SLAM2::Paper2::BoundingBox2D;
using ORB_SLAM2::Paper2::DynamicMapFilter;
using ORB_SLAM2::Paper2::MapPointStatus;
using ORB_SLAM2::Paper2::ObjectLifecycleState;
using ORB_SLAM2::Paper2::ObjectState;
using ORB_SLAM2::Paper2::StableMapView;
using ORB_SLAM2::Paper2::Vector3D;

namespace
{

ObjectState MakeObject(ObjectState::ObjectId object_id,
                       ObjectLifecycleState state,
                       ObjectState::MapPointId first_point,
                       ObjectState::MapPointId second_point)
{
    ObjectState object = ObjectState::Create(
        object_id, 3, "person", BoundingBox2D(10.0, 10.0, 40.0, 60.0),
        0.9, Vector3D(0.0, 0.0, 2.0), 1.0);
    object.SetLifecycleState(state);
    object.AddMapPoint(first_point);
    object.AddMapPoint(second_point);
    return object;
}

} // namespace

int main()
{
    DynamicMapFilter filter(1);

    ObjectState static_object = MakeObject(
        10, ObjectLifecycleState::Static, 100, 101);
    ObjectState dynamic_object = MakeObject(
        20, ObjectLifecycleState::Dynamic, 200, 201);

    StableMapView first_view;
    first_view.frame_id = 1;
    first_view.timestamp = 1.0;
    first_view.snapshot_accepted = true;
    first_view.active_objects.push_back(static_object);
    first_view.active_objects.push_back(dynamic_object);
    first_view.dynamic_objects.push_back(dynamic_object);

    assert(filter.UpdateMapView(first_view));
    assert(filter.GetTrackedPointCount() == 4);
    assert(filter.GetPointStatus(100) == MapPointStatus::Static);
    assert(!filter.IsDynamicMapPoint(100));
    assert(filter.GetPointStatus(200) == MapPointStatus::Dynamic);
    assert(filter.IsDynamicMapPoint(201));

    ObjectState::ObjectId associated_object = 0;
    assert(filter.GetAssociatedObjectId(200, &associated_object));
    assert(associated_object == 20);

    ObjectState recovered_object = dynamic_object;
    recovered_object.SetLifecycleState(ObjectLifecycleState::Recovered);
    StableMapView recovered_view;
    recovered_view.frame_id = 2;
    recovered_view.timestamp = 2.0;
    recovered_view.snapshot_accepted = true;
    recovered_view.recovered_objects.push_back(recovered_object);

    assert(filter.UpdateMapView(recovered_view));
    assert(filter.GetPointStatus(200) == MapPointStatus::Recovered);
    assert(!filter.IsDynamicMapPoint(200));
    assert(filter.GetPointStatus(201) == MapPointStatus::Recovered);

    StableMapView third_view;
    third_view.frame_id = 3;
    third_view.timestamp = 3.0;
    third_view.snapshot_accepted = true;
    third_view.recovered_objects.push_back(recovered_object);
    assert(filter.UpdateMapView(third_view));

    // Static points were last observed at frame 1 and expire at age 2 (> 1).
    assert(filter.ClearExpiredPoints() == 2);
    assert(!filter.HasMapPoint(100));
    assert(!filter.HasMapPoint(101));
    assert(filter.HasMapPoint(200));
    assert(filter.GetPointStatus(999) == MapPointStatus::Static);

    StableMapView rejected_view;
    rejected_view.frame_id = 4;
    rejected_view.timestamp = 4.0;
    rejected_view.snapshot_accepted = false;
    assert(!filter.UpdateMapView(rejected_view));
    assert(filter.GetTrackedPointCount() == 2);

    filter.Clear();
    assert(filter.GetTrackedPointCount() == 0);
    return 0;
}
