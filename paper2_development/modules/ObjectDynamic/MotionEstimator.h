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

#include "ObjectState.h"

namespace ORB_SLAM2
{
namespace Paper2
{

enum class MotionEstimationStatus
{
    Success,
    MissingTimestamp,
    InvalidDeltaTime,
    InvalidPosition,
    ObjectIdMismatch
};

struct MotionEstimate
{
    bool valid;
    MotionEstimationStatus status;
    ObjectState::ObjectId object_id;
    double delta_time;
    Vector3D velocity;
    Vector3D motion_direction;
    double speed;
    double direction_consistency;
    double history_stability;
    double motion_score;
    double updated_dynamic_probability;

    MotionEstimate();
};

class MotionEstimator
{
public:
    MotionEstimator();
    ~MotionEstimator();

    MotionEstimate Estimate(const ObjectState &previous,
                            const ObjectState &current) const;

    bool ApplyEstimate(ObjectState &current,
                       const MotionEstimate &estimate) const;

    void SetSmoothingAlpha(double alpha);
    void SetValidDeltaTimeRange(double minimum_delta_time,
                                double maximum_delta_time);
    void SetSpeedScale(double speed_scale);
    void SetVelocityStabilityScale(double stability_scale);
    void SetConsistencyWeights(double direction_weight,
                               double history_weight);

    double GetSmoothingAlpha() const;

private:
    static bool IsFiniteVector(const Vector3D &value);
    static double Norm(const Vector3D &value);
    static Vector3D Normalize(const Vector3D &value);
    static double DirectionConsistency(const Vector3D &current_velocity,
                                       const Vector3D &previous_velocity);
    static double ClampUnit(double value);

    double smoothing_alpha_;
    double minimum_delta_time_;
    double maximum_delta_time_;
    double speed_scale_;
    double velocity_stability_scale_;
    double direction_weight_;
    double history_weight_;
};

} // namespace Paper2
} // namespace ORB_SLAM2

#endif // PAPER2_OBJECT_DYNAMIC_MOTION_ESTIMATOR_H
