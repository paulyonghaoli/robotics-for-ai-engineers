# 7.1 Camera models: pixels are rays

**Status:** Code verified · **Prereqs:** lessons 1.1, 1.3 · **Time:** ~2 h · **Verified:** 2026-08-03, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

A neural network sees an image as a grid of numbers. A robot has to answer a different question: *given that this pixel lit up, where in the world could the thing that lit it be?*

The answer is never a point. A single pixel constrains the world to a **ray** — one degree of freedom is gone forever the moment 3D was flattened to 2D. Everything downstream in perception is an argument about how to recover it: from a second camera (7.2), from a depth sensor, from motion over time, or from a prior about what objects look like.

Get the camera model wrong and every one of those recoveries inherits the error, silently and systematically. This is why calibration is not paperwork.

## B. Mental model

Three coordinate frames, in this order, and most camera bugs are a confusion between two of them:

| Frame | Units | What it is |
|---|---|---|
| **World** | metres | where things actually are |
| **Camera** | metres | the same points, rotated and translated so the camera is at the origin looking down +Z |
| **Image** | pixels | the camera-frame points divided by their depth, then scaled |

The move from camera frame to image is the lossy one, and it is just division:

```
u = fx · (X/Z) + cx
v = fy · (Y/Z) + cy
```

Divide by Z and you have thrown Z away. That single division is the whole problem of 3D perception, and it is worth remembering that it is not a difficult operation being approximated — it is an exactly-known operation that is *not invertible*.

**The extrinsics/intrinsics split.** Intrinsics (`K`) describe the *camera*: focal lengths, principal point, distortion. They stay fixed if you move the camera. Extrinsics (`R`, `t`) describe *where the camera is*. They change every frame on a moving robot. Conflating them is the single most common calibration bug, and it presents as a perception error that mysteriously depends on where the robot is standing.

## C. Formulation

The pinhole projection, written as a matrix chain:

$$
\begin{bmatrix} u \\ v \\ 1 \end{bmatrix} \sim
K \, [\,R \mid t\,]
\begin{bmatrix} X_w \\ Y_w \\ Z_w \\ 1 \end{bmatrix},
\qquad
K = \begin{bmatrix} f_x & 0 & c_x \\ 0 & f_y & c_y \\ 0 & 0 & 1 \end{bmatrix}
$$

The `~` matters: the result is a *homogeneous* vector, defined up to scale. You recover pixels by dividing through by the third component, and that division is the projection.

**Unprojection** goes the other way and returns a ray, not a point:

$$
\mathbf{d}_{cam} = K^{-1} \begin{bmatrix} u \\ v \\ 1 \end{bmatrix}
$$

Any world point along $s\,\mathbf{d}_{cam}$ for $s > 0$ projects back to exactly $(u,v)$. Choosing $s$ is what a depth sensor, a stereo pair, or an object-size prior buys you.

**Radial distortion** breaks the straight-line assumption near the image edges. With $r^2 = x^2 + y^2$ on the normalized plane:

$$
x_d = x\,(1 + k_1 r^2 + k_2 r^4), \qquad y_d = y\,(1 + k_1 r^2 + k_2 r^4)
$$

Note $r^2$: the correction is negligible at the centre and grows quadratically outward. A model that ignores distortion is *nearly perfect* in the middle of the image, which is exactly why the bug survives testing.

## D. From ML to robotics

You already have the linear algebra. What is new is that these matrices have **units and physical meaning**, so an error in one is not a slightly worse fit — it is a claim about the world that is wrong in a structured way.

- `fx` wrong by 2% → every depth estimate wrong by 2%, growing linearly with range
- `cx, cy` wrong by 5 px → a bearing bias that rotates your whole map
- distortion ignored → errors that are zero where you looked and large at the edges, where the obstacles you are about to hit appear first

And unlike a training loss, none of these produce a number that goes up. They produce a system that is confidently, consistently, geometrically wrong.

## E. Practice

<code-exercise src="per-l1-project"></code-exercise>

<code-exercise src="per-l1-distortion"></code-exercise>

## F. In production

OpenCV's `calibrateCamera` with a checkerboard is still the standard path, and ROS 2 ships `camera_calibration` around it. What matters more than the tool is the discipline:

- **Calibrate at the working distance.** A calibration done at 0.5 m and used at 20 m extrapolates, and the residual you were shown does not cover that range.
- **Report reprojection error per-region, not just the mean.** A 0.3 px mean can hide 2 px at the corners, which is precisely where distortion lives.
- **Recalibrate after anything mechanical.** A dropped camera, a retightened mount, a thermal cycle. Intrinsics are properties of a physical object.
- **Store the calibration with the data.** A bag file without its calibration is not replayable, which is a [Module 12](../../curriculum.md) concern arriving early.

## G. Experiment

Take a synthetic 20 m × 20 m grid of world points, project it with a correct `K`, then re-project with `fx` scaled by 1.02 and unproject both back to rays. Plot the angular error against distance from the image centre. You will find the bearing error is essentially flat — a focal error is a *scale* error, not a pointing error — while the same experiment with `cx` shifted by 5 px produces a bias that does not shrink with range. Two calibration parameters, two completely different failure signatures.

## H. Failure modes

- **Intrinsics/extrinsics confusion.** Perception error that depends on the robot's position. If the error rotates with the robot, you have an extrinsics problem; if it scales with range, suspect focal length.
- **Distortion ignored.** Accurate in the image centre, degrading toward the edges. Detections near the frame boundary get mislocated by metres at range.
- **Principal point assumed to be the image centre.** It usually isn't, by a few pixels, and the resulting bearing bias integrates into a map as a slow curve.
- **Rolling shutter treated as global.** Rows are captured at different times; on a robot turning at 1 rad/s with a 20 ms readout, the top and bottom of the frame are 1.1° apart in world orientation.
- **Resolution changed without rescaling `K`.** Downsampling an image by 2 halves `fx, fy, cx, cy`. Forgetting this is a silent 2× depth error.

## I. Questions

<quiz-bank src="per-l1-quiz"></quiz-bank>

## J. References

- Hartley & Zisserman, *Multiple View Geometry*, ch. 6 — the definitive treatment of the camera matrix; read 6.1–6.2 and skip the projective-geometry generality on a first pass.
- Szeliski, *Computer Vision: Algorithms and Applications*, §2.1.4 — a gentler derivation with better diagrams.
- Zhang, *A Flexible New Technique for Camera Calibration* (2000) — the paper behind essentially every checkerboard calibrator you will ever run.
- OpenCV `calib3d` documentation — specifically the distortion-model section, which names the coefficient conventions that differ between libraries and cause a great deal of confusion.

## K. Graded work & portfolio extension

**Graded:** the two exercises above, plus the projection and unprojection components of the [perception mini-project](project-perception.md).

**Portfolio:** build a calibration-sensitivity figure — for each of `fx`, `cx`, `k1`, perturb it by a realistic calibration residual and plot the resulting world-space error against range and against image position. Three parameters, three distinct error surfaces. It is a genuinely useful artifact, because the question "how good does my calibration need to be?" is asked constantly and almost never answered with numbers.
