# 8.4 Configuration-space planning: the obstacle you cannot draw

**Status:** Code verified · **Prereqs:** lessons 8.1, 5.3 · **Time:** ~2.5 h · **Verified:** 2026-08-03, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

"Move the gripper around the box" is a sentence with an obvious meaning for a mobile base and no meaning at all for an arm.

The base is a point in the space it plans in, so an obstacle in the world is an obstacle in the plan. An arm is not. The arm occupies a *region* of the world that changes shape as it moves, and the set of joint configurations that collide with a box is some curved, disconnected, generally undrawable subset of a 3- or 7-dimensional space. You cannot inflate it, you cannot look at it, and for anything above three joints you cannot even store it.

Everything in this lesson follows from that: since the obstacle cannot be represented, you sample instead.

## B. Mental model

**A configuration is a point; the arm it describes is a region.** Collision checking maps the second onto the first: `collides(q)` asks whether the region swept by the links at `q` intersects anything. That single predicate is all a sampling planner needs, and it is the only thing standing between you and a plan.

**C-space obstacles have no useful shape.** A convex box in the world becomes, in joint space, something with concavities and holes and disconnected components. Two configurations that look adjacent — the same tool pose, elbow up and elbow down — can be in different connected components with no collision-free path between them at all.

**Task-space straight lines are not safe.** Interpolating the tool along a line and solving IK at each waypoint feels natural and produces three separate hazards: the intermediate configurations may collide, the solver may jump branches ([8.2](02-inverse-kinematics.md)), and the path may cross a singularity where the required joint speed diverges ([8.1](01-kinematics.md)). Planning in joint space avoids all three by construction, because the thing being interpolated is the thing being checked.

## C. Formulation

**Collision checking for a planar arm** reduces to segment-versus-circle tests. The distance from a point $\mathbf{c}$ to segment $\overline{\mathbf{ab}}$:

$$
t^{*} = \mathrm{clamp}\!\left(\frac{(\mathbf{c}-\mathbf{a})\cdot(\mathbf{b}-\mathbf{a})}{\|\mathbf{b}-\mathbf{a}\|^{2}},\,0,\,1\right),
\qquad
d = \left\|\mathbf{c} - \left(\mathbf{a} + t^{*}(\mathbf{b}-\mathbf{a})\right)\right\|
$$

with a collision when $d < r_{\text{obstacle}} + r_{\text{link}}$. The clamp is what makes it a *segment* rather than an infinite line, and forgetting it reports collisions with obstacles that are nowhere near the arm.

**Edge checking is where planners actually fail.** A path is a sequence of configurations, and checking only the endpoints is not enough — the straight line between two collision-free configurations can pass straight through an obstacle. Subdivide by a resolution small enough that the arm cannot move further than the smallest obstacle between checks:

$$
\Delta q_{\max} \le \frac{r_{\min}}{L_{\text{total}}}
$$

Getting this wrong produces a planner that returns confident, verified, colliding paths — and the bug is invisible until hardware runs it.

**RRT in joint space** is [5.3's](../05-planning/03-rrt.md) algorithm with the metric changed: sample a random configuration, step toward it from the nearest tree node, keep the step if the *edge* is collision-free. Nothing else changes, which is the point — the algorithm never needed to know what the configuration meant.

### How coarse can the edge check be — measured on the honest cases

Edge collision-checking resolution is a straight compute-safety dial, and
measuring it took two attempts that are both worth reporting. The first
attempt sampled random configuration pairs and found that even a 0.6 rad
resolution missed *nothing* — because randomly chosen colliding edges mostly
collide at an endpoint, and endpoints are checked at any resolution. The
number that matters is conditional: among **tunnel edges**, whose endpoints
are free while the interior collides — exactly the edges an RRT actually
asks about, since it never extends from or toward a colliding configuration:

| Check resolution (rad) | Tunnel edges missed |
|---|---|
| 0.05 | 1% |
| 0.15 | 2% |
| 0.3 | 10% |
| 0.6 | **22%** |

At 0.6 rad the checker waves through more than a fifth of the edges that
sweep an arm link straight through an obstacle, and every one becomes a
planned path the physical arm cannot execute. The scaling is set by the
sweep: a joint step of \(\Delta q\) moves the farthest link point by up to
\(\Delta q\) times its lever arm (2.4 m here), so 0.3 rad sweeps up to 70 cm
between samples — wider than this scene's obstacles. The production answers
are the ones the lesson names: sample at a resolution matched to obstacle
size over lever arm, or use conservative swept-volume bounds that cannot
tunnel at any resolution. And the first attempt's lesson stands on its own:
**an average over the wrong distribution can certify a broken component**,
because the edges that matter are never a random sample of edges.

## D. From ML to robotics

The instinct to reach for a learned planner is reasonable and premature. Sampling planners are probabilistically complete, need no training data, and generalise to any obstacle configuration you hand them. What they lack is speed and path quality, which is exactly what learned samplers and neural motion planners target — they bias *where* you sample rather than replacing the collision checker.

The transferable insight: **your collision checker is the ground truth, and it is not learned.** Whatever proposes candidate motions, something verifiable must approve them. A learned planner whose output is not collision-checked is not a planner, it is a suggestion.

## E. Practice

<code-exercise src="man-l4-collision"></code-exercise>

<code-exercise src="man-l4-rrt"></code-exercise>

## F. In production

MoveIt with OMPL is the default, and the planner choice usually matters less than three things people underinvest in:

- **Collision-check speed.** It dominates planning time — typically 90% of it — so the fastest correct broad-phase you can manage buys more than a cleverer algorithm.
- **Path smoothing.** Raw RRT output is jagged and slow to execute. Shortcut smoothing (repeatedly try to replace two waypoints with a direct edge) is cheap and dramatic.
- **Planning time budgets.** Sampling planners are anytime algorithms; decide in advance what you do when the budget expires, because "keep trying" is not a behaviour a robot can exhibit while holding something.

## G. Experiment

Plan the same task twice — once by interpolating the tool along a straight line with IK at each waypoint, once with RRT in joint space — through a workspace with one obstacle between start and goal. Plot both joint trajectories and mark every configuration that collides. The task-space path looks perfect in the workspace and is riddled with collisions in joint space, which is difficult to believe until you have seen it plotted.

## H. Failure modes

- **Checking only waypoints, not edges.** The most common serious bug in a hand-rolled planner: verified paths that collide.
- **A collision-check resolution coarser than the smallest obstacle.** The same failure, with a plausible-looking parameter to hide behind.
- **Forgetting the arm can hit itself.** Self-collision is not exotic on a redundant arm, and it is the failure the null-space term in [8.2](02-inverse-kinematics.md) will happily walk you into.
- **Planning to a goal configuration nobody checked.** If IK returned a colliding configuration, the planner will spend its whole budget failing to reach it and report "no path found."
- **Assuming connectivity.** Elbow-up and elbow-down can be genuinely disconnected. "No path found" is sometimes correct.

## I. Questions

<quiz-bank src="man-l4-quiz"></quiz-bank>

## J. References

- LaValle, *Planning Algorithms*, ch. 4–5 — the definitive treatment of configuration space, freely available online.
- Kavraki et al., *Probabilistic Roadmaps* (1996) — the multi-query counterpart to RRT, and better when the environment is static.
- Şucan, Moll & Kavraki, *The Open Motion Planning Library* (2012) — OMPL, which is what you will actually run.
- Schulman et al., *TrajOpt* (2013) — optimisation-based planning, and the standard counterpoint to sampling.

## K. Graded work & portfolio extension

**Graded:** the two exercises above, plus the planning stage of [Capstone III](../capstone-3/index.md).

**Portfolio:** build the two-panel comparison from section G. The workspace panel shows two paths that both look fine; the joint-space panel shows one of them passing through a collision region. It is the clearest single argument for configuration-space planning, and it takes about forty lines once the collision checker exists.
