# 1.4 Twists: how robots describe velocity

**Status:** Code verified · **Prereqs:** lessons 1.1, 1.3 · **Time:** ~2 h · **Verified:** 2026-08-01, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Poses tell you where the robot *is*; twists tell you how it *moves*. Every velocity command you will ever send a mobile robot — ROS's `cmd_vel` message — is a twist: \((v_x, v_y, \omega)\) in 2D. Wheel odometry is twist integration. The difference between a cheap odometry model and a good one is *how* you integrate a twist over a timestep, and that choice shows up directly in localization error in Module 3.

## B. Mental model

A 2D twist \(\xi = (v_x, v_y, \omega)\) is a velocity **expressed in the robot's own body frame**: \(v_x\) forward, \(v_y\) leftward (zero for a car-like or differential-drive robot — it can't slide sideways), \(\omega\) counterclockwise spin. Held constant for a timestep, a twist doesn't move you along a straight line — it drives you along a **circular arc** of radius \(v_x/\omega\). Straight-line integration (Euler) cuts the corner of that arc; the error is tiny per step and systematic over a trajectory, which is the worst combination for dead-reckoning.

Differential drive makes this concrete: two wheel speeds \((v_r, v_l)\), wheelbase \(b\), give

\[
v_x = \frac{v_r + v_l}{2}, \qquad \omega = \frac{v_r - v_l}{b}, \qquad v_y = 0 .
\]

## C. Mathematical formulation

Integrating a constant body twist \((v_x, 0, \omega)\) over \(\Delta t\) from heading \(\theta\) (the **exact / arc** model, \(\omega \neq 0\)):

\[
\begin{aligned}
x' &= x + \frac{v_x}{\omega}\big(\sin(\theta + \omega \Delta t) - \sin\theta\big) \\
y' &= y - \frac{v_x}{\omega}\big(\cos(\theta + \omega \Delta t) - \cos\theta\big) \\
\theta' &= \theta + \omega \Delta t
\end{aligned}
\]

versus the **Euler** approximation \(x' = x + v_x \cos\theta\, \Delta t\), \(y' = y + v_x \sin\theta\, \Delta t\). As \(\omega \to 0\) the arc model reduces to Euler (guard the division!). In Lie-group language the arc formula is the closed-form exponential map \(\exp: \mathfrak{se}(2) \to SE(2)\) — the same object you'll meet as \(\exp/\log\) in SLAM libraries — but you don't need that vocabulary to use it correctly.

Velocities also change with frames: a twist expressed in the body frame relates to world-frame velocity through the current rotation, \(\dot{p}_{world} = R(\theta)\, (v_x, v_y)^\top\).

## D. From ML to robotics

- **Euler vs exact integration ≈ discretization error in ODE solvers** — the same trade you meet in neural ODEs or physics-informed models. Robotics adds a twist (sorry): the error is *biased* (always cutting the same corner), so it accumulates as systematic drift rather than washing out as noise. Biased error you must model; unbiased error you can filter.
- **The motion model you pick here *is* the process model** \(f(x_t, u_t)\) of the Kalman/particle filters in Module 3. Sloppy integration now becomes unexplained innovation later — like serving a model with different preprocessing than it was trained with.
- **`cmd_vel` is an action-space contract**: policies (Module 9) output twists too. RL for mobile robots usually means "learn a function that emits \((v_x, \omega)\) at 20 Hz."

## E. Minimal implementation

```python
import numpy as np

def integrate_twist(pose, v, omega, dt):
    """Exact (arc) integration of a body twist (v, 0, omega) over dt."""
    x, y, theta = pose
    if abs(omega) < 1e-9:                       # straight-line limit
        return (x + v * np.cos(theta) * dt,
                y + v * np.sin(theta) * dt,
                theta)
    r = v / omega
    return (x + r * (np.sin(theta + omega * dt) - np.sin(theta)),
            y - r * (np.cos(theta + omega * dt) - np.cos(theta)),
            theta + omega * dt)
```

### Practice — write and run code here

<code-exercise src="geo-l4-diff-drive"></code-exercise>

<code-exercise src="geo-l4-euler-vs-arc"></code-exercise>

## F. Robotics-framework implementation

In ROS 2 the twist is `geometry_msgs/Twist` (`linear.x`, `angular.z` for planar robots), published to `cmd_vel`; the base driver converts it to wheel speeds using exactly the differential-drive inverse of section B, and the odometry node integrates measured wheel speeds back into `odom → base` — the dynamic tree edge from lesson 1.3. `ros2_control`'s `diff_drive_controller` is this lesson as production C++.

## G. Experiment

Drive a simulated robot in a circle (constant \(v_x = 1\) m/s, \(\omega = 0.5\) rad/s) for one full revolution, integrating at 50 Hz with Euler and with the arc model. The true trajectory closes exactly; measure each model's closure error, then repeat at 10 Hz and 5 Hz. Plot error vs rate: the arc model is exact at any rate for constant twists; Euler's error grows quadratically as the rate drops. Now add noise to the wheel speeds and observe that at 50 Hz the *noise* dominates the *discretization* — a preview of why Module 3 models both.

## H. Failure modes

- **Dividing by ω near zero:** the arc formula explodes for straight-line motion. Every production implementation has the `abs(omega) < eps` guard; forgetting it yields NaN poses that poison the TF tree.
- **Integrating in the wrong frame:** applying \((v_x, v_y)\) in world coordinates without rotating by \(R(\theta)\) sends the robot along the world x-axis regardless of heading.
- **Assuming \(v_y = 0\) holds on a real floor:** wheel slip and kidnapping violate the no-slide constraint; treat the motion model as a prior, not the truth (Module 3's whole reason to exist).
- **Timestep from the wrong clock:** using intended `dt` instead of measured elapsed time between encoder reads turns scheduler jitter directly into position drift.

## I. Questions

1. *(Concept)* Why is Euler-integration error in dead-reckoning worse than sensor noise of comparable magnitude?
2. *(Calculation)* \(v_r = 1.2\), \(v_l = 0.8\) m/s, wheelbase 0.5 m: compute \(v_x\) and \(\omega\), and the turning radius.
3. *(Debugging)* A robot commanded to drive straight slowly veers left in odometry but drives straight per an external tracker. List two distinct causes and how to distinguish them.
4. *(System design)* Odometry can run at 20, 50 or 200 Hz. What trades off, and what would make you pick each?

??? note "Answer sketches"
    **1.** Euler cuts the corner of the arc the same way every step, so the error is a signed bias tied to the turn direction: over \(N\) steps it accumulates as \(O(N)\), while zero-mean sensor noise accumulates as a random walk, \(O(\sqrt N)\). And a filter can shrink noise by averaging and can carry it as process covariance, but a bias that isn't in the motion model is indistinguishable from real motion — it goes straight into the state estimate and stays there.

    **2.** \(v_x = 1.0\) m/s, \(\omega = 0.8\) rad/s, radius \(= v_x/\omega = 1.25\) m.

    **3.** The odometry is wrong, not the motion. Either (a) mismatched effective wheel radii / encoder scale, so equal true wheel speeds are reported as \(v_r \neq v_l\) and \(\omega = (v_r - v_l)/b\) comes out nonzero, or (b) a yaw-rate bias in the gyro, if odometry fuses an IMU. Distinguish by time vs distance: park the robot for a minute — heading that drifts while stationary is gyro bias, since a wheel-scale error only accrues with distance travelled — and as a second check, drive the same path in reverse, which flips a wheel-scale veer to the right while a gyro bias keeps drifting the same way.

    **4.** Run 50 Hz. At 50 Hz with the arc model, discretization error is already below encoder quantization noise (the section G result), whereas 20 Hz adds integration error on fast turns *and* latency to whatever controller consumes `odom → base`, and 200 Hz mostly publishes quantization noise while quadrupling TF buffer traffic and CPU for no accuracy gain. Go to 200 Hz only if an EKF fusing a high-rate IMU wants matched prediction steps; drop to 20 Hz only on a bandwidth-starved link or a genuinely slow robot.

### Interactive quiz

<quiz-bank src="geometry-l4-twists"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Lynch & Park, *Modern Robotics*, ch. 3.3 & 13.2 | book | intermediate | Twists properly, and the differential-drive model |
| Thrun et al., *Probabilistic Robotics*, ch. 5 | book | intermediate | Velocity and odometry motion models — read before Module 3 |
| [`diff_drive_controller` docs](https://control.ros.org/jazzy/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html) | docs | intermediate | This lesson as shipped production code |

## K. Graded work & portfolio extension

**Graded:** twist integration is the motion model inside the Module 3 localization project.

**Portfolio:** the section G experiment as a notebook with closure-error plots is a small, complete, quantitative artifact — evidence you distinguish discretization error from noise, which is precisely what estimation interviews probe.
