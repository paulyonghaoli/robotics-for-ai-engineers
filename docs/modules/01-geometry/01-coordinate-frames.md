# 1.1 Coordinate frames and rigid transformations

**Status:** Code verified · **Prereqs:** linear algebra, NumPy · **Time:** ~2 h · **Verified:** 2026-08-01, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Every number on a robot lives in *some* coordinate frame. The LiDAR reports
points relative to itself. The wheel encoders describe how the chassis moved.
The map stores obstacles relative to a corner of the building. The arm reports
joint angles relative to its own base. None of these agree with each other,
and the planner needs them all in one frame before it can do anything at all.

Getting this wrong is not an exotic failure. It is *the* characteristic
robotics bug, and it produces symptoms that look like something else entirely:

- The map appears to rotate around the robot as it drives.
- Obstacles appear mirrored, so the robot swerves *into* them.
- The goal drifts a little further away each time you approach it.
- Everything works in simulation and fails on hardware, because the mount
  offset is zero in one and 12 cm in the other.

Each of those is a two-line fix once you know what you are looking at, and a
lost week if you do not. The machinery in this lesson is about a hundred lines
of code, and the entire rest of the stack sits on top of it.

!!! note "Terms defined here"

    **Frame** (short for *coordinate frame*) — a point of view: an origin
    plus a set of axes. "The sensor frame" means "positions measured from the
    sensor, along the sensor's own axes".

    **Pose** — position *and* orientation together. In 2D that is three
    numbers \((x, y, \theta)\); in 3D it is six. A pose is always *relative
    to some frame* — "the robot's pose" is meaningless without saying "in
    which frame".

    **Rigid transform** — a change of frame that preserves all distances and
    angles: rotation plus translation, no scaling, no shearing, no
    reflection. Real objects move rigidly, which is why this restricted class
    is the one robotics cares about.

    **Dead reckoning** — estimating where you are by accumulating how far you
    have moved, with no external reference. Cheap, always available, and
    drifts without bound.

## B. Mental model

Two ideas, and the second one does most of the work.

**A frame is a point of view.** Nothing more. When the LiDAR says a point is
at \((2, 0)\), it means "two metres along my own x-axis". The same physical
point, described from the map's point of view, is a completely different pair
of numbers. Neither is more correct.

**A transform is a sentence about the relationship between two points of
view.** We write \(T_{A \leftarrow B}\) — in code, `T_A_B` — and read it as
"frame B, as seen from frame A".

Now the convention that prevents most frame bugs before they happen. **Read
subscripts right to left, and cancel adjacent inner subscripts exactly like
units:**

\[
T_{map \leftarrow sensor} = T_{map \leftarrow base}\; T_{base \leftarrow sensor}
\]

The inner `base` cancels. This is dimensional analysis, and it is just as
reliable: **if the subscripts do not cancel, the code is wrong, and you do not
need to run it to know that.** Writing

```python
T_map_sensor = T_base_map @ T_base_sensor     # map ← base? base ← sensor?
```

is visibly broken on inspection — `base` appears twice on the left of an
arrow — even though it runs happily and produces plausible numbers.

One more idea, and it is the one that confuses people longest. **A single
transform does double duty:**

1. It **describes a pose**: \(T_{map \leftarrow base}\) *is* where the robot
   sits in the map.
2. It **converts data**: multiply a point expressed in `base` and you get the
   same physical point expressed in `map`.

These sound like different jobs and they are the same matrix. If that feels
odd, the reason is that "where B is, seen from A" and "how to re-express B's
numbers in A's terms" are the same information written once.

## C. Mathematical formulation

### Rotation first

A 2D rotation by angle \(\theta\) is the matrix

\[
R(\theta) = \begin{bmatrix} \cos\theta & -\sin\theta \\ \sin\theta & \cos\theta \end{bmatrix}
\]

Two properties matter, and neither is about the individual entries:

\[
R^\top R = I \qquad \text{and} \qquad \det(R) = +1
\]

The first says the columns are orthonormal, which means \(R^{-1} = R^\top\) —
inverting a rotation costs a transpose, which is free. The second
distinguishes rotation from reflection. The set of matrices with both
properties is called \(SO(2)\), the *special orthogonal group*; "special"
means the determinant is \(+1\) rather than \(-1\).

That determinant is not pedantry. Question 3 below is a real bug in which a
single misplaced minus sign produces \(\det = +1\) still, but builds
\(R(-\theta)\) instead of \(R(\theta)\) — and every self-consistency check
passes while the world is mirrored.

### Adding translation: homogeneous coordinates

Rotation is a matrix multiply; translation is an addition. Doing them
separately means every piece of code carries two objects around and has to
remember the order. The standard trick is to make translation into a
multiplication too, by adding a dummy coordinate:

\[
\tilde p = \begin{bmatrix} x \\ y \\ 1 \end{bmatrix}, \qquad
T = \begin{bmatrix} R & t \\ 0\ 0 & 1 \end{bmatrix}
\]

Then

\[
\tilde p_A = T_{A \leftarrow B}\, \tilde p_B
\]

does rotation and translation in one operation, and — the real payoff —
composing two transforms is just multiplying two matrices. Chains of frames
become chains of matrix products. This set is called \(SE(2)\), the *special
Euclidean group*.

The 1 in the last row is what makes the translation column apply. If you ever
transform a *direction* rather than a *point* — a velocity, a surface normal —
you use a 0 there instead, because directions should rotate but not translate.
That distinction causes real bugs; it is worth remembering now.

### The inverse, in closed form

Because \(R\) is orthogonal, the inverse of a rigid transform has a closed
form and never needs a general matrix solve:

\[
T^{-1} = \begin{bmatrix} R^\top & -R^\top t \\ 0\ 0 & 1 \end{bmatrix}
\]

Worth deriving once, because the \(-R^\top t\) term looks arbitrary and is
not. We want the \(S\) with \(ST = I\). Writing it out:

\[
\begin{bmatrix} R^\top & u \\ 0 & 1 \end{bmatrix}
\begin{bmatrix} R & t \\ 0 & 1 \end{bmatrix}
= \begin{bmatrix} R^\top R & R^\top t + u \\ 0 & 1 \end{bmatrix}
= \begin{bmatrix} I & R^\top t + u \\ 0 & 1 \end{bmatrix}
\]

For that to be the identity we need \(u = -R^\top t\). Intuitively: to undo
"rotate then translate", you undo the translation *in the rotated frame*,
which is why the rotation is applied to \(t\) before negating.

### Angle wrapping

Angles are periodic and subtraction does not respect that. If a robot is
heading at \(179°\) and the target is \(-179°\), the naive difference is
\(358°\) — the robot turns almost all the way around to reach a heading two
degrees away.

So **every time you subtract two headings, wrap the result** to
\((-\pi, \pi]\):

```python
def wrap_angle(theta):
    return -(np.mod(-theta + np.pi, 2 * np.pi) - np.pi)   # -> (-pi, pi]
```

The interval is half-open deliberately: \(+\pi\) and \(-\pi\) are the same
heading, so exactly one of them must be chosen to make the function
single-valued. This convention is stated once in `CONTRIBUTING.md` and used
everywhere in the codebase.

This bug is unusually nasty because it is *intermittent*. It only appears when
the heading error crosses \(\pm\pi\), which in most test runs it does not.

## D. From ML to robotics

| You already know | The robotics version | Where they differ |
|---|---|---|
| Basis change / projecting an embedding into another space | Transforming a point from `sensor` to `map` | The spaces are physical. Mixing them crashes a robot rather than degrading a metric |
| A DAG of pipeline stages, data lineage | The transform tree (TF2) — a graph of frames with timestamped edges | Edges are time-indexed and interpolated; querying at the wrong time is a real and common bug |
| Schema mismatch between services | Convention mismatch: scalar-first vs scalar-last quaternions, degrees vs radians, `T_A_B` vs `T_B_A` | Same class of bug, same fix: pick one, document it, validate at the boundary |
| Numerical drift in long float pipelines | Composed rotations slowly stop being orthonormal | Fixed by explicit re-normalisation; see the experiment in section G |

The third row deserves emphasis. Frame-convention bugs *are* schema bugs, and
your instincts from data engineering apply directly: the fix is not
cleverness, it is a documented convention plus validation at every boundary.

## E. Minimal implementation

The library implementation lives in
[`robotics_ai/geometry/transforms2d.py`](https://github.com/paulyonghaoli/robotics-for-ai-engineers/blob/main/robotics_ai/geometry/transforms2d.py).
The essential core is short enough to hold in your head:

```python
import numpy as np

def se2(x, y, theta):
    """Pose (x, y, theta) as a 3x3 homogeneous SE(2) transform."""
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s, x],
                     [s,  c, y],
                     [0,  0, 1.0]])

def se2_inverse(T):
    """Invert: se2_inverse(T_a_b) is T_b_a."""
    R, t = T[:2, :2], T[:2, 2]
    Ti = np.eye(3)
    Ti[:2, :2] = R.T
    Ti[:2, 2] = -R.T @ t
    return Ti

def wrap_angle(theta):
    """Wrap to (-pi, pi]."""
    return -(np.mod(-theta + np.pi, 2 * np.pi) - np.pi)
```

### A worked example, step by step

A robot sits at \((1, 0)\) in the map, **facing \(+y\)** (so
\(\theta = 90°\)). A LiDAR is bolted 0.5 m ahead of the base along the base's
own x-axis. The LiDAR reports a detection 2 m straight ahead of itself. Where
is that point in the map?

```python
T_map_base   = se2(1.0, 0.0, np.pi / 2)   # robot pose in the map
T_base_lidar = se2(0.5, 0.0, 0.0)         # sensor mount, static
T_map_lidar  = se2_compose(T_map_base, T_base_lidar)

p_lidar = np.array([2.0, 0.0])            # detection, in the sensor frame
p_map   = transform_points(T_map_lidar, p_lidar)
```

Work it through by hand before trusting the code, because this is exactly the
reasoning you will do while debugging:

1. The robot faces \(+y\). So the base's x-axis points along the map's
   \(+y\).
2. The sensor is 0.5 m along the base's x-axis, i.e. 0.5 m along map \(+y\)
   from \((1, 0)\). **The sensor sits at \((1, 0.5)\).**
3. The sensor inherits the base's orientation, so the sensor's x-axis also
   points along map \(+y\).
4. The detection is 2 m along the sensor's x-axis: 2 m further along map
   \(+y\).
5. **The point is at \((1, 2.5)\).**

Running the code gives `[1.0, 2.5]`. Note that the subscripts cancelled —
`map←base`, `base←lidar` gives `map←lidar` — which is the check you do
*before* running anything.

### Practice — write and run code here

Implement the machinery yourself, in the page. **Run** executes your code;
**Submit** also runs the hidden checks. (The first run downloads the Python
runtime, about 10 MB.)

<code-exercise src="geo-l1-wrap-angle"></code-exercise>

<code-exercise src="geo-l1-compose"></code-exercise>

<code-exercise src="geo-l1-relative-pose"></code-exercise>

## F. Robotics-framework implementation

In ROS 2 this exact machinery is **TF2**. Every node that knows about a frame
relationship broadcasts `TransformStamped` messages; consumers query the tree
with `lookup_transform('map', 'lidar', t)` and get back the composed chain,
interpolated to the timestamp you asked for.

Two conventions to internalise now, because they cause avoidable pain later:

- **Quaternions on the ROS wire are scalar-last**, `[x, y, z, w]`. This
  curriculum uses scalar-first `[w, x, y, z]` internally, as most of the
  literature does. Convert at the boundary, and only at the boundary.
- **Frame names follow [REP 105](https://www.ros.org/reps/rep-0105.html)**:
  `map`, `odom`, `base_link`, and sensor frames hanging off `base_link`.
  Following the standard means other people's tools work on your robot.

Module 6 rebuilds this lesson's example as a real TF tree with the sensor
mount declared in a URDF.

## G. Experiment — watch rotations rot

Two runs, and the second is the interesting one.

**Round trip.** Transform 1,000 random points `sensor → map → sensor` and
measure the maximum error. You should see something around \(10^{-12}\) —
floating-point noise and nothing more. This is your baseline for "the
mathematics is right".

**Drift.** Now perturb a rotation matrix by adding uniform noise of magnitude
\(10^{-3}\), *without* re-orthonormalising, and compose it with itself 10,000
times — simulating a long run of dead-reckoning updates. Measure two things:
how far \(R R^\top\) drifts from the identity, and what happens to the norms
of transformed points.

What you will see is that the matrix stops being a rotation. It starts
scaling. Points slowly grow or shrink, which in a real system means a map that
gradually expands — a symptom nobody would connect to matrix orthogonality
without having seen this once.

This is why production code re-normalises rotations periodically, and it is
the first argument for quaternions, which drift more gracefully because they
have four numbers and one constraint rather than nine numbers and six
constraints. That is lesson 1.2.

## H. Failure modes

- **Inverted convention.** Using `T_B_A` where `T_A_B` is expected. Produces
  plausible output that is wrong everywhere except the origin — which is
  precisely why unit tests centred on the origin pass. *Symptom:* the map
  appears to rotate around the robot as it drives.
- **Heading subtraction without wrapping.** *Symptom:* the controller
  oscillates or spins the long way, intermittently, only when crossing
  \(\pm\pi\).
- **Stale or missing timestamps.** Transforms are time-indexed. Pairing a
  LiDAR scan with a pose from 100 ms earlier smears every obstacle along the
  direction of travel. *Symptom:* walls that look thick, or duplicated, in
  proportion to speed.
- **Numerical drift.** Long chains of composed rotations stop being
  orthonormal. *Symptom:* slow, unexplained scale change in the map.
- **Transforming a direction as if it were a point.** Applying the
  translation to a velocity or a surface normal. *Symptom:* normals that
  point somewhere sensible near the origin and nowhere sensible far from it.

## I. Questions

1. *(Concept)* Why does \(T^{-1}\) have a closed form for rigid transforms
   but not for general affine ones?
2. *(Calculation)* \(T_{map \leftarrow base} = (2, 1, 90°)\) and
   \(T_{base \leftarrow cam} = (0.2, 0, -90°)\). Where is the camera in the
   map frame, and which way does it face?
3. *(Debugging)* A teammate's occupancy grid is mirrored left-right relative
   to reality. Which single-character bug in `rot2` would cause this, and why
   does composition still "work"?
4. *(System design)* Your robot has 4 sensors, 2 arms, and a mobile base. How
   many frames do you define, which transforms are static versus dynamic, and
   where does each get published?

??? note "Answer sketches"
    **1.** The linear block of a rigid transform is orthogonal, so
    \(R^{-1} = R^\top\) — the inverse is a transpose plus one matrix–vector
    product: exact, \(O(n^2)\), and never singular. A general affine map's
    linear block carries arbitrary scale and shear, so it has no structural
    inverse. You need an actual solve: \(O(n^3)\), undefined when the block is
    singular, and numerically fragile when it is merely close to singular.

    **2.** \(T_{map \leftarrow cam} = T_{map \leftarrow base}\,T_{base \leftarrow cam}\).
    The base faces \(+y\), so a mount 0.2 m "ahead" along the base x-axis is
    0.2 m along map \(+y\), putting the camera at \((2, 1.2)\). Orientation is
    \(90° + (-90°) = 0°\), so the camera faces map \(+x\). Verified
    numerically: position `[2.0, 1.2]`, heading `0.0°`.

    **3.** The minus sign is on the wrong sine: `[[c, s], [-s, c]]` instead of
    `[[c, -s], [s, c]]`. That builds \(R(-\theta) = R(\theta)^\top\).
    Composition still "works" because
    \(R(-\theta_1)R(-\theta_2) = R(-(\theta_1+\theta_2))\) — the matrices are
    still orthonormal, still closed under multiplication, and inverse
    round-trips still pass to machine precision, so *every* self-consistency
    check succeeds. What actually happened is that the whole world is
    reflected about the base x-axis, which for a robot facing \(+x\) reads as
    a left-right mirrored grid. This is the canonical example of why
    self-consistency is not correctness.

    **4.** About 14 frames: `map`, `odom`, `base_link`, one per sensor (4),
    an arm-base plus per-link frames for each arm, and a tool frame per arm.
    The mounts (`base_link → sensor_*`, `base_link → arm_*_base`, tool
    offsets) are **static** — declare them in the URDF and let
    `robot_state_publisher` latch them on `/tf_static`, rather than
    hard-coding an offset in application code. The arms' joint edges are
    **dynamic**, published by the same node from `/joint_states`.
    `odom → base_link` comes from the wheel-odometry node and `map → odom`
    from the localizer. One publisher per edge, always: two writers on one
    edge is the inverted-convention failure mode waiting to happen.

### Interactive quiz

<quiz-bank src="geometry-l1-frames"></quiz-bank>

## J. Annotated references

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Lynch & Park, *Modern Robotics*, ch. 3 | book | introductory | The cleanest treatment of rigid-body transforms anywhere, and the authors give the PDF away free |
| [REP 105 — Coordinate Frames for Mobile Platforms](https://www.ros.org/reps/rep-0105.html) | docs | introductory | The frame-naming conventions every ROS robot uses. Short, and worth reading in full |
| [TF2 tutorials](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Tf2-Main.html) | docs | intermediate | How production systems manage transform trees, including the time-indexing this lesson only mentions |
| Barfoot, *State Estimation for Robotics*, ch. 6 | book | advanced | Rotations and poses done rigorously, with the Lie-group machinery. Read after Module 3, not before |

## K. Graded work and portfolio extension

**Graded:** complete the [frame-transforms mini-project](project-frames.md)
(100 pts, autograded locally with `python -m grader`).

**Portfolio:** build a **frame-debugging visualiser** — a small matplotlib
tool that renders a transform tree, animates a robot driving while its sensor
observes fixed landmarks, and has a *bug-injection* mode (flipped convention,
unwrapped angles, stale timestamps) so a viewer can see each failure
signature. This becomes a reusable debugging aid for every later module, and
it is a genuinely useful open-source artifact because the failure signatures
are hard to picture from a description and instantly obvious once animated.
