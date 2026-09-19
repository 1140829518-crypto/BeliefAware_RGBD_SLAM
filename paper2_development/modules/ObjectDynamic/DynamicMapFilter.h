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
#include "MapPoint.h"

#include <cstddef>
#include <cstdint>
#include <fstream>
#include <unordered_map>
#include <vector>

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

// Paper2 extension:
// Persistent dynamic landmark belief representation
typedef MapPointDynamicBelief DynamicBelief;

class DynamicMapFilter
{
public:
    explicit DynamicMapFilter(std::uint64_t expiration_frame_threshold = 30);

    bool UpdateMapView(const StableMapView &map_view);

    bool IsDynamicMapPoint(ObjectState::MapPointId map_point_id) const;
    // Paper2 extension:
    // Belief-aware measurement reliability
    bool IsHighConfidenceDynamicMapPoint(
        ObjectState::MapPointId map_point_id) const;
    MapPointStatus GetPointStatus(ObjectState::MapPointId map_point_id) const;
    // Paper2 extension:
    // Persistent dynamic landmark belief representation
    float GetDynamicProbability(
        ObjectState::MapPointId map_point_id) const;
    float GetUncertainty(ObjectState::MapPointId map_point_id) const;
    // Paper2 extension:
    // Belief-aware measurement reliability
    float GetMeasurementReliability(
        ObjectState::MapPointId map_point_id) const;
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
        // Paper2 extension:
        // Persistent dynamic landmark belief representation
        PointRecord();
        PointRecord(ObjectState::ObjectId object_id_value,
                    MapPointStatus status_value,
                    std::uint64_t frame_id_value);
    };

    typedef std::unordered_map<ObjectState::MapPointId, PointRecord> PointMap;

    struct ObjectRecord
    {
        MapPointStatus status;
        DynamicBelief belief;

        ObjectRecord();
    };
    typedef std::unordered_map<ObjectState::ObjectId, ObjectRecord> ObjectMap;

    void UpdateObjects(const std::vector<ObjectState> &objects,
                       MapPointStatus status,
                       std::uint64_t frame_id);
    void UpdatePoint(ObjectState::MapPointId map_point_id,
                     ObjectState::ObjectId object_id,
                     MapPointStatus status,
                     std::uint64_t frame_id);
    struct BeliefUpdateTrace
    {
        DynamicBelief previous;
        DynamicBelief after_gap;
        DynamicBelief after_observation;
        float observation;
        int previous_observation;
        float switch_event;
        float persistence_before;
        float persistence_after;
        float raw_conflict;
        float persistent_conflict;
        float conflict;
        float uncertainty_consistency_term;
        std::uint64_t missing_gap;

        BeliefUpdateTrace()
            : observation(0.0f), previous_observation(0), switch_event(0.0f),
              persistence_before(0.0f), persistence_after(0.0f),
              raw_conflict(0.0f), persistent_conflict(0.0f), conflict(0.0f),
              uncertainty_consistency_term(0.0f), missing_gap(0)
        {
        }
    };
    BeliefUpdateTrace UpdateBelief(DynamicBelief &belief,
                                   MapPointStatus status,
                                   std::uint64_t frame_id);
    bool FindCarrierBelief(ObjectState::MapPointId map_point_id,
                           DynamicBelief *belief) const;
    void LogBeliefUpdate(ObjectState::MapPointId map_point_id,
                         const PointRecord &record,
                         const BeliefUpdateTrace &trace);
    static int StatusPriority(MapPointStatus status);

    PointMap points_;
    ObjectMap objects_;
    std::uint64_t expiration_frame_threshold_;
    std::uint64_t current_frame_id_;
    bool has_current_frame_;
    // Paper2 experiment instrumentation; empty unless a log path is supplied.
    std::ofstream belief_log_;
};

} // namespace Paper2
} // namespace ORB_SLAM2

#endif // PAPER2_OBJECT_DYNAMIC_DYNAMIC_MAP_FILTER_H
