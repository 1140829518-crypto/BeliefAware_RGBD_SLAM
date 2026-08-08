/*
Paper2 Object-level Dynamic SLAM Module

Purpose:
Object-level spatio-temporal dynamic modeling.

Author:
Dong Jianing

Branch:
paper2_development
*/

#ifndef PAPER2_OBJECT_DYNAMIC_OBJECT_STATE_H
#define PAPER2_OBJECT_DYNAMIC_OBJECT_STATE_H

namespace ORB_SLAM2
{
namespace Paper2
{

// Interface skeleton for object identity, semantic, motion, and dynamic state.
class ObjectState
{
public:
    ObjectState();
    ~ObjectState();

    // TODO(paper2): Declare state access and update interfaces after design review.
};

} // namespace Paper2
} // namespace ORB_SLAM2

#endif // PAPER2_OBJECT_DYNAMIC_OBJECT_STATE_H
