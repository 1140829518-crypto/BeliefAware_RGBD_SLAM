#include "Optimizer.h"
#include "Frame.h"
#include "Map.h"
#include "MapPoint.h"
#include "SemanticConfig.h"

#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>

using namespace ORB_SLAM2;

struct Result
{
    int inliers;
    cv::Mat pose;
    std::vector<bool> outliers;
    std::vector<MapPointDynamicBelief> beliefs;
};

static Result Run(const char *logPath)
{
    if(logPath)
        setenv("ORB_SLAM2_OPTIMIZER_MEASUREMENT_LOG", logPath, 1);
    else
        unsetenv("ORB_SLAM2_OPTIMIZER_MEASUREMENT_LOG");

    Frame frame;
    frame.mnId = 17;
    frame.N = 8;
    frame.fx = 500.0f; frame.fy = 500.0f;
    frame.cx = 320.0f; frame.cy = 240.0f; frame.mbf = 40.0f;
    frame.mnScaleLevels = 1;
    frame.mvScaleFactors.assign(1, 1.0f);
    frame.mvInvLevelSigma2.assign(1, 1.0f);
    frame.mvKeysUn.resize(frame.N);
    frame.mvuRight.assign(frame.N, -1.0f);
    frame.mvpMapPoints.assign(frame.N, static_cast<MapPoint*>(NULL));
    frame.mvMeasurementReliability.resize(frame.N);
    frame.mvbOutlier.assign(frame.N, false);
    frame.mDescriptors = cv::Mat::zeros(frame.N, 32, CV_8U);
    cv::Mat initial = cv::Mat::eye(4, 4, CV_32F);
    initial.at<float>(0,3) = 0.015f;
    frame.SetPose(initial);

    Map map;
    std::vector<MapPoint*> points;
    for(int i=0; i<frame.N; ++i)
    {
        const float x = (i%4-1.5f)*0.35f;
        const float y = (i/4-0.5f)*0.30f;
        const float z = 4.0f + 0.15f*i;
        frame.mvKeysUn[i] = cv::KeyPoint(frame.cx+frame.fx*x/z,
                                         frame.cy+frame.fy*y/z, 1.0f);
        frame.mvKeysUn[i].octave = 0;
        frame.mvMeasurementReliability[i] = 0.35f + 0.07f*i;
        cv::Mat pos = (cv::Mat_<float>(3,1) << x,y,z);
        MapPoint *mp = new MapPoint(pos, &map, &frame, i);
        MapPointDynamicBelief b = mp->GetDynamicBelief();
        b.dynamic_probability = 0.1f + 0.05f*i;
        b.uncertainty = 0.2f + 0.03f*i;
        b.conflict = 0.04f*i;
        b.conflict_persistence = 0.02f*i;
        mp->SetDynamicBelief(b);
        frame.mvpMapPoints[i] = mp;
        points.push_back(mp);
    }

    Result result;
    result.inliers = Optimizer::PoseOptimization(&frame);
    result.pose = frame.mTcw.clone();
    result.outliers = frame.mvbOutlier;
    for(size_t i=0; i<points.size(); ++i)
    {
        result.beliefs.push_back(points[i]->GetDynamicBelief());
        delete points[i];
    }
    return result;
}

int main()
{
    setenv("ORB_SLAM2_MEASUREMENT_POLICY", "BELIEF_ONLY", 1);
    const std::string path = "/tmp/orb_slam2_optimizer_measurement_regression.csv";
    std::remove(path.c_str());
    const Result off = Run(NULL);
    const Result on = Run(path.c_str());
    assert(off.inliers == on.inliers);
    assert(off.outliers == on.outliers);
    assert(cv::norm(off.pose-on.pose) < 1e-9);
    assert(off.beliefs.size() == on.beliefs.size());
    for(size_t i=0; i<off.beliefs.size(); ++i)
    {
        assert(off.beliefs[i].dynamic_probability == on.beliefs[i].dynamic_probability);
        assert(off.beliefs[i].uncertainty == on.beliefs[i].uncertainty);
        assert(off.beliefs[i].conflict_persistence == on.beliefs[i].conflict_persistence);
    }
    std::ifstream in(path.c_str());
    std::string header, row;
    assert(std::getline(in, header));
    int rows = 0;
    while(std::getline(in,row))
    {
        if(!row.empty()) ++rows;
    }
    assert(rows == 8);

    setenv("ORB_SLAM2_MEASUREMENT_POLICY", "GEOMETRY_PROTECTED", 1);
    // A: consistent geometry and low uncertainty changes little.
    assert(std::fabs(SemanticConfig::EffectiveBeliefReliability(
        0.76f, 0.2f, 1.0f, 5.991f) - 0.8f) < 1e-6f);
    // B: consistent geometry protects a low-p/high-u measurement up to 1-p.
    assert(std::fabs(SemanticConfig::EffectiveBeliefReliability(
        0.18f, 0.1f, 1.0f, 5.991f) - 0.9f) < 1e-6f);
    // C: inconsistent initial geometry receives no protection.
    assert(std::fabs(SemanticConfig::EffectiveBeliefReliability(
        0.18f, 0.1f, 12.0f, 5.991f) - 0.18f) < 1e-6f);
    // D: high dynamic probability remains suppressed at approximately 1-p.
    assert(std::fabs(SemanticConfig::EffectiveBeliefReliability(
        0.05f, 0.9f, 1.0f, 5.991f) - 0.1f) < 1e-6f);
    // E: the existing reliability floor is retained.
    assert(std::fabs(SemanticConfig::EffectiveBeliefReliability(
        0.05f, 1.0f, 1.0f, 5.991f) - 0.05f) < 1e-6f);
    std::remove(path.c_str());
    return 0;
}
