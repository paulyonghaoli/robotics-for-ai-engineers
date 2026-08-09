# 1.2 3D rotations: matrices, Euler angles, and why robotics runs on quaternions

**Status:** Code verified · **Prereqs:** lesson 1.1, linear algebra · **Time:** ~2.5 h · **Verified:** 2026-08-01, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

In 2D, an orientation is one number. You saw in lesson 1.1 how much machinery
that one number already needs — wrapping, conventions, careful subtraction.

In 3D, an orientation is a point on a curved three-dimensional surface called
\(SO(3)\), and here is the uncomfortable fact that shapes this entire lesson:
**there is no way to represent it with three numbers without introducing a
singularity.** Not "no convenient way" — no way at all. It is a topological
fact about spheres, and it is why the field settled on a four-number
representation with a constraint attached.

Every representation is therefore a compromise:

| Representation | Numbers | Main problem |
|---|---|---|
| Rotation matrix | 9 | Six constraints to maintain; drifts out of \(SO(3)\) under composition |
| Euler angles | 3 | **Gimbal lock**, plus 24 different ordering conventions in the wild |
| Axis–angle | 3 (or 4) | Clean to state, awkward to compose |
| **Unit quaternion** | **4** | Double cover; unfamiliar arithmetic |

Robotics runs on the last one. Your IMU integrates orientation as a
quaternion. TF2 ships quaternions on the wire. Every attitude estimator and
every 3D pose message in ROS is a quaternion. When a drone flips upside down
because someone routed Euler angles through ±90° of pitch, this lesson is the
postmortem.

!!! note "Terms defined here"

    **DOF (degrees of freedom)** — the number of independent numbers needed
    to specify a configuration. A 3D orientation has 3 DOF, which is why the
    4-number quaternion needs exactly one constraint.

    **\(SO(3)\)** — the set of all 3D rotations. Formally the 3×3 matrices
    with \(R^\top R = I\) and \(\det R = +1\), exactly as in lesson 1.1 but
    one dimension up.

    **Manifold** — a space that looks flat locally but is curved globally.
    The surface of the Earth is a 2D manifold; \(SO(3)\) is a 3D one. The
    practical consequence: you cannot cover it with one flat coordinate chart
    without something going wrong somewhere.

    **Gimbal lock** — the singularity in Euler angles: at certain
    orientations two of the three axes align, one degree of freedom
    disappears, and the representation cannot express a rotation the robot
    can physically perform.

    **Attitude** — orientation, in the aerospace and IMU literature. Same
    thing; different vocabulary.

## B. Mental model

**A unit quaternion is axis–angle in disguise.** To rotate by angle
\(\theta\) about the unit axis \(\hat n\):

\[
q = \left[\cos\tfrac{\theta}{2},\; \sin\tfrac{\theta}{2}\,\hat{n}\right] = [w, x, y, z]
\]

That is the whole construction. The mysterious part is the halving, and it
has a precise reason we will come back to in the questions: rotating a vector
is a **two-sided** product, \(v' = q\,v\,q^{*}\), so the quaternion's angle
gets applied twice, and the half is what makes the sandwich come out to
\(\theta\).

What you buy for that oddity:

- **Composing rotations is multiplying quaternions.** No trigonometry, no
  special cases.
- **The representation is smooth everywhere.** No gimbal lock, no orientation
  at which the arithmetic degenerates.
- **Interpolation is natural.** A quaternion lives on the unit sphere in 4D,
  and interpolating between two orientations is walking the great-circle arc
  between two points on that sphere at constant speed. That operation is
  called **slerp** (spherical linear interpolation).

### The one genuine oddity: the double cover

\(q\) and \(-q\) encode **the same rotation**.

This is not a convention you can choose away; it is structural. The sphere in
4D wraps twice around the space of 3D rotations. A physical consequence you
can check: rotate an object by 360° and it returns to where it started, but
its quaternion has flipped sign. You need 720° to get the quaternion back.

This is harmless right up until you average, interpolate, or compare
quaternions naively — and then it produces spectacular bugs. Averaging \(q\)
and \(-q\) gives **zero**, which is not a rotation at all. A tracking filter
that does not sign-align consecutive estimates sees phantom 360° flips.
Failure mode 2 in section H is exactly this.

## C. Mathematical formulation

### Composition: the Hamilton product

\[
q_1 q_2 = \begin{bmatrix}
w_1 w_2 - \mathbf{v}_1 \cdot \mathbf{v}_2 \\
w_1 \mathbf{v}_2 + w_2 \mathbf{v}_1 + \mathbf{v}_1 \times \mathbf{v}_2
\end{bmatrix}
\]

with \(\mathbf v\) the vector part. This matches matrix order:
\(R(q_1 q_2) = R(q_1)\,R(q_2)\), so **\(q_1 q_2\) applies \(q_2\) first** —
the same right-to-left reading as lesson 1.1's subscript cancellation.

For a unit quaternion the inverse is simply the conjugate,
\(q^{*} = [w, -\mathbf{v}]\): negate the vector part. Like the transpose
trick for rotation matrices, inverting is free.

### Converting to a matrix

\[
R(q) = \begin{bmatrix}
1-2(y^2+z^2) & 2(xy - wz) & 2(xz + wy) \\
2(xy + wz) & 1-2(x^2+z^2) & 2(yz - wx) \\
2(xz - wy) & 2(yz + wx) & 1-2(x^2+y^2)
\end{bmatrix}
\]

Every entry is quadratic in the components. This is why an unnormalised
quaternion is dangerous: if \(\|q\| = 1.01\), the resulting matrix carries
about 2% of scale, and it is still *almost* a rotation, so nothing throws.

### Interpolation: slerp

\[
\mathrm{slerp}(q_0, q_1, t) = \frac{\sin((1-t)\Omega)}{\sin\Omega}\, q_0 + \frac{\sin(t\Omega)}{\sin\Omega}\, q_1
\]

where \(\Omega = \arccos(q_0 \cdot q_1)\), **after** flipping the sign of
\(q_1\) if the dot product is negative. That sign flip is the double cover
again: without it you interpolate the long way round, up to 358° of
unnecessary rotation.

Two practical notes the formula does not show. When \(\Omega \to 0\) the
denominator vanishes and you must fall back to plain linear interpolation
plus normalisation — the two agree to first order, so the seam is invisible.
And slerp gives *constant angular velocity*, which is what makes it correct
for replaying recorded motion; naive linear interpolation of the four
components speeds up in the middle of the arc.

## D. From ML to robotics

**Unit quaternions are normalised embeddings.** Both live on a hypersphere,
both compare by dot product, and both need re-normalisation after arithmetic
or they silently degrade. Slerp is exactly the geodesic interpolation you may
already know as the right way to interpolate in a latent space — and naive
lerp is wrong here for the same reason it is wrong there.

**Why four numbers for a three-DOF quantity?** For the same reason
over-parameterisation often helps in machine learning: the minimal
three-parameter charts necessarily contain singularities. This is a theorem,
not an engineering failure — you cannot smoothly cover a sphere with a single
flat chart, which is also why every world map distorts something. The fourth
dimension buys a globally smooth, singularity-free representation, and the
price is one constraint (\(\|q\| = 1\)) plus the double cover.

**Convention chaos is schema drift.** Scalar-first `[w,x,y,z]` (this
curriculum, Eigen, most of the literature) versus scalar-last `[x,y,z,w]`
(ROS messages, SciPy). Both are correct. Mixing them is the robotics
equivalent of a silently reordered CSV column: everything runs, nothing is
right, and the error is a scramble rather than a small offset — which
perversely makes it easier to spot than a subtle one.

### Gimbal lock, concretely

Worth making tangible, because "a singularity in the parameterisation" is easy
to nod along to and hard to picture.

Take the common aerospace convention: yaw about \(z\), then pitch about the
new \(y\), then roll about the new \(x\). Now pitch the nose up to exactly
90°. The aircraft's \(x\)-axis now points along the world \(z\)-axis — which
is the *same axis* the yaw rotation used. Yaw and roll have become the same
motion. You have three knobs and only two independent effects: one degree of
freedom has vanished.

The robot can still physically rotate in that lost direction. The
*representation* cannot express it, so a controller working in Euler angles
either stalls or produces an enormous correction as the parameterisation
snaps. That is the drone flipping.

## E. Minimal implementation

Library:
[`robotics_ai/geometry/rotations3d.py`](https://github.com/paulyonghaoli/robotics-for-ai-engineers/blob/main/robotics_ai/geometry/rotations3d.py).
The essential core:

```python
import numpy as np

def quat_from_axis_angle(axis, angle):
    """Unit quaternion for `angle` radians about `axis`, scalar-first."""
    axis = axis / np.linalg.norm(axis)
    half = 0.5 * angle
    return np.concatenate(([np.cos(half)], np.sin(half) * axis))

def quat_multiply(q1, q2):
    """Hamilton product. quat_multiply(a, b) applies b FIRST."""
    w1, x1, y1, z1 = q1; w2, x2, y2, z2 = q2
    return np.array([
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
    ])

def quat_rotate(q, v):
    """Rotate 3-vector v by unit quaternion q, via the sandwich product."""
    qv = np.concatenate(([0.0], v))
    q_conj = q * np.array([1.0, -1, -1, -1])
    return quat_multiply(quat_multiply(q, qv), q_conj)[1:]
```

### A worked example

Rotate the vector \((1, 0, 0)\) by 90° about the \(z\)-axis. By hand:

1. \(\theta = 90°\), so the half-angle is 45°.
2. \(q = [\cos 45°,\; 0,\; 0,\; \sin 45°] \approx [0.7071, 0, 0, 0.7071]\).
3. A 90° rotation about \(z\) takes \(+x\) to \(+y\), so we expect
   \((0, 1, 0)\).

`quat_rotate(q, [1,0,0])` returns `[0, 1, 0]` to machine precision. Note that
neither the axis nor the angle appears directly in the quaternion — the axis
is scaled by \(\sin(\theta/2)\) and the angle is buried in a cosine. Reading a
quaternion by eye is a skill you will not develop and do not need; convert to
axis–angle when debugging.

### Practice — write and run code here

<code-exercise src="geo-l2-quat-compose"></code-exercise>

<code-exercise src="geo-l2-slerp"></code-exercise>

## F. Robotics-framework implementation

ROS 2 sends orientation as `geometry_msgs/Quaternion` with fields
`x, y, z, w` — **scalar-last**. Convert at the boundary, in exactly one
place, and never in application code:

```python
def to_ros(q_wxyz):                      # our convention -> wire format
    w, x, y, z = q_wxyz
    return Quaternion(x=x, y=y, z=z, w=w)
```

SciPy's `Rotation.from_quat` is also scalar-last by default. Eigen and this
curriculum are scalar-first. There is no winning this argument; there is only
converting in one place and validating at ingest.

Module 6 revisits this when we build a real TF tree, and the
[frame-debugging lab](06-lab-frame-debugging.md) includes a deliberately
mixed-convention bug to find.

## G. Experiment — which representation rots faster

Compose a small rotation — 1° about a tilted axis — with itself 100,000
times, once with rotation matrices and once with quaternions, renormalising
**neither**. Measure two things over time:

- for the matrix, \(\|R R^\top - I\|\);
- for the quaternion, \(\bigl|\,\|q\| - 1\,\bigr|\).

Then repeat *with* renormalisation each step. For the quaternion that is one
line, `q /= np.linalg.norm(q)`. For the matrix it is an SVD or a Gram–Schmidt
pass — orders of magnitude more expensive.

You will find two things, and the second matters more than the first. The
quaternion drifts more slowly, because it has one constraint to violate rather
than six. And **fixing the quaternion is trivially cheap while fixing the
matrix is not**, which is the practical reason estimators integrate
orientation as quaternions and convert to matrices only when they need to
transform a batch of points.

## H. Failure modes

- **Convention mismatch** (scalar-first vs scalar-last). Rotations come out
  scrambled rather than slightly wrong. Code full of internal round-trips can
  appear to work until it crosses a library boundary — which is why the bug
  usually surfaces during integration, far from its cause.
- **Forgetting the double cover.** Averaging \(q\) and \(-q\) gives zero. A
  tracking filter that does not enforce \(q_k \cdot q_{k-1} \ge 0\) reports
  phantom 360° jumps while the physical sensor moved smoothly.
- **Unnormalised quaternions.** After long integration \(\|q\| \neq 1\), and
  `quat_to_matrix` silently produces a matrix carrying scale. Point clouds
  slowly grow or shrink — the same symptom as matrix drift in lesson 1.1, from
  a different cause.
- **Naive lerp instead of slerp** across large angular differences. The
  interpolated orientation speeds up mid-arc and the norm dips, visible as a
  "pinch" in animation.
- **Euler angles as internal state.** Fine as human-readable input and
  output. Catastrophic in the core of a pipeline near ±90° pitch, where
  gimbal lock collapses a degree of freedom.

## I. Questions

1. *(Concept)* Why do quaternions use half-angles? What specifically goes
   wrong with \(q = [\cos\theta, \sin\theta\,\hat{n}]\)?
2. *(Calculation)* Compute the quaternion for a 180° rotation about the
   \(z\)-axis, and verify it by rotating \((1, 0, 0)\).
3. *(Debugging)* An attitude estimator's output occasionally "spins" 360° in
   a single frame while the physical IMU moved smoothly. What is the bug?
4. *(System design)* Your logging format stores orientations. Choose a
   representation and justify it against: interpolation for replay, storage
   size, human debuggability, and convention safety across three consumer
   teams.

??? note "Answer sketches"
    **1.** Rotation is the two-sided product \(v' = q\,v\,q^{*}\), so the
    quaternion's angle is applied twice — once by \(q\) and once by
    \(q^{*}\) — and the half-angle is exactly what makes the sandwich come out
    to \(\theta\). With \(q = [\cos\theta, \sin\theta\,\hat n]\) the sandwich
    rotates by \(2\theta\), so every rotation doubles and, worse, quaternion
    multiplication no longer corresponds to composing the rotations that the
    factors name — the algebra stops being useful.

    **2.** \(\theta = 180°\) about \(\hat n = (0,0,1)\) gives half-angle 90°,
    so \(q = [\cos 90°, 0, 0, \sin 90°] = [0, 0, 0, 1]\). Rotating
    \((1,0,0)\): the first column of \(R(q)\) with \(w = x = y = 0, z = 1\) is
    \([1-2(y^2+z^2),\; 2(xy+wz),\; 2(xz-wy)] = [1-2,\;0,\;0] = (-1,0,0)\).
    So \(+x\) flips to \(-x\), as a 180° turn about \(z\) must.

    **3.** Consecutive estimates crossed the double cover: the filter, or its
    output serialiser, is not enforcing \(q_k \cdot q_{k-1} \ge 0\). Sign-align
    each output against the previous one. Note the giveaway in the symptom —
    *exactly* 360°, and in a *single* frame. Physical motion cannot do that,
    so the bug is in the representation, not the sensor.

    **4.** Store unit quaternions, scalar-first, with the ordering and the
    frame pair named in the schema header and validated at ingest: 4 floats,
    directly slerp-able for replay, no gimbal lock, and one documented
    convention is what stops three consumer teams each guessing. Canonicalise
    the sign on write (\(w \ge 0\)) so the double cover never reaches a
    consumer, and normalise on write so no reader inherits a scale-carrying
    rotation matrix. Human debuggability is the only real loss — recover it in
    the log *viewer* by printing derived roll–pitch–yaw beside the raw
    quaternion, never by storing Euler angles as the source of truth.

### Interactive quiz

<quiz-bank src="geometry-l2-quats"></quiz-bank>

## J. Annotated references

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Lynch & Park, *Modern Robotics*, ch. 3.2–3.3 | book | introductory | Rotation matrices and exponential coordinates, cleanly and free |
| Sola, *"Quaternion kinematics for the error-state Kalman filter"* (2017) | paper | intermediate | The reference every estimation engineer keeps open. Read §1–2 now and the rest during Module 3 |
| Shoemake, *"Animating rotation with quaternion curves"* (1985) | paper | intermediate | The original slerp paper — short, readable, and the source of the technique |
| [REP 103 — Standard Units and Coordinate Conventions](https://www.ros.org/reps/rep-0103.html) | docs | introductory | ROS's conventions, including quaternion ordering. Two pages |

## K. Graded work and portfolio extension

**Graded:** the [frame-transforms mini-project](project-frames.md) covers this
module's 2D core; quaternion tasks join the Module 1 final assignment.

**Portfolio:** turn the section G drift experiment into a short plotted
write-up — matrix versus quaternion drift, with and without renormalisation,
and cost per step for each. It makes a strong short blog post precisely
because the conclusion is quantitative and mildly surprising, and it
demonstrates that you measure before claiming.
