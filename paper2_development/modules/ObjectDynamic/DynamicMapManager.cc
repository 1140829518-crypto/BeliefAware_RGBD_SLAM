/*
Paper2 Object-level Dynamic SLAM Module

Purpose:
Object-map association, dynamic map update, and recovery interfaces.

Author:
Dong Jianing

Branch:
paper2_development
*/

#include "DynamicMapManager.h"

namespace ORB_SLAM2
{
namespace Paper2
{

DynamicMapManager::DynamicMapManager()
    : static_threshold_(0.30),
      potential_dynamic_threshold_(0.50),
      dynamic_threshold_(0.70),
      recovery_confirmation_frames_(3)
{
}

DynamicMapManager::~DynamicMapManager()
{
}

bool DynamicMapManager::AddObject(const ObjectState &object)
{
    const ObjectState::ObjectId object_id = object.GetObjectId();
    if(objects_.count(object_id) != 0)
        return false;

    objects_.insert(std::make_pair(object_id, object));
    const std::vector<ObjectState::MapPointId> &map_points =
        object.GetAssociatedMapPoints();
    map_point_associations_[object_id].insert(map_points.begin(), map_points.end());
    recovery_confirmations_[object_id] = 0;
    return true;
}

bool DynamicMapManager::RemoveObject(ObjectState::ObjectId object_id)
{
    if(objects_.erase(object_id) == 0)
        return false;
    map_point_associations_.erase(object_id);
    recovery_confirmations_.erase(object_id);
    return true;
}

bool DynamicMapManager::UpdateObject(const ObjectState &object)
{
    const ObjectState::ObjectId object_id = object.GetObjectId();
    ObjectMap::iterator it = objects_.find(object_id);
    if(it == objects_.end())
        return false;

    it->second = object;
    SynchronizeObjectMapPoints(object_id);
    return true;
}

bool DynamicMapManager::HasObject(ObjectState::ObjectId object_id) const
{
    return objects_.count(object_id) != 0;
}

bool DynamicMapManager::GetObject(ObjectState::ObjectId object_id,
                                  ObjectState *object) const
{
    if(object == NULL)
        return false;
    const ObjectMap::const_iterator it = objects_.find(object_id);
    if(it == objects_.end())
        return false;
    *object = it->second;
    return true;
}

std::vector<ObjectState> DynamicMapManager::GetActiveObjects() const
{
    std::vector<ObjectState> result;
    for(ObjectMap::const_iterator it = objects_.begin(); it != objects_.end(); ++it)
    {
        if(IsActiveState(it->second.GetLifecycleState()))
            result.push_back(it->second);
    }
    return result;
}

std::vector<ObjectState> DynamicMapManager::GetLostObjects() const
{
    std::vector<ObjectState> result;
    for(ObjectMap::const_iterator it = objects_.begin(); it != objects_.end(); ++it)
    {
        if(it->second.GetLifecycleState() == ObjectLifecycleState::Lost)
            result.push_back(it->second);
    }
    return result;
}

std::vector<ObjectState> DynamicMapManager::GetRecoveredObjects() const
{
    std::vector<ObjectState> result;
    for(ObjectMap::const_iterator it = objects_.begin(); it != objects_.end(); ++it)
    {
        if(it->second.GetLifecycleState() == ObjectLifecycleState::Recovered)
            result.push_back(it->second);
    }
    return result;
}

std::size_t DynamicMapManager::GetObjectCount() const
{
    return objects_.size();
}

bool DynamicMapManager::UpdateObjectState(ObjectState::ObjectId object_id,
                                          double dynamic_probability,
                                          bool observed)
{
    ObjectMap::iterator it = objects_.find(object_id);
    if(it == objects_.end())
        return false;
    it->second.SetDynamicProbability(dynamic_probability);
    return CheckTransition(object_id, observed);
}

bool DynamicMapManager::CheckTransition(ObjectState::ObjectId object_id,
                                        bool observed)
{
    ObjectMap::iterator it = objects_.find(object_id);
    if(it == objects_.end())
        return false;

    ObjectState &object = it->second;
    ObjectLifecycleState current_state = object.GetLifecycleState();

    if(!observed)
    {
        object.SetLifecycleState(ObjectLifecycleState::Lost);
        recovery_confirmations_[object_id] = 0;
        return true;
    }

    if(current_state == ObjectLifecycleState::Lost)
    {
        object.SetLifecycleState(ObjectLifecycleState::PotentialDynamic);
        recovery_confirmations_[object_id] = 0;
        current_state = ObjectLifecycleState::PotentialDynamic;
    }

    const double probability = object.GetDynamicProbability();
    const double object_dynamic_threshold =
        object.GetClassId() == 3 ? 0.60 : dynamic_threshold_;
    if(current_state == ObjectLifecycleState::Static)
    {
        if(probability >= potential_dynamic_threshold_)
            object.SetLifecycleState(ObjectLifecycleState::PotentialDynamic);
    }
    else if(current_state == ObjectLifecycleState::PotentialDynamic)
    {
        if(probability >= object_dynamic_threshold)
            object.SetLifecycleState(ObjectLifecycleState::Dynamic);
        else if(probability <= static_threshold_)
            object.SetLifecycleState(ObjectLifecycleState::Static);
    }
    else if(current_state == ObjectLifecycleState::Dynamic)
    {
        if(probability < potential_dynamic_threshold_)
            object.SetLifecycleState(ObjectLifecycleState::PotentialDynamic);
    }
    else if(current_state == ObjectLifecycleState::Recovered)
    {
        if(probability >= object_dynamic_threshold)
            object.SetLifecycleState(ObjectLifecycleState::Dynamic);
        else if(probability <= static_threshold_)
            object.SetLifecycleState(ObjectLifecycleState::Static);
        else
            object.SetLifecycleState(ObjectLifecycleState::PotentialDynamic);
    }

    recovery_confirmations_[object_id] = 0;
    return true;
}

bool DynamicMapManager::RecoverObject(ObjectState::ObjectId object_id)
{
    ObjectMap::iterator it = objects_.find(object_id);
    if(it == objects_.end()
       || it->second.GetLifecycleState() != ObjectLifecycleState::Lost)
        return false;

    std::size_t &confirmation_count = recovery_confirmations_[object_id];
    ++confirmation_count;
    if(confirmation_count < recovery_confirmation_frames_)
        return false;

    it->second.SetLifecycleState(ObjectLifecycleState::Recovered);
    confirmation_count = 0;
    return true;
}

bool DynamicMapManager::AssociateMapPoint(ObjectState::ObjectId object_id,
                                          ObjectState::MapPointId map_point_id)
{
    ObjectMap::iterator object_it = objects_.find(object_id);
    if(object_it == objects_.end())
        return false;

    MapPointSet &map_points = map_point_associations_[object_id];
    if(!map_points.insert(map_point_id).second)
        return false;

    object_it->second.AddMapPoint(map_point_id);
    return true;
}

bool DynamicMapManager::RemoveMapPoint(ObjectState::ObjectId object_id,
                                       ObjectState::MapPointId map_point_id)
{
    ObjectMap::iterator object_it = objects_.find(object_id);
    std::map<ObjectState::ObjectId, MapPointSet>::iterator association_it =
        map_point_associations_.find(object_id);
    if(object_it == objects_.end() || association_it == map_point_associations_.end()
       || association_it->second.erase(map_point_id) == 0)
        return false;

    object_it->second.RemoveMapPoint(map_point_id);
    return true;
}

std::vector<ObjectState::MapPointId> DynamicMapManager::GetObjectMapPoints(
    ObjectState::ObjectId object_id) const
{
    const std::map<ObjectState::ObjectId, MapPointSet>::const_iterator it =
        map_point_associations_.find(object_id);
    if(it == map_point_associations_.end())
        return std::vector<ObjectState::MapPointId>();
    return std::vector<ObjectState::MapPointId>(it->second.begin(), it->second.end());
}

void DynamicMapManager::SetTransitionThresholds(
    double static_threshold,
    double potential_dynamic_threshold,
    double dynamic_threshold)
{
    if(static_threshold < 0.0 || dynamic_threshold > 1.0
       || static_threshold >= potential_dynamic_threshold
       || potential_dynamic_threshold >= dynamic_threshold)
        return;

    static_threshold_ = static_threshold;
    potential_dynamic_threshold_ = potential_dynamic_threshold;
    dynamic_threshold_ = dynamic_threshold;
}

void DynamicMapManager::SetRecoveryConfirmationFrames(std::size_t frame_count)
{
    if(frame_count > 0)
        recovery_confirmation_frames_ = frame_count;
}

std::size_t DynamicMapManager::GetRecoveryConfirmationFrames() const
{
    return recovery_confirmation_frames_;
}

std::size_t DynamicMapManager::GetRecoveryConfirmationCount(
    ObjectState::ObjectId object_id) const
{
    const std::map<ObjectState::ObjectId, std::size_t>::const_iterator it =
        recovery_confirmations_.find(object_id);
    return it == recovery_confirmations_.end() ? 0 : it->second;
}

void DynamicMapManager::SynchronizeObjectMapPoints(
    ObjectState::ObjectId object_id)
{
    ObjectMap::iterator object_it = objects_.find(object_id);
    if(object_it == objects_.end())
        return;

    const std::vector<ObjectState::MapPointId> current =
        object_it->second.GetAssociatedMapPoints();
    for(std::size_t index = 0; index < current.size(); ++index)
        object_it->second.RemoveMapPoint(current[index]);

    const MapPointSet &authoritative = map_point_associations_[object_id];
    for(MapPointSet::const_iterator it = authoritative.begin();
        it != authoritative.end(); ++it)
        object_it->second.AddMapPoint(*it);
}

bool DynamicMapManager::IsActiveState(ObjectLifecycleState state)
{
    return state != ObjectLifecycleState::Lost;
}

} // namespace Paper2
} // namespace ORB_SLAM2
