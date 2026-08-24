#ifndef ORB_SLAM2_EXPERIMENT_TIMING_H
#define ORB_SLAM2_EXPERIMENT_TIMING_H

#include <chrono>
#include <string>

namespace ORB_SLAM2
{

enum class TimingComponent
{
    TrackingTotal = 0,
    SemanticDetection,
    TemporalEvidenceUpdate,
    ObjectDynamicAdapter,
    DynamicMapFilter,
    EndToEndFrame,
    Count
};

class ExperimentTiming
{
public:
    static void Reset(std::size_t frameCount, std::size_t warmupFrames);
    static void SetCurrentFrame(std::size_t frameIndex);
    static void Add(TimingComponent component, double seconds);
    static bool WriteReports(const std::string &outputDirectory);
};

class ScopedExperimentTimer
{
public:
    explicit ScopedExperimentTimer(TimingComponent component)
        : mComponent(component), mStart(std::chrono::steady_clock::now()) {}

    ~ScopedExperimentTimer()
    {
        const std::chrono::steady_clock::time_point end =
            std::chrono::steady_clock::now();
        ExperimentTiming::Add(
            mComponent,
            std::chrono::duration_cast<std::chrono::duration<double> >(
                end - mStart).count());
    }

private:
    TimingComponent mComponent;
    std::chrono::steady_clock::time_point mStart;
};

} // namespace ORB_SLAM2

#endif
