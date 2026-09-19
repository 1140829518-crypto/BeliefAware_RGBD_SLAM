#include "DynamicMapFilter.h"

#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

using ORB_SLAM2::Frame;
using ORB_SLAM2::Map;
using ORB_SLAM2::MapPoint;
using ORB_SLAM2::Paper2::BoundingBox2D;
using ORB_SLAM2::Paper2::DynamicMapFilter;
using ORB_SLAM2::Paper2::ObjectLifecycleState;
using ORB_SLAM2::Paper2::ObjectState;
using ORB_SLAM2::Paper2::StableMapView;
using ORB_SLAM2::Paper2::Vector3D;

namespace
{

struct Observation
{
    std::uint64_t frame_id;
    int z;
};

std::vector<std::string> Split(const std::string &line)
{
    std::vector<std::string> cells;
    std::stringstream stream(line);
    std::string cell;
    while(std::getline(stream, cell, ','))
        cells.push_back(cell);
    return cells;
}

MapPoint *MakeMapPoint(Map *map, Frame *frame)
{
    frame->mnId = 0;
    frame->SetPose(cv::Mat::eye(4, 4, CV_32F));
    frame->mvKeysUn.assign(1, cv::KeyPoint(0.0f, 0.0f, 1.0f));
    frame->mvScaleFactors.assign(1, 1.0f);
    frame->mnScaleLevels = 1;
    frame->mDescriptors = cv::Mat::zeros(1, 32, CV_8U);
    return new MapPoint((cv::Mat_<float>(3,1) << 0.0f, 0.0f, 2.0f),
                        map, frame, 0);
}

ObjectState MakeObject(MapPoint *point, int z)
{
    ObjectState object = ObjectState::Create(
        1, z ? 3 : 1, z ? "person" : "static", BoundingBox2D(0.0, 0.0, 10.0, 10.0),
        1.0, Vector3D(0.0, 0.0, 2.0), 1.0);
    object.SetLifecycleState(z ? ObjectLifecycleState::Dynamic
                               : ObjectLifecycleState::Static);
    object.AddMapPoint(point->mnId);
    return object;
}

void RunSequence(const std::string &output_directory,
                 const std::string &mode,
                 const std::string &name,
                 const std::vector<Observation> &observations)
{
    const std::string raw_path = output_directory + "/" + name + "_production.csv";
    const std::string output_path = output_directory + "/" + name + ".csv";
    setenv("ORB_SLAM2_BELIEF_LOG", raw_path.c_str(), 1);

    Map map;
    Frame frame;
    MapPoint *point = MakeMapPoint(&map, &frame);
    {
        DynamicMapFilter filter(1000);
        for(std::size_t step = 0; step < observations.size(); ++step)
        {
            const Observation &observation = observations[step];
            const ObjectState object = MakeObject(point, observation.z);
            StableMapView view;
            view.frame_id = observation.frame_id;
            view.timestamp = static_cast<double>(observation.frame_id);
            view.snapshot_accepted = true;
            view.active_objects.push_back(object);
            if(observation.z)
                view.dynamic_objects.push_back(object);
            StableMapView::CarrierObservation carrier;
            carrier.object_id = 1;
            carrier.class_id = observation.z ? 3 : 1;
            carrier.map_point_ids.push_back(point->mnId);
            view.carrier_observations.push_back(carrier);
            if(!filter.UpdateMapView(view))
                throw std::runtime_error("production UpdateMapView rejected sequence " + name);
        }
    }
    delete point;

    std::ifstream raw(raw_path.c_str());
    std::ofstream output(output_path.c_str());
    if(!raw || !output)
        throw std::runtime_error("cannot open synthetic output for " + name);
    std::string line;
    std::getline(raw, line);
    output << "mode,sequence,step,frame_id,z,previous_p,previous_u,missing_gap,"
              "after_gap_p,after_gap_u,after_observation_p,after_observation_u,"
              "reliability,raw_conflict,persistent_conflict,"
              "previous_observation,switch_event,persistence_before,persistence_after,"
              "uncertainty_consistency_term,"
              "high_confidence_dynamic\n";
    std::size_t step = 0;
    output << std::setprecision(9);
    while(std::getline(raw, line))
    {
        const std::vector<std::string> cells = Split(line);
        if(cells.size() < 23)
            throw std::runtime_error("incomplete production belief row for " + name);
        output << mode << ',' << name << ',' << ++step << ',' << cells[0] << ',' << cells[8] << ','
               << cells[3] << ',' << cells[4] << ',' << cells[5] << ','
               << cells[6] << ',' << cells[7] << ',' << cells[11] << ','
               << cells[12] << ',' << cells[13] << ',' << cells[21] << ','
               << cells[22] << ',' << cells[17] << ',' << cells[18] << ','
               << cells[19] << ',' << cells[20] << ',' << cells[10] << ','
               << (cells[15] == "Dynamic" ? 1 : 0) << '\n';
    }
    if(step != observations.size())
        throw std::runtime_error("unexpected production row count for " + name);
}

std::vector<Observation> Consecutive(const std::string &bits)
{
    std::vector<Observation> result;
    for(std::size_t i = 0; i < bits.size(); ++i)
        result.push_back(Observation{static_cast<std::uint64_t>(i + 1),
                                     bits[i] == '1' ? 1 : 0});
    return result;
}

} // namespace

int main(int argc, char **argv)
{
    if(argc != 3 || (std::string(argv[2]) != "clean"
                     && std::string(argv[2]) != "raw"
                     && std::string(argv[2]) != "persistent"))
    {
        std::cerr << "usage: synthetic_belief_conflict OUTPUT_DIRECTORY clean|raw|persistent\n";
        return 2;
    }
    setenv("ORB_SLAM2_MEMORY_CARRIER", "mappoint", 1);
    setenv("ORB_SLAM2_BELIEF_ENABLED", "1", 1);
    setenv("ORB_SLAM2_BELIEF_GAP_ENABLED", "1", 1);
    setenv("ORB_SLAM2_UNCERTAINTY_ENABLED", "1", 1);
    setenv("ORB_SLAM2_RELIABILITY_ENABLED", "1", 1);
    setenv("ORB_SLAM2_LEGACY_TEMPORAL_WEIGHT_ENABLED", "0", 1);
    setenv("ORB_SLAM2_LEGACY_TEMPORAL_HARD_REJECTION_ENABLED", "0", 1);
    const std::string mode(argv[2]);
    setenv("ORB_SLAM2_UNCERTAINTY_MODE", mode.c_str(), 1);

    try
    {
        RunSequence(argv[1], mode, "A_stable_static", Consecutive("00000000000000000000"));
        RunSequence(argv[1], mode, "B_stable_dynamic", Consecutive("11111111111111111111"));
        RunSequence(argv[1], mode, "C_alternating_conflict", Consecutive("01010101010101010101"));
        RunSequence(argv[1], mode, "D_static_dynamic_static",
                    Consecutive("000000000011111111110000000000"));
        RunSequence(argv[1], mode, "E_dynamic_static_dynamic",
                    Consecutive("111111111100000000001111111111"));
        std::vector<Observation> sparse = Consecutive("0000000000");
        sparse.push_back(Observation{14, 1});
        sparse.push_back(Observation{20, 1});
        sparse.push_back(Observation{27, 1});
        RunSequence(argv[1], mode, "F_sparse_contradictory", sparse);
        RunSequence(argv[1], mode, "G_isolated_flip",
                    Consecutive("000000000010000000000"));
        RunSequence(argv[1], mode, "H_short_transition",
                    Consecutive("00000000001110000000000"));
        RunSequence(argv[1], mode, "I_bursty_contradiction",
                    Consecutive(std::string(8, '0') + "01010" + std::string(8, '0')));
        RunSequence(argv[1], mode, "J_long_genuine_transition",
                    Consecutive("0000000000111111111111111"));
    }
    catch(const std::exception &error)
    {
        std::cerr << error.what() << '\n';
        return 1;
    }
    return 0;
}
