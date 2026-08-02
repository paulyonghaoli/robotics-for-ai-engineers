# 1.2 3D rotations: matrices, Euler angles, and why robotics runs on quaternions

**Status:** Code verified · **Prereqs:** lesson 1.1, linear algebra · **Time:** ~2.5 h · **Verified:** 2026-08-01, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

In 2D an orientation is one number. In 3D it is a point on a curved 3-dimensional manifold, \(SO(3)\), and every representation of it is a compromise: rotation matrices (9 numbers, drift under composition), Euler angles (3 numbers, gimbal lock and 24 ordering conventions), axis-angle (clean, awkward to compose), and unit quaternions (4 numbers, the industry default). Your IMU integrates orientation with quaternions; TF2 ships quaternions on the wire; every attitude estimator and every 3D pose in ROS is a quaternion. When a drone flips upside-down because someone fed Euler angles through ±90° pitch, this lesson is the postmortem.

## B. Mental model

A unit quaternion is **axis-angle in disguise**: to rotate by angle \(\theta\) about unit axis \(\hat{n}\),

\[
q = \left[\cos\tfrac{\theta}{2},\; \sin\tfrac{\theta}{2}\,\hat{n}\right] = [w, x, y, z]
\]

Half-angles are the price of a beautiful property: rotating a vector is the two-sided product \(v' = q\,v\,q^{*}\), and composing rotations is just multiplying quaternions. Think of \(q\) as living on the unit sphere in 4D; rotations compose by moving along that sphere, and interpolation (slerp) walks the great-circle arc between two orientations at constant angular speed.

One genuine oddity to internalize: \(q\) and \(-q\) encode the **same rotation** (the "double cover"). Rotating by 360° brings the vector back but flips the quaternion's sign. This is harmless until you average, interpolate, or compare quaternions naively — then it bites.

## C. Mathematical formulation

The Hamilton product composes rotations (matching matrix order, \(R(q_1 q_2) = R(q_1) R(q_2)\)):

\[
q_1 q_2 = \begin{bmatrix}
w_1 w_2 - \mathbf{v}_1 \cdot \mathbf{v}_2 \\
w_1 \mathbf{v}_2 + w_2 \mathbf{v}_1 + \mathbf{v}_1 \times \mathbf{v}_2
\end{bmatrix}
\]

For a unit quaternion the inverse is the conjugate \(q^{*} = [w, -\mathbf{v}]\). The rotation matrix is a quadratic form in the components:

\[
R(q) = \begin{bmatrix}
1-2(y^2+z^2) & 2(xy - wz) & 2(xz + wy) \\
2(xy + wz) & 1-2(x^2+z^2) & 2(yz - wx) \\
2(xz - wy) & 2(yz + wx) & 1-2(x^2+y^2)
\end{bmatrix}
\]

Slerp between \(q_0, q_1\) at parameter \(t\), with \(\Omega = \arccos(q_0 \cdot q_1)\) after flipping \(q_1\)'s sign if the dot product is negative (shortest arc):

\[
\mathrm{slerp}(q_0, q_1, t) = \frac{\sin((1-t)\Omega)}{\sin\Omega}\, q_0 + \frac{\sin(t\Omega)}{\sin\Omega}\, q_1
\]

## D. From ML to robotics

- **Unit quaternions ≈ normalized embeddings.** Both live on a hypersphere; both compare by dot product; both need re-normalization after arithmetic or they silently degrade. Slerp is exactly the geodesic interpolation you may know from latent-space interpolation done right (vs. naive lerp).
- **Why 4 numbers for a 3-DOF quantity?** The same reason over-parameterization helps in ML: the minimal 3-parameter charts (Euler angles) necessarily contain singularities (gimbal lock), like trying to flatten a sphere onto a plane. The 4th dimension buys a globally smooth, singularity-free representation at the cost of one constraint (\(\|q\|=1\)) and the double cover.
- **Convention chaos ≈ schema drift.** Scalar-first `[w,x,y,z]` (this curriculum, Eigen) vs scalar-last `[x,y,z,w]` (ROS messages, SciPy). Both are "correct"; mixing them is the robotics equivalent of a silently reordered CSV column — everything runs, nothing is right.

## E. Minimal implementation

Library: [`robotics_ai/geometry/rotations3d.py`](https://github.com/paulyonghaoli/robotics-for-ai-engineers/blob/main/robotics_ai/geometry/rotations3d.py). The essential core:

```python
import numpy as np

def quat_from_axis_angle(axis, angle):
    axis = axis / np.linalg.norm(axis)
    half = 0.5 * angle
    return np.concatenate(([np.cos(half)], np.sin(half) * axis))

def quat_multiply(q1, q2):
    w1, x1, y1, z1 = q1; w2, x2, y2, z2 = q2
    return np.array([
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
    ])

def quat_rotate(q, v):
    qv = np.concatenate(([0.0], v))
    q_conj = q * np.array([1.0, -1, -1, -1])
    return quat_multiply(quat_multiply(q, qv), q_conj)[1:]
```

### Practice — write and run code here

<code-exercise src="geo-l2-quat-compose"></code-exercise>

<code-exercise src="geo-l2-slerp"></code-exercise>

## F. Robotics-framework implementation

ROS 2 sends orientation as `geometry_msgs/Quaternion` with fields `x, y, z, w` — **scalar-last**. Convert at the boundary, in exactly one place:

```python
def to_ros(q_wxyz):                      # our convention -> wire format
    w, x, y, z = q_wxyz
    return Quaternion(x=x, y=y, z=z, w=w)
```

SciPy's `Rotation.from_quat` is also scalar-last by default. Eigen and this curriculum are scalar-first. Module 6 revisits this when we build the TF tree; the frame-debugging lab includes a deliberately mixed-convention bug to find.

## G. Experiment

Compose a small rotation (1° about a tilted axis) with itself 100,000 times, once with rotation matrices and once with quaternions, renormalizing **neither**. Measure \(\|R R^\top - I\|\) and \(|\,\|q\| - 1|\) over time, then repeat with renormalization every step (for the quaternion this is one `q /= np.linalg.norm(q)`; for the matrix it's an SVD or Gram-Schmidt). You'll find the quaternion drifts more slowly, and renormalizing it is trivially cheap while re-orthonormalizing a matrix is not — which is a large part of why estimators integrate orientation as quaternions.

## H. Failure modes

- **Convention mismatch** (scalar-first vs scalar-last): rotations come out wrong by a scramble, not by a small error — yet code full of round-trips can *appear* to work until it crosses a library boundary.
- **Forgetting the double cover:** averaging \(q\) and \(-q\) (same rotation!) gives zero; a tracking filter that doesn't sign-align consecutive quaternions sees phantom 360° jumps.
- **Unnormalized quaternions:** after long integration \(\|q\| \neq 1\), and `quat_to_matrix` silently produces a matrix with scale in it — downstream point clouds slowly shrink or grow.
- **Naive lerp instead of slerp** for large angular differences: the interpolated orientation speeds up mid-arc and the norm dips (visible as a "pinch" in animation).
- **Euler angles in the pipeline's core:** fine as human-readable I/O, catastrophic as internal state near ±90° pitch (gimbal lock collapses a DOF).

## I. Questions

1. *(Concept)* Why do quaternions use half-angles? What goes wrong with \(q = [\cos\theta, \sin\theta\,\hat{n}]\)?
2. *(Calculation)* Compute the quaternion for a 180° rotation about the z-axis, and verify by rotating the vector \((1, 0, 0)\).
3. *(Debugging)* An attitude estimator's output occasionally "spins" 360° in one frame while the physical IMU moved smoothly. What's the bug?
4. *(System design)* Your logging format stores orientations. Choose a representation and justify it against: interpolation for replay, storage size, human debuggability, and convention safety across three consumer teams.

??? note "Answer sketch for Q3"
    Consecutive quaternion estimates crossed the double cover: the filter (or its output serializer) isn't enforcing \(q_k \cdot q_{k-1} \geq 0\). Sign-align each output against the previous one.

### Interactive quiz

<quiz-bank src="geometry-l2-quats"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Lynch & Park, *Modern Robotics*, ch. 3.2–3.3 | book | introductory | Rotation matrices and exponential coordinates, cleanly |
| Sola, *"Quaternion kinematics for the error-state Kalman filter"* (2017) | paper | intermediate | The reference every estimation engineer keeps open; read §1–2 now, the rest in Module 3 |
| Shoemake, *"Animating rotation with quaternion curves"* (1985) | paper | intermediate | The original slerp paper — short and readable |
| [REP 103 — Standard Units and Coordinate Conventions](https://www.ros.org/reps/rep-0103.html) | docs | introductory | ROS's conventions, including quaternion ordering |

## K. Graded work & portfolio extension

**Graded:** the [frame-transforms mini-project](project-frames.md) covers this module's 2D core; quaternion tasks join the Module 1 final assignment (planned).

**Portfolio:** extend the drift experiment (section G) into a short, plotted write-up — matrix vs quaternion drift, with and without renormalization, cost per step — the kind of micro-benchmark that makes a strong blog post and demonstrates you measure before you claim.
