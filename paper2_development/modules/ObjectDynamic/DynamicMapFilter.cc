/*
Paper2 Object-level Dynamic SLAM Module

Purpose:
Value-only MapPoint filtering view derived from ObjectDynamic output.

Author:
Dong Jianing

Branch:
paper2_development
*/

#include "DynamicMapFilter.h"

namespace ORB_SLAM2
{
namespace Paper2
{

DynamicMapFilter::PointRecord::PointRecord()
    : object_id(0), status(MapPointStatus::Static), last_seen_frame_id(0)
{
}

DynamicMapFilter::PointRecord::PointRecord(
    ObjectState::ObjectId object_id_value,
    MapPointStatus status_value,
    std::uint64_t frame_id_value)
    : object_id(object_id_value),
      status(status_value),
      last_seen_frame_id(frame_id_value)
{
}

DynamicMapFilter::DynamicMapFilter(std::uint64_t expiration_frame_threshold)
    : expiration_frame_threshold_(expiration_frame_threshold),
      current_frame_id_(0),
      has_current_frame_(false)
{
}

bool DynamicMapFilter::UpdateMapView(const StableMapView &map_view)
{
    if(!map_view.snapshot_accepted
       || (has_current_frame_ && map_view.frame_id <= current_frame_id_))
    {
        return false;
    }

    current_frame_id_ = map_view.frame_id;
    has_current_frame_ = true;

    // Apply lower-priority states first. A malformed view containing the same
    // point in several groups is resolved conservatively in favour of Dynamic.
    UpdateObjects(map_view.active_objects, MapPointStatus::Static,
                  map_view.frame_id);
    UpdateObjects(map_view.recovered_objects, MapPointStatus::Recovered,
                  map_view.frame_id);
    UpdateObjects(map_view.dynamic_objects, MapPointStatus::Dynamic,
                  map_view.frame_id);
    return true;
}

bool DynamicMapFilter::IsDynamicMapPoint(
    ObjectState::MapPointId map_point_id) const
{
    return GetPointStatus(map_point_id) == MapPointStatus::Dynamic;
}

MapPointStatus DynamicMapFilter::GetPointStatus(
    ObjectState::MapPointId map_point_id) const
{
    const PointMap::const_iterator found = points_.find(map_point_id);
    if(found == points_.end())
        return MapPointStatus::Static;
    return found->second.status;
}

bool DynamicMapFilter::HasMapPoint(ObjectState::MapPointId map_point_id) const
{
    return points_.find(map_point_id) != points_.end();
}

bool DynamicMapFilter::GetAssociatedObjectId(
    ObjectState::MapPointId map_point_id,
    ObjectState::ObjectId *object_id) const
{
    if(object_id == NULL)
        return false;
    const PointMap::const_iterator found = points_.find(map_point_id);
    if(found == points_.end())
        return false;
    *object_id = found->second.object_id;
    return true;
}

std::size_t DynamicMapFilter::ClearExpiredPoints()
{
    if(!has_current_frame_)
        return 0;

    std::size_t removed = 0;
    PointMap::iterator current = points_.begin();
    while(current != points_.end())
    {
        const std::uint64_t age = current_frame_id_ >= current->second.last_seen_frame_id
                                ? current_frame_id_ - current->second.last_seen_frame_id
                                : 0;
        if(age > expiration_frame_threshold_)
        {
            current = points_.erase(current);
            ++removed;
        }
        else
        {
            ++current;
        }
    }
    return removed;
}

void DynamicMapFilter::SetExpirationFrameThreshold(
    std::uint64_t frame_threshold)
{
    expiration_frame_threshold_ = frame_threshold;
}

std::uint64_t DynamicMapFilter::GetExpirationFrameThreshold() const
{
    return expiration_frame_threshold_;
}

std::size_t DynamicMapFilter::GetTrackedPointCount() const
{
    return points_.size();
}

void DynamicMapFilter::Clear()
{
    points_.clear();
    current_frame_id_ = 0;
    has_current_frame_ = false;
}

void DynamicMapFilter::UpdateObjects(const std::vector<ObjectState> &objects,
                                     MapPointStatus status,
                                     std::uint64_t frame_id)
{
    for(std::size_t object_index = 0;
        object_index < objects.size(); ++object_index)
    {
        const ObjectState &object = objects[object_index];
        MapPointStatus effective_status = status;
        if(status == MapPointStatus::Static
           && object.GetLifecycleState() == ObjectLifecycleState::Dynamic)
        {
            effective_status = MapPointStatus::Dynamic;
        }
        else if(status == MapPointStatus::Static
                && object.GetLifecycleState() == ObjectLifecycleState::Recovered)
        {
            effective_status = MapPointStatus::Recovered;
        }

        const std::vector<ObjectState::MapPointId> &map_points =
            object.GetAssociatedMapPoints();
        for(std::size_t point_index = 0;
            point_index < map_points.size(); ++point_index)
        {
            UpdatePoint(map_points[point_index], object.GetObjectId(),
                        effective_status, frame_id);
        }
    }
}

void DynamicMapFilter::UpdatePoint(ObjectState::MapPointId map_point_id,
                                   ObjectState::ObjectId object_id,
                                   MapPointStatus status,
                                   std::uint64_t frame_id)
{
    PointMap::iterator found = points_.find(map_point_id);
    if(found == points_.end())
    {
        points_.insert(std::make_pair(
            map_point_id, PointRecord(object_id, status, frame_id)));
        return;
    }

    if(found->second.last_seen_frame_id != frame_id
       || StatusPriority(status) > StatusPriority(found->second.status)
       || (StatusPriority(status) == StatusPriority(found->second.status)
           && object_id < found->second.object_id))
    {
        found->second.object_id = object_id;
        found->second.status = status;
    }
    found->second.last_seen_frame_id = frame_id;
}

int DynamicMapFilter::StatusPriority(MapPointStatus status)
{
    if(status == MapPointStatus::Dynamic)
        return 2;
    if(status == MapPointStatus::Recovered)
        return 1;
    return 0;
}

} // namespace Paper2
} // namespace ORB_SLAM2
