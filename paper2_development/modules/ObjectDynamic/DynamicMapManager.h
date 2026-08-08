/*
Paper2 Object-level Dynamic SLAM Module

Purpose:
Object-map association, dynamic map update, and recovery interfaces.

Author:
Dong Jianing

Branch:
paper2_development
*/

#ifndef PAPER2_OBJECT_DYNAMIC_DYNAMIC_MAP_MANAGER_H
#define PAPER2_OBJECT_DYNAMIC_DYNAMIC_MAP_MANAGER_H

#include "ObjectState.h"

#include <cstddef>
#include <map>
#include <set>
#include <vector>

namespace ORB_SLAM2
{
namespace Paper2
{

class DynamicMapManager
{
public:
    DynamicMapManager();
    ~DynamicMapManager();

    bool AddObject(const ObjectState &object);
    bool RemoveObject(ObjectState::ObjectId object_id);
    bool UpdateObject(const ObjectState &object);
    bool HasObject(ObjectState::ObjectId object_id) const;
    bool GetObject(ObjectState::ObjectId object_id, ObjectState *object) const;

    std::vector<ObjectState> GetActiveObjects() const;
    std::vector<ObjectState> GetLostObjects() const;
    std::vector<ObjectState> GetRecoveredObjects() const;
    std::size_t GetObjectCount() const;

    bool UpdateObjectState(ObjectState::ObjectId object_id,
                           double dynamic_probability,
                           bool observed);
    bool CheckTransition(ObjectState::ObjectId object_id, bool observed);
    bool RecoverObject(ObjectState::ObjectId object_id);

    bool AssociateMapPoint(ObjectState::ObjectId object_id,
                           ObjectState::MapPointId map_point_id);
    bool RemoveMapPoint(ObjectState::ObjectId object_id,
                        ObjectState::MapPointId map_point_id);
    std::vector<ObjectState::MapPointId> GetObjectMapPoints(
        ObjectState::ObjectId object_id) const;

    void SetTransitionThresholds(double static_threshold,
                                 double potential_dynamic_threshold,
                                 double dynamic_threshold);
    void SetRecoveryConfirmationFrames(std::size_t frame_count);
    std::size_t GetRecoveryConfirmationFrames() const;
    std::size_t GetRecoveryConfirmationCount(
        ObjectState::ObjectId object_id) const;

private:
    typedef std::map<ObjectState::ObjectId, ObjectState> ObjectMap;
    typedef std::set<ObjectState::MapPointId> MapPointSet;

    void SynchronizeObjectMapPoints(ObjectState::ObjectId object_id);
    static bool IsActiveState(ObjectLifecycleState state);

    ObjectMap objects_;
    std::map<ObjectState::ObjectId, MapPointSet> map_point_associations_;
    std::map<ObjectState::ObjectId, std::size_t> recovery_confirmations_;

    double static_threshold_;
    double potential_dynamic_threshold_;
    double dynamic_threshold_;
    std::size_t recovery_confirmation_frames_;
};

} // namespace Paper2
} // namespace ORB_SLAM2

#endif // PAPER2_OBJECT_DYNAMIC_DYNAMIC_MAP_MANAGER_H
