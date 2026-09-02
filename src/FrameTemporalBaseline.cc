#include "FrameTemporalBaseline.h"

#include "Frame.h"
#include "FrameTemporalConfig.h"
#include "Object.h"
#include "SemanticConfig.h"

#include <algorithm>
#include <limits>

namespace ORB_SLAM2
{
FrameTemporalBaseline::FrameTemporalBaseline()
    : mLastFrameId(0), mInitialized(false)
{
}

FrameTemporalBaseline &FrameTemporalBaseline::Instance()
{
    static FrameTemporalBaseline instance;
    return instance;
}

void FrameTemporalBaseline::Reset()
{
    mProbability.release();
    mLastFrameId = 0;
    mInitialized = false;
}

void FrameTemporalBaseline::UpdateForFrame(const Frame &frame)
{
    if(mInitialized && frame.mnId == mLastFrameId)
        return;

    const int width = std::max(1, static_cast<int>(frame.mnMaxX + 0.5f));
    const int height = std::max(1, static_cast<int>(frame.mnMaxY + 0.5f));
    if(!mInitialized || mProbability.cols != width || mProbability.rows != height ||
       frame.mnId < mLastFrameId)
    {
        mProbability = cv::Mat(height, width, CV_32F,
                               cv::Scalar(FrameTemporalConfig::kInitialProbability));
        mInitialized = true;
    }

    cv::Mat observation(height, width, CV_32F, cv::Scalar(0.0f));
    cv::Mat staticMask(height, width, CV_8U, cv::Scalar(0));
    for(const std::shared_ptr<Object> &object : frame.objects_cur_)
    {
        if(!object || object->vdetect_parameter.size() < 4)
            continue;
        const int left = std::max(0, static_cast<int>(object->vdetect_parameter[0] - 2));
        const int top = std::max(0, static_cast<int>(object->vdetect_parameter[1] - 2));
        const int right = std::min(width - 1, static_cast<int>(object->vdetect_parameter[2] + 2));
        const int bottom = std::min(height - 1, static_cast<int>(object->vdetect_parameter[3] + 2));
        if(right < left || bottom < top)
            continue;
        const cv::Rect region(left, top, right - left + 1, bottom - top + 1);
        if(SemanticConfig::IsStaticObjectClass(object->ndetect_class))
            staticMask(region).setTo(255);
        else if(SemanticConfig::IsDynamicObjectClass(object->ndetect_class))
            observation(region).setTo(1.0f);
    }
    observation.setTo(0.0f, staticMask);

    const float alpha = FrameTemporalConfig::kCurrentObservationAlpha;
    mProbability = alpha * observation + (1.0f - alpha) * mProbability;
    mLastFrameId = frame.mnId;
}

float FrameTemporalBaseline::ScoreAt(const Frame &frame, float u, float v)
{
    UpdateForFrame(frame);
    const int x = static_cast<int>(u + 0.5f);
    const int y = static_cast<int>(v + 0.5f);
    if(x < 0 || y < 0 || x >= mProbability.cols || y >= mProbability.rows)
        return 0.0f;
    return mProbability.at<float>(y, x);
}

bool FrameTemporalBaseline::IsDynamicAt(const Frame &frame, float u, float v)
{
    return ScoreAt(frame, u, v) >= FrameTemporalConfig::kDynamicThreshold;
}
} // namespace ORB_SLAM2
