# 1.4 Twists: how robots describe velocity

**Status:** Code verified · **Prereqs:** lessons 1.1, 1.3 · **Time:** ~2 h · **Verified:** 2026-08-01, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Poses tell you where the robot *is*. Twists tell you how it *moves*.

Every velocity command you will ever send a mobile robot is a twist. ROS's
`cmd_vel` message is a twist. Wheel odometry is twist integration. The
`odom → base` edge from lesson 1.3 — the one controllers depend on being
smooth — is produced by integrating twists, several hundred times a second,
forever.

And here is the thing that makes this lesson worth two hours rather than
twenty minutes: **the difference between a cheap integration and a correct one
is a few lines of code, and it shows up directly as localisation error in
Module 3.** Not as a rounding difference — as a systematic, accumulating drift
that a filter cannot remove, because it is not noise.

!!! note "Terms defined here"

    **Twist** — a velocity expressed in the robot's own body frame. In 2D,
    \((v_x, v_y, \omega)\): forward speed, sideways speed, and turn rate.

    **Body frame** — the frame attached to the robot, moving with it.
    "Forward" means the robot's forward, whatever direction that currently
    points in the map.

    **Differential drive** — the two-independently-driven-wheels
    configuration used by most indoor robots. Steering is done by driving the
    wheels at different speeds.

    **Wheelbase** (here, \(b\)) — the distance between the two driven wheels.

    **Dead reckoning** — estimating pose by accumulating motion, with no
    external reference. Introduced in 1.1; this lesson is how it is actually
    computed.

## B. Mental model

A 2D twist \(\xi = (v_x, v_y, \omega)\) is a velocity **in the robot's own
frame**:

- \(v_x\) — forward,
- \(v_y\) — to the left. **Zero** for a car-like or differential-drive robot,
  because it cannot slide sideways,
- \(\omega\) — counter-clockwise turn rate.

Now the central insight of the lesson, and it is worth pausing on because it
is not obvious:

**A constant twist does not move you in a straight line. It drives you along a
circular arc.**

Consider why. You are moving forward at \(v_x\) *and* rotating at \(\omega\).
An instant later you are still moving forward at \(v_x\) — but "forward" now
points somewhere slightly different, because you turned. Integrate that and
you trace a circle, of radius

\[
r = \frac{v_x}{\omega}
\]

Straight-line (Euler) integration ignores this and cuts the corner of the arc.
The error per step is tiny. It is also **systematic** — it always cuts the
same way for a given turn direction — and tiny-plus-systematic is the worst
possible combination for something you are going to accumulate a million
times.

### Differential drive makes it concrete

Two wheel speeds \((v_r, v_l)\) and a wheelbase \(b\) give

\[
v_x = \frac{v_r + v_l}{2}, \qquad \omega = \frac{v_r - v_l}{b}, \qquad v_y = 0
\]

Both formulas are worth reading physically rather than memorising. The forward
speed is the *average* of the wheels — obviously, since if both wheels do the
same thing the robot goes that fast. The turn rate is the *difference* divided
by the separation — a wheel-speed difference of 0.4 m/s spread over a wide
robot turns it slowly, and over a narrow robot turns it sharply.

## C. Mathematical formulation

Integrating a constant body twist \((v_x, 0, \omega)\) over \(\Delta t\),
starting from pose \((x, y, \theta)\). The **exact (arc)** model, valid for
\(\omega \neq 0\):

\[
\begin{aligned}
x' &= x + \frac{v_x}{\omega}\big(\sin(\theta + \omega \Delta t) - \sin\theta\big) \\
y' &= y - \frac{v_x}{\omega}\big(\cos(\theta + \omega \Delta t) - \cos\theta\big) \\
\theta' &= \theta + \omega \Delta t
\end{aligned}
\]

versus the **Euler** approximation:

\[
x' = x + v_x \cos\theta\, \Delta t, \qquad
y' = y + v_x \sin\theta\, \Delta t, \qquad
\theta' = \theta + \omega\,\Delta t
\]

Euler evaluates the heading once, at the start of the step, and pretends it
held for the whole step. The arc model accounts for the heading changing
*during* the step.

As \(\omega \to 0\) the arc model reduces to Euler — but the formula divides
by \(\omega\), so **you must guard the division** or straight-line driving
produces `NaN`. Every production implementation has that guard; forgetting it
is failure mode 1.

For the mathematically curious: the arc formula is the closed-form exponential
map \(\exp: \mathfrak{se}(2) \to SE(2)\), the same \(\exp\)/\(\log\) pair you
will meet in SLAM libraries. You do not need that vocabulary to use it
correctly, and this curriculum introduces it properly only where it earns its
keep.

**Frames apply to velocities too.** A body-frame twist relates to world-frame
velocity through the current rotation:

\[
\dot{p}_{world} = R(\theta)\,(v_x, v_y)^\top
\]

Forgetting this rotation is failure mode 2, and it produces a robot that
drives along the world x-axis no matter which way it is pointing — a
memorable and instantly recognisable bug once you have seen it.

## D. From ML to robotics

**Euler versus exact integration is discretisation error**, the same trade you
meet in ODE solvers, neural ODEs, or any physics-informed model. Robotics adds
one twist, and this is the part worth internalising:

> The error is **biased** — it always cuts the corner the same way — so it
> accumulates as \(O(N)\) systematic drift rather than washing out as an
> \(O(\sqrt N)\) random walk.

That distinction matters enormously downstream. A filter can shrink zero-mean
noise by averaging, and can carry it honestly as process covariance. A bias
that is not in the motion model is **indistinguishable from real motion** — it
goes straight into the state estimate and stays there. Unbiased error you can
filter; biased error you must model.

**The motion model you pick here *is* the process model** \(f(x_t, u_t)\) of
the Kalman and particle filters in Module 3. Sloppy integration now becomes
unexplained innovation later — the same class of mistake as serving a model
with different preprocessing than it was trained with.

**`cmd_vel` is an action-space contract.** Learned policies (Module 9) output
twists too. Reinforcement learning for mobile robots usually means "learn a
function emitting \((v_x, \omega)\) at 20 Hz", which means everything in this
lesson applies to the learned stack unchanged.

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

Nine lines, one guard, and it is exact for any constant twist at any timestep.
The Euler version is shorter and wrong in a way that will cost you a metre
over a warehouse.

### Practice — write and run code here

<code-exercise src="geo-l4-diff-drive"></code-exercise>

<code-exercise src="geo-l4-euler-vs-arc"></code-exercise>

## F. Robotics-framework implementation

In ROS 2 the twist is `geometry_msgs/Twist` — `linear.x` and `angular.z` for
a planar robot — published on `cmd_vel`. The chain is:

1. A planner or policy publishes a twist on `cmd_vel`.
2. The base driver converts it to wheel speeds, using the inverse of the
   differential-drive equations in section B.
3. The wheels turn; encoders measure what actually happened.
4. The odometry node integrates the *measured* wheel speeds back into a pose,
   and publishes the `odom → base` edge from lesson 1.3.

Note step 3 and 4: odometry integrates what the wheels *did*, not what was
*commanded*. Those differ, and the difference is called slip.

`ros2_control`'s `diff_drive_controller` is this lesson as production C++.

## G. Experiment — measure the discretisation error

Drive a simulated robot in a circle: constant \(v_x = 1\) m/s,
\(\omega = 0.5\) rad/s, for one full revolution. The true trajectory closes
exactly — the robot returns to its start.

Integrate at 50 Hz with both models and measure the **closure error**: how
far from the start each model thinks you ended up. Then repeat at 10 Hz and
5 Hz, and plot error against rate.

What you will find:

- **The arc model is exact at every rate**, for a constant twist. Its error is
  floating-point noise, and it does not care about \(\Delta t\).
- **Euler's error grows quadratically as the rate drops.** Halving the rate
  roughly quadruples the closure error.

Then add noise to the wheel speeds and repeat. At 50 Hz you will find the
*noise* now dominates the *discretisation error* — which is exactly why
Module 3 models both, and why the answer to "how fast should odometry run" is
"fast enough that discretisation is below your noise floor, and no faster".

## H. Failure modes

- **Dividing by \(\omega\) near zero.** The arc formula explodes for
  straight-line motion. *Symptom:* `NaN` poses that propagate into the TF tree
  and poison every downstream lookup, usually with an error message pointing
  somewhere unrelated.
- **Integrating in the wrong frame.** Applying \((v_x, v_y)\) in world
  coordinates without rotating by \(R(\theta)\). *Symptom:* the robot drives
  along the world x-axis regardless of its heading — unmistakable once seen.
- **Assuming \(v_y = 0\) holds on a real floor.** Wheel slip, carpet, being
  picked up and moved. Treat the motion model as a *prior*, not the truth;
  that gap is Module 3's entire reason to exist.
- **Timestep from the wrong clock.** Using the intended `dt` instead of the
  measured elapsed time between encoder reads turns scheduler jitter directly
  into position drift. *Symptom:* odometry accuracy that mysteriously depends
  on system load.

## I. Questions

1. *(Concept)* Why is Euler-integration error in dead reckoning worse than
   sensor noise of comparable magnitude?
2. *(Calculation)* \(v_r = 1.2\), \(v_l = 0.8\) m/s, wheelbase 0.5 m: compute
   \(v_x\), \(\omega\), and the turning radius.
3. *(Debugging)* A robot commanded to drive straight slowly veers left in
   odometry but drives straight according to an external tracker. List two
   distinct causes and how to distinguish them.
4. *(System design)* Odometry can run at 20, 50 or 200 Hz. What trades off,
   and what would make you pick each?

??? note "Answer sketches"
    **1.** Euler cuts the corner of the arc the same way every step, so the
    error is a signed bias tied to the turn direction. Over \(N\) steps it
    accumulates as \(O(N)\), while zero-mean sensor noise accumulates as a
    random walk, \(O(\sqrt N)\). Worse, a filter can shrink noise by averaging
    and can carry it as process covariance, but a bias that is not in the
    motion model is indistinguishable from real motion — it enters the state
    estimate and stays there.

    **2.** \(v_x = (1.2 + 0.8)/2 = 1.0\) m/s.
    \(\omega = (1.2 - 0.8)/0.5 = 0.8\) rad/s.
    Radius \(= v_x/\omega = 1.25\) m.

    **3.** The odometry is wrong, not the motion. Either **(a)** mismatched
    effective wheel radii or encoder scale, so equal true wheel speeds are
    reported as \(v_r \neq v_l\) and \(\omega = (v_r - v_l)/b\) comes out
    nonzero; or **(b)** a yaw-rate bias in the gyro, if odometry fuses an IMU.
    Distinguish by **time versus distance**: park the robot for a minute. A
    heading that drifts while stationary is gyro bias, since a wheel-scale
    error only accrues with distance travelled. As a second check, drive the
    same path in reverse — a wheel-scale veer flips to the right, while a gyro
    bias keeps drifting the same way.

    **4.** Run 50 Hz. At 50 Hz with the arc model, discretisation error is
    already below encoder quantisation noise (the section G result), whereas
    20 Hz adds integration error on fast turns *and* latency to whatever
    controller consumes `odom → base`, and 200 Hz mostly publishes
    quantisation noise while quadrupling TF buffer traffic and CPU for no
    accuracy gain. Go to 200 Hz only if an EKF fusing a high-rate IMU wants
    matched prediction steps; drop to 20 Hz only on a bandwidth-starved link
    or a genuinely slow robot.

### Interactive quiz

<quiz-bank src="geometry-l4-twists"></quiz-bank>

## J. Annotated references

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Lynch & Park, *Modern Robotics*, ch. 3.3 & 13.2 | book | intermediate | Twists done properly, plus the differential-drive model in its own chapter |
| Thrun et al., *Probabilistic Robotics*, ch. 5 | book | intermediate | Velocity and odometry motion models. Read this before Module 3, not during |
| [`diff_drive_controller` docs](https://control.ros.org/jazzy/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html) | docs | intermediate | This lesson as shipped production C++, including the parameters you will actually have to set |

## K. Graded work and portfolio extension

**Graded:** twist integration is the motion model inside the Module 3
localisation project. Getting it right here is not optional — it is a
dependency.

**Portfolio:** the section G experiment, written up as a notebook with
closure-error plots against integration rate. It is small, complete and
quantitative, and it demonstrates that you distinguish discretisation error
from noise — which is precisely what estimation interviews probe, and what
most candidates conflate.
