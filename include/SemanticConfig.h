
/**
 * Semantic configuration for dynamic-point management and object mapping.
 * Semantic Dynamic RGB-D SLAM shared parameters.
 */

#ifndef SEMANTICCONFIG_H
#define SEMANTICCONFIG_H

#include <set>
#include <algorithm>
#include <string>
#include <vector>
#include <cstdlib>

namespace ORB_SLAM2
{
namespace SemanticConfig
{
inline int Mode()
{
    static const int mode = []() {
        const char *env = std::getenv("ORB_SLAM2_SEMANTIC_MODE");
        if(!env)
            return 2;
        const int parsed = std::atoi(env);
        if(parsed < 0)
            return 0;
        if(parsed > 3)
            return 3;
        return parsed;
    }();
    return mode;
}

inline bool UseSemanticPipeline()
{
    return Mode() >= 1;
}

inline bool UseDynamicAccumulation()
{
    return Mode() == 2;
}

inline bool UseFrameTemporalBaseline()
{
    return Mode() == 3;
}

inline bool UseObjectSemanticMap()
{
    const char *env = std::getenv("ORB_SLAM2_OBJECT_MAP");
    if(!env)
        return Mode() == 2;
    return std::atoi(env) != 0;
}

static const float kDynamicScoreThreshold = 3.0f;
static const float kDynamicScoreIncrement = 1.0f;
static const float kDynamicScoreDecay = 0.95f;
// Semantic Dynamic Probability Accumulation:
// person 类作为最强动态目标，采用更激进的评分与衰减策略，
// 让动态抑制更快收敛，从而尽量优先保证 Tracking 的几何纯净度。
static const float kPersonDynamicScoreThreshold = 2.0f;
static const float kPersonDynamicScoreIncrement = 1.0f;
static const float kPersonDynamicScoreDecay = 0.90f;
static const float kUncertainScoreThreshold = 1.0f;
static const float kPersonUncertainScoreThreshold = 1.0f;
static const float kUncertainWeight = 0.5f;
static const float kObjectAssociationDistance = 0.65f;

enum TemporalReliabilityMode
{
    P1_HARD = 0,
    A_HARD_STATE = 1,
    A_SOFT = 2
};

inline TemporalReliabilityMode ReliabilityMode()
{
    const char *env = std::getenv("ORB_SLAM2_TEMPORAL_RELIABILITY_MODE");
    if(!env || !env[0] || std::string(env) == "P1-Hard" || std::string(env) == "p1-hard")
        return P1_HARD;
    if(std::string(env) == "A-HardState" || std::string(env) == "a-hardstate")
        return A_HARD_STATE;
    if(std::string(env) == "A-Soft" || std::string(env) == "a-soft")
        return A_SOFT;
    const int parsed = std::atoi(env);
    if(parsed <= 0)
        return P1_HARD;
    if(parsed == 1)
        return A_HARD_STATE;
    return A_SOFT;
}

inline bool UseSingleEvidenceUpdatePerFrame()
{
    return ReliabilityMode() != P1_HARD;
}

inline bool UseLegacyTemporalWeight();

inline bool UseTemporalSoftWeighting()
{
    return UseLegacyTemporalWeight() && ReliabilityMode() == A_SOFT;
}

inline bool EnvSwitch(const char *name, const bool fallback = true)
{
    const char *env = std::getenv(name);
    if(!env)
        return fallback;
    const std::string value(env);
    return value != "0" && value != "false" && value != "FALSE"
        && value != "off" && value != "OFF";
}

inline bool UseLegacyTemporalWeight()
{
    return EnvSwitch("ORB_SLAM2_LEGACY_TEMPORAL_WEIGHT_ENABLED", true);
}

inline bool UseLegacyTemporalHardRejection()
{
    return EnvSwitch("ORB_SLAM2_LEGACY_TEMPORAL_HARD_REJECTION_ENABLED", true);
}

inline bool BeliefEnabled()
{
    return EnvSwitch("ORB_SLAM2_BELIEF_ENABLED", true);
}

inline bool ReliabilityEnabled()
{
    return EnvSwitch("ORB_SLAM2_RELIABILITY_ENABLED", true);
}

inline bool ActiveModeEnabled()
{
    return EnvSwitch("ORB_SLAM2_ACTIVE_MODE_ENABLED", true);
}

inline bool ConflictAwareUncertaintyEnabled()
{
    return EnvSwitch("ORB_SLAM2_CONFLICT_AWARE_UNCERTAINTY_ENABLED", false);
}

enum BeliefUncertaintyMode
{
    BELIEF_UNCERTAINTY_CLEAN = 0,
    BELIEF_UNCERTAINTY_RAW = 1,
    BELIEF_UNCERTAINTY_PERSISTENT = 2
};

inline BeliefUncertaintyMode UncertaintyMode()
{
    const char *env = std::getenv("ORB_SLAM2_UNCERTAINTY_MODE");
    if(env && env[0])
    {
        const std::string value(env);
        if(value == "CLEAN" || value == "clean" || value == "0")
            return BELIEF_UNCERTAINTY_CLEAN;
        if(value == "RAW" || value == "raw" || value == "1")
            return BELIEF_UNCERTAINTY_RAW;
        if(value == "PERSISTENT" || value == "persistent" || value == "2")
            return BELIEF_UNCERTAINTY_PERSISTENT;
    }
    // Backward-compatible fallback for V2 experiment commands.
    return ConflictAwareUncertaintyEnabled() ? BELIEF_UNCERTAINTY_RAW
                                              : BELIEF_UNCERTAINTY_CLEAN;
}

inline const char *UncertaintyModeName()
{
    switch(UncertaintyMode())
    {
    case BELIEF_UNCERTAINTY_RAW: return "RAW";
    case BELIEF_UNCERTAINTY_PERSISTENT: return "PERSISTENT";
    default: return "CLEAN";
    }
}

enum MeasurementPolicyMode
{
    MEASUREMENT_POLICY_BELIEF_ONLY = 0,
    MEASUREMENT_POLICY_GEOMETRY_PROTECTED = 1,
    MEASUREMENT_POLICY_NO_BELIEF_WEIGHT = 2
};

inline MeasurementPolicyMode MeasurementPolicy()
{
    const char *env = std::getenv("ORB_SLAM2_MEASUREMENT_POLICY");
    if(!env || !env[0])
        return MEASUREMENT_POLICY_BELIEF_ONLY;
    const std::string value(env);
    if(value == "GEOMETRY_PROTECTED" || value == "geometry_protected" || value == "1")
        return MEASUREMENT_POLICY_GEOMETRY_PROTECTED;
    if(value == "NO_BELIEF_WEIGHT" || value == "no_belief_weight" || value == "2")
        return MEASUREMENT_POLICY_NO_BELIEF_WEIGHT;
    return MEASUREMENT_POLICY_BELIEF_ONLY;
}

inline const char *MeasurementPolicyName()
{
    switch(MeasurementPolicy())
    {
    case MEASUREMENT_POLICY_GEOMETRY_PROTECTED: return "GEOMETRY_PROTECTED";
    case MEASUREMENT_POLICY_NO_BELIEF_WEIGHT: return "NO_BELIEF_WEIGHT";
    default: return "BELIEF_ONLY";
    }
}

inline float DynamicOnlyReliability(const float dynamicProbability)
{
    const float value = 1.0f - dynamicProbability;
    return value < 0.05f ? 0.05f : (value > 1.0f ? 1.0f : value);
}

inline float BeliefReliability(const float dynamicProbability,
                               const float uncertainty)
{
    const float value = (1.0f - dynamicProbability) * (1.0f - uncertainty);
    return value < 0.05f ? 0.05f : (value > 1.0f ? 1.0f : value);
}

inline float EffectiveBeliefReliability(const float beliefReliability,
                                        const float dynamicProbability,
                                        const float baseInitialChi2,
                                        const float chi2Threshold)
{
    if(MeasurementPolicy() == MEASUREMENT_POLICY_NO_BELIEF_WEIGHT)
        return 1.0f;
    if(MeasurementPolicy() == MEASUREMENT_POLICY_GEOMETRY_PROTECTED
       && chi2Threshold > 0.0f
       && baseInitialChi2 / chi2Threshold <= 1.0f)
        return std::max(beliefReliability,
                        DynamicOnlyReliability(dynamicProbability));
    return beliefReliability;
}

inline float EnvFloat(const char *name, const float fallback)
{
    const char *env = std::getenv(name);
    if(!env)
        return fallback;
    char *end = NULL;
    const float parsed = std::strtof(env, &end);
    if(end == env)
        return fallback;
    return parsed;
}

inline bool IsPersonClass(const int classId)
{
    return classId == 3;
}

inline float DynamicScoreThresholdForClass(const int classId)
{
    const float fallback = IsPersonClass(classId) ? kPersonDynamicScoreThreshold : kDynamicScoreThreshold;
    const char *specificName = IsPersonClass(classId) ? "ORB_SLAM2_PERSON_DYNAMIC_THETA" : "ORB_SLAM2_DYNAMIC_THETA";
    float threshold = EnvFloat(specificName, EnvFloat("ORB_SLAM2_DYNAMIC_THETA", fallback));
    if(threshold < 0.0f)
        threshold = 0.0f;
    return threshold;
}

inline float DynamicScoreIncrementForClass(const int classId)
{
    const float fallback = IsPersonClass(classId) ? kPersonDynamicScoreIncrement : kDynamicScoreIncrement;
    const char *specificName = IsPersonClass(classId)
                               ? "ORB_SLAM2_PERSON_DYNAMIC_INCREMENT"
                               : "ORB_SLAM2_DYNAMIC_INCREMENT";
    float increment = EnvFloat(specificName, fallback);
    if(increment < 0.0f)
        increment = 0.0f;
    return increment;
}

inline float DynamicScoreDecayForClass(const int classId)
{
    const float defaultDecay = IsPersonClass(classId) ? kPersonDynamicScoreDecay : kDynamicScoreDecay;
    const char *specificName = IsPersonClass(classId)
                               ? "ORB_SLAM2_PERSON_DYNAMIC_LAMBDA"
                               : "ORB_SLAM2_DYNAMIC_LAMBDA";
    float decay = EnvFloat(specificName, defaultDecay);
    if(decay < 0.0f)
        decay = 0.0f;
    if(decay > 0.999f)
        decay = 0.999f;
    return decay;
}

inline float UncertainScoreThresholdForClass(const int classId)
{
    const float dynamicThreshold = DynamicScoreThresholdForClass(classId);
    const float fallback = IsPersonClass(classId)
                         ? kPersonUncertainScoreThreshold
                         : kUncertainScoreThreshold;
    const char *name = IsPersonClass(classId)
                     ? "ORB_SLAM2_PERSON_UNCERTAIN_THETA"
                     : "ORB_SLAM2_UNCERTAIN_THETA";
    float threshold = EnvFloat(name, fallback);
    if(threshold < 0.0f)
        threshold = 0.0f;
    if(threshold >= dynamicThreshold)
        threshold = dynamicThreshold > 0.0f ? dynamicThreshold * 0.5f : 0.0f;
    return threshold;
}

inline float UncertainWeight()
{
    float weight = EnvFloat("ORB_SLAM2_UNCERTAIN_WEIGHT", kUncertainWeight);
    if(weight <= 0.0f)
        weight = kUncertainWeight;
    if(weight > 1.0f)
        weight = 1.0f;
    return weight;
}

inline const std::set<int> &DynamicObjectClasses()
{
    if(!UseSemanticPipeline())
    {
        static const std::set<int> empty;
        return empty;
    }
    static const std::set<int> classes = {3};
    return classes;
}

inline const std::set<int> &StaticObjectClasses()
{
    if(!UseSemanticPipeline())
    {
        static const std::set<int> empty;
        return empty;
    }
    static const std::set<int> classes = {1, 2};
    return classes;
}

inline bool IsDynamicObjectClass(const int classId)
{
    return DynamicObjectClasses().count(classId) > 0;
}

inline bool IsStaticObjectClass(const int classId)
{
    return StaticObjectClasses().count(classId) > 0;
}

inline bool IsSemanticObjectClass(const int classId)
{
    return IsDynamicObjectClass(classId) || IsStaticObjectClass(classId);
}

inline std::string ClassNameFromId(const int classId)
{
    if(classId == 1)
        return "static_group";
    if(classId == 2)
        return "low_dynamic_group";
    if(classId == 3)
        return "person";
    return "unknown";
}

} // namespace SemanticConfig
} // namespace ORB_SLAM2

#endif // SEMANTICCONFIG_H
