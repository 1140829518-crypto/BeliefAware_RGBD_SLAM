/*
Paper2 Object-level Dynamic SLAM Module

Purpose:
Offline adapter pipeline between value snapshots and ObjectDynamic modules.

Author:
Dong Jianing

Branch:
paper2_development
*/

#include "ObjectDynamicAdapter.h"

#include <cstddef>
#include <iostream>

namespace ORB_SLAM2
{
namespace Paper2
{

namespace
{

const char *LifecycleStateName(ObjectLifecycleState state)
{
    switch(state)
    {
        case ObjectLifecycleState::Static: return "Static";
        case ObjectLifecycleState::PotentialDynamic: return "PotentialDynamic";
        case ObjectLifecycleState::Dynamic: return "Dynamic";
        case ObjectLifecycleState::Lost: return "Lost";
        case ObjectLifecycleState::Recovered: return "Recovered";
    }
    return "Unknown";
}

} // namespace

StableMapView::StableMapView()
    : frame_id(0), timestamp(0.0), snapshot_accepted(false)
{
}

ObjectDynamicAdapter::ObjectDynamicAdapter(ObjectState::ObjectId first_object_id)
    : association_(first_object_id),
      motion_estimator_(),
      map_manager_(),
      has_last_frame_(false),
      last_frame_id_(0),
      last_timestamp_(0.0)
{
}

StableMapView ObjectDynamicAdapter::ProcessFrame(const ObjectSnapshot &snapshot)
{
    if(!snapshot.IsValid()
       || (has_last_frame_ && (snapshot.frame_id <= last_frame_id_
                               || snapshot.timestamp <= last_timestamp_)))
    {
        return BuildStableMapView(last_frame_id_, last_timestamp_, false);
    }

    const std::vector<ObjectState> previous_objects = GetPreviousObjects();
    const std::vector<Detection> detections = ConvertDetections(snapshot);
    const AssociationResult association_result = association_.AssociateObjects(
        previous_objects, detections, snapshot.timestamp);

    // Matched objects preserve IDs, receive motion estimates, and update lifecycle state.
    for(std::size_t index = 0; index < association_result.matches.size(); ++index)
    {
        const ObjectMatch &match = association_result.matches[index];
        ObjectState current = association_result.objects[index];
        const ObjectState &previous = previous_objects[match.previous_index];
        const bool recovering_from_lost =
            previous.GetLifecycleState() == ObjectLifecycleState::Lost;

        // ObjectAssociation marks a matched Lost object as Recovered immediately.
        // Restore Lost here so DynamicMapManager can enforce multi-frame recovery.
        if(recovering_from_lost)
            current.SetLifecycleState(ObjectLifecycleState::Lost);

        const MotionEstimate estimate = motion_estimator_.Estimate(previous, current);
        if(estimate.valid)
            motion_estimator_.ApplyEstimate(current, estimate);

        map_manager_.UpdateObject(current);
        if(recovering_from_lost)
        {
            if(map_manager_.RecoverObject(current.GetObjectId()))
            {
                std::cout << "[ObjectDynamicRecovery] frame=" << snapshot.frame_id
                          << " object_id=" << current.GetObjectId()
                          << " confirmations="
                          << map_manager_.GetRecoveryConfirmationFrames()
                          << " state=Recovered" << std::endl;
            }
        }
        else
        {
            map_manager_.UpdateObjectState(current.GetObjectId(),
                                           current.GetDynamicProbability(), true);
        }
        ObjectState managed;
        if(map_manager_.GetObject(current.GetObjectId(), &managed)
           && managed.GetLifecycleState() != previous.GetLifecycleState())
        {
            std::cout << "[ObjectDynamicTransition] frame=" << snapshot.frame_id
                      << " object_id=" << managed.GetObjectId()
                      << " class_id=" << managed.GetClassId()
                      << " from="
                      << LifecycleStateName(previous.GetLifecycleState())
                      << " to="
                      << LifecycleStateName(managed.GetLifecycleState())
                      << " position_valid=" << managed.IsPositionValid()
                      << " motion_score="
                      << (estimate.valid ? estimate.motion_score : 0.0)
                      << " dynamic_probability="
                      << managed.GetDynamicProbability() << std::endl;
        }
        AssociateDetectionMapPoints(current.GetObjectId(), snapshot,
                                    match.detection_index);
    }

    // Unmatched previous objects become/remain Lost and reset partial recovery.
    for(std::size_t index = 0;
        index < association_result.unmatched_previous_indices.size(); ++index)
    {
        const std::size_t previous_index =
            association_result.unmatched_previous_indices[index];
        const ObjectState &previous = previous_objects[previous_index];
        map_manager_.UpdateObjectState(previous.GetObjectId(),
                                       previous.GetDynamicProbability(), false);
    }

    // New detections are appended after matched and unmatched previous objects.
    const std::size_t new_object_offset = association_result.matches.size()
                                        + association_result.unmatched_previous_indices.size();
    for(std::size_t index = 0;
        index < association_result.unmatched_detection_indices.size(); ++index)
    {
        const ObjectState &created = association_result.objects[new_object_offset + index];
        map_manager_.AddObject(created);
        AssociateDetectionMapPoints(
            created.GetObjectId(), snapshot,
            association_result.unmatched_detection_indices[index]);
    }

    has_last_frame_ = true;
    last_frame_id_ = snapshot.frame_id;
    last_timestamp_ = snapshot.timestamp;
    return BuildStableMapView(snapshot.frame_id, snapshot.timestamp, true);
}

StableMapView ObjectDynamicAdapter::GetStableMapView() const
{
    return BuildStableMapView(last_frame_id_, last_timestamp_, has_last_frame_);
}

ObjectAssociation &ObjectDynamicAdapter::GetObjectAssociation()
{
    return association_;
}

MotionEstimator &ObjectDynamicAdapter::GetMotionEstimator()
{
    return motion_estimator_;
}

DynamicMapManager &ObjectDynamicAdapter::GetDynamicMapManager()
{
    return map_manager_;
}

const DynamicMapManager &ObjectDynamicAdapter::GetDynamicMapManager() const
{
    return map_manager_;
}

std::vector<ObjectState> ObjectDynamicAdapter::GetPreviousObjects() const
{
    std::vector<ObjectState> objects = map_manager_.GetActiveObjects();
    const std::vector<ObjectState> lost = map_manager_.GetLostObjects();
    objects.insert(objects.end(), lost.begin(), lost.end());
    return objects;
}

std::vector<Detection> ObjectDynamicAdapter::ConvertDetections(
    const ObjectSnapshot &snapshot) const
{
    std::vector<Detection> result;
    result.reserve(snapshot.detections.size());
    for(std::size_t index = 0; index < snapshot.detections.size(); ++index)
    {
        const SnapshotDetection &detection = snapshot.detections[index];
        result.push_back(Detection(detection.class_id, detection.class_name,
                                   detection.bbox, detection.confidence,
                                   detection.position_3d,
                                   detection.position_valid));
    }
    return result;
}

const std::vector<ObjectState::MapPointId> &
ObjectDynamicAdapter::MapPointsForDetection(const ObjectSnapshot &snapshot,
                                            std::size_t detection_index) const
{
    const SnapshotDetection &detection = snapshot.detections[detection_index];
    if(!detection.map_point_ids.empty())
        return detection.map_point_ids;
    if(snapshot.detections.size() == 1)
        return snapshot.map_point_ids;

    static const std::vector<ObjectState::MapPointId> empty;
    return empty;
}

void ObjectDynamicAdapter::AssociateDetectionMapPoints(
    ObjectState::ObjectId object_id,
    const ObjectSnapshot &snapshot,
    std::size_t detection_index)
{
    const std::vector<ObjectState::MapPointId> &map_points =
        MapPointsForDetection(snapshot, detection_index);
    for(std::size_t index = 0; index < map_points.size(); ++index)
        map_manager_.AssociateMapPoint(object_id, map_points[index]);
}

StableMapView ObjectDynamicAdapter::BuildStableMapView(
    std::uint64_t frame_id,
    double timestamp,
    bool snapshot_accepted) const
{
    StableMapView view;
    view.frame_id = frame_id;
    view.timestamp = timestamp;
    view.snapshot_accepted = snapshot_accepted;
    view.active_objects = map_manager_.GetActiveObjects();
    view.recovered_objects = map_manager_.GetRecoveredObjects();

    for(std::size_t index = 0; index < view.active_objects.size(); ++index)
    {
        if(view.active_objects[index].GetLifecycleState()
           == ObjectLifecycleState::Dynamic)
            view.dynamic_objects.push_back(view.active_objects[index]);
    }
    return view;
}

} // namespace Paper2
} // namespace ORB_SLAM2
