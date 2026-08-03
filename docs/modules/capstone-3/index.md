# Capstone III · See It, Grasp It

**Status:** Brief live; implementation planned · **Prereqs:** Modules 7 and 8 · **Time:** ~20 h

---

## The premise

Every robot in this curriculum so far has been the same robot: a differential-drive base moving through a world it does not change.

This one has an arm. It sees objects with a depth sensor, decides where to grip them, plans a path through its own configuration space, and executes it under Jacobian control. Nothing about it is a bigger version of the navigation capstone — the state space, the failure modes and the notion of "obstacle" are all different.

That difference is the point. **A portfolio with two distinct embodiments argues something a fifth navigation stack cannot**: that you can pick up an unfamiliar robot morphology and reason about it, rather than having learned one system deeply and generalised nothing.

## The pipeline

| Stage | You build | Draws on |
|---|---|---|
| **Perceive** | Depth image → point cloud → ground removal → object segmentation | [7.1](../07-perception/01-camera-models.md), [7.2](../07-perception/02-stereo-depth.md), [7.3](../07-perception/03-point-clouds.md) |
| **Grasp** | Antipodal grasp candidates on each object, scored and ranked | 8.3 |
| **Plan** | A collision-free path in configuration space, not task space | 8.4, [5.3](../05-planning/03-rrt.md) |
| **Execute** | Damped IK with null-space posture control along the path | [8.1](../08-manipulation/01-kinematics.md), [8.2](../08-manipulation/02-inverse-kinematics.md) |
| **Verify** | A published rubric, scored across randomized scenes | [10.1](../10-evaluation/01-statistical-rigor.md) |

## The rubric (draft)

Scored the same way as the navigation capstone — a published bar, randomized scenes, and an operating envelope reported rather than tuned away.

| Metric | Draft bar |
|---|---|
| Grasp success rate | ≥ 0.80 |
| Collision-free rate | ≥ 0.95 |
| Mean planning time | ≤ 200 ms |
| Joint-limit violations | 0 |
| Manipulability along executed paths | > 0.05 throughout |

That last one is unusual and deliberate. A stack can hit every other number while routing through configurations where the arm is one modelling error from being uncontrollable — and [8.1's](../08-manipulation/01-kinematics.md) exercise measured what that costs: a hundredfold drop in conditioning demands a hundredfold rise in joint speed, and no motor delivers it. Publishing the *worst conditioning along the executed path* makes that visible instead of leaving it to luck.

## Why a planar arm

Three links, two dimensions, pure NumPy — the same constraint that has kept every other project in this curriculum runnable in a browser tab and reviewable in an afternoon.

A 7-DOF spatial arm would be more impressive and would teach nothing extra at this stage: the null space is one-dimensional instead of four, the collision checking is cheaper, and every concept — redundancy, singularities, configuration-space obstacles, grasp quality — appears in full. What it loses is the wrist, and wrists are a topic rather than an idea.

## What this is not

It is not a learned grasping system. There is no reason it could not become one — the [Course IV capstone](../capstone-2/index.md) already shows how to decide whether a learned policy is safe to ship, and this pipeline would be a reasonable thing to point that machinery at. But the geometry has to be right first, and a grasp planner that works for understood reasons is a better foundation than one that works for unknown ones.
