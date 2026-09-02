#ifndef FRAME_TEMPORAL_CONFIG_H
#define FRAME_TEMPORAL_CONFIG_H

namespace ORB_SLAM2
{
namespace FrameTemporalConfig
{
// Frozen control-baseline parameters. Alpha weights the current binary
// frame observation; the complement weights the previous image-plane state.
static const float kCurrentObservationAlpha = 0.60f;
static const float kDynamicThreshold = 0.50f;
static const float kInitialProbability = 0.0f;
} // namespace FrameTemporalConfig
} // namespace ORB_SLAM2

#endif
