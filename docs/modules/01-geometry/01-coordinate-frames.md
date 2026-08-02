# 1.1 Coordinate frames and rigid transformations

**Status:** Code verified · **Prereqs:** linear algebra, NumPy · **Time:** ~2 h · **Verified:** 2026-08-01, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Every quantity on a robot lives in *some* coordinate frame: the LiDAR reports points in the **sensor frame**, the wheel encoders describe motion of the **base frame**, the map stores obstacles in the **map frame**, and the planner needs everything in one consistent frame before it can do anything. A large fraction of real robotics bugs — maps that rotate as the robot moves, obstacles that appear mirrored, goals that drift — are coordinate-frame bugs. The transform math in this lesson is the ~100 lines of code the entire rest of the stack sits on.

## B. Mental model

A **frame** is a point of view: an origin plus axes. A **rigid transform** is a sentence about the relationship between two points of view: "frame B, as seen from frame A." We write it \(T_{A \leftarrow B}\) (code: `T_A_B`).

The single most useful convention in robotics: **read subscripts right-to-left, and cancel inner subscripts like units:**

\[
T_{map \leftarrow sensor} = T_{map \leftarrow base}\; T_{base \leftarrow sensor}
\]

The inner `base` cancels, exactly like dimensional analysis. If the subscripts don't cancel, the code is wrong — no need to run it.

One transform does double duty:

- It **describes a pose**: where frame B sits in frame A.
- It **converts data**: multiply a point expressed in B, get the same point expressed in A.

## C. Mathematical formulation

A 2D rigid transform is a rotation \(R \in SO(2)\) plus a translation \(t \in \mathbb{R}^2\), packaged as a homogeneous matrix in \(SE(2)\):

\[
T = \begin{bmatrix} R & t \\ 0 & 1 \end{bmatrix},\qquad
R(\theta) = \begin{bmatrix} \cos\theta & -\sin\theta \\ \sin\theta & \cos\theta \end{bmatrix}
\]

A point \(p_B\) in frame B maps to frame A via \(\tilde p_A = T_{A\leftarrow B}\, \tilde p_B\) using homogeneous coordinates \(\tilde p = [x, y, 1]^\top\).

Because \(R\) is orthogonal (\(R^{-1} = R^\top\)), the inverse has a closed form — no general matrix inversion needed:

\[
T^{-1} = \begin{bmatrix} R^\top & -R^\top t \\ 0 & 1 \end{bmatrix}
\]

Angles must be **wrapped** to \((-\pi, \pi]\) whenever you subtract two headings; otherwise an error of \(0.1\) rad near \(\pm\pi\) shows up as \(\approx 2\pi\) and your controller spins the robot the long way around.

## D. From ML to robotics

- **Frames ≈ feature spaces.** Transforming a LiDAR point from `sensor` to `map` is a basis change — the same mental machinery as projecting an embedding into a different space. The difference: in robotics the "spaces" are physical, and mixing them up crashes a robot instead of degrading a metric.
- **The transform tree ≈ a DAG of pipeline stages.** ROS's TF2 is literally a graph of frames with timestamped edges; querying `map → sensor` is a path query with interpolation. If you have debugged data lineage, you can debug a TF tree.
- **Convention bugs ≈ schema bugs.** Scalar-first vs scalar-last quaternions, degrees vs radians, `T_A_B` vs `T_B_A` — these are schema mismatches. The fix is the same as in data engineering: pick one convention, document it, and validate at the boundary.

## E. Minimal implementation

The library implementation lives in [`robotics_ai/geometry/transforms2d.py`](https://github.com/paulyonghaoli/robotics-for-ai-engineers/blob/main/robotics_ai/geometry/transforms2d.py). The essential core:

```python
import numpy as np

def se2(x, y, theta):
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s, x],
                     [s,  c, y],
                     [0,  0, 1.0]])

def se2_inverse(T):
    R, t = T[:2, :2], T[:2, 2]
    Ti = np.eye(3)
    Ti[:2, :2] = R.T
    Ti[:2, 2] = -R.T @ t
    return Ti

def wrap_angle(theta):
    return -(np.mod(-theta + np.pi, 2 * np.pi) - np.pi)   # -> (-pi, pi]
```

Worked example — a robot at \((1, 0)\) facing \(+y\), with a sensor mounted 0.5 m ahead of the base, sees a point 2 m straight ahead:

```python
from robotics_ai.geometry import se2, se2_compose, transform_points

T_map_base   = se2(1.0, 0.0, np.pi / 2)   # robot pose in map
T_base_lidar = se2(0.5, 0.0, 0.0)         # sensor mount (static)
T_map_lidar  = se2_compose(T_map_base, T_base_lidar)

p_lidar = np.array([2.0, 0.0])            # detection, sensor frame
p_map   = transform_points(T_map_lidar, p_lidar)
# -> [1.0, 2.5]: the sensor sits at (1, 0.5) facing +y, so 2 m ahead is (1, 2.5)
```

### Practice — write and run code here

Implement the machinery yourself, in the page. **Run** executes your code; **Submit** also runs the hidden checks. (First run downloads the Python runtime, ~10 MB.)

<code-exercise src="geo-l1-wrap-angle"></code-exercise>

<code-exercise src="geo-l1-compose"></code-exercise>

<code-exercise src="geo-l1-relative-pose"></code-exercise>

## F. Robotics-framework implementation

In ROS 2 this exact machinery is **TF2**: every node broadcasts `TransformStamped` messages, and consumers query the tree (`lookup_transform('map', 'lidar', t)`). Module 6 rebuilds this example as a TF tree with a URDF-defined sensor mount. Until then, note two ROS conventions to internalize now: quaternions on the wire are scalar-**last** `[x, y, z, w]`, and frame names follow [REP 105](https://www.ros.org/reps/rep-0105.html) (`map`, `odom`, `base_link`).

## G. Experiment

Run the round-trip: transform 1,000 random points `sensor → map → sensor` and measure the max error (it should be ~1e-12). Then perturb the rotation matrix by adding uniform noise of magnitude `1e-3` *without* re-orthonormalizing, compose it with itself 10,000 times (simulating dead-reckoning updates), and measure how far \(R R^\top\) drifts from identity and what happens to point norms. This is why production code re-normalizes rotations — and why quaternions (next lesson) drift more gracefully than matrices.

## H. Failure modes

- **Inverted convention.** Using `T_B_A` where `T_A_B` is expected produces plausible-looking output that's wrong everywhere except the origin. Symptom: the map "rotates around the robot" as it drives.
- **Heading subtraction without wrapping.** Controllers oscillate or spin the long way exactly when crossing \(\pm\pi\) — an intermittent bug that vanishes in most test runs.
- **Stale or missing timestamps.** In a real system transforms are time-indexed; pairing a LiDAR scan with a robot pose from 100 ms earlier smears every obstacle along the direction of motion.
- **Numerical drift.** Long chains of composed rotations slowly stop being orthonormal (see the experiment).

## I. Questions

1. *(Concept)* Why does \(T^{-1}\) have a closed form for rigid transforms but not for general affine ones?
2. *(Calculation)* \(T_{map \leftarrow base} = (2, 1, 90°)\) and \(T_{base \leftarrow cam} = (0.2, 0, -90°)\). Where is the camera in the map frame, and which way does it face?
3. *(Debugging)* A teammate's occupancy grid is mirrored left-right relative to reality. Which single-character bug in `rot2` would cause this, and why does composition still "work"?
4. *(System design)* Your robot has 4 sensors, 2 arms, and a mobile base. How many frames do you define, which transforms are static vs dynamic, and where does each get published?

??? note "Answer sketches"
    **1.** The linear block of a rigid transform is orthogonal, so \(R^{-1} = R^\top\) — the inverse is a transpose plus one matrix-vector product, exact and \(O(n^2)\). A general affine map's linear block carries arbitrary scale and shear, so it has no structural inverse: you need an actual solve, \(O(n^3)\), undefined when the block is singular, and numerically fragile when it is merely close to singular.

    **2.** \(T_{map \leftarrow cam} = T_{map \leftarrow base} T_{base \leftarrow cam}\). The base faces \(+y\), so a mount 0.2 m "ahead" is at \((2, 1.2)\); orientation \(90° - 90° = 0°\) — the camera faces \(+x\) in the map.

    **3.** The minus sign is on the wrong sine: `[[c, s], [-s, c]]` instead of `[[c, -s], [s, c]]`, which builds \(R(-\theta) = R(\theta)^\top\). Composition still "works" because \(R(-\theta_1) R(-\theta_2) = R(-(\theta_1 + \theta_2))\) — the matrices are still orthonormal, still closed under multiplication, and inverse round-trips still pass to machine precision, so every self-consistency check succeeds. What actually happened is that the whole world is reflected about the base x-axis, which for a robot facing \(+x\) reads as a left-right mirrored grid.

    **4.** About 14 frames: `map`, `odom`, `base_link`, one per sensor (4), an arm-base plus per-link frames for each arm, and a tool frame per arm. The mounts (`base_link → sensor_*`, `base_link → arm_*_base`, tool offsets) are static — declare them in the URDF and let `robot_state_publisher` latch them on `/tf_static` rather than hard-coding an offset in application code; the arm's joint edges are dynamic and come from the same node driven by `/joint_states`. `odom → base_link` is published by the wheel-odometry node and `map → odom` by the localizer: one publisher per edge, since two writers on one edge is the inverted-convention and multi-parent failure mode waiting to happen.

### Interactive quiz

<quiz-bank src="geometry-l1-frames"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Lynch & Park, *Modern Robotics*, ch. 3 | book | introductory | The cleanest treatment of rigid-body transforms; free PDF from the authors |
| [REP 105 — Coordinate Frames for Mobile Platforms](https://www.ros.org/reps/rep-0105.html) | docs | introductory | The frame-naming conventions every ROS robot uses |
| [TF2 tutorials](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Tf2-Main.html) | docs | intermediate | How production ROS systems manage transform trees |
| Barfoot, *State Estimation for Robotics*, ch. 6 | book | advanced | Rotations/poses done rigorously; read after Module 3 |

## K. Graded work & portfolio extension

**Graded:** complete the [frame-transforms mini-project](project-frames.md) (100 pts, autograded locally with `python -m grader`).

**Portfolio:** build a **frame-debugging visualizer**: a small matplotlib tool that renders a transform tree, animates a robot driving while its sensor observes fixed landmarks, and has a "bug injection" mode (flipped convention, unwrapped angles, stale timestamps) so the viewer can see each failure signature. This becomes a reusable debugging aid for every later module — and a genuinely useful open-source artifact.
