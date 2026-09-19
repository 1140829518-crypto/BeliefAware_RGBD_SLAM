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
#include "SemanticConfig.h"
#include "ExperimentTiming.h"

#include <algorithm>
#include <cstdlib>
#include <cmath>
#include <string>
#include <map>

namespace
{

const float kUncertaintyRetentionAlpha = 0.8f;

bool ExperimentSwitch(const char *name, bool default_value)
{
    const char *value = std::getenv(name);
    if(value == NULL || *value == '\0')
        return default_value;
    const std::string text(value);
    return text != "0" && text != "false" && text != "FALSE"
        && text != "off" && text != "OFF";
}

const char *StatusName(ORB_SLAM2::Paper2::MapPointStatus status)
{
    if(status == ORB_SLAM2::Paper2::MapPointStatus::Dynamic)
        return "Dynamic";
    if(status == ORB_SLAM2::Paper2::MapPointStatus::Recovered)
        return "Recovered";
    return "Static";
}

bool UseObjectCarrier()
{
    const char *value = std::getenv("ORB_SLAM2_MEMORY_CARRIER");
    return value != NULL && std::string(value) == "object";
}

bool UsesStrictCarrierMemory()
{
    const char *value = std::getenv("ORB_SLAM2_MEMORY_CARRIER");
    return value != NULL && (std::string(value) == "object"
                          || std::string(value) == "mappoint");
}

} // namespace

namespace ORB_SLAM2
{
namespace Paper2
{

// Paper2 extension:
// Persistent dynamic landmark belief representation
DynamicMapFilter::PointRecord::PointRecord()
    : object_id(0), status(MapPointStatus::Static)
{
}

DynamicMapFilter::PointRecord::PointRecord(
    ObjectState::ObjectId object_id_value,
    MapPointStatus status_value,
    std::uint64_t frame_id_value)
    : object_id(object_id_value),
      status(status_value)
{
    // Paper2 extension:
    // Persistent dynamic landmark belief representation
    (void)frame_id_value;
}

DynamicMapFilter::ObjectRecord::ObjectRecord()
    : status(MapPointStatus::Static), belief()
{
}

DynamicMapFilter::DynamicMapFilter(std::uint64_t expiration_frame_threshold)
    : expiration_frame_threshold_(expiration_frame_threshold),
      current_frame_id_(0),
      has_current_frame_(false)
{
    const char *log_path = std::getenv("ORB_SLAM2_BELIEF_LOG");
    if(log_path != NULL && *log_path != '\0')
    {
        belief_log_.open(log_path, std::ios::out | std::ios::trunc);
        if(belief_log_)
        {
            belief_log_ << "frame_id,map_point_id,object_id,previous_p,previous_u,"
                           "missing_gap,after_gap_p,after_gap_u,observation,conflict,"
                           "uncertainty_consistency_term,after_observation_p,"
                           "after_observation_u,final_reliability,"
                           "previous_state,new_state,status,previous_observation,"
                           "switch_event,persistence_before,persistence_after,"
                           "raw_conflict,persistent_conflict\n";
        }
    }
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
    double beliefUpdateSeconds = 0.0;
    std::size_t beliefUpdateCalls = 0;

    if(UsesStrictCarrierMemory())
    {
        // The carrier experiment consumes only associations actually visible
        // in this frame; lifetime-cumulative ObjectState associations are not
        // valid landmark observations.
        std::map<ObjectState::ObjectId, MapPointStatus> object_status;
        for(std::size_t i = 0; i < map_view.carrier_observations.size(); ++i)
        {
            const StableMapView::CarrierObservation &observation =
                map_view.carrier_observations[i];
            const MapPointStatus status =
                SemanticConfig::IsDynamicObjectClass(observation.class_id)
                ? MapPointStatus::Dynamic : MapPointStatus::Static;
            object_status[observation.object_id] = status;
            if(UseObjectCarrier())
            {
                ObjectRecord &record = objects_[observation.object_id];
                if(record.belief.last_observation_frame != map_view.frame_id)
                    UpdateBelief(record.belief, status, map_view.frame_id);
                record.status = status;
            }
            for(std::size_t j = 0; j < observation.map_point_ids.size(); ++j)
            {
                const ObjectState::MapPointId point_id = observation.map_point_ids[j];
                PointRecord &point = points_[point_id];
                point.object_id = observation.object_id;
                point.status = status;
                MapPoint *mapPoint = MapPoint::GetById(point_id);
                if(!mapPoint)
                    continue;
                BeliefUpdateTrace trace;
                if(UseObjectCarrier())
                {
                    trace.previous = mapPoint->GetDynamicBelief();
                    mapPoint->SetDynamicBelief(objects_[observation.object_id].belief);
                    trace.after_gap = trace.after_observation = mapPoint->GetDynamicBelief();
                    trace.observation = status == MapPointStatus::Dynamic ? 1.0f : 0.0f;
                    trace.conflict = trace.after_observation.conflict;
                    trace.raw_conflict = trace.conflict;
                    trace.persistence_before = trace.previous.conflict_persistence;
                    trace.persistence_after = trace.after_observation.conflict_persistence;
                    trace.persistent_conflict = trace.raw_conflict * trace.persistence_after;
                    trace.previous_observation = trace.previous.previous_observation;
                    trace.uncertainty_consistency_term =
                        (1.0f - kUncertaintyRetentionAlpha)
                        * (SemanticConfig::UncertaintyMode() == SemanticConfig::BELIEF_UNCERTAINTY_PERSISTENT
                           ? trace.persistent_conflict : trace.raw_conflict);
                    trace.missing_gap = 0;
                }
                else
                {
                    DynamicBelief belief = mapPoint->GetDynamicBelief();
                    const std::chrono::steady_clock::time_point beliefStart =
                        std::chrono::steady_clock::now();
                    trace = UpdateBelief(belief, status, map_view.frame_id);
                    mapPoint->SetDynamicBelief(belief);
                    beliefUpdateSeconds +=
                        std::chrono::duration_cast<std::chrono::duration<double> >(
                            std::chrono::steady_clock::now() - beliefStart).count();
                    ++beliefUpdateCalls;
                }
                LogBeliefUpdate(point_id, point, trace);
            }
        }
        ExperimentTiming::AddAggregate(TimingComponent::BeliefUpdate,
            beliefUpdateSeconds, beliefUpdateCalls);
        return true;
    }

    // Resolve duplicate memberships first so every carrier receives exactly
    // one observation update per frame. Dynamic has conservative priority.
    std::map<ObjectState::ObjectId, std::pair<const ObjectState*, MapPointStatus> > observations;
    const std::vector<std::pair<const std::vector<ObjectState>*, MapPointStatus> > groups = {
        std::make_pair(&map_view.active_objects, MapPointStatus::Static),
        std::make_pair(&map_view.recovered_objects, MapPointStatus::Recovered),
        std::make_pair(&map_view.dynamic_objects, MapPointStatus::Dynamic)};
    for(std::size_t group_index = 0; group_index < groups.size(); ++group_index)
    {
        const std::vector<ObjectState> &group = *groups[group_index].first;
        for(std::size_t i = 0; i < group.size(); ++i)
        {
            MapPointStatus status = groups[group_index].second;
            if(UsesStrictCarrierMemory())
            {
                status = SemanticConfig::IsDynamicObjectClass(group[i].GetClassId())
                       ? MapPointStatus::Dynamic : MapPointStatus::Static;
            }
            else if(status == MapPointStatus::Static
               && group[i].GetLifecycleState() == ObjectLifecycleState::Dynamic)
                status = MapPointStatus::Dynamic;
            else if(status == MapPointStatus::Static
                    && group[i].GetLifecycleState() == ObjectLifecycleState::Recovered)
                status = MapPointStatus::Recovered;
            std::pair<const ObjectState*, MapPointStatus> &slot = observations[group[i].GetObjectId()];
            if(slot.first == NULL || StatusPriority(status) > StatusPriority(slot.second))
                slot = std::make_pair(&group[i], status);
        }
    }

    for(std::map<ObjectState::ObjectId, std::pair<const ObjectState*, MapPointStatus> >::const_iterator
            it = observations.begin(); it != observations.end(); ++it)
    {
        const ObjectState &object = *it->second.first;
        const MapPointStatus status = it->second.second;
        if(UseObjectCarrier())
        {
            ObjectRecord &record = objects_[object.GetObjectId()];
            record.status = status;
            UpdateBelief(record.belief, status, map_view.frame_id);
        }
        const std::vector<ObjectState::MapPointId> &map_points =
            object.GetAssociatedMapPoints();
        for(std::size_t point_index = 0; point_index < map_points.size(); ++point_index)
        {
            if(UseObjectCarrier())
            {
                PointRecord &point = points_[map_points[point_index]];
                point.object_id = object.GetObjectId();
                point.status = status;
                MapPoint *mapPoint = MapPoint::GetById(map_points[point_index]);
                if(!mapPoint)
                    continue;
                BeliefUpdateTrace trace;
                trace.previous = mapPoint->GetDynamicBelief();
                mapPoint->SetDynamicBelief(objects_[object.GetObjectId()].belief);
                trace.after_gap = trace.after_observation = mapPoint->GetDynamicBelief();
                trace.observation = status == MapPointStatus::Dynamic ? 1.0f : 0.0f;
                trace.conflict = trace.after_observation.conflict;
                trace.raw_conflict = trace.conflict;
                trace.persistence_before = trace.previous.conflict_persistence;
                trace.persistence_after = trace.after_observation.conflict_persistence;
                trace.persistent_conflict = trace.raw_conflict * trace.persistence_after;
                trace.previous_observation = trace.previous.previous_observation;
                trace.uncertainty_consistency_term =
                    (1.0f - kUncertaintyRetentionAlpha)
                    * (SemanticConfig::UncertaintyMode() == SemanticConfig::BELIEF_UNCERTAINTY_PERSISTENT
                       ? trace.persistent_conflict : trace.raw_conflict);
                trace.missing_gap = 0;
                LogBeliefUpdate(map_points[point_index], point, trace);
            }
            else
                UpdatePoint(map_points[point_index], object.GetObjectId(),
                            status, map_view.frame_id);
        }
    }
    ExperimentTiming::AddAggregate(TimingComponent::BeliefUpdate,
        beliefUpdateSeconds, beliefUpdateCalls);
    return true;
}

bool DynamicMapFilter::IsDynamicMapPoint(
    ObjectState::MapPointId map_point_id) const
{
    if(!ExperimentSwitch("ORB_SLAM2_BELIEF_ENABLED", true))
        return GetPointStatus(map_point_id) == MapPointStatus::Dynamic;
    // Paper2 extension:
    // Persistent dynamic landmark belief representation
    return GetDynamicProbability(map_point_id) > 0.5f;
}

// Paper2 extension:
// Belief-aware measurement reliability
bool DynamicMapFilter::IsHighConfidenceDynamicMapPoint(
    ObjectState::MapPointId map_point_id) const
{
    const PointMap::const_iterator found = points_.find(map_point_id);
    if(found == points_.end())
        return false;
    if(!ExperimentSwitch("ORB_SLAM2_BELIEF_ENABLED", true))
        return found->second.status == MapPointStatus::Dynamic;
    const bool uncertainty_enabled =
        ExperimentSwitch("ORB_SLAM2_UNCERTAINTY_ENABLED", true);
    DynamicBelief belief;
    const bool foundBelief = FindCarrierBelief(map_point_id, &belief);
    return foundBelief && belief.dynamic_probability >= 0.8f
        && (!uncertainty_enabled
            || belief.uncertainty <= 0.3f);
}

MapPointStatus DynamicMapFilter::GetPointStatus(
    ObjectState::MapPointId map_point_id) const
{
    const PointMap::const_iterator found = points_.find(map_point_id);
    if(found == points_.end())
        return MapPointStatus::Static;
    return found->second.status;
}

// Paper2 extension:
// Persistent dynamic landmark belief representation
float DynamicMapFilter::GetDynamicProbability(
    ObjectState::MapPointId map_point_id) const
{
    const PointMap::const_iterator found = points_.find(map_point_id);
    if(found == points_.end())
        return 0.0f;
    DynamicBelief belief;
    return FindCarrierBelief(map_point_id, &belief) ? belief.dynamic_probability : 0.0f;
}

// Paper2 extension:
// Persistent dynamic landmark belief representation
float DynamicMapFilter::GetUncertainty(
    ObjectState::MapPointId map_point_id) const
{
    const PointMap::const_iterator found = points_.find(map_point_id);
    if(found == points_.end())
        return 1.0f;
    DynamicBelief belief;
    return FindCarrierBelief(map_point_id, &belief) ? belief.uncertainty : 1.0f;
}

// Paper2 extension:
// Belief-aware measurement reliability
float DynamicMapFilter::GetMeasurementReliability(
    ObjectState::MapPointId map_point_id) const
{
    if(!ExperimentSwitch("ORB_SLAM2_RELIABILITY_ENABLED", true))
        return 1.0f;
    const PointMap::const_iterator found = points_.find(map_point_id);
    if(found == points_.end())
        return 1.0f;

    DynamicBelief belief;
    if(!FindCarrierBelief(map_point_id, &belief))
        return 1.0f;
    const float reliability = (1.0f - belief.dynamic_probability)
                            * (1.0f - belief.uncertainty);
    return reliability > 0.05f ? reliability : 0.05f;
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
        // Paper2 extension:
        // Persistent dynamic landmark belief representation
        MapPoint *mapPoint = MapPoint::GetById(current->first);
        const DynamicBelief belief = mapPoint ? mapPoint->GetDynamicBelief() : DynamicBelief();
        const std::uint64_t age = current_frame_id_ >= belief.last_observation_frame
                                ? current_frame_id_ - belief.last_observation_frame
                                : 0;
        if(!mapPoint || age > expiration_frame_threshold_)
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
    objects_.clear();
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
    bool is_new_point = false;
    if(found == points_.end())
    {
        found = points_.insert(std::make_pair(
            map_point_id, PointRecord(object_id, status, frame_id))).first;
        is_new_point = true;
    }

    MapPoint *mapPoint = MapPoint::GetById(map_point_id);
    if(!mapPoint)
        return;
    DynamicBelief belief = mapPoint->GetDynamicBelief();
    const std::uint64_t previous_observation_frame =
        belief.last_observation_frame;
    const std::uint64_t gap = belief.observation_count == 0
                            ? 0
                            : (frame_id >= previous_observation_frame
                               ? frame_id - previous_observation_frame
                               : 0);
    const BeliefUpdateTrace trace = UpdateBelief(belief, status, frame_id);
    mapPoint->SetDynamicBelief(belief);

    if(is_new_point
       || previous_observation_frame != frame_id
       || StatusPriority(status) > StatusPriority(found->second.status)
       || (StatusPriority(status) == StatusPriority(found->second.status)
           && object_id < found->second.object_id))
    {
        found->second.object_id = object_id;
        found->second.status = status;
    }

    (void)gap;
    LogBeliefUpdate(map_point_id, found->second, trace);
}

DynamicMapFilter::BeliefUpdateTrace DynamicMapFilter::UpdateBelief(DynamicBelief &belief,
                                    MapPointStatus status,
                                    std::uint64_t frame_id)
{
    BeliefUpdateTrace trace;
    trace.previous = belief;
    trace.missing_gap = belief.observation_count == 0 ? 0
        : (frame_id > belief.last_observation_frame
           ? frame_id - belief.last_observation_frame - 1 : 0);
    trace.observation = status == MapPointStatus::Dynamic ? 1.0f : 0.0f;
    const bool enabled = ExperimentSwitch("ORB_SLAM2_BELIEF_ENABLED", true);
    const bool gap_enabled = ExperimentSwitch("ORB_SLAM2_BELIEF_GAP_ENABLED", true);
    const bool uncertainty_enabled = ExperimentSwitch("ORB_SLAM2_UNCERTAINTY_ENABLED", true);
    if(enabled && gap_enabled)
    {
        belief.dynamic_probability *= std::exp(-0.05f * static_cast<float>(trace.missing_gap));
        if(uncertainty_enabled)
            belief.uncertainty = 1.0f - (1.0f - belief.uncertainty)
                               * std::exp(-0.03f * static_cast<float>(trace.missing_gap));
    }
    trace.after_gap = belief;
    trace.previous_observation = belief.previous_observation;
    trace.switch_event = belief.has_previous_observation
        && static_cast<int>(trace.observation) != belief.previous_observation ? 1.0f : 0.0f;
    trace.persistence_before = belief.conflict_persistence;
    belief.conflict_persistence = std::min(1.0f, std::max(0.0f,
        0.8f * belief.conflict_persistence + 0.2f * trace.switch_event));
    trace.persistence_after = belief.conflict_persistence;
    trace.raw_conflict = std::min(1.0f, std::max(0.0f,
        std::fabs(trace.observation - belief.dynamic_probability)
        * (1.0f - belief.uncertainty)));
    trace.persistent_conflict = std::min(1.0f, std::max(0.0f,
        trace.raw_conflict * trace.persistence_after));
    trace.conflict = trace.raw_conflict;
    trace.uncertainty_consistency_term =
        (1.0f - kUncertaintyRetentionAlpha)
        * (SemanticConfig::UncertaintyMode() == SemanticConfig::BELIEF_UNCERTAINTY_PERSISTENT
           ? trace.persistent_conflict : trace.raw_conflict);
    belief.conflict = trace.raw_conflict;
    if(!enabled)
    {
        belief.dynamic_probability = status == MapPointStatus::Dynamic ? 1.0f : 0.0f;
        belief.uncertainty = 0.0f;
    }
    else
    {
        belief.dynamic_probability = 0.7f * belief.dynamic_probability
                                   + 0.3f * trace.observation;
        if(uncertainty_enabled)
        {
            const float uncertainty_update =
                kUncertaintyRetentionAlpha * belief.uncertainty
                + (SemanticConfig::UncertaintyMode() != SemanticConfig::BELIEF_UNCERTAINTY_CLEAN
                   ? trace.uncertainty_consistency_term : 0.0f);
            belief.uncertainty = std::min(1.0f,
                std::max(0.05f, uncertainty_update));
        }
        else
            belief.uncertainty = 0.0f;
    }
    if(status == MapPointStatus::Dynamic)
        belief.last_dynamic_frame = frame_id;
    belief.previous_observation = static_cast<int>(trace.observation);
    belief.has_previous_observation = true;
    ++belief.observation_count;
    belief.last_observation_frame = frame_id;
    trace.after_observation = belief;
    return trace;
}

bool DynamicMapFilter::FindCarrierBelief(ObjectState::MapPointId map_point_id,
                                         DynamicBelief *belief) const
{
    if(!belief || points_.find(map_point_id) == points_.end())
        return false;
    MapPoint *mapPoint = MapPoint::GetById(map_point_id);
    if(!mapPoint)
        return false;
    *belief = mapPoint->GetDynamicBelief();
    return true;
}

void DynamicMapFilter::LogBeliefUpdate(
    ObjectState::MapPointId map_point_id,
    const PointRecord &record,
    const BeliefUpdateTrace &trace)
{
    if(!belief_log_)
        return;
    belief_log_ << current_frame_id_ << ','
                << map_point_id << ','
                << record.object_id << ','
                << trace.previous.dynamic_probability << ','
                << trace.previous.uncertainty << ','
                << trace.missing_gap << ','
                << trace.after_gap.dynamic_probability << ','
                << trace.after_gap.uncertainty << ','
                << trace.observation << ','
                << trace.conflict << ','
                << trace.uncertainty_consistency_term << ','
                << trace.after_observation.dynamic_probability << ','
                << trace.after_observation.uncertainty << ','
                << GetMeasurementReliability(map_point_id) << ','
                << (trace.previous.dynamic_probability >= 0.8f && trace.previous.uncertainty <= 0.3f ? "Dynamic" : "NotDynamic") << ','
                << (trace.after_observation.dynamic_probability >= 0.8f && trace.after_observation.uncertainty <= 0.3f ? "Dynamic" : "NotDynamic") << ','
                << StatusName(record.status) << ','
                << trace.previous_observation << ','
                << trace.switch_event << ','
                << trace.persistence_before << ','
                << trace.persistence_after << ','
                << trace.raw_conflict << ','
                << trace.persistent_conflict << '\n';
    belief_log_.flush();
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
