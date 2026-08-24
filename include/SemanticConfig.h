
/**
 * Semantic configuration for dynamic-point management and object mapping.
 * Semantic Dynamic RGB-D SLAM shared parameters.
 */

#ifndef SEMANTICCONFIG_H
#define SEMANTICCONFIG_H

#include <set>
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
        if(parsed > 2)
            return 2;
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
    return Mode() >= 2;
}

inline bool UseObjectSemanticMap()
{
    const char *env = std::getenv("ORB_SLAM2_OBJECT_MAP");
    if(!env)
        return Mode() >= 2;
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
static const float kObjectAssociationDistance = 0.65f;

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
