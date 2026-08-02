# Curriculum map

Three courses, eleven modules. **Courses I and II's classical stack are complete and live** — 31 lessons, 3 graded projects, and an autonomous-navigation capstone you can run today. Course III is in development.

*Status legend:* ✅ complete · 🔨 in progress · ⬜ planned

## Course I — Foundations of Embodied AI ✅

| Module | Contents | Status |
|---|---|---|
| [**0 · From ML to Robotics**](modules/00-transition/index.md) | Embodiment, closed-loop behavior, the autonomy stack's anatomy, robotics roles, math diagnostic | ✅ 4 lessons |
| [**1 · Geometry & robot motion**](modules/01-geometry/index.md) | Frames, quaternions, transform trees, twists, configuration space, frame-debugging lab | ✅ 6 lessons + [autograded project](modules/01-geometry/project-frames.md) |
| [**2 · Kinematics & control**](modules/02-control/index.md) | FK/IK, PID, Jacobians, pure pursuit, dynamics & gravity compensation, MPC | ✅ 6 lessons |
| [**3 · State estimation**](modules/03-estimation/index.md) | Kalman, particle, and extended Kalman filters; sensor models; fusion architecture; consistency lab | ✅ 6 lessons + [autograded project](modules/03-estimation/project-localization.md) |
| [**Course I exam**](course-1-exam.md) | 16 cross-module questions, closed-book | ✅ form A |

## Course II — Robot Autonomy 🔨

| Module | Contents | Status |
|---|---|---|
| [**4 · Mapping & SLAM**](modules/04-mapping/index.md) | Occupancy grids, ICP/scan matching, EKF-SLAM, pose graphs & loop closure | ✅ 4 lessons (visual odometry lands with Module 7) |
| [**5 · Planning & decision-making**](modules/05-planning/index.md) | A*, costmaps, RRT, dynamic-window local planning, planning under uncertainty | ✅ 5 lessons |
| [**6 · ROS 2**](modules/06-ros2/index.md) *(parallel track)* | Nodes, topics, services, actions, TF2, URDF, launch, bags, QoS | ⬜ planned |
| [**Capstone · autonomous 2D robot**](modules/capstone/index.md) | Scenario-evaluated navigation stack | ✅ v0–v3 live, v4 planned |
| [**Course II exam**](course-2-exam.md) | 16 cross-module questions, closed-book | ✅ form A |

**Module 6 is a parallel track, not a prerequisite.** Everything through the capstone runs in pure Python — you never need a ROS installation to complete Courses I–II. Take ROS 2 whenever you want the industrial integration skills (and note from the [frontier research](frontier.md) that it's mandatory at Agility, Boston Dynamics, and Amazon, but conspicuously absent from frontier VLA-lab job postings).

## Course III — AI Robotics Systems ⬜

| Module | Contents | Status |
|---|---|---|
| 7 · Robotic perception | Camera models, stereo, point clouds, 3D detection, BEV, fusion, tactile/force survey | ⬜ planned |
| 8 · Manipulation | Manipulator kinematics, grasping, motion planning, visual servoing | ⬜ planned |
| 9 · Robot learning & embodied AI | Imitation (ACT, diffusion policy), the data engine & human-in-the-loop, RL, sim-to-real, world models, VLA evaluation | ⬜ planned |
| [**10 · Evaluation & data systems**](modules/10-evaluation/index.md) | Statistical rigor, scenario suites, regression from logs, dataset lifecycle, drift monitoring | 🔨 first lesson live |
| 11 · Deployment, fleet & safety | Latency budgets, edge inference, rollout/rollback, fleet telemetry, safety cases, incident forensics | ⬜ planned |

Modules 10 and 11 were split from a single "production robotics" module because [the 2026 frontier research](frontier.md) ranks evaluation and data infrastructure as the **highest-leverage area** for this curriculum's audience — and because the field is in a documented evaluation crisis. Module 10 is deliberately being written early, out of numerical order.

## The capstone

**[Autonomous 2D mobile robot](modules/capstone/index.md)** — a differential-drive robot navigating randomized obstacle worlds, scored by a published rubric (success rate, collision-free rate, path ratio vs A*-optimal, p95 control latency, localization RMSE). Three stacks pass it today:

- **v0** — A* + inflation + pure pursuit on a known map with a noisy pose sensor
- **v1** — particle-filter lidar localization replaces the pose sensor (6–11 cm RMSE)
- **v2** — the map itself is unknown, built online from scans while driving
- **v3** *(planned)* — dynamic obstacles, SLAM, ROS 2 packaging

The [capstone engineering log](capstone-log.md) documents six real debugging campaigns from building these.

## Role-oriented paths (planned)

- **ML Engineer Transition Path** *(default)*: Modules 0 → 1 → 3 → 2 → 5 → capstone → 7 → 9
- **Robotics Perception Engineer**: 1 → 3 → 7 → 4 → 10
- **Autonomy Engineer**: 1 → 3 → 4 → 5 → 2 → capstone → 6
- **Robot Learning Engineer**: 1 → 2 → 3 → 9 → 10 (simulation and evaluation heavy)
- **Robotics Platform Engineer**: 6 → 10 → 11 (with 1–5 as literacy)

## Lesson format

Every lesson follows the same schema, so you always know where you are:

1. **Why this matters** — where the concept appears in a real robot
2. **Mental model** — intuition before equations
3. **Mathematical formulation**
4. **From ML to robotics** — the bridge to what you already know
5. **Minimal implementation** — no frameworks
6. **Framework implementation** — ROS 2 / simulator / production library
7. **Experiment** — change parameters, observe behavior
8. **Failure modes** — how it breaks on real systems
9. **Questions** — concept, calculation, debugging, system design
10. **References** — annotated, with reading guidance
11. **Portfolio extension** — turn the lab into a presentable project

Most modules also include a **diagnostic lab** — [frame debugging](modules/01-geometry/06-lab-frame-debugging.md), [catching a lying filter](modules/03-estimation/06-consistency-lab.md) — where you're handed working-looking code containing a real bug and must find it from the symptom.
