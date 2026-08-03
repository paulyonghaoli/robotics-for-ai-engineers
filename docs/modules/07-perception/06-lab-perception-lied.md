# 7.6 Lab: the perception stack that lied

**Status:** Code verified · **Prereqs:** lessons 7.1–7.5 · **Time:** ~2 h · **Verified:** 2026-08-03, Python 3.13, NumPy ≥ 1.26

---

## A. Why this lab exists

None of the three systems here has a broken sensor, a weak model, or a bug in any algorithm. Every one produces a confident, well-formed, internally consistent answer that is wrong about the world.

That is the characteristic shape of perception failure. A detector that crashes gets fixed before lunch. The ones that cost a quarter are the ones that keep returning plausible numbers after an assumption underneath them stopped holding — a calibration that describes a sensor you no longer have, a placeholder that reads as a measurement, a preprocessing step that silently removed the units.

Each bug below is diagnosable in about two minutes *from the probe*, and essentially undiagnosable by reading the code and thinking hard about it.

## B. The diagnostic table

| Symptom | The tempting explanation | The assumption that actually broke |
|---|---|---|
| Every distance halved after a hardware upgrade | the new sensor is worse | **`K` is in pixels** — it scales with resolution |
| Robot plans through a wall the sensor can see | the planner is broken | **a placeholder became a measurement** |
| Classifier flips depending on scene clutter | the model needs more data | **normalisation deleted metric scale** |
| Fusion drifts only in corners | the extrinsic calibration | **the two sensors sampled at different times** ([7.5](05-bev-fusion.md)) |
| Depth confident on a blank wall | the wall genuinely is flat | **no texture, no correspondence** ([7.2](02-stereo-depth.md)) |

## C. The gauntlet

<code-exercise src="per-l6-bug-resolution"></code-exercise>

The team doubled the resolution with the same lens, so the field of view is identical and the picture is strictly better — and every range estimate halves. A factor of exactly two, arriving the same day the pixel count doubled, is not a quality problem. `fx` is a focal length expressed **in pixels**: same angle, twice as many pixels across it, twice the `fx`. The stored calibration describes a sensor that no longer exists.

<code-exercise src="per-l6-bug-invalid-depth"></code-exercise>

This one is the most instructive, because the bug was introduced *deliberately, as a safety measure.* Missing depth defaults to "far away" so the robot will not panic about dropouts. But sixteen beams looking at a blank wall three metres ahead return no measurement — the matcher has no texture to work with — and "far away" turns *I could not see* into *I looked, and it is clear.* The robot then plans straight through the one region it had no information about.

There are three states, not two, and collapsing "unknown" into either neighbour fabricates evidence. Note also that inventing an obstacle would be the same error with the opposite sign: the fix is to preserve the distinction and let the consumer choose, not to pick a safer lie.

<code-exercise src="per-l6-bug-normalized"></code-exercise>

Zero mean, unit scale. It is the most automatic gesture in machine learning and it is exactly wrong here. Dividing by the scene's extent expresses every length as a fraction *of that scene*, so a 0.7 m pedestrian measures 0.09 in a tight scene and 0.012 in an open one, and a size threshold becomes a function of how much clutter is in view. Metric scale is the thing a point cloud gives you that an image cannot ([7.3](03-point-clouds.md)); centring is fine, rescaling throws it away.

## D. Diagnosis drills

<quiz-bank src="per-l6-drills"></quiz-bank>

## E. Debrief: the method

**Check the units on your constants.** Bug 1 is a units error wearing a hardware-quality costume. `fx` is pixels, `Z` is metres, `k1` is dimensionless, `B` is metres — and any constant that came from a calibration is a claim about a specific physical configuration that may no longer be true.

**Never let a placeholder cross an interface.** Bug 2's `MAX_RANGE` default is indistinguishable from a real max-range return one function call later. This is the same failure as the capstone's phantom max-range ring and the mini-project's zero-depth dropouts — three appearances of one idea, which is why it is worth naming: **the absence of a measurement must remain distinguishable from a measurement.**

**Ask what a transformation removed.** Bug 3's normalisation is reversible arithmetic that destroys irreversible information. Before applying a reflex from another domain, ask what property it assumes is irrelevant — and whether that property was the reason you chose this sensor.

## F. Graded work & portfolio extension

**Graded:** the three fixes are Module 7's diagnostic assessment, and they compose with the [perception mini-project](project-perception.md), where the same "measured nothing versus measured zero" discipline is worth 55 of 100 points.

**Portfolio:** write the calibration-invariant test suite these bugs would have caught — assertions that run against a recorded frame and a stored calibration, checking that a known target's range is recovered at two resolutions, that invalid returns never map to free space, and that a known object's measured size is independent of scene extent. Wiring those into CI as fixtures is a small, unglamorous artifact that demonstrably prevents an entire class of field failure, which is a more convincing thing to show than a better detector.
