/*
Paper2 Object-level Dynamic SLAM Module

Purpose:
Value-only MapPoint filtering view derived from ObjectDynamic output.

Author:
Dong Jianing

Branch:
paper2_development
*/

#ifndef PAPER2_OBJECT_DYNAMIC_DYNAMIC_MAP_FILTER_H
#define PAPER2_OBJECT_DYNAMIC_DYNAMIC_MAP_FILTER_H

#include "ObjectDynamicAdapter.h"

#include <cstddef>
#include <cstdint>
#include <unordered_map>

namespace ORB_SLAM2
{
namespace Paper2
{

enum class MapPointStatus
{
    Static,
    Dynamic,
    Recovered
};

class DynamicMapFilter
{
public:
    explicit DynamicMapFilter(std::uint64_t expiration_frame_threshold = 30);

    bool UpdateMapView(const StableMapView &map_view);

    bool IsDynamicMapPoint(ObjectState::MapPointId map_point_id) const;
    MapPointStatus GetPointStatus(ObjectState::MapPointId map_point_id) const;
    bool HasMapPoint(ObjectState::MapPointId map_point_id) const;
    bool GetAssociatedObjectId(ObjectState::MapPointId map_point_id,
                               ObjectState::ObjectId *object_id) const;

    std::size_t ClearExpiredPoints();
    void SetExpirationFrameThreshold(std::uint64_t frame_threshold);
    std::uint64_t GetExpirationFrameThreshold() const;
    std::size_t GetTrackedPointCount() const;
    void Clear();

private:
    struct PointRecord
    {
        ObjectState::ObjectId object_id;
        MapPointStatus status;
        std::uint64_t last_seen_frame_id;

        PointRecord();
        PointRecord(ObjectState::ObjectId object_id_value,
                    MapPointStatus status_value,
                    std::uint64_t frame_id_value);
    };

    typedef std::unordered_map<ObjectState::MapPointId, PointRecord> PointMap;

    void UpdateObjects(const std::vector<ObjectState> &objects,
                       MapPointStatus status,
                       std::uint64_t frame_id);
    void UpdatePoint(ObjectState::MapPointId map_point_id,
                     ObjectState::ObjectId object_id,
                     MapPointStatus status,
                     std::uint64_t frame_id);
    static int StatusPriority(MapPointStatus status);

    PointMap points_;
    std::uint64_t expiration_frame_threshold_;
    std::uint64_t current_frame_id_;
    bool has_current_frame_;
};

} // namespace Paper2
} // namespace ORB_SLAM2

#endif // PAPER2_OBJECT_DYNAMIC_DYNAMIC_MAP_FILTER_H
