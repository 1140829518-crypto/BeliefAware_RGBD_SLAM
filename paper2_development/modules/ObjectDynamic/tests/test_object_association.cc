#include "ObjectAssociation.h"

#include <cassert>
#include <cmath>
#include <vector>

using ORB_SLAM2::Paper2::AssociationResult;
using ORB_SLAM2::Paper2::BoundingBox2D;
using ORB_SLAM2::Paper2::Detection;
using ORB_SLAM2::Paper2::ObjectAssociation;
using ORB_SLAM2::Paper2::ObjectState;
using ORB_SLAM2::Paper2::Vector3D;

int main()
{
    std::vector<ObjectState> previous;
    previous.push_back(ObjectState::Create(
        7, 3, "person", BoundingBox2D(10.0, 10.0, 50.0, 90.0),
        0.90, Vector3D(1.0, 0.0, 2.0), 1.0));

    std::vector<Detection> detections;
    detections.push_back(Detection(
        3, "person", BoundingBox2D(12.0, 10.0, 52.0, 90.0),
        0.95, Vector3D(1.1, 0.0, 2.0)));

    ObjectAssociation association(100);

    // An invalid zero placeholder skips the 3D term, while a valid origin is
    // a real position and contributes its actual distance. They are distinct.
    const Detection invalid_zero(
        3, "person", BoundingBox2D(10.0, 10.0, 50.0, 90.0),
        0.95, Vector3D(), false);
    const Detection valid_zero(
        3, "person", BoundingBox2D(10.0, 10.0, 50.0, 90.0),
        0.95, Vector3D(), true);
    const double invalid_zero_cost = association.ComputeAssociationCost(
        previous[0], invalid_zero);
    const double valid_zero_cost = association.ComputeAssociationCost(
        previous[0], valid_zero);
    assert(std::fabs(invalid_zero_cost) < 1e-12);
    assert(valid_zero_cost > invalid_zero_cost);

    AssociationResult first_result = association.AssociateObjects(previous, detections, 1.1);

    assert(first_result.matches.size() == 1);
    assert(first_result.matches[0].object_id == 7);
    assert(first_result.objects.size() == 1);
    assert(first_result.objects[0].GetObjectId() == 7);
    assert(first_result.objects[0].GetObservationCount() == 2);

    std::vector<Detection> second_detections;
    second_detections.push_back(Detection(
        3, "person", BoundingBox2D(14.0, 10.0, 54.0, 90.0),
        0.96, Vector3D(1.2, 0.0, 2.0)));
    AssociationResult second_result = association.AssociateObjects(
        first_result.objects, second_detections, 1.2);

    assert(second_result.matches.size() == 1);
    assert(second_result.matches[0].object_id == 7);
    assert(second_result.objects[0].GetObjectId() == 7);

    std::vector<Detection> new_detection;
    new_detection.push_back(Detection(
        1, "chair", BoundingBox2D(300.0, 200.0, 350.0, 300.0),
        0.88, Vector3D(5.0, 0.0, 4.0)));
    AssociationResult new_result = association.AssociateObjects(
        second_result.objects, new_detection, 1.3);

    assert(new_result.matches.empty());
    assert(new_result.unmatched_detection_indices.size() == 1);
    assert(new_result.objects.size() == 2);
    assert(new_result.objects[0].GetObjectId() == 7);
    assert(new_result.objects[1].GetObjectId() >= 100);
    return 0;
}
