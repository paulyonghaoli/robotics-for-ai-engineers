# Capstone III — See It, Grasp It

A planar arm with a depth sensor. Perceive the objects, choose a grasp, plan
in configuration space, execute under damped IK.

**This is an assignment.** Start in [`student_stack.py`](student_stack.py).

```bash
cd projects/capstone_grasp
python -m eval run --episodes 12 --stack student_stack
```

That command is the autograder.

## The rubric

| Metric | Bar |
|---|---|
| `grasp_success_rate` | ≥ 0.80 |
| `collision_free_rate` | ≥ 0.95 |
| `joint_limit_violations` | 0 |
| `mean_plan_ms` | ≤ 200 |
| `min_manipulability` | ≥ 0.05 |

The reference stack scores **30/30 with zero collisions, 17 ms mean planning
time, and worst-case manipulability 0.164** — so the bar is achievable and
the harness is honest.

That last metric is the unusual one. A stack can satisfy every other number
while routing through configurations where the arm is one modelling error
from uncontrollable. [Lesson 8.1](../../docs/modules/08-manipulation/01-kinematics.md)
measured the cost: a hundredfold drop in conditioning demands a hundredfold
rise in joint speed, which no motor delivers. Reporting the *worst*
conditioning along the executed path makes it visible rather than lucky.

## The four stages

| Stage | Lesson |
|---|---|
| Perceive — remove the table, cluster, fit circles | [7.3](../../docs/modules/07-perception/03-point-clouds.md) |
| Grasp — antipodal candidates, filtered by the gripper stroke | [8.3](../../docs/modules/08-manipulation/03-grasping.md) |
| Plan — RRT in configuration space, edges checked | [8.4](../../docs/modules/08-manipulation/04-cspace-planning.md) |
| Execute — warm-started damped IK | [8.2](../../docs/modules/08-manipulation/02-inverse-kinematics.md) |

## The one that will catch you

**Remove the table before clustering.** It is tempting to treat ground removal
as tidying-up and skip it. The table is *continuous*, so its returns bridge
the gaps between objects; single-link clustering then merges an object with
the floor either side of it, the circle fit sees an arc plus a straight line
and rejects the group, and the object silently vanishes from perception.

This is not hypothetical — it is what the reference implementation did on its
first run. Perception reported 3 of 4 objects, the missing one was the target
in half the scenes, and the symptom was "no reachable grasp" with no
indication that anything perceptual was wrong. Adding one line of ground
removal took the pipeline from 2/8 to 12/12.

## Layout

```
world.py           the arm, the scene, the depth sensor, the collision predicates
eval/              the autograder — python -m eval run --stack <name>
student_stack.py   START HERE
solutions/         the reference pipeline
```

## Commands

```bash
python -m eval run --episodes 12 --stack student_stack     # grade yours
python -m eval run --episodes 30 --stack reference_stack   # the reference
```
