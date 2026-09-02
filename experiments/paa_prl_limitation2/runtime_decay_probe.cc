#include "SemanticConfig.h"
#include <iomanip>
#include <iostream>

int main()
{
    std::cout << std::fixed << std::setprecision(9)
              << "ordinary=" << ORB_SLAM2::SemanticConfig::DynamicScoreDecayForClass(-1) << "\n"
              << "person=" << ORB_SLAM2::SemanticConfig::DynamicScoreDecayForClass(3) << "\n";
    return 0;
}
