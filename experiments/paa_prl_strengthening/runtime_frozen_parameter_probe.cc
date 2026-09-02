#include "SemanticConfig.h"
#include <iomanip>
#include <iostream>
int main() {
  std::cout << std::fixed << std::setprecision(9)
    << "ordinary_threshold=" << ORB_SLAM2::SemanticConfig::DynamicScoreThresholdForClass(-1) << "\n"
    << "ordinary_increment=" << ORB_SLAM2::SemanticConfig::DynamicScoreIncrementForClass(-1) << "\n"
    << "ordinary_decay=" << ORB_SLAM2::SemanticConfig::DynamicScoreDecayForClass(-1) << "\n"
    << "person_threshold=" << ORB_SLAM2::SemanticConfig::DynamicScoreThresholdForClass(3) << "\n"
    << "person_increment=" << ORB_SLAM2::SemanticConfig::DynamicScoreIncrementForClass(3) << "\n"
    << "person_decay=" << ORB_SLAM2::SemanticConfig::DynamicScoreDecayForClass(3) << "\n";
}
