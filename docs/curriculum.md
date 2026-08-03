# Curriculum map

Four courses, thirteen modules. **Courses I and II are complete**; Course IV is most of the way there and Course III is the gap. Today that is **55 lessons, 9 diagnostic labs, 5 autograded mini-projects, 76 in-browser exercises, 57 quiz banks and 2 capstones**, all CI-verified.

Courses I and II are the classical stack, which is well covered elsewhere — they are meant to be complete and polished rather than expanded. The weight goes into III and IV.

*Status legend:* ✅ complete · 🔨 in progress · ⬜ planned

## Course I — Foundations of Embodied AI ✅

| Module | Contents | Status |
|---|---|---|
| [**0 · From ML to Robotics**](modules/00-transition/index.md) | Embodiment, closed-loop behavior, the autonomy stack's anatomy, robotics roles, math diagnostic, notebook-to-robot lab | ✅ 5 lessons |
| [**1 · Geometry & robot motion**](modules/01-geometry/index.md) | Frames, quaternions, transform trees, twists, configuration space, frame-debugging lab | ✅ 6 lessons + [autograded project](modules/01-geometry/project-frames.md) |
| [**2 · Kinematics & control**](modules/02-control/index.md) | FK/IK, PID, Jacobians, pure pursuit, dynamics & gravity compensation, MPC, control-pathologies lab | ✅ 7 lessons + [autograded project](modules/02-control/project-control.md) |
| [**3 · State estimation**](modules/03-estimation/index.md) | Kalman, particle, and extended Kalman filters; sensor models; fusion architecture; consistency lab | ✅ 6 lessons + [autograded project](modules/03-estimation/project-localization.md) |
| [**Course I exam**](course-1-exam.md) | 16 cross-module questions, closed-book | ✅ form A |

## Course II — Robot Autonomy ✅

| Module | Contents | Status |
|---|---|---|
| [**4 · Mapping & SLAM**](modules/04-mapping/index.md) | Occupancy grids, ICP/scan matching, EKF-SLAM, pose graphs & loop closure, SLAM-failures lab | ✅ 5 lessons + [autograded project](modules/04-mapping/project-mapping.md) |
| [**5 · Planning & decision-making**](modules/05-planning/index.md) | A*, costmaps, RRT, dynamic-window local planning, planning under uncertainty, planner-pathologies lab | ✅ 6 lessons + [autograded project](modules/05-planning/project-planning.md) |
| [**6 · ROS 2**](modules/06-ros2/index.md) *(parallel track)* | Nodes, topics, services, actions, TF2, URDF, launch, bags, QoS | ⬜ planned |
| [**Capstone · autonomous 2D robot**](modules/capstone/index.md) | Scenario-evaluated navigation stack | ✅ v0–v4 live (v4 = SLAM) |
| [**Course II exam**](course-2-exam.md) | 16 cross-module questions, closed-book | ✅ form A |

**Module 6 is a parallel track, not a prerequisite.** Everything through the capstone runs in pure Python — you never need a ROS installation to complete Courses I–II. Take ROS 2 whenever you want the industrial integration skills (and note from the [frontier research](frontier.md) that it's mandatory at Agility, Boston Dynamics, and Amazon, but conspicuously absent from frontier VLA-lab job postings).

## Course III — Perception & Embodied Learning 🔨

| Module | Contents | Status |
|---|---|---|
| [**7 · Robotic perception**](modules/07-perception/index.md) | Camera models, stereo & depth, point clouds, registration, 3D detection, BEV, fusion | 🔨 2 lessons + [autograded project](modules/07-perception/project-perception.md) |
| 8 · Manipulation | Manipulator kinematics, IK, grasp synthesis, configuration-space planning, visual servoing | ⬜ planned |
| [**9 · Robot learning & embodied AI**](modules/09-robot-learning/index.md) | Imitation (ACT, diffusion policy), the data engine & human-in-the-loop, RL, sim-to-real, world models, VLA evaluation | ✅ 7 lessons + lab |
| **Capstone III · see it, grasp it** | A planar manipulator with a depth sensor: perceive, synthesize a grasp, plan in configuration space, execute under Jacobian control | ⬜ planned |

Capstone III is deliberately a **second robot**. Everything so far has been one differential-drive base, and a portfolio with two distinct embodiments argues something a fifth navigation stack cannot.

## Course IV — Production Robot Systems 🔨

| Module | Contents | Status |
|---|---|---|
| [**10 · Evaluation & data systems**](modules/10-evaluation/index.md) | Statistical rigor, scenario suites, regression from logs, dataset lifecycle, drift monitoring | ✅ 7 lessons + lab |
| [**11 · Deployment, fleet & safety**](modules/11-deployment/index.md) | Latency budgets, edge inference, rollout/rollback, fleet telemetry, safety cases, incident forensics | ✅ 6 lessons + lab |
| 12 · Robot data infrastructure | Logging schemas, episode storage, indexing and search over fleet data, replay determinism, dataset lineage | ⬜ planned |
| 13 · Systems performance | The **C++ track** (ports with parity checks against the Python references), the GPU performance model, real-time constraints | ⬜ planned |
| [**Capstone IV · ship a learned policy**](modules/capstone-2/index.md) | Build the infrastructure that decides whether a policy is safe to ship | 🔨 stages 0–1 live |

Modules 10 and 11 were split from a single "production robotics" module because [the 2026 frontier research](frontier.md) ranks evaluation and data infrastructure as the **highest-leverage area** for this curriculum's audience — and because the field is in a documented evaluation crisis. They were written early, out of numerical order, for the same reason.

**Module 13 exists because C++ is the largest single gap here.** Production robotics is overwhelmingly C++, and for an ML engineer transitioning in, not writing it closes a large fraction of postings. It is built as *ports with parity checks* — re-implement components that already have a verified Python reference, and prove numerical equivalence plus a latency budget Python cannot meet — rather than as a language tutorial. Edge computing is already covered in [11.1](modules/11-deployment/01-latency-budgets.md) and [11.2](modules/11-deployment/02-edge-inference.md); GPU work here is the performance model (bandwidth, launch overhead, transfers, batch-1), not kernel authoring.

## The capstone

### Course II — [autonomous 2D mobile robot](modules/capstone/index.md)

A differential-drive robot navigating randomized obstacle worlds, scored by a published rubric (success rate, collision-free rate, path ratio vs A*-optimal, p95 control latency, localization RMSE). Each version removes something the previous one was allowed to assume:

- **v0** — A* + inflation + pure pursuit on a known map with a noisy pose sensor
- **v1** — particle-filter lidar localization replaces the pose sensor (6–11 cm RMSE)
- **v2** — the map itself is unknown, built online from scans while driving
- **v3** — six moving obstacles that are not in the map (18/18 at six movers)
- **v4** — **SLAM**: no map *and* no pose sensor after step 0 (18/24, 0.39 m drift, on its own published envelope)

The [capstone engineering log](capstone-log.md) documents thirteen real debugging campaigns from building these.

### Course IV — ship a learned policy 🔨

Course IV's capstone inverts the question. You don't build a better robot; you build the **infrastructure that decides whether a robot is safe to ship** — which is what Modules 9, 10 and 11 are for, and what [the frontier research](frontier.md) identifies as the highest-leverage skill for this curriculum's audience.

The system under test is the navigation capstone you already have. See [its brief](modules/capstone-2/index.md).

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
