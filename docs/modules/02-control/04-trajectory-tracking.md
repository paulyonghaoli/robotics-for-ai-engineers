# 2.4 Trajectory tracking: pure pursuit

**Status:** Code verified · **Prereqs:** lessons 1.4, 2.2 · **Time:** ~2 h · **Verified:** 2026-08-01, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

The planner (Module 5) hands you a path — a polyline of waypoints. The robot is never *on* it: disturbances, model error, and the planner's own discretization guarantee an offset. **Path tracking** is the controller that closes this gap, and it is the literal last hop between all your autonomy software and the motors. Our capstone's driving is exactly this lesson's controller; Nav2's `RegulatedPurePursuitController` ships the same algorithm to thousands of real robots.

## B. Mental model

**Pure pursuit is how you ride a bicycle.** You don't stare at the front wheel (the nearest path point); you look *ahead* at a point on the path and continuously steer an arc toward it. Formally: pick the path point one **lookahead distance** \(L\) ahead, express it in the body frame as \((x_b, y_b)\), and command the curvature of the circle passing through you and it:

\[
\kappa = \frac{2 y_b}{L^2}, \qquad \omega = v \, \kappa
\]

The lateral offset \(y_b\) does all the work: goal dead ahead → zero curvature; goal to the left → arc left. That the *longitudinal* component drops out is the trick's elegance.

The lookahead is the controller's one real knob, and it trades exactly like a learning rate: **short L = tight tracking but oscillation-prone; long L = smooth but corner-cutting.** (The library test suite literally asserts the corner-cutting direction of this trade.)

## C. Mathematical formulation

Given pose \((x, y, \theta)\) and path \(\{p_i\}\): find the nearest vertex, walk forward to the first vertex at distance \(\ge L\), transform it into the body frame with \(T^{-1}_{world \leftarrow base}\) (lesson 1.1 machinery, verbatim), apply the curvature law. Complementary diagnostic — the **cross-track error**: the signed lateral component of the nearest path point in the body frame; it is the number you plot, the number the capstone's rubric scores, and (in the PID-based alternative follower) the error you'd feed a PID.

Failure edge cases the implementation must own: end-of-path (clamp to the final vertex), a goal at zero distance (return zero), and the fact that pure pursuit alone never *stops* — goal-arrival logic lives outside the steering law.

## D. From ML to robotics

- **Lookahead ≈ discount horizon.** Reacting to the immediate nearest point is greedy and unstable; aiming far ahead smooths behavior but ignores near-term error. Sound familiar? It's the same bias the RL discount factor trades.
- **Pure pursuit is a *policy with two parameters*** \((L, v)\) — a useful mental calibration for Module 9, where a network replacing it must beat this 30-line baseline before it earns its GPU.
- **The path is a reference distribution; tracking error is your serving-time drift.** You monitor cross-track error over a fleet the way you monitor prediction drift — same dashboards, same percentile thinking (Module 10 makes this literal).

## E. Minimal implementation

Library: [`robotics_ai/control/tracking.py`](https://github.com/paulyonghaoli/robotics-for-ai-engineers/blob/main/robotics_ai/control/tracking.py) — `pure_pursuit`, `lookahead_point`, `cross_track_error`, tested closed-loop on straight-line convergence and circle tracking.

### Practice — write and run code here

<code-exercise src="ctl-l4-pursuit"></code-exercise>

## F. Robotics-framework implementation

Nav2's `RegulatedPurePursuitController` is this plus production regulation: slow down for high curvature, for nearby obstacles, and near the goal; scale lookahead with speed (\(L = k \cdot v\), the standard refinement). Its parameters read like this lesson's vocabulary — `lookahead_dist`, `use_velocity_scaled_lookahead_dist`, `regulated_linear_scaling_min_radius`.

## G. Experiment

Track a figure-eight (two tangent circles — a curvature sign flip at the crossing) at \(L \in \{0.5, 1.0, 2.5\}\) and plot cross-track error over a lap. Short L oscillates after the flip; long L cuts both lobes. Then scale lookahead with speed and watch the compromise dominate both fixed settings. Twenty minutes, and you will never again need to memorize which way the trade goes.

## H. Failure modes

- **Corner cutting** on sharp turns with long lookahead — the goal point "tunnels" across the inside of the corner. Bound L, or regulate speed by curvature.
- **Oscillation** with short lookahead at speed — the bicycle-with-eyes-on-the-front-wheel failure.
- **Nearest-vertex aliasing on self-crossing paths** (the figure-eight's crossing): a naive nearest-point search can jump to the *other* branch. Production followers track progress along the path index monotonically.
- **No goal logic:** pure pursuit happily orbits the final waypoint forever — pair it with an arrival check and a stopping controller.

## I. Questions

1. *(Concept)* Why does the pure-pursuit law use only the *lateral* body coordinate of the goal, and what does a purely-longitudinal goal imply?
2. *(Calculation)* Goal in body frame at \((1.8, 0.6)\), \(v = 1\) m/s: compute \(\kappa\), \(\omega\), and the arc radius.
3. *(Debugging)* Your robot tracks well everywhere except immediately after passing the figure-eight crossing, where it briefly steers toward the wrong lobe. Diagnose.
4. *(System design)* Speed-scaled lookahead \(L = kv\): derive what stays constant as speed varies, and why that's the stabilizing property.

??? note "Answer sketch for Q2"
    \(L^2 = 3.6\); \(\kappa = 1.2/3.6 = 1/3\); \(\omega = 1/3\) rad/s; radius 3 m.

### Interactive quiz

<quiz-bank src="control-l4-tracking"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Coulter, *"Implementation of the Pure Pursuit Path Tracking Algorithm"* (1992, CMU) | report | introductory | The original write-up — 9 pages, entirely readable |
| [Nav2 `RegulatedPurePursuitController` docs](https://docs.nav2.org/configuration/packages/configuring-regulated-pp.html) | docs | intermediate | The production regulation layer |
| Snider, *"Automatic Steering Methods for Autonomous Automobile Path Tracking"* (2009) | report | intermediate | Pure pursuit vs Stanley vs kinematic controllers — the comparison read |

## K. Graded work & portfolio extension

**Graded:** cross-track error is a headline metric in the capstone rubric; this controller is the capstone's driver.

**Portfolio:** the figure-eight lookahead study (section G) with an animated robot + breadcrumb trail per L value — three GIFs that explain the trade better than any paragraph.
