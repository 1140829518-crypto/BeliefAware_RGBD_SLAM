/*
Paper2 Object-level Dynamic SLAM Module

Purpose:
Offline adapter pipeline between value snapshots and ObjectDynamic modules.

Author:
Dong Jianing

Branch:
paper2_development
*/

#ifndef PAPER2_OBJECT_DYNAMIC_OBJECT_DYNAMIC_ADAPTER_H
#define PAPER2_OBJECT_DYNAMIC_OBJECT_DYNAMIC_ADAPTER_H

#include "DynamicMapManager.h"
#include "MotionEstimator.h"
#include "ObjectAssociation.h"
#include "ObjectSnapshot.h"

#include <cstdint>
#include <vector>

namespace ORB_SLAM2
{
namespace Paper2
{

struct StableMapView
{
    std::uint64_t frame_id;
    double timestamp;
    bool snapshot_accepted;
    std::vector<ObjectState> active_objects;
    std::vector<ObjectState> dynamic_objects;
    std::vector<ObjectState> recovered_objects;

    StableMapView();
};

class ObjectDynamicAdapter
{
public:
    explicit ObjectDynamicAdapter(ObjectState::ObjectId first_object_id = 1);

    StableMapView ProcessFrame(const ObjectSnapshot &snapshot);
    StableMapView GetStableMapView() const;

    ObjectAssociation &GetObjectAssociation();
    MotionEstimator &GetMotionEstimator();
    DynamicMapManager &GetDynamicMapManager();
    const DynamicMapManager &GetDynamicMapManager() const;

private:
    std::vector<ObjectState> GetPreviousObjects() const;
    std::vector<Detection> ConvertDetections(const ObjectSnapshot &snapshot) const;
    const std::vector<ObjectState::MapPointId> &MapPointsForDetection(
        const ObjectSnapshot &snapshot, std::size_t detection_index) const;
    void AssociateDetectionMapPoints(ObjectState::ObjectId object_id,
                                     const ObjectSnapshot &snapshot,
                                     std::size_t detection_index);
    StableMapView BuildStableMapView(std::uint64_t frame_id,
                                     double timestamp,
                                     bool snapshot_accepted) const;

    ObjectAssociation association_;
    MotionEstimator motion_estimator_;
    DynamicMapManager map_manager_;
    bool has_last_frame_;
    std::uint64_t last_frame_id_;
    double last_timestamp_;
};

} // namespace Paper2
} // namespace ORB_SLAM2

#endif // PAPER2_OBJECT_DYNAMIC_OBJECT_DYNAMIC_ADAPTER_H
