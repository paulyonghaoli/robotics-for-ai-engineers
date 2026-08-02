# 1.5 Configuration space: where planning actually happens

**Status:** Code verified · **Prereqs:** lessons 1.1, 1.4 · **Time:** ~2 h · **Verified:** 2026-08-01, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Path planning looks like it happens in the world — but it doesn't. It happens in **configuration space** (C-space): the space of every variable needed to fully pose the robot. A circular vacuum robot plans in \((x, y)\); a car in \((x, y, \theta)\); a 7-DOF arm in a 7-dimensional joint space. Obstacles that look simple in the workspace become strange-shaped forbidden regions in C-space, and *every planner in Module 5 — A\*, RRT, trajectory optimization — searches C-space, not the world*. Misunderstand this and planning algorithms seem arbitrary; understand it and they become inevitable.

## B. Mental model

The magic trick of C-space: **the robot becomes a point.** All the geometry of the robot's body is absorbed into the shape of the obstacles. A disk robot of radius \(r\) among walls is *equivalent* to a point robot among walls **inflated** by \(r\) — this is why occupancy grids in Nav2 have an "inflation layer." For an arm, a chair in the workspace becomes a curved blob in joint-angle space: every joint combination that would intersect the chair.

Topology matters too. A revolute joint's angle lives on a **circle**, not a line — so a 2-link arm's C-space is a **torus**: walk off the right edge of the \((\theta_1, \theta_2)\) square and you re-enter on the left. Planners that forget this take absurd long-way-around paths through joint space (the wrap_angle bug, now in planning clothes).

## C. Mathematical formulation

Configuration space \(\mathcal{C}\); obstacle region and free space:

\[
\mathcal{C}_{obs} = \{ q \in \mathcal{C} \mid A(q) \cap \mathcal{O} \neq \emptyset \},
\qquad
\mathcal{C}_{free} = \mathcal{C} \setminus \mathcal{C}_{obs}
\]

where \(A(q)\) is the set of workspace points the robot's body occupies at configuration \(q\). A path is a continuous map \(\tau : [0,1] \to \mathcal{C}_{free}\). For a disk robot among obstacles, \(\mathcal{C}_{obs}\) is exactly the obstacles **dilated** by the robot's radius (a Minkowski sum). Dimensions: a planar rigid body has \(\dim \mathcal{C} = 3\) (\(SE(2)\)); an \(n\)-joint arm has \(\dim \mathcal{C} = n\); explicit geometric construction of \(\mathcal{C}_{obs}\) is intractable beyond a few dimensions — planners instead *sample* configurations and collision-check them, which is the entire reason sampling-based planning (RRT, PRM) exists.

## D. From ML to robotics

- **C-space is a feature space** where the problem becomes linear-ish: like a kernel trick, the transformation (robot shrinks to a point, obstacles absorb its shape) makes a hard question ("does this pose collide?") a simple one ("is this point in the forbidden set?").
- **The curse of dimensionality is literal here.** Gridding C-space at 1° resolution costs \(360^n\) cells for an \(n\)-joint arm — the exact combinatorial explosion that pushed ML toward sampling and pushed robotics toward sampling-based planners. Same disease, same cure.
- **\(\mathcal{C}_{free}\) membership is a binary classifier** you query, not a dataset you enumerate: collision checkers are cheap-ish oracles, and planners are active-learning loops over them.

## E. Minimal implementation

A 2-link arm and its C-space obstacle map by brute-force sampling:

```python
import numpy as np

def arm_points(theta1, theta2, l1=1.0, l2=0.8, n=20):
    """Sample points along both links of a planar 2-link arm."""
    elbow = np.array([l1 * np.cos(theta1), l1 * np.sin(theta1)])
    hand = elbow + [l2 * np.cos(theta1 + theta2), l2 * np.sin(theta1 + theta2)]
    t = np.linspace(0, 1, n)[:, None]
    return np.vstack([t * elbow, elbow + t * (hand - elbow)])

def in_collision(theta1, theta2, circles):
    """circles: list of (cx, cy, r) workspace obstacles."""
    pts = arm_points(theta1, theta2)
    return any(np.min(np.hypot(pts[:, 0] - cx, pts[:, 1] - cy)) < r
               for cx, cy, r in circles)
```

Evaluate `in_collision` on a \(90 \times 90\) grid over \([-\pi, \pi]^2\) and you have the C-space obstacle map — a picture worth the whole lesson.

### Practice — write and run code here

<code-exercise src="geo-l5-cspace"></code-exercise>

## F. Robotics-framework implementation

Nav2's **costmap inflation layer** is section C shipped as product: obstacles from the occupancy grid are dilated by the robot's footprint radius (plus a decaying cost skirt) so the global planner can treat the robot as a point. For arms, MoveIt 2 never builds \(\mathcal{C}_{obs}\) explicitly — it wraps a collision checker (FCL) and lets sampling-based planners (OMPL) query it, exactly the oracle pattern from section D.

## G. Experiment

Build the C-space map for two workspace obstacles and vary the *robot*: fatten the links (collision margin from 0 to 0.2 m) and watch \(\mathcal{C}_{obs}\) grow until free-space corridors pinch off — the planning problem becomes infeasible without a single workspace obstacle moving. Then move one obstacle 0.3 m and watch a topologically new corridor open. This "obstacle geometry ↔ C-space topology" intuition is what planning engineers actually carry in their heads.

## H. Failure modes

- **Planning with the wrong footprint:** an inflation radius smaller than the true robot means "valid" plans that scrape walls; larger means doorways become impassable in C-space while physically fine.
- **Ignoring joint topology:** treating \(\theta \in [-\pi, \pi]\) as an interval instead of a circle makes configurations near \(\pm\pi\) look maximally far apart; planners detour absurdly or oscillate.
- **Workspace-distance intuition in C-space:** two arm poses with hands nearly touching can be far apart in joint space (elbow-up vs elbow-down) — interpolating between them sweeps the arm through the workspace, and possibly through a person.
- **Sparse collision sampling along links** (the `n=20` above): thin obstacles can slip between sample points. Production checkers use swept volumes or conservative padding.

## I. Questions

1. *(Concept)* Why does inflating obstacles by the robot radius let us plan for a point? What breaks for a *non-circular* robot?
2. *(Calculation)* How many DOF has a mobile manipulator: differential-drive base + 6-joint arm + 1-DOF gripper? What is \(\dim \mathcal{C}\)?
3. *(Debugging)* An arm planner produces paths where the elbow swings wildly between adjacent waypoints although the hand barely moves. What's the likely metric bug?
4. *(System design)* Your warehouse robot is rectangular (1.2 × 0.6 m). Circular inflation by which radius is safe? What do you lose, and what would fix it?

??? note "Answer sketch for Q4"
    Safe: circumscribed radius \(\sqrt{0.6^2+0.3^2} \approx 0.67\) m — but narrow aisles the robot could pass lengthwise become blocked in C-space. Fix: plan in \((x, y, \theta)\) with the true footprint (Nav2's footprint-based collision checking), paying the extra dimension.

### Interactive quiz

<quiz-bank src="geometry-l5-cspace"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| LaValle, *Planning Algorithms*, ch. 4 | book | intermediate | The C-space chapter — free online, canonical |
| Lynch & Park, *Modern Robotics*, ch. 2 | book | introductory | C-space, DOF counting, topology — gentler entry |
| [Nav2 costmap concepts](https://docs.nav2.org/concepts/index.html) | docs | introductory | Inflation layers as shipped engineering |

## K. Graded work & portfolio extension

**Graded:** C-space collision checking returns as the core of the Module 5 planning project.

**Portfolio:** render the 2-link arm's C-space map side-by-side with its workspace (two subplots, shared cursor: hover a configuration, see the arm pose). As an interactive matplotlib or small web demo, it is the single most explanatory robotics visual you can put in front of an interviewer.
