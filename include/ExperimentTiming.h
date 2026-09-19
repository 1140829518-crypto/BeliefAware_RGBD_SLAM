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
    BeliefUpdate,
    GeometryProtection,
    PoseOptimization,
    EndToEndFrame,
    Count
};

class ExperimentTiming
{
public:
    static void Reset(std::size_t frameCount, std::size_t warmupFrames);
    static void SetCurrentFrame(std::size_t frameIndex);
    static void Add(TimingComponent component, double seconds);
    static void AddAggregate(TimingComponent component, double seconds,
                             std::size_t calls, std::size_t events = 0);
    static bool WriteReports(const std::string &outputDirectory);
};

class ScopedExperimentTimer
{
public:
    explicit ScopedExperimentTimer(TimingComponent component,
                                   bool countCall = false)
        : mComponent(component), mCountCall(countCall),
          mStart(std::chrono::steady_clock::now()) {}

    ~ScopedExperimentTimer()
    {
        const std::chrono::steady_clock::time_point end =
            std::chrono::steady_clock::now();
        ExperimentTiming::AddAggregate(
            mComponent,
            std::chrono::duration_cast<std::chrono::duration<double> >(
                end - mStart).count(), mCountCall ? 1 : 0);
    }

private:
    TimingComponent mComponent;
    bool mCountCall;
    std::chrono::steady_clock::time_point mStart;
};

class ExperimentTimingAggregate
{
public:
    explicit ExperimentTimingAggregate(TimingComponent component)
        : mComponent(component), mSeconds(0.0), mCalls(0), mEvents(0) {}
    ~ExperimentTimingAggregate()
    {
        ExperimentTiming::AddAggregate(mComponent, mSeconds, mCalls, mEvents);
    }
    void Add(double seconds, std::size_t calls = 1, std::size_t events = 0)
    {
        mSeconds += seconds;
        mCalls += calls;
        mEvents += events;
    }
private:
    TimingComponent mComponent;
    double mSeconds;
    std::size_t mCalls;
    std::size_t mEvents;
};

} // namespace ORB_SLAM2

#endif
