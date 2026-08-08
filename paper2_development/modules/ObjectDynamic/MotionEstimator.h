/*
Paper2 Object-level Dynamic SLAM Module

Purpose:
Object motion estimation and trajectory prediction interfaces.

Author:
Dong Jianing

Branch:
paper2_development
*/

#ifndef PAPER2_OBJECT_DYNAMIC_MOTION_ESTIMATOR_H
#define PAPER2_OBJECT_DYNAMIC_MOTION_ESTIMATOR_H

namespace ORB_SLAM2
{
namespace Paper2
{

// Interface skeleton for object motion estimation and trajectory prediction.
class MotionEstimator
{
public:
    MotionEstimator();
    ~MotionEstimator();

    // TODO(paper2): Declare prediction and observation-update interfaces after design review.
};

} // namespace Paper2
} // namespace ORB_SLAM2

#endif // PAPER2_OBJECT_DYNAMIC_MOTION_ESTIMATOR_H
