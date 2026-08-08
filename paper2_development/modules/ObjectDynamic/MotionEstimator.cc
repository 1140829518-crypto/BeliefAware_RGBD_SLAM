/*
Paper2 Object-level Dynamic SLAM Module

Purpose:
Object motion estimation and trajectory prediction interfaces.

Author:
Dong Jianing

Branch:
paper2_development
*/

#include "MotionEstimator.h"

#include <cmath>

namespace ORB_SLAM2
{
namespace Paper2
{

MotionEstimate::MotionEstimate()
    : valid(false),
      status(MotionEstimationStatus::MissingTimestamp),
      object_id(0),
      delta_time(0.0),
      velocity(),
      motion_direction(),
      speed(0.0),
      direction_consistency(0.0),
      history_stability(0.0),
      motion_score(0.0),
      updated_dynamic_probability(0.0)
{
}

MotionEstimator::MotionEstimator()
    : smoothing_alpha_(0.8),
      minimum_delta_time_(1e-6),
      maximum_delta_time_(10.0),
      speed_scale_(0.5),
      velocity_stability_scale_(0.5),
      direction_weight_(0.5),
      history_weight_(0.5)
{
}

MotionEstimator::~MotionEstimator()
{
}

MotionEstimate MotionEstimator::Estimate(const ObjectState &previous,
                                         const ObjectState &current) const
{
    MotionEstimate estimate;
    estimate.object_id = current.GetObjectId();
    estimate.updated_dynamic_probability = current.GetDynamicProbability();

    if(previous.GetObjectId() != current.GetObjectId())
    {
        estimate.status = MotionEstimationStatus::ObjectIdMismatch;
        return estimate;
    }

    if(previous.GetObservationCount() == 0 || current.GetObservationCount() == 0
       || !std::isfinite(previous.GetTimestamp())
       || !std::isfinite(current.GetTimestamp()))
    {
        estimate.status = MotionEstimationStatus::MissingTimestamp;
        return estimate;
    }

    const double delta_time = current.GetTimestamp() - previous.GetTimestamp();
    estimate.delta_time = delta_time;
    if(!std::isfinite(delta_time)
       || delta_time <= minimum_delta_time_
       || delta_time > maximum_delta_time_)
    {
        estimate.status = MotionEstimationStatus::InvalidDeltaTime;
        return estimate;
    }

    const Vector3D &previous_position = previous.GetPosition();
    const Vector3D &current_position = current.GetPosition();
    if(!IsFiniteVector(previous_position) || !IsFiniteVector(current_position))
    {
        estimate.status = MotionEstimationStatus::InvalidPosition;
        return estimate;
    }

    estimate.velocity = Vector3D(
        (current_position.x - previous_position.x) / delta_time,
        (current_position.y - previous_position.y) / delta_time,
        (current_position.z - previous_position.z) / delta_time);

    if(!IsFiniteVector(estimate.velocity))
    {
        estimate.status = MotionEstimationStatus::InvalidPosition;
        return estimate;
    }

    estimate.speed = Norm(estimate.velocity);
    estimate.motion_direction = Normalize(estimate.velocity);

    const Vector3D &previous_velocity = previous.GetVelocity();
    const bool has_previous_motion = IsFiniteVector(previous_velocity)
                                  && Norm(previous_velocity) > 1e-12;
    if(has_previous_motion)
    {
        estimate.direction_consistency =
            DirectionConsistency(estimate.velocity, previous_velocity);

        const Vector3D velocity_difference(
            estimate.velocity.x - previous_velocity.x,
            estimate.velocity.y - previous_velocity.y,
            estimate.velocity.z - previous_velocity.z);
        estimate.history_stability = std::exp(
            -Norm(velocity_difference) / velocity_stability_scale_);
    }
    else
    {
        // No prior motion direction exists; the first valid estimate is neutral.
        estimate.direction_consistency = 1.0;
        estimate.history_stability = 1.0;
    }

    const double speed_score = 1.0 - std::exp(-estimate.speed / speed_scale_);
    const double consistency_weight_sum = direction_weight_ + history_weight_;
    double consistency_score = 1.0;
    if(consistency_weight_sum > 0.0)
    {
        consistency_score =
            (direction_weight_ * estimate.direction_consistency
             + history_weight_ * estimate.history_stability)
            / consistency_weight_sum;
    }

    estimate.motion_score = ClampUnit(speed_score * consistency_score);
    estimate.updated_dynamic_probability = ClampUnit(
        smoothing_alpha_ * current.GetDynamicProbability()
        + (1.0 - smoothing_alpha_) * estimate.motion_score);
    estimate.valid = true;
    estimate.status = MotionEstimationStatus::Success;
    return estimate;
}

bool MotionEstimator::ApplyEstimate(ObjectState &current,
                                    const MotionEstimate &estimate) const
{
    if(!estimate.valid || estimate.status != MotionEstimationStatus::Success
       || estimate.object_id != current.GetObjectId())
        return false;

    current.UpdateVelocity(estimate.velocity);
    current.SetDynamicProbability(estimate.updated_dynamic_probability);
    return true;
}

void MotionEstimator::SetSmoothingAlpha(double alpha)
{
    smoothing_alpha_ = ClampUnit(alpha);
}

void MotionEstimator::SetValidDeltaTimeRange(double minimum_delta_time,
                                             double maximum_delta_time)
{
    if(minimum_delta_time > 0.0 && maximum_delta_time > minimum_delta_time)
    {
        minimum_delta_time_ = minimum_delta_time;
        maximum_delta_time_ = maximum_delta_time;
    }
}

void MotionEstimator::SetSpeedScale(double speed_scale)
{
    if(speed_scale > 0.0)
        speed_scale_ = speed_scale;
}

void MotionEstimator::SetVelocityStabilityScale(double stability_scale)
{
    if(stability_scale > 0.0)
        velocity_stability_scale_ = stability_scale;
}

void MotionEstimator::SetConsistencyWeights(double direction_weight,
                                            double history_weight)
{
    if(direction_weight >= 0.0 && history_weight >= 0.0
       && direction_weight + history_weight > 0.0)
    {
        direction_weight_ = direction_weight;
        history_weight_ = history_weight;
    }
}

double MotionEstimator::GetSmoothingAlpha() const
{
    return smoothing_alpha_;
}

bool MotionEstimator::IsFiniteVector(const Vector3D &value)
{
    return std::isfinite(value.x) && std::isfinite(value.y) && std::isfinite(value.z);
}

double MotionEstimator::Norm(const Vector3D &value)
{
    return std::sqrt(value.x * value.x + value.y * value.y + value.z * value.z);
}

Vector3D MotionEstimator::Normalize(const Vector3D &value)
{
    const double norm = Norm(value);
    if(norm <= 1e-12 || !std::isfinite(norm))
        return Vector3D();
    return Vector3D(value.x / norm, value.y / norm, value.z / norm);
}

double MotionEstimator::DirectionConsistency(const Vector3D &current_velocity,
                                             const Vector3D &previous_velocity)
{
    const double current_norm = Norm(current_velocity);
    const double previous_norm = Norm(previous_velocity);
    if(current_norm <= 1e-12 || previous_norm <= 1e-12)
        return 1.0;

    const double cosine =
        (current_velocity.x * previous_velocity.x
         + current_velocity.y * previous_velocity.y
         + current_velocity.z * previous_velocity.z)
        / (current_norm * previous_norm);
    return ClampUnit(0.5 * (cosine + 1.0));
}

double MotionEstimator::ClampUnit(double value)
{
    if(value < 0.0)
        return 0.0;
    if(value > 1.0)
        return 1.0;
    return value;
}

} // namespace Paper2
} // namespace ORB_SLAM2
