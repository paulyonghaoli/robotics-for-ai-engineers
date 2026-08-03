# Module 8 · Manipulation

**Status:** In progress · **Course III**

Everything so far has been a base that moves through a world. This module is about an arm that *changes* one — and almost every intuition built up over five modules of mobile robotics needs adjusting.

A mobile robot has three degrees of freedom and a two-dimensional world. A six-joint arm has a six-dimensional configuration space, obstacles that are not obstacles in that space until you compute them, and a workspace whose boundary is a place where the mathematics stops being invertible. Planning "go around the box" is a sentence with an obvious meaning for a base and no meaning at all for an arm until you have chosen a representation.

The payoff is that manipulation is where robotics stops being navigation. Grasping, assembly, and every task a humanoid is being built to do live here.

## Lessons

1. [Manipulator kinematics: from joints to a pose](01-kinematics.md) — **available**
2. [Inverse kinematics and the singularities that eat it](02-inverse-kinematics.md) — **available**
3. [Grasp synthesis: where to put the fingers](03-grasping.md) — **available**
4. [Configuration-space planning: the obstacle you cannot draw](04-cspace-planning.md) — **available**
5. [Visual servoing: closing the loop through the camera](05-visual-servoing.md) — **available**
6. Lab: the arm that worked in simulation — *planned*

## What you'll build

Forward and inverse kinematics for a planar arm, a manipulability analysis that tells you where the arm is about to become useless, collision checking in configuration space, and a grasp scorer — leading into [Capstone III](../capstone-3/index.md), where all of it drives a second robot.

## What transfers from Module 2

More than you expect. [2.3's](../02-control/03-jacobians.md) Jacobian is the same object, [2.1's](../02-control/01-kinematics.md) forward kinematics is the same idea with more links, and the damped least squares you wrote in the [control mini-project](../02-control/project-control.md) is the workhorse here.

What is new is that the redundancy becomes exploitable: with more joints than task dimensions, there is a whole subspace of joint motions that do not move the end effector at all, and you can use it to avoid obstacles, stay away from limits, or keep away from singularities — all while holding the tool exactly where it needs to be.
