/*
Paper2 Object-level Dynamic SLAM Module

Purpose:
Object-map association, dynamic map update, and recovery interfaces.

Author:
Dong Jianing

Branch:
paper2_development
*/

#ifndef PAPER2_OBJECT_DYNAMIC_DYNAMIC_MAP_MANAGER_H
#define PAPER2_OBJECT_DYNAMIC_DYNAMIC_MAP_MANAGER_H

namespace ORB_SLAM2
{
namespace Paper2
{

// Interface skeleton for object-level dynamic map lifecycle management.
class DynamicMapManager
{
public:
    DynamicMapManager();
    ~DynamicMapManager();

    // TODO(paper2): Declare association, map-update, and recovery interfaces after design review.
};

} // namespace Paper2
} // namespace ORB_SLAM2

#endif // PAPER2_OBJECT_DYNAMIC_DYNAMIC_MAP_MANAGER_H
