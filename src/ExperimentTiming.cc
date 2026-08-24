#include "ExperimentTiming.h"

#include <array>
#include <fstream>
#include <iomanip>
#include <limits>
#include <mutex>
#include <vector>

namespace ORB_SLAM2
{
namespace
{
typedef std::array<double, static_cast<std::size_t>(TimingComponent::Count)> TimingRow;

std::mutex gTimingMutex;
std::vector<TimingRow> gFrameTimings;
std::size_t gCurrentFrame = 0;
std::size_t gWarmupFrames = 30;

const char *ComponentName(TimingComponent component)
{
    switch(component)
    {
    case TimingComponent::TrackingTotal: return "tracking_total";
    case TimingComponent::SemanticDetection: return "semantic_detection";
    case TimingComponent::TemporalEvidenceUpdate: return "temporal_evidence_update";
    case TimingComponent::ObjectDynamicAdapter: return "objectdynamic_adapter";
    case TimingComponent::DynamicMapFilter: return "dynamic_map_filter";
    case TimingComponent::EndToEndFrame: return "end_to_end_frame";
    default: return "unknown";
    }
}
}

void ExperimentTiming::Reset(std::size_t frameCount, std::size_t warmupFrames)
{
    std::lock_guard<std::mutex> lock(gTimingMutex);
    TimingRow empty;
    empty.fill(0.0);
    gFrameTimings.assign(frameCount, empty);
    gCurrentFrame = 0;
    gWarmupFrames = warmupFrames;
}

void ExperimentTiming::SetCurrentFrame(std::size_t frameIndex)
{
    std::lock_guard<std::mutex> lock(gTimingMutex);
    gCurrentFrame = frameIndex;
}

void ExperimentTiming::Add(TimingComponent component, double seconds)
{
    std::lock_guard<std::mutex> lock(gTimingMutex);
    if(gCurrentFrame >= gFrameTimings.size())
        return;
    gFrameTimings[gCurrentFrame][static_cast<std::size_t>(component)] += seconds;
}

bool ExperimentTiming::WriteReports(const std::string &outputDirectory)
{
    std::lock_guard<std::mutex> lock(gTimingMutex);
    std::ofstream perFrame((outputDirectory + "/runtime_breakdown.csv").c_str());
    if(!perFrame.is_open())
        return false;

    perFrame << "frame_index,in_steady_state";
    for(std::size_t component = 0;
        component < static_cast<std::size_t>(TimingComponent::Count); ++component)
        perFrame << ',' << ComponentName(static_cast<TimingComponent>(component)) << "_seconds";
    perFrame << '\n' << std::setprecision(12);
    for(std::size_t frame = 0; frame < gFrameTimings.size(); ++frame)
    {
        perFrame << frame << ',' << (frame >= gWarmupFrames ? 1 : 0);
        for(std::size_t component = 0;
            component < static_cast<std::size_t>(TimingComponent::Count); ++component)
            perFrame << ',' << gFrameTimings[frame][component];
        perFrame << '\n';
    }

    std::ofstream summary((outputDirectory + "/runtime_summary.csv").c_str());
    if(!summary.is_open())
        return false;
    summary << "component,count_all,total_seconds_all,mean_seconds_all,"
               "count_steady,total_seconds_steady,mean_seconds_steady,fps_steady\n";
    summary << std::setprecision(12);
    for(std::size_t component = 0;
        component < static_cast<std::size_t>(TimingComponent::Count); ++component)
    {
        double totalAll = 0.0;
        double totalSteady = 0.0;
        for(std::size_t frame = 0; frame < gFrameTimings.size(); ++frame)
        {
            totalAll += gFrameTimings[frame][component];
            if(frame >= gWarmupFrames)
                totalSteady += gFrameTimings[frame][component];
        }
        const std::size_t countAll = gFrameTimings.size();
        const std::size_t countSteady = countAll > gWarmupFrames
                                      ? countAll - gWarmupFrames : 0;
        const double meanAll = countAll ? totalAll / countAll : 0.0;
        const double meanSteady = countSteady ? totalSteady / countSteady : 0.0;
        const double fpsSteady = meanSteady > 0.0
                               ? 1.0 / meanSteady
                               : std::numeric_limits<double>::quiet_NaN();
        summary << ComponentName(static_cast<TimingComponent>(component)) << ','
                << countAll << ',' << totalAll << ',' << meanAll << ','
                << countSteady << ',' << totalSteady << ',' << meanSteady << ','
                << fpsSteady << '\n';
    }
    return true;
}

} // namespace ORB_SLAM2
