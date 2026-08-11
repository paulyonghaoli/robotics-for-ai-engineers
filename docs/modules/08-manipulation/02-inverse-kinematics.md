# 8.2 Inverse kinematics and the null space you get for free

**Status:** Code verified · **Prereqs:** lesson 8.1 · **Time:** ~2.5 h · **Verified:** 2026-08-03, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Forward kinematics is a function. Inverse kinematics is a *relation*, and most of the engineering is in coping with that difference.

A target pose may have no solution (outside the workspace), exactly one (at a singularity, which is the worst place to have one), two (elbow up or elbow down), or infinitely many (a redundant arm). Any code that returns "the" answer has silently made a choice, and the moment that choice changes mid-trajectory the arm flips configuration — a fast, loud, occasionally destructive event that appears nowhere in the planner's output.

The good news is that redundancy, once you stop treating it as an inconvenience, is the most useful thing an arm has. It lets you satisfy the task *and* something else at the same time, for free.

## B. Mental model

**Two families of solver.**

| | Analytic | Iterative (Jacobian-based) |
|---|---|---|
| Speed | microseconds | milliseconds |
| Completeness | gives you *all* solutions | gives you the nearest one |
| Effort | a derivation per robot | one implementation for any chain |
| Behaviour near singularities | exact, and tells you when there is no solution | needs damping or it explodes |

Production stacks use analytic solutions where a closed form exists (most 6-DOF industrial arms, by design) and iterative ones everywhere else. The iterative version is the one worth writing yourself, because it is the same damped-least-squares step from the [control mini-project](../02-control/project-control.md) applied repeatedly.

**The null space is a subspace of joint velocities that do nothing.** For a redundant arm, $J$ has more columns than rows, so there are non-zero $\dot{q}$ with $J\dot{q} = 0$ — motions that leave the tool exactly where it is. Project any secondary objective into that subspace and you pursue it without disturbing the task at all. Not approximately: exactly, to the precision of your linearisation.

That is how a redundant arm avoids an obstacle with its elbow while the gripper holds a glass steady.

## C. Formulation

**Damped least squares** (Levenberg–Marquardt applied to IK):

$$
\Delta\mathbf{q} = J^\top\left(JJ^\top + \lambda^2 I\right)^{-1}\mathbf{e},
\qquad \mathbf{e} = \mathbf{p}_{target} - \mathbf{p}(\mathbf{q})
$$

As $\lambda \to 0$ this is the pseudo-inverse — fastest convergence, and unbounded near a singularity. As $\lambda$ grows it becomes gradient descent — slow, and stable everywhere. The damping is a deliberate trade of accuracy for not commanding 200 rad/s, and [8.1's](01-kinematics.md) exercise measured exactly what you are buying.

**Null-space projection** adds a secondary objective without touching the first:

$$
\Delta\mathbf{q} = \underbrace{J^{+}\mathbf{e}}_{\text{task}} \;+\; \underbrace{\left(I - J^{+}J\right)\mathbf{z}}_{\text{free motion}}
$$

$\left(I - J^{+}J\right)$ is the projector onto the null space, so the second term produces **no tool motion whatsoever**. `z` is whatever you want: the gradient of distance-from-joint-limits, of distance-from-an-obstacle, or of manipulability itself.

A common and effective choice is joint-limit avoidance, pushing each joint toward the middle of its range:

$$
z_i = -k\,\frac{q_i - \bar{q}_i}{(q_i^{max} - q_i^{min})^2}
$$

### The null-space "invariant" drifts — measured, then fixed for free

The null-space projector \(N = I - J^{+}J\) promises that motion through it
leaves the tip fixed, and the promise is exact only for infinitesimal steps.
Descending the joint-limit cost from a near-limits posture down to the same
cost level, at four step sizes:

| Step size × iterations | Tip drift |
|---|---|
| 0.2 × 50 | **133.4 mm** |
| 0.05 × 200 | 33.2 mm |
| 0.01 × 1000 | 6.6 mm |
| 0.002 × 5000 | 1.3 mm |
| 0.05 × 200, **plus task re-correction each step** | **0.0000 mm** |

The drift is linear in step size — each finite step incurs an
\(O(\|\Delta q\|^2)\) task-space error because \(J\) changed over the step,
and the errors accumulate — so "the null space doesn't move the tip" is true
in the limit and off by *thirteen centimetres* at a step size someone would
actually use. The last row is the production answer, and it costs one line:
after each null-space step, close the loop with a tiny damped IK correction
back to the held pose. The secondary objective then runs at whatever step
size converges fastest while the task error stays at machine precision,
because the correction consumes exactly the drift the projector leaked. Open
loop, invariants decay; closed loop, they hold — which is this curriculum's
oldest lesson, reappearing inside a single arm posture.

## D. From ML to robotics

Iterative IK is gradient descent on a squared error, so the vocabulary is familiar and two of the instincts are wrong.

- **"Just add more iterations."** IK has genuine local minima — configurations where the error gradient vanishes but the target is not reached, usually because the arm is folded the wrong way. More iterations converge harder onto the wrong answer. The fix is a different initial guess, which in practice means seeding from the previous timestep.
- **"Tune the step size."** The damping term is not a learning rate. It is a physical statement about how much joint velocity you are willing to spend for a unit of task-space progress, and the right value depends on where you are in the workspace, not on how training is going.

The transferable instinct that *is* right: warm-starting. Seeding IK from the previous solution keeps you on a continuous branch, which is what stops the elbow flipping.

## E. Practice

<code-exercise src="man-l2-ik"></code-exercise>

<code-exercise src="man-l2-nullspace"></code-exercise>

## F. In production

IKFast generates analytic solvers from a URDF and is still the fastest thing available when your chain admits a closed form. TRAC-IK runs a damped-least-squares solver and a nonlinear optimiser concurrently and returns whichever finishes first, which handles the local-minimum problem pragmatically. MoveIt wraps both.

The detail that catches people: **an IK solution is not a plan.** Solving IK at the goal tells you a configuration that reaches it; it says nothing about whether a path exists from where you are, or whether the straight line in joint space collides with something. That is [8.4's](../../curriculum.md) job, and conflating the two produces a robot that knows exactly where it wants to be and drives its elbow through a table getting there.

## G. Experiment

Solve IK for a target near the workspace boundary from two different initial guesses — elbow up and elbow down — and plot both joint trajectories. They converge to different solutions with identical tool error. Then sweep the target slowly along an arc that crosses the boundary between the two basins, warm-starting each solve from the last, and watch the moment the solver jumps branches. That jump is the configuration flip, and seeing it happen in a plot is worth more than any warning about it.

## H. Failure modes

- **No damping near singularities.** The step explodes and the solver diverges, usually reported as "IK failed" with no indication that it failed *geometrically*.
- **Ignoring joint limits.** The solver happily returns a configuration the hardware cannot adopt, and the failure surfaces at execution time.
- **Cold-starting every solve.** Loses branch continuity, so the arm flips configuration between adjacent waypoints of a smooth path.
- **Treating convergence failure as unreachable.** A local minimum and an out-of-workspace target both return "no solution." They need different responses, and distinguishing them takes one extra check: is the target within the sum of the link lengths?
- **Using an IK solution as a plan.** It is a destination, not a route.

## I. Questions

<quiz-bank src="man-l2-quiz"></quiz-bank>

## J. References

- Buss, *Introduction to Inverse Kinematics with Jacobian Transpose, Pseudoinverse and Damped Least Squares* (2004) — short, practical, and the clearest derivation of the damping trade-off.
- Lynch & Park, *Modern Robotics*, §6.2 — numerical IK in the product-of-exponentials framework.
- Beeson & Ames, *TRAC-IK* (2015) — the concurrent-solver design, and a good discussion of why local minima dominate practical failure.
- Chiaverini, *Singularity-robust task-priority redundancy resolution* (1997) — null-space projection done carefully, including what happens when the secondary task conflicts with the primary one.

## K. Graded work & portfolio extension

**Graded:** the two exercises above, plus the IK component of the manipulation mini-project.

**Portfolio:** build the branch-flip demonstration from section G — the arc sweep with warm-starting, plotting joint angles against target position, with the discontinuity marked. Then add the same sweep with a null-space term keeping joints near their range centres, and show that the flip disappears. Two plots, one clear engineering argument, and it is the kind of thing that reads as having actually operated an arm.
