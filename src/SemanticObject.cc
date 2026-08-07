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

#include "SemanticObject.h"

#include <cmath>
#include <limits>

namespace ORB_SLAM2
{

long unsigned int SemanticObject::nNextId = 0;

SemanticObject::SemanticObject()
    :mnObjectId(nNextId++),
     mnClassId(-1),
     msClassName("unknown"),
     mnObservedFrameId(0),
     mnFirstObservedFrameId(0),
     mnObservedCount(0)
{
    mvBBox = {0, 0, 0, 0};
    mWorldCenter = cv::Mat::zeros(3, 1, CV_32F);
}

SemanticObject::SemanticObject(const int &classId,
                               const std::string &className,
                               const std::vector<double> &bbox,
                               const cv::Mat &worldCenter,
                               const long unsigned int &frameId)
    :mnObjectId(nNextId++),
     mnClassId(classId),
     msClassName(className),
     mvBBox(bbox),
     mnObservedFrameId(frameId),
     mnFirstObservedFrameId(frameId),
     mnObservedCount(1)
{
    worldCenter.copyTo(mWorldCenter);
    if(mWorldCenter.empty())
        mWorldCenter = cv::Mat::zeros(3, 1, CV_32F);
}

void SemanticObject::UpdateObservation(const std::vector<double> &bbox,
                                       const cv::Mat &worldCenter,
                                       const long unsigned int &frameId)
{
    std::lock_guard<std::mutex> lock(mMutexObject);

    if(mnObservedCount <= 0)
        mnObservedCount = 1;

    const float alpha = 1.0f / static_cast<float>(mnObservedCount + 1);
    if(!worldCenter.empty())
    {
        if(mWorldCenter.empty())
            worldCenter.copyTo(mWorldCenter);
        else
            mWorldCenter = (1.0f - alpha) * mWorldCenter + alpha * worldCenter;
    }

    if(!bbox.empty())
        mvBBox = bbox;

    mnObservedCount++;
    mnObservedFrameId = frameId;
}

float SemanticObject::DistanceTo(const SemanticObject &other) const
{
    if(mWorldCenter.empty() || other.mWorldCenter.empty())
        return std::numeric_limits<float>::max();
    return static_cast<float>(cv::norm(mWorldCenter - other.mWorldCenter));
}

cv::Mat SemanticObject::GetWorldCenter()
{
    std::lock_guard<std::mutex> lock(mMutexObject);
    return mWorldCenter.clone();
}

std::vector<double> SemanticObject::GetBBox()
{
    std::lock_guard<std::mutex> lock(mMutexObject);
    return mvBBox;
}

std::string SemanticObject::GetClassName()
{
    std::lock_guard<std::mutex> lock(mMutexObject);
    return msClassName;
}

} // namespace ORB_SLAM2
