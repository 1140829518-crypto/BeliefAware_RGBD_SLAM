#include "DynamicMapFilter.h"

#include <cassert>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <sstream>

using ORB_SLAM2::Paper2::BoundingBox2D;
using ORB_SLAM2::Paper2::DynamicMapFilter;
using ORB_SLAM2::Paper2::MapPointStatus;
using ORB_SLAM2::Paper2::ObjectLifecycleState;
using ORB_SLAM2::Paper2::ObjectState;
using ORB_SLAM2::Paper2::StableMapView;
using ORB_SLAM2::Paper2::Vector3D;
using ORB_SLAM2::Frame;
using ORB_SLAM2::Map;
using ORB_SLAM2::MapPoint;
using ORB_SLAM2::MapPointDynamicBelief;

namespace
{

ObjectState MakeObject(ObjectState::ObjectId object_id,
                       ObjectLifecycleState state,
                       ObjectState::MapPointId first_point,
                       ObjectState::MapPointId second_point)
{
    ObjectState object = ObjectState::Create(
        object_id, 3, "person", BoundingBox2D(10.0, 10.0, 40.0, 60.0),
        0.9, Vector3D(0.0, 0.0, 2.0), 1.0);
    object.SetLifecycleState(state);
    object.AddMapPoint(first_point);
    object.AddMapPoint(second_point);
    return object;
}

MapPoint *MakeMapPoint(Map *map, Frame *frame)
{
    frame->mnId = 1;
    frame->SetPose(cv::Mat::eye(4, 4, CV_32F));
    frame->mvKeysUn.assign(1, cv::KeyPoint(0.0f, 0.0f, 1.0f));
    frame->mvScaleFactors.assign(1, 1.0f);
    frame->mnScaleLevels = 1;
    frame->mDescriptors = cv::Mat::zeros(1, 32, CV_8U);
    return new MapPoint((cv::Mat_<float>(3,1) << 0.0f, 0.0f, 2.0f),
                        map, frame, 0);
}

bool Near(float lhs, float rhs)
{
    return std::fabs(lhs - rhs) < 1e-5f;
}

} // namespace

int main()
{
    setenv("ORB_SLAM2_MEMORY_CARRIER", "mappoint", 1);
    setenv("ORB_SLAM2_BELIEF_LOG", "/tmp/orbslam2_belief_v2_test.csv", 1);
    setenv("ORB_SLAM2_LEGACY_TEMPORAL_WEIGHT_ENABLED", "0", 1);
    setenv("ORB_SLAM2_LEGACY_TEMPORAL_HARD_REJECTION_ENABLED", "0", 1);
    setenv("ORB_SLAM2_UNCERTAINTY_MODE", "clean", 1);

    Map map;
    Frame frame;
    MapPoint *static_point = MakeMapPoint(&map, &frame);
    MapPoint *dynamic_point = MakeMapPoint(&map, &frame);
    MapPoint *dynamic_point_2 = MakeMapPoint(&map, &frame);
    MapPoint *static_point_2 = MakeMapPoint(&map, &frame);

    DynamicMapFilter filter(30);

    ObjectState static_object = MakeObject(
        10, ObjectLifecycleState::Static, static_point->mnId, static_point_2->mnId);
    ObjectState dynamic_object = MakeObject(
        20, ObjectLifecycleState::Dynamic, dynamic_point->mnId, dynamic_point_2->mnId);

    StableMapView first_view;
    first_view.frame_id = 1;
    first_view.timestamp = 1.0;
    first_view.snapshot_accepted = true;
    first_view.active_objects.push_back(static_object);
    first_view.active_objects.push_back(dynamic_object);
    first_view.dynamic_objects.push_back(dynamic_object);
    StableMapView::CarrierObservation static_observation;
    static_observation.object_id = 10;
    static_observation.class_id = 1;
    static_observation.map_point_ids = {static_point->mnId, static_point_2->mnId};
    first_view.carrier_observations.push_back(static_observation);
    StableMapView::CarrierObservation dynamic_observation;
    dynamic_observation.object_id = 20;
    dynamic_observation.class_id = 3;
    dynamic_observation.map_point_ids = {dynamic_point->mnId, dynamic_point_2->mnId};
    first_view.carrier_observations.push_back(dynamic_observation);

    assert(filter.UpdateMapView(first_view));
    assert(filter.GetTrackedPointCount() == 4);
    assert(filter.GetPointStatus(static_point->mnId) == MapPointStatus::Static);
    assert(filter.GetPointStatus(dynamic_point->mnId) == MapPointStatus::Dynamic);
    MapPointDynamicBelief first = dynamic_point->GetDynamicBelief();
    assert(Near(first.dynamic_probability, 0.65f));
    assert(Near(first.uncertainty, 0.4f));
    assert(Near(first.conflict, 0.25f));

    ObjectState::ObjectId associated_object = 0;
    assert(filter.GetAssociatedObjectId(dynamic_point->mnId, &associated_object));
    assert(associated_object == 20);

    StableMapView consecutive = first_view;
    consecutive.frame_id = 2;
    consecutive.timestamp = 2.0;
    assert(filter.UpdateMapView(consecutive));
    MapPointDynamicBelief second = dynamic_point->GetDynamicBelief();
    assert(Near(second.dynamic_probability, 0.755f));
    assert(Near(second.uncertainty, 0.32f));

    StableMapView gapped = first_view;
    gapped.frame_id = 5;
    gapped.timestamp = 5.0;
    assert(filter.UpdateMapView(gapped));
    const float expected_gap_p = second.dynamic_probability * std::exp(-0.05f * 2.0f);
    const float expected_gap_u = 1.0f - (1.0f - second.uncertainty) * std::exp(-0.03f * 2.0f);
    MapPointDynamicBelief after_gap_observation = dynamic_point->GetDynamicBelief();
    assert(Near(after_gap_observation.dynamic_probability, 0.7f * expected_gap_p + 0.3f));
    assert(Near(after_gap_observation.uncertainty, expected_gap_u * 0.8f));

    MapPoint *replacement = MakeMapPoint(&map, &frame);
    MapPointDynamicBelief replacement_belief;
    replacement_belief.dynamic_probability = 0.2f;
    replacement_belief.uncertainty = 0.1f;
    replacement_belief.observation_count = 1;
    replacement_belief.has_previous_observation = true;
    replacement_belief.previous_observation = 0;
    replacement_belief.conflict_persistence = 0.6f;
    replacement_belief.last_observation_frame = 1;
    replacement->SetDynamicBelief(replacement_belief);
    const MapPointDynamicBelief source_belief = dynamic_point->GetDynamicBelief();
    dynamic_point->Replace(replacement);
    const MapPointDynamicBelief merged = replacement->GetDynamicBelief();
    assert(merged.observation_count == source_belief.observation_count + 1);
    assert(Near(merged.dynamic_probability,
                (source_belief.dynamic_probability * source_belief.observation_count + 0.2f)
                / merged.observation_count));
    assert(merged.has_previous_observation);
    assert(merged.previous_observation == source_belief.previous_observation);
    assert(Near(merged.conflict_persistence,
                (source_belief.conflict_persistence * source_belief.observation_count + 0.6f)
                / merged.observation_count));
    assert(MapPoint::GetById(dynamic_point->mnId) == NULL);
    assert(MapPoint::GetById(replacement->mnId) == replacement);

    ObjectState replacement_object = MakeObject(
        30, ObjectLifecycleState::Dynamic, replacement->mnId, dynamic_point_2->mnId);
    StableMapView after_replacement;
    after_replacement.frame_id = 6;
    after_replacement.timestamp = 6.0;
    after_replacement.snapshot_accepted = true;
    after_replacement.active_objects.push_back(replacement_object);
    after_replacement.dynamic_objects.push_back(replacement_object);
    StableMapView::CarrierObservation replacement_observation;
    replacement_observation.object_id = 30;
    replacement_observation.class_id = 3;
    replacement_observation.map_point_ids = {replacement->mnId, dynamic_point_2->mnId};
    after_replacement.carrier_observations.push_back(replacement_observation);
    assert(filter.UpdateMapView(after_replacement));
    const MapPointDynamicBelief after_replacement_update = replacement->GetDynamicBelief();
    assert(Near(after_replacement_update.conflict_persistence,
                0.8f * merged.conflict_persistence));

    assert(!ORB_SLAM2::SemanticConfig::UseLegacyTemporalWeight());
    assert(!ORB_SLAM2::SemanticConfig::UseLegacyTemporalHardRejection());
    assert(ORB_SLAM2::SemanticConfig::UncertaintyMode()
           == ORB_SLAM2::SemanticConfig::BELIEF_UNCERTAINTY_CLEAN);
    assert(filter.GetPointStatus(999) == MapPointStatus::Static);

    StableMapView rejected_view;
    rejected_view.frame_id = 4;
    rejected_view.timestamp = 4.0;
    rejected_view.snapshot_accepted = false;
    assert(!filter.UpdateMapView(rejected_view));
    assert(filter.GetTrackedPointCount() == 5);

    std::ifstream log("/tmp/orbslam2_belief_v2_test.csv");
    std::string header;
    std::getline(log, header);
    assert(header.find("previous_p,previous_u,missing_gap,after_gap_p,after_gap_u,observation,conflict")
           != std::string::npos);
    assert(header.find("previous_observation,switch_event,persistence_before,persistence_after,raw_conflict,persistent_conflict")
           != std::string::npos);
    std::string row;
    bool saw_consecutive = false;
    bool saw_gap = false;
    bool saw_replacement_persistence = false;
    while(std::getline(log, row))
    {
        std::stringstream stream(row);
        std::string cell;
        std::vector<std::string> cells;
        while(std::getline(stream, cell, ',')) cells.push_back(cell);
        if(cells.size() >= 11 && cells[0] == "2" && cells[1] == std::to_string(dynamic_point->mnId))
        {
            assert(cells[5] == "0");
            assert(Near(std::stof(cells[3]), std::stof(cells[6])));
            assert(Near(std::stof(cells[4]), std::stof(cells[7])));
            saw_consecutive = true;
        }
        if(cells.size() >= 11 && cells[0] == "5" && cells[1] == std::to_string(dynamic_point->mnId))
        {
            assert(cells[5] == "2");
            assert(!Near(std::stof(cells[3]), std::stof(cells[6])));
            assert(!Near(std::stof(cells[4]), std::stof(cells[7])));
            saw_gap = true;
        }
        if(cells.size() >= 23 && cells[0] == "6"
           && cells[1] == std::to_string(replacement->mnId))
        {
            assert(Near(std::stof(cells[19]), merged.conflict_persistence));
            assert(Near(std::stof(cells[20]), after_replacement_update.conflict_persistence));
            saw_replacement_persistence = true;
        }
    }
    assert(saw_consecutive && saw_gap && saw_replacement_persistence);

    filter.Clear();
    assert(filter.GetTrackedPointCount() == 0);
    delete static_point;
    delete static_point_2;
    delete dynamic_point;
    delete dynamic_point_2;
    delete replacement;
    return 0;
}
