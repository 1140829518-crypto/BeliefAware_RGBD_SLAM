#ifndef FRAME_TEMPORAL_BASELINE_H
#define FRAME_TEMPORAL_BASELINE_H

#include <opencv2/core/core.hpp>

namespace ORB_SLAM2
{
class Frame;

class FrameTemporalBaseline
{
public:
    static FrameTemporalBaseline &Instance();
    float ScoreAt(const Frame &frame, float u, float v);
    bool IsDynamicAt(const Frame &frame, float u, float v);
    void Reset();

private:
    FrameTemporalBaseline();
    void UpdateForFrame(const Frame &frame);
    cv::Mat mProbability;
    unsigned long mLastFrameId;
    bool mInitialized;
};
} // namespace ORB_SLAM2

#endif
