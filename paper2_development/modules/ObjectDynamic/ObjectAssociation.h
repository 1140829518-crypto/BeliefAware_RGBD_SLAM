/*
Paper2 Object-level Dynamic SLAM Module

Purpose:
Cross-frame object association using semantic, image, and 3D costs.

Author:
Dong Jianing

Branch:
paper2_development
*/

#ifndef PAPER2_OBJECT_DYNAMIC_OBJECT_ASSOCIATION_H
#define PAPER2_OBJECT_DYNAMIC_OBJECT_ASSOCIATION_H

#include "ObjectState.h"

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace ORB_SLAM2
{
namespace Paper2
{

struct Detection
{
    int class_id;
    std::string class_name;
    BoundingBox2D bbox;
    double confidence;
    Vector3D position_3d;

    Detection();
    Detection(int class_id_value,
              const std::string &class_name_value,
              const BoundingBox2D &bbox_value,
              double confidence_value,
              const Vector3D &position_3d_value);
};

struct AssociationWeights
{
    double semantic;
    double iou;
    double spatial;
    double distance_3d;

    AssociationWeights();
};

struct ObjectMatch
{
    std::size_t previous_index;
    std::size_t detection_index;
    ObjectState::ObjectId object_id;
    double cost;
};

struct AssociationResult
{
    std::vector<ObjectMatch> matches;
    std::vector<ObjectState> objects;
    std::vector<std::size_t> unmatched_previous_indices;
    std::vector<std::size_t> unmatched_detection_indices;
};

class ObjectAssociation
{
public:
    explicit ObjectAssociation(ObjectState::ObjectId first_object_id = 1);

    void SetWeights(const AssociationWeights &weights);
    void SetMaximumCost(double maximum_cost);
    void SetSpatialScale(double pixels);
    void SetDistance3DScale(double distance);

    double ComputeAssociationCost(const ObjectState &object,
                                  const Detection &detection) const;

    AssociationResult AssociateObjects(const std::vector<ObjectState> &previous_objects,
                                       const std::vector<Detection> &current_detections,
                                       double timestamp);

private:
    struct Candidate
    {
        std::size_t previous_index;
        std::size_t detection_index;
        double cost;
    };

    static double IntersectionOverUnion(const BoundingBox2D &first,
                                        const BoundingBox2D &second);
    static double CenterDistance(const BoundingBox2D &first,
                                 const BoundingBox2D &second);
    static double Distance3D(const Vector3D &first, const Vector3D &second);
    static double ClampUnit(double value);
    static bool CandidateLess(const Candidate &first, const Candidate &second);

    ObjectState::ObjectId AllocateObjectId();
    void AdvanceObjectIdPast(const std::vector<ObjectState> &objects);

    ObjectState::ObjectId next_object_id_;
    AssociationWeights weights_;
    double maximum_cost_;
    double spatial_scale_;
    double distance_3d_scale_;
};

} // namespace Paper2
} // namespace ORB_SLAM2

#endif // PAPER2_OBJECT_DYNAMIC_OBJECT_ASSOCIATION_H
