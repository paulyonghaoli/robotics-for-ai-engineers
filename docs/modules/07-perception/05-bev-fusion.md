# 7.5 BEV and fusion: two sensors, one frame, one clock

**Status:** Code verified · **Prereqs:** lessons 7.1, 7.4 · **Time:** ~2.5 h · **Verified:** 2026-08-03, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

A camera knows *what* something is. A lidar knows *where* it is. Neither is much use alone in a system that has to decide whether to brake.

Fusing them sounds like a modelling problem and is mostly a bookkeeping problem. Both sensors must be expressed in one spatial frame, and both must describe the same *instant*. Get either wrong and you produce a confident, well-formed, entirely fictional scene — an object with a car's appearance and a wall's position, or a pedestrian placed where they were 80 ms ago.

The two errors look almost identical in a single frame and completely different across frames, which is the whole diagnostic story of this lesson.

## B. Mental model

**BEV is the shared frame.** Bird's-eye view works as a fusion space because it is the frame in which the *task* lives: planning, tracking and prediction all happen on the ground plane. Camera features get lifted into it (via depth, learned or measured), lidar features get flattened into it (via [7.4's](04-3d-detection.md) pillars), and once both are there they are just channels of the same tensor.

**Two transforms and a clock.** Every fused pipeline carries:

| | What it is | How it goes wrong |
|---|---|---|
| **Extrinsics** `T_cam_lidar` | a fixed rigid transform between sensors | a small *rotation* error, which grows linearly with range |
| **Ego motion** `T_t1_t0` | where the robot moved between captures | ignored entirely, which is the time-sync bug |
| **Timestamps** | when each sensor actually sampled | assumed equal because the messages arrived together |

**The asymmetry worth internalising:** an extrinsic rotation error of 0.5° puts a point 9 cm off at 10 m and 44 cm off at 50 m — it scales with range and is *constant over time*. A 60 ms time offset while turning at 0.6 rad/s is a 2° error — it scales with **speed**, not range, and changes every frame. Same symptom, opposite signatures.

## C. Formulation

Projecting a lidar point into the camera image is a chain, and the order is where the bugs live:

$$
\mathbf{p}_{cam} = T_{cam \leftarrow lidar}\,\mathbf{p}_{lidar},
\qquad
(u, v) = \pi\!\left(K\,\mathbf{p}_{cam}\right)
$$

With motion between the two captures, one more transform belongs in the middle:

$$
\mathbf{p}_{cam}(t_{cam}) = T_{cam \leftarrow lidar}\;T_{lidar(t_{cam}) \leftarrow lidar(t_{lidar})}\;\mathbf{p}_{lidar}(t_{lidar})
$$

That middle term is identity **only** if the two sensors sampled at the same instant. They never do.

**Lateral error from a small rotation** at range `Z`:

$$
e \approx Z \sin\theta \approx Z\theta
$$

**Lateral error from a time offset** `Δt` at yaw rate `ω`, again at range `Z`:

$$
e \approx Z\,\omega\,\Delta t
$$

Both are linear in `Z`, which is why a single frame cannot separate them. Only `ω` distinguishes the two, and `ω` is something you already log.

### Sixty milliseconds of disagreement, in pixels

This lesson's exercise carries a lidar sampled 60 ms before the camera —
an ordinary offset for unsynchronised sensors — and projecting the stale
points through the extrinsics as if simultaneous costs, at three turn rates:

| Robot turn rate | Mean pixel error of naive projection |
|---|---|
| 0.3 rad/s (gentle arc) | 11.3 px |
| 0.8 rad/s (ordinary corner) | **30.1 px** |
| 1.5 rad/s (tight turn) | 56.7 px |

Thirty pixels is the width of a pedestrian at mid-range: paint-by-projection
at that error rate colours the road surface with pedestrian labels and the
pedestrian with road. Note what the number depends on — not the offset alone
but the offset *times the motion*, which is why the bug class is so
treacherous: on the bench the robot is stationary, the 60 ms costs zero
pixels, and every fusion demo looks perfect. The error budget only activates
when the robot moves, growing linearly with angular rate, and the fix is
lesson 6.4's, verbatim — transform each sensor's data at *its own* timestamp
through the TF buffer, letting interpolation absorb the offset. Motion
compensation is not a refinement of sensor fusion; below about 30 px of
tolerable error, it is a precondition for it.

## D. From ML to robotics

**What transfers:** multi-modal fusion architecture, attention across modalities, the whole late/early/mid fusion vocabulary.

**What is new and non-negotiable:** the model cannot learn its way out of a calibration error. A network trained on data with a consistent 0.5° extrinsic bias will absorb it and appear to work — until the mount is bumped and the bias changes, at which point performance collapses for reasons no retraining diagnoses.

**The practical consequence:** calibration and synchronisation are *upstream invariants*, and you test them separately from the model. Projecting lidar onto the image and looking at whether points land on objects is a five-minute check that catches an entire class of failure, and it is worth wiring into CI as a fixture rather than doing by eye once a quarter.

## E. Practice

<code-exercise src="per-l5-extrinsics"></code-exercise>

<code-exercise src="per-l5-timesync"></code-exercise>

## F. In production

BEVFusion and its descendants are the standard architecture in 2026: lift camera features into BEV, flatten lidar into BEV, concatenate, run a shared head. The interesting engineering is almost never the fusion module.

- **Hardware sync** where you can get it. A trigger line that fires the camera when the lidar sweep crosses its optical axis removes the problem instead of compensating for it.
- **Motion compensation** where you can't. Every point in a spinning lidar sweep has its *own* timestamp; the sweep is not an instant either, and at 10 Hz the first and last points are 100 ms apart.
- **Continuous extrinsic monitoring.** Compare the projection residual against a known target, or track the disagreement between per-sensor detections. A slow drift in that residual is a bumped mount, and it is much cheaper to detect than to explain later.

## G. Experiment

Fix a yaw rate and sweep the time offset from 0 to 100 ms; separately, fix the offset at zero and sweep the extrinsic yaw error from 0 to 1°. Plot lateral error against range for both. The two families of curves are indistinguishable — and then plot each against yaw rate instead, where one is flat and the other is a straight line through the origin. That second plot is the diagnostic, and it is why you log ego motion beside every fused frame.

## H. Failure modes

- **Extrinsic rotation error.** Projected points land consistently off to one side, worse with range, identical from frame to frame regardless of what the robot is doing.
- **Time offset.** Projection is perfect when stationary and degrades in proportion to turn rate. If your fusion "gets worse in corners," stop looking at the calibration.
- **Translation-only calibration.** Tempting because it is easy to measure with a tape. It cannot fix a rotation error, and a rotation error is what you almost always have.
- **Assuming the sweep is an instant.** A 10 Hz spinning lidar spreads its points over 100 ms. At 15 m/s that is 1.5 m of ego motion smeared across a single "frame."
- **Sync by arrival time.** Messages arriving together says something about your network, not about when the photons landed. Use sensor timestamps.

## I. Questions

<quiz-bank src="per-l5-quiz"></quiz-bank>

## J. References

- Liu et al., *BEVFusion* (2022) — the shared-BEV-space argument, clearly made.
- Philion & Fidler, *Lift, Splat, Shoot* (2020) — how camera features get into BEV without a depth sensor.
- Geiger et al., *Automatic Camera and Range Sensor Calibration* (2012) — the KITTI calibration methodology, and a good survey of what goes wrong.
- Furgale, Rehder & Siegwart, *Unified Temporal and Spatial Calibration* (2013) — Kalibr's foundation, and the paper that treats the time offset as a parameter to estimate rather than a nuisance to assume away.

## K. Graded work & portfolio extension

**Graded:** the two exercises above.

**Portfolio:** build the two-panel diagnostic from section G — lateral error against range (where the two causes are indistinguishable) beside lateral error against yaw rate (where they separate cleanly). Annotate it with the residual your own pipeline shows. A figure that turns "fusion seems off" into a decision between two specific, differently-fixed causes is worth considerably more than a better fusion architecture.
