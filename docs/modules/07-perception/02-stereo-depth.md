# 7.2 Stereo and depth: the error grows as Z²

**Status:** Code verified · **Prereqs:** lesson 7.1 · **Time:** ~2 h · **Verified:** 2026-08-03, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

[7.1](01-camera-models.md) left you with a ray. A second camera gives you a second ray, and two rays that intersect give you back the depth the projection threw away.

The important part is not that this works — it is *how the accuracy behaves*. Stereo depth error grows with the **square** of range, and that single fact determines where a stereo-equipped robot can safely drive, how fast, and what it must refuse to make decisions about. A depth camera that is accurate to 1 cm at 2 m is accurate to 25 cm at 10 m and 1 m at 20 m, from the same hardware, with nothing broken.

Teams discover this in the field constantly, usually as "the depth camera gets bad far away." It is not bad far away. It is doing exactly what the geometry says, and the geometry was knowable in advance.

## B. Mental model

Two cameras, separated by a **baseline** `B`, looking the same direction. A world point at depth `Z` appears in both images, shifted horizontally by a **disparity** `d` — and disparity is the entire signal:

```
Z = f · B / d
```

Far away → small disparity. At infinity, disparity is zero and the two images are identical. All the depth information is in a difference that shrinks as the thing you care about gets further away.

Now differentiate. Because `Z ∝ 1/d`, a fixed disparity uncertainty `σ_d` (which is what you actually have — matching is good to some fraction of a pixel, roughly independent of range) becomes a depth uncertainty:

$$
\sigma_Z \;=\; \frac{Z^2}{f B}\,\sigma_d
$$

**That `Z²` is the whole lesson.** It is not a modelling choice or an artifact of a particular matcher; it follows from the reciprocal relationship. No amount of better matching removes it, and the only levers you have are `f`, `B`, and `σ_d`, all three of which are linear.

## C. Formulation

For a **rectified** pair — the two images transformed so that corresponding points share a row — with left pixel `(u_L, v)` and right pixel `(u_R, v)`:

$$
d = u_L - u_R, \qquad Z = \frac{f\,B}{d}, \qquad X = \frac{(u_L - c_x)\,Z}{f}, \qquad Y = \frac{(v - c_y)\,Z}{f}
$$

Rectification is what makes matching a 1D search along a row instead of a 2D search over the image, which is the difference between a real-time system and an offline one.

Propagating uncertainty through $Z = fB/d$:

$$
\frac{\partial Z}{\partial d} = -\frac{fB}{d^2} = -\frac{Z^2}{fB}
\quad\Longrightarrow\quad
\sigma_Z = \frac{Z^2}{fB}\,\sigma_d
$$

Some numbers worth carrying around, for `f = 600 px`, `B = 0.12 m`, `σ_d = 0.25 px`:

| Range | Disparity | σ_Z |
|---:|---:|---:|
| 2 m | 36.0 px | 1.4 cm |
| 5 m | 14.4 px | 8.7 cm |
| 10 m | 7.2 px | 35 cm |
| 20 m | 3.6 px | 1.4 m |

At 20 m the disparity is under four pixels. There is almost nothing left to measure.

## D. From ML to robotics

You are used to models whose error is roughly stationary across the input distribution — a detector is about as good on one image as another. Here the error is a **known function of the output**, and that changes what you do with it.

- **Never threshold depth without range-dependent tolerance.** "Is this obstacle within 30 cm of the path?" is answerable at 3 m and meaningless at 20 m.
- **Feed σ_Z into the filter, not a constant.** [Module 3's](../03-estimation/01-kalman.md) measurement noise `R` should be a function of the measured range. A constant `R` makes the filter overconfident precisely where it is worst.
- **Learned stereo doesn't repeal it.** A network can push `σ_d` down and interpolate texture-less regions, but Z²/(fB) is geometry. It sets the floor.

## E. Practice

<code-exercise src="per-l2-triangulate"></code-exercise>

<code-exercise src="per-l2-error-budget"></code-exercise>

## F. In production

Realsense, ZED and friends publish their baselines and expected error curves — read them before choosing where to mount, because `B` is the one parameter you control at design time and it enters linearly. Doubling the baseline halves the depth error at every range.

The trade is field of view overlap: a wider baseline sees less in common, and nothing is measurable in the region only one camera can see. That near-field blind zone scales with `B` too, so the "better" sensor is the one matched to your working range rather than the one with the best spec-sheet number.

Structured-light and time-of-flight sensors have completely different error models — ToF error is roughly constant with range, not quadratic — which occasionally makes a much cheaper sensor the right answer at long range.

## G. Experiment

Take the error table above and re-derive it for a 0.5 m baseline — a wide stereo rig on a vehicle roof rather than a handheld camera. Then plot both curves with your *decision threshold* overlaid: the range at which σ_Z exceeds, say, half a lane width. That crossing point is the honest maximum operating range of the sensor, and it is a number most teams never write down.

## H. Failure modes

- **Texture-less surfaces.** A blank white wall has no features to match, so disparity is undefined. Matchers return *something* — often a confidently wrong plane. Check the confidence channel; do not treat missing data as far away.
- **Repetitive texture.** Railings, tiles, fences. The matcher locks onto the wrong period and returns a depth that is wrong by a fixed, plausible-looking offset.
- **Occlusion.** Regions visible to one camera only have no correspondence by construction. This band sits along every depth discontinuity — that is, at the edge of every obstacle.
- **Constant depth variance in the filter.** The most common downstream bug, and it makes the estimator most overconfident exactly where the measurement is weakest.
- **Decalibrated baseline.** `B` off by 1% is every depth off by 1%. Thermal expansion and mounting flex both do this, and there is no signature in the images.

## I. Questions

<quiz-bank src="per-l2-quiz"></quiz-bank>

## J. References

- Szeliski, *Computer Vision*, ch. 12 — stereo correspondence, with the rectification treatment worth reading closely.
- Hirschmüller, *Semi-Global Matching* (2008) — still the workhorse behind a great deal of production stereo.
- Hartley & Zisserman ch. 11 — triangulation done properly, including why the midpoint method is not the optimal one.
- Intel RealSense depth-quality documentation — an unusually honest vendor treatment of the error model, and a good template for the numbers you should demand of any depth sensor.

## K. Graded work & portfolio extension

**Graded:** the two exercises above, plus the triangulation and error-propagation components of the [perception mini-project](project-perception.md).

**Portfolio:** produce the operating-envelope figure from section G for two or three real sensors you could actually buy, using their published baselines and pixel accuracies, with your application's tolerance drawn across it. Sensor selection justified with a derived error curve rather than a spec-sheet range is exactly the kind of artifact that reads as engineering judgement rather than shopping.
