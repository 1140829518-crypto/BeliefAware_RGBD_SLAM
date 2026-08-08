#include "DynamicMapManager.h"

#include <cassert>
#include <vector>

using ORB_SLAM2::Paper2::BoundingBox2D;
using ORB_SLAM2::Paper2::DynamicMapManager;
using ORB_SLAM2::Paper2::ObjectLifecycleState;
using ORB_SLAM2::Paper2::ObjectState;
using ORB_SLAM2::Paper2::Vector3D;

namespace
{

ObjectState MakeObject(ObjectState::ObjectId id)
{
    return ObjectState::Create(id, 3, "person",
                               BoundingBox2D(10.0, 10.0, 50.0, 90.0),
                               0.9, Vector3D(1.0, 0.0, 2.0), 1.0);
}

ObjectLifecycleState GetState(const DynamicMapManager &manager,
                              ObjectState::ObjectId id)
{
    ObjectState object;
    assert(manager.GetObject(id, &object));
    return object.GetLifecycleState();
}

} // namespace

int main()
{
    DynamicMapManager manager;
    const ObjectState object = MakeObject(10);
    assert(manager.AddObject(object));
    assert(!manager.AddObject(object));
    assert(manager.GetObjectCount() == 1);

    // 1. PotentialDynamic -> Static -> PotentialDynamic -> Dynamic.
    assert(manager.UpdateObjectState(10, 0.2, true));
    assert(GetState(manager, 10) == ObjectLifecycleState::Static);
    assert(manager.UpdateObjectState(10, 0.6, true));
    assert(GetState(manager, 10) == ObjectLifecycleState::PotentialDynamic);
    assert(manager.UpdateObjectState(10, 0.8, true));
    assert(GetState(manager, 10) == ObjectLifecycleState::Dynamic);

    // 2. A missing dynamic object becomes Lost and leaves the active view.
    assert(manager.UpdateObjectState(10, 0.8, false));
    assert(GetState(manager, 10) == ObjectLifecycleState::Lost);
    assert(manager.GetActiveObjects().empty());
    assert(manager.GetLostObjects().size() == 1);

    // 3. Recovery needs three consecutive confirmations, not one frame.
    assert(!manager.RecoverObject(10));
    assert(GetState(manager, 10) == ObjectLifecycleState::Lost);
    assert(manager.GetRecoveryConfirmationCount(10) == 1);
    assert(!manager.RecoverObject(10));
    assert(GetState(manager, 10) == ObjectLifecycleState::Lost);
    assert(manager.RecoverObject(10));
    assert(GetState(manager, 10) == ObjectLifecycleState::Recovered);
    assert(manager.GetRecoveredObjects().size() == 1);
    assert(manager.GetActiveObjects().size() == 1);

    // A new miss clears recovery progress and returns the object to Lost.
    assert(manager.CheckTransition(10, false));
    assert(GetState(manager, 10) == ObjectLifecycleState::Lost);
    assert(manager.GetRecoveryConfirmationCount(10) == 0);

    // 4. MapPoint associations are independent ID mappings with no duplicates.
    assert(manager.AssociateMapPoint(10, 100));
    assert(manager.AssociateMapPoint(10, 200));
    assert(!manager.AssociateMapPoint(10, 100));
    std::vector<ObjectState::MapPointId> map_points =
        manager.GetObjectMapPoints(10);
    assert(map_points.size() == 2);
    assert(map_points[0] == 100);
    assert(map_points[1] == 200);
    assert(manager.RemoveMapPoint(10, 100));
    assert(!manager.RemoveMapPoint(10, 100));
    map_points = manager.GetObjectMapPoints(10);
    assert(map_points.size() == 1);
    assert(map_points[0] == 200);

    ObjectState stored;
    assert(manager.GetObject(10, &stored));
    assert(stored.HasMapPoint(200));
    assert(!stored.HasMapPoint(100));

    assert(manager.RemoveObject(10));
    assert(!manager.HasObject(10));
    assert(manager.GetObjectMapPoints(10).empty());
    return 0;
}
