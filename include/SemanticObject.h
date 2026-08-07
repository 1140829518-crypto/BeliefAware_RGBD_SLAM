/**
* This file is part of ORB-SLAM2.
*
* Copyright (C) 2014-2016 Raúl Mur-Artal <raulmur at unizar dot es> (University of Zaragoza)
* For more information see <https://github.com/raulmur/ORB_SLAM2>
*
* ORB-SLAM2 is free software: you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation, either version 3 of the License, or
* (at your option) any later version.
*
* ORB-SLAM2 is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with ORB-SLAM2. If not, see <http://www.gnu.org/licenses/>.
*/

#ifndef SEMANTICOBJECT_H
#define SEMANTICOBJECT_H

#include <opencv2/core/core.hpp>

#include <mutex>
#include <string>
#include <vector>

namespace ORB_SLAM2
{

/**
 * @brief 对象级语义地标
 * @details Semantic Object Landmark for object-level map construction.
 */
class SemanticObject
{
public:
    SemanticObject();
    SemanticObject(const int &classId,
                   const std::string &className,
                   const std::vector<double> &bbox,
                   const cv::Mat &worldCenter,
                   const long unsigned int &frameId);

    void UpdateObservation(const std::vector<double> &bbox,
                           const cv::Mat &worldCenter,
                           const long unsigned int &frameId);

    float DistanceTo(const SemanticObject &other) const;

    cv::Mat GetWorldCenter();
    std::vector<double> GetBBox();
    std::string GetClassName();

public:
    static long unsigned int nNextId;
    long unsigned int mnObjectId;

    int mnClassId;
    std::string msClassName;
    std::vector<double> mvBBox;
    cv::Mat mWorldCenter;

    long unsigned int mnObservedFrameId;
    long unsigned int mnFirstObservedFrameId;
    int mnObservedCount;

protected:
    std::mutex mMutexObject;
};

} // namespace ORB_SLAM2

#endif // SEMANTICOBJECT_H
