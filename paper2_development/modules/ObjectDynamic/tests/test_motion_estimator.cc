#include "MotionEstimator.h"

#include <cassert>
#include <cmath>
#include <limits>

using ORB_SLAM2::Paper2::BoundingBox2D;
using ORB_SLAM2::Paper2::MotionEstimate;
using ORB_SLAM2::Paper2::MotionEstimationStatus;
using ORB_SLAM2::Paper2::MotionEstimator;
using ORB_SLAM2::Paper2::ObjectState;
using ORB_SLAM2::Paper2::Vector3D;

namespace
{

ObjectState MakeObject(ObjectState::ObjectId id,
                       const Vector3D &position,
                       double timestamp)
{
    return ObjectState::Create(id, 3, "person",
                               BoundingBox2D(10.0, 10.0, 50.0, 90.0),
                               0.9, position, timestamp);
}

bool Near(double first, double second, double tolerance = 1e-12)
{
    return std::fabs(first - second) <= tolerance;
}

} // namespace

int main()
{
    MotionEstimator estimator;

    // 1. A stationary object has zero velocity and a low motion score.
    const ObjectState stationary_previous = MakeObject(1, Vector3D(1.0, 2.0, 3.0), 1.0);
    ObjectState stationary_current = MakeObject(1, Vector3D(1.0, 2.0, 3.0), 2.0);
    const MotionEstimate stationary = estimator.Estimate(
        stationary_previous, stationary_current);
    assert(stationary.valid);
    assert(stationary.status == MotionEstimationStatus::Success);
    assert(Near(stationary.speed, 0.0));
    assert(stationary.motion_score < 1e-12);

    // 2. Consecutive one-metre-per-second motion remains stable.
    const ObjectState moving_previous = MakeObject(2, Vector3D(0.0, 0.0, 0.0), 1.0);
    ObjectState moving_current = MakeObject(2, Vector3D(1.0, 0.0, 0.0), 2.0);
    const MotionEstimate first_motion = estimator.Estimate(moving_previous, moving_current);
    assert(first_motion.valid);
    assert(Near(first_motion.velocity.x, 1.0));
    assert(estimator.ApplyEstimate(moving_current, first_motion));

    ObjectState moving_next = MakeObject(2, Vector3D(2.0, 0.0, 0.0), 3.0);
    const MotionEstimate second_motion = estimator.Estimate(moving_current, moving_next);
    assert(second_motion.valid);
    assert(Near(second_motion.velocity.x, 1.0));
    assert(Near(second_motion.motion_direction.x, 1.0));
    assert(Near(second_motion.direction_consistency, 1.0));
    assert(Near(second_motion.history_stability, 1.0));
    assert(second_motion.motion_score > 0.8);

    // 3. Dynamic probability follows exponential smoothing exactly.
    moving_next.SetDynamicProbability(0.2);
    const MotionEstimate probability_update = estimator.Estimate(moving_current, moving_next);
    const double expected_probability =
        estimator.GetSmoothingAlpha() * 0.2
        + (1.0 - estimator.GetSmoothingAlpha()) * probability_update.motion_score;
    assert(Near(probability_update.updated_dynamic_probability,
                expected_probability));
    assert(estimator.ApplyEstimate(moving_next, probability_update));
    assert(Near(moving_next.GetDynamicProbability(), expected_probability));

    // Invalid inputs are reported without mutating the object.
    const ObjectState missing_timestamp;
    const ObjectState timestamp_current = MakeObject(0, Vector3D(), 1.0);
    const MotionEstimate missing = estimator.Estimate(missing_timestamp, timestamp_current);
    assert(!missing.valid);
    assert(missing.status == MotionEstimationStatus::MissingTimestamp);

    ObjectState invalid_time = MakeObject(2, Vector3D(3.0, 0.0, 0.0), 3.0);
    const MotionEstimate invalid_delta = estimator.Estimate(moving_next, invalid_time);
    assert(!invalid_delta.valid);
    assert(invalid_delta.status == MotionEstimationStatus::InvalidDeltaTime);

    ObjectState invalid_position = MakeObject(
        2, Vector3D(std::numeric_limits<double>::quiet_NaN(), 0.0, 0.0), 4.0);
    const MotionEstimate invalid_position_result = estimator.Estimate(
        moving_next, invalid_position);
    assert(!invalid_position_result.valid);
    assert(invalid_position_result.status == MotionEstimationStatus::InvalidPosition);
    return 0;
}
