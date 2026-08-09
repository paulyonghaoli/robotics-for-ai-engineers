# 1.5 Configuration space: where planning actually happens

**Status:** Code verified · **Prereqs:** lessons 1.1, 1.4 · **Time:** ~2 h · **Verified:** 2026-08-01, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Path planning looks like it happens in the world. It does not. It happens in
**configuration space**, and this is the single idea that makes every planning
algorithm in Module 5 stop looking arbitrary.

Here is the problem it solves. A robot is not a point — it is a shape, and
whether it collides depends on its position *and* its orientation *and*, for
an arm, every joint angle. Asking "can this robot get from A to B" means
asking, for every pose along the way, whether a complicated shape overlaps
other complicated shapes. That is a horrible question to search over.

Configuration space makes it a tractable one, by a change of representation
that is worth calling a trick.

!!! note "Terms defined here"

    **Configuration** — the complete set of numbers needed to fully pose the
    robot. Written \(q\).

    **Configuration space** (**C-space**, \(\mathcal{C}\)) — the space of all
    possible configurations. A circular vacuum robot's is \((x, y)\); a car's
    is \((x, y, \theta)\); a 7-joint arm's is 7-dimensional joint space.

    **Workspace** — ordinary physical space, where the obstacles actually
    are. Not the same thing as C-space, and confusing the two is the source of
    several failure modes below.

    **DOF (degrees of freedom)** — the number of independent numbers needed
    to specify a configuration. Usually, but not always, equal to
    \(\dim \mathcal{C}\).

    **Holonomic / nonholonomic** — a holonomic robot can move instantly in
    any direction of its C-space. A car cannot slide sideways, so it is
    **nonholonomic**: it has fewer controls than configuration dimensions.

## B. Mental model

**The magic trick: the robot becomes a point.**

All the geometry of the robot's body is absorbed into the shape of the
obstacles. A disk robot of radius \(r\) navigating among walls is *exactly
equivalent* to a **point** robot navigating among those same walls **inflated
by \(r\)**.

That equivalence is worth checking rather than accepting. The disk collides
with an obstacle precisely when its centre comes within \(r\) of that
obstacle. So "the disk collides" and "the centre point is inside the
\(r\)-inflated obstacle" are the same statement. Nothing was approximated.

This is why occupancy grids in Nav2 have an **inflation layer**. It is not a
safety margin bolted on — it is the C-space transformation, shipped.

For an arm the same trick applies but the result is stranger. A chair sitting
in the workspace becomes a curved blob in joint-angle space: the set of every
joint combination that would put some part of the arm inside the chair. That
blob has no resemblance to a chair. It is, however, exactly the forbidden
region, and a planner searching joint space only needs to avoid it.

### Topology matters

A revolute joint's angle lives on a **circle**, not a line. \(-179°\) and
\(+179°\) are two degrees apart, not 358.

So a two-link arm's configuration space is not a square — it is a **torus**.
Walk off the right edge of the \((\theta_1, \theta_2)\) square and you re-enter
on the left; walk off the top and you re-enter at the bottom.

Planners that forget this take absurd long-way-around paths through joint
space. If that sounds familiar, it should: it is the `wrap_angle` bug from
lesson 1.1, wearing planning clothes. The same mistake, one level up.

## C. Mathematical formulation

Let \(A(q)\) be the set of workspace points the robot's body occupies at
configuration \(q\), and \(\mathcal{O}\) the workspace obstacles. Then

\[
\mathcal{C}_{obs} = \{ q \in \mathcal{C} \mid A(q) \cap \mathcal{O} \neq \emptyset \},
\qquad
\mathcal{C}_{free} = \mathcal{C} \setminus \mathcal{C}_{obs}
\]

and a path is a continuous map \(\tau : [0,1] \to \mathcal{C}_{free}\). That
is the whole formalism: planning is finding a continuous curve through the
free set.

For a disk robot, \(\mathcal{C}_{obs}\) is exactly \(\mathcal{O}\) **dilated**
by the robot's radius — formally a Minkowski sum. This is the section B trick
written precisely.

**Dimensions**, which is where the difficulty lives:

| Robot | \(\dim \mathcal{C}\) |
|---|---|
| Disk robot on a plane | 2 |
| Planar rigid body (a car) | 3, i.e. \(SE(2)\) |
| \(n\)-joint arm | \(n\) |
| Mobile base + 6-joint arm + gripper | 10 |

And now the crucial practical fact: **explicitly constructing
\(\mathcal{C}_{obs}\) is intractable beyond two or three dimensions.** Grid a
7-dimensional joint space at 1° resolution and you have \(360^7 \approx
10^{17.8}\) cells. You cannot build it, store it, or search it.

So planners do not build it. They **sample** configurations and
collision-check them individually. That single constraint is the entire reason
sampling-based planning — RRT, PRM, and everything in Module 5 — exists in the
form it does.

## D. From ML to robotics

**C-space is a feature space in which the problem becomes easy.** Exactly like
a kernel trick: the transformation (robot shrinks to a point, obstacles absorb
its shape) turns a hard question — "does this complicated shape at this pose
overlap those complicated shapes?" — into a trivial one — "is this point in
the forbidden set?"

**The curse of dimensionality is literal here**, and the numbers above make it
concrete. This is the same combinatorial explosion that pushed machine
learning toward sampling and stochastic methods, and it pushed robotics toward
sampling-based planners for the same reason. Same disease, same cure,
discovered independently.

**\(\mathcal{C}_{free}\) membership is a binary classifier you query, not a
dataset you enumerate.** Collision checkers are cheap-ish oracles; planners are
active-learning loops that decide where to query next. If you have built an
active-learning system, RRT will feel structurally familiar — it is choosing
informative samples under a query budget.

## E. Minimal implementation

A two-link arm and its C-space obstacle map, by brute-force sampling:

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

Evaluate `in_collision` over a \(90 \times 90\) grid on \([-\pi, \pi]^2\) and
you have the C-space obstacle map. **Do this.** It is a picture worth the
whole lesson: two innocuous circles in the workspace produce a pair of curved,
connected bands in joint space that look nothing like circles, and the shape
of the free corridors between them is the shape of the planning problem.

Note the `n=20`: the links are checked at twenty sample points each. A thin
obstacle can slip between samples, which is failure mode 4.

### Practice — write and run code here

<code-exercise src="geo-l5-cspace"></code-exercise>

## F. Robotics-framework implementation

**Nav2's costmap inflation layer** is section C shipped as product. Obstacles
from the occupancy grid are dilated by the robot's footprint radius, plus a
decaying cost skirt that makes the planner prefer the middle of corridors, so
the global planner can treat the robot as a point.

**MoveIt 2 never builds \(\mathcal{C}_{obs}\) at all.** It wraps a collision
checker (FCL) and lets sampling-based planners (OMPL) query it — exactly the
oracle pattern from section D, because for a 7-DOF arm there is no
alternative.

## G. Experiment — watch the corridor pinch shut

Build the C-space map for two workspace obstacles, then vary **the robot**
rather than the world.

Increase the collision margin — fattening the links — from 0 to 0.2 m in
steps, re-rendering the map each time. Watch \(\mathcal{C}_{obs}\) grow, and
watch the free corridor between the two obstacle bands narrow and then **pinch
off entirely**. At that moment the planning problem becomes infeasible, and
not one workspace obstacle has moved.

Then put the margin back and move one obstacle 0.3 m. Watch a topologically
*new* corridor open where there was none.

This intuition — obstacle geometry on one side, C-space topology on the
other — is what planning engineers actually carry in their heads, and it is
almost impossible to acquire from equations. Twenty minutes with this plot is
worth a chapter.

## H. Failure modes

- **Planning with the wrong footprint.** An inflation radius smaller than the
  true robot produces "valid" plans that scrape walls. Larger, and doorways
  the robot physically fits through become impassable in C-space. Both are
  common; the second gets reported as "the planner is broken", the first as
  "the robot is careless".
- **Ignoring joint topology.** Treating \(\theta \in [-\pi, \pi]\) as an
  interval rather than a circle makes configurations either side of \(\pm\pi\)
  look maximally far apart. Planners detour absurdly or oscillate.
- **Workspace-distance intuition applied in C-space.** Two arm poses with the
  hands nearly touching can be enormously far apart in joint space — elbow-up
  versus elbow-down. Interpolating between them sweeps the whole arm through
  the workspace, and possibly through a person. This one is genuinely
  dangerous, not merely wrong.
- **Sparse collision sampling along links.** The `n=20` above. Thin obstacles
  slip between sample points and the checker reports free space that is not.
  Production checkers use swept volumes or conservative padding.

## I. Questions

1. *(Concept)* Why does inflating obstacles by the robot radius let us plan
   for a point? What breaks for a *non-circular* robot?
2. *(Calculation)* How many DOF has a mobile manipulator: differential-drive
   base + 6-joint arm + 1-DOF gripper? What is \(\dim \mathcal{C}\)?
3. *(Debugging)* An arm planner produces paths where the elbow swings wildly
   between adjacent waypoints although the hand barely moves. What is the
   likely metric bug?
4. *(System design)* Your warehouse robot is rectangular (1.2 × 0.6 m).
   Circular inflation by which radius is safe? What do you lose, and what
   would fix it?

??? note "Answer sketches"
    **1.** For a disk robot the occupied set \(A(q) = \mathrm{disk}(q, r)\)
    merely *translates* with \(q\) — it does not change shape — so it
    intersects an obstacle exactly when \(q\) lies within \(r\) of that
    obstacle. \(\mathcal{C}_{obs}\) is therefore precisely \(\mathcal{O}\)
    dilated by \(r\), and the robot collapses to a point with nothing
    approximated. For a non-circular robot \(A(q)\) also depends on
    \(\theta\), so **no single 2D dilation is correct**: inflating by the
    circumscribed radius is conservative and blocks gaps the robot would fit
    through, inflating by the inscribed radius admits real collisions, and the
    honest fix is to keep \(\theta\) as a dimension and check the true
    footprint.

    **2.** The differential-drive base contributes \(SE(2)\), i.e. 3
    configuration dimensions \((x, y, \theta)\); the arm adds 6 and the
    gripper 1, so \(\dim \mathcal{C} = 3 + 6 + 1 = 10\). Note that "DOF" is
    ambiguous here: the base is **nonholonomic**, so it has only 2 controls
    \((v_x, \omega)\) — 9 independent velocity inputs against a
    10-dimensional configuration space. That mismatch is exactly why the
    base's motion is planned with the twist model of lesson 1.4 rather than
    as free motion in \((x, y, \theta)\).

    **3.** Distance is being measured in the **workspace** — end-effector
    position or pose — instead of in C-space. An elbow-up and an elbow-down
    configuration whose hands nearly coincide then score as neighbours despite
    being far apart in joint space. Fix: use a joint-space metric for both
    edge cost and interpolation — a weighted \(L_2\) over joint angles, with
    each difference wrapped to \((-\pi, \pi]\) so the torus topology is
    respected.

    **4.** Safe is the **circumscribed** radius,
    \(\sqrt{0.6^2 + 0.3^2} \approx 0.67\) m — half the diagonal. What you lose
    is every narrow aisle the robot could traverse lengthwise, which becomes
    blocked in C-space although the robot fits. The fix is to plan in
    \((x, y, \theta)\) with the true footprint — Nav2's footprint-based
    collision checking — paying one extra dimension of search for the aisles
    back.

### Interactive quiz

<quiz-bank src="geometry-l5-cspace"></quiz-bank>

## J. Annotated references

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| LaValle, *Planning Algorithms*, ch. 4 | book | intermediate | The canonical C-space chapter, free online from the author |
| Lynch & Park, *Modern Robotics*, ch. 2 | book | introductory | C-space, DOF counting and topology, with a gentler on-ramp than LaValle |
| [Nav2 costmap concepts](https://docs.nav2.org/concepts/index.html) | docs | introductory | Inflation layers as shipped engineering, including the cost skirt this lesson only mentions |

## K. Graded work and portfolio extension

**Graded:** C-space collision checking returns as the core of the Module 5
planning project.

**Portfolio:** render the two-link arm's C-space map side by side with its
workspace — two subplots with a shared cursor, so hovering a configuration
shows the corresponding arm pose. As an interactive matplotlib figure or a
small web demo this is arguably the single most explanatory robotics visual
you can put in front of an interviewer, because it makes a concept that takes
ten minutes to explain obvious in about four seconds.
