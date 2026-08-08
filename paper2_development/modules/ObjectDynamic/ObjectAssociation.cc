/*
Paper2 Object-level Dynamic SLAM Module

Purpose:
Cross-frame object association using semantic, image, and 3D costs.

Author:
Dong Jianing

Branch:
paper2_development
*/

#include "ObjectAssociation.h"

#include <algorithm>
#include <cmath>
#include <limits>

namespace ORB_SLAM2
{
namespace Paper2
{

Detection::Detection()
    : class_id(-1), class_name("unknown"), bbox(), confidence(0.0), position_3d()
{
}

Detection::Detection(int class_id_value,
                     const std::string &class_name_value,
                     const BoundingBox2D &bbox_value,
                     double confidence_value,
                     const Vector3D &position_3d_value)
    : class_id(class_id_value),
      class_name(class_name_value),
      bbox(bbox_value),
      confidence(confidence_value),
      position_3d(position_3d_value)
{
}

AssociationWeights::AssociationWeights()
    : semantic(0.35), iou(0.30), spatial(0.15), distance_3d(0.20)
{
}

ObjectAssociation::ObjectAssociation(ObjectState::ObjectId first_object_id)
    : next_object_id_(first_object_id),
      weights_(),
      maximum_cost_(0.70),
      spatial_scale_(100.0),
      distance_3d_scale_(2.0)
{
}

void ObjectAssociation::SetWeights(const AssociationWeights &weights)
{
    weights_ = weights;
}

void ObjectAssociation::SetMaximumCost(double maximum_cost)
{
    maximum_cost_ = maximum_cost < 0.0 ? 0.0 : maximum_cost;
}

void ObjectAssociation::SetSpatialScale(double pixels)
{
    if(pixels > 0.0)
        spatial_scale_ = pixels;
}

void ObjectAssociation::SetDistance3DScale(double distance)
{
    if(distance > 0.0)
        distance_3d_scale_ = distance;
}

double ObjectAssociation::ComputeAssociationCost(const ObjectState &object,
                                                 const Detection &detection) const
{
    const double semantic_cost = object.GetClassId() == detection.class_id ? 0.0 : 1.0;
    const double iou_cost = 1.0 - IntersectionOverUnion(object.GetBoundingBox(), detection.bbox);
    const double spatial_cost = ClampUnit(
        CenterDistance(object.GetBoundingBox(), detection.bbox) / spatial_scale_);
    const double distance_3d_cost = ClampUnit(
        Distance3D(object.GetPosition(), detection.position_3d) / distance_3d_scale_);

    const double weight_sum = weights_.semantic + weights_.iou
                            + weights_.spatial + weights_.distance_3d;
    if(weight_sum <= 0.0)
        return std::numeric_limits<double>::infinity();

    return (weights_.semantic * semantic_cost
          + weights_.iou * iou_cost
          + weights_.spatial * spatial_cost
          + weights_.distance_3d * distance_3d_cost) / weight_sum;
}

AssociationResult ObjectAssociation::AssociateObjects(
    const std::vector<ObjectState> &previous_objects,
    const std::vector<Detection> &current_detections,
    double timestamp)
{
    AdvanceObjectIdPast(previous_objects);

    std::vector<Candidate> candidates;
    for(std::size_t object_index = 0; object_index < previous_objects.size(); ++object_index)
    {
        for(std::size_t detection_index = 0;
            detection_index < current_detections.size(); ++detection_index)
        {
            const double cost = ComputeAssociationCost(
                previous_objects[object_index], current_detections[detection_index]);
            if(cost <= maximum_cost_)
            {
                Candidate candidate;
                candidate.previous_index = object_index;
                candidate.detection_index = detection_index;
                candidate.cost = cost;
                candidates.push_back(candidate);
            }
        }
    }

    std::sort(candidates.begin(), candidates.end(), CandidateLess);

    std::vector<bool> object_used(previous_objects.size(), false);
    std::vector<bool> detection_used(current_detections.size(), false);
    AssociationResult result;

    for(std::size_t index = 0; index < candidates.size(); ++index)
    {
        const Candidate &candidate = candidates[index];
        if(object_used[candidate.previous_index]
           || detection_used[candidate.detection_index])
            continue;

        object_used[candidate.previous_index] = true;
        detection_used[candidate.detection_index] = true;

        ObjectState updated = previous_objects[candidate.previous_index];
        const Detection &detection = current_detections[candidate.detection_index];
        updated.UpdateState(detection.class_id, detection.class_name,
                            detection.bbox, detection.confidence,
                            detection.position_3d, timestamp);
        if(updated.GetLifecycleState() == ObjectLifecycleState::Lost)
            updated.SetLifecycleState(ObjectLifecycleState::Recovered);

        ObjectMatch match;
        match.previous_index = candidate.previous_index;
        match.detection_index = candidate.detection_index;
        match.object_id = updated.GetObjectId();
        match.cost = candidate.cost;
        result.matches.push_back(match);
        result.objects.push_back(updated);
    }

    for(std::size_t index = 0; index < previous_objects.size(); ++index)
    {
        if(object_used[index])
            continue;
        ObjectState lost = previous_objects[index];
        lost.SetLifecycleState(ObjectLifecycleState::Lost);
        result.unmatched_previous_indices.push_back(index);
        result.objects.push_back(lost);
    }

    for(std::size_t index = 0; index < current_detections.size(); ++index)
    {
        if(detection_used[index])
            continue;
        const Detection &detection = current_detections[index];
        result.unmatched_detection_indices.push_back(index);
        result.objects.push_back(ObjectState::Create(
            AllocateObjectId(), detection.class_id, detection.class_name,
            detection.bbox, detection.confidence, detection.position_3d, timestamp));
    }

    return result;
}

double ObjectAssociation::IntersectionOverUnion(const BoundingBox2D &first,
                                                const BoundingBox2D &second)
{
    const double intersection_left = std::max(first.left, second.left);
    const double intersection_top = std::max(first.top, second.top);
    const double intersection_right = std::min(first.right, second.right);
    const double intersection_bottom = std::min(first.bottom, second.bottom);

    const double intersection_width = std::max(0.0, intersection_right - intersection_left);
    const double intersection_height = std::max(0.0, intersection_bottom - intersection_top);
    const double intersection_area = intersection_width * intersection_height;

    const double first_area = std::max(0.0, first.right - first.left)
                            * std::max(0.0, first.bottom - first.top);
    const double second_area = std::max(0.0, second.right - second.left)
                             * std::max(0.0, second.bottom - second.top);
    const double union_area = first_area + second_area - intersection_area;
    if(union_area <= 0.0)
        return 0.0;
    return ClampUnit(intersection_area / union_area);
}

double ObjectAssociation::CenterDistance(const BoundingBox2D &first,
                                         const BoundingBox2D &second)
{
    const double first_x = 0.5 * (first.left + first.right);
    const double first_y = 0.5 * (first.top + first.bottom);
    const double second_x = 0.5 * (second.left + second.right);
    const double second_y = 0.5 * (second.top + second.bottom);
    const double dx = first_x - second_x;
    const double dy = first_y - second_y;
    return std::sqrt(dx * dx + dy * dy);
}

double ObjectAssociation::Distance3D(const Vector3D &first, const Vector3D &second)
{
    const double dx = first.x - second.x;
    const double dy = first.y - second.y;
    const double dz = first.z - second.z;
    return std::sqrt(dx * dx + dy * dy + dz * dz);
}

double ObjectAssociation::ClampUnit(double value)
{
    if(value < 0.0)
        return 0.0;
    if(value > 1.0)
        return 1.0;
    return value;
}

bool ObjectAssociation::CandidateLess(const Candidate &first, const Candidate &second)
{
    if(first.cost != second.cost)
        return first.cost < second.cost;
    if(first.previous_index != second.previous_index)
        return first.previous_index < second.previous_index;
    return first.detection_index < second.detection_index;
}

ObjectState::ObjectId ObjectAssociation::AllocateObjectId()
{
    return next_object_id_++;
}

void ObjectAssociation::AdvanceObjectIdPast(const std::vector<ObjectState> &objects)
{
    for(std::size_t index = 0; index < objects.size(); ++index)
    {
        if(objects[index].GetObjectId() >= next_object_id_)
            next_object_id_ = objects[index].GetObjectId() + 1;
    }
}

} // namespace Paper2
} // namespace ORB_SLAM2
