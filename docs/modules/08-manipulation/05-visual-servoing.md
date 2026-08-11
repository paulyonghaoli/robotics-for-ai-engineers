# 8.5 Visual servoing: closing the loop through the camera

**Status:** Code verified · **Prereqs:** lessons 8.1, 7.1 · **Time:** ~2 h · **Verified:** 2026-08-03, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Everything so far has been open loop with respect to vision. Perceive the object, plan a path, execute it — and if the object was 2 cm from where you thought, you miss it by 2 cm.

Visual servoing closes that loop: keep looking while you move, and drive the *image* error to zero rather than the estimated *pose* error. The consequence is worth stating plainly, because it is the whole reason the technique exists: **you no longer need the object's pose to be right.** You need the image to converge, and errors in calibration, depth and hand-eye transform become disturbances the loop rejects rather than biases it inherits.

That is the same trade as [Module 3's](../03-estimation/index.md) closed-loop estimation, arriving in manipulation.

## B. Mental model

Two families, and the choice determines which errors hurt you.

| | Position-based (PBVS) | Image-based (IBVS) |
|---|---|---|
| Error is computed in | 3D pose space | image coordinates (pixels) |
| Needs | object pose estimate, good calibration | feature positions, a rough depth |
| Trajectory in the world | straight and predictable | can be strange |
| Trajectory in the image | can leave the frame | features stay in view by construction |
| Sensitive to | calibration error | depth error (mildly), local minima |

**The core idea of IBVS is the interaction matrix.** It relates camera velocity to the image velocity of a feature — the visual analogue of the Jacobian, and used the same way: build it, invert it (with damping), and step.

**Depth error is survivable, asymmetrically.** The interaction matrix contains `1/Z`, and *only in the translation columns* — rotation is unaffected. So a wrong depth rescales part of your step rather than misdirecting it, and the loop still points downhill.

But the two directions of error are not equivalent. **Underestimating `Z` shrinks the commanded translation**, making the loop conservative and slow: always safe. **Overestimating `Z` makes those columns too small, and inverting them amplifies the effective gain** — enough overestimate and the loop oscillates and stalls. Measured in the exercise: at gain 0.5, a 3× overestimate converges cleanly, 5× stalls, and 8× diverges — while 10× *under*estimate converges without complaint.

The practical rule follows: it is the **product of gain and depth error** that must stay in the stable region, so the two cannot be tuned independently, and when you are unsure of `Z` you should guess low.

## C. Formulation

For a point feature at image coordinates $(u, v)$ (normalised, so $x = (u-c_x)/f_x$) at depth $Z$, the interaction matrix relating camera velocity $\mathbf{v} = (v_x, v_y, v_z, \omega_x, \omega_y, \omega_z)$ to feature velocity is:

$$
L =
\begin{bmatrix}
-1/Z & 0 & x/Z & xy & -(1+x^2) & y \\
0 & -1/Z & y/Z & 1+y^2 & -xy & -x
\end{bmatrix}
$$

Stack one such block per feature, and the control law is a damped least-squares step toward the desired features:

$$
\mathbf{v} = -\lambda\, L^{+}\left(\mathbf{s} - \mathbf{s}^{*}\right)
$$

Three features give you a square-ish system; four is the usual choice, because three admits configurations with multiple solutions.

**The classic pathology** is a target rotated 180° about the optical axis. IBVS computes a motion that retreats the camera toward infinity — every feature moves correctly in the image while the camera does something absurd in the world. It is not a bug in the implementation; the image error genuinely decreases along that trajectory. It is the clearest demonstration that minimising image error and moving sensibly are different objectives.

### How wrong can the depth be — measured

The interaction matrix needs each feature's depth \(Z\), which the camera
does not measure, and IBVS's celebrated robustness is that a bad guess
mostly doesn't matter. Servoing this lesson's four-point target from a
displaced start, with the controller's depth deliberately scaled away from
truth:

| Depth estimate | Outcome |
|---|---|
| true Z × 0.25 | converged, 65 steps |
| × 0.5 | converged, 36 steps |
| × 1.0 | converged, 13 steps |
| × 2.0 | converged, 30 steps |
| × 4.0 | converged, 67 steps |
| × 10 | **diverged** — error stuck at 0.23 |

Depth wrong by a factor of four in either direction still converges,
merely two to five times slower — the wrong \(Z\) mis-scales the commanded
translation, the next image measurement absorbs the mistake, and the loop
grinds on. That tolerance is the entire justification for running IBVS with
a crude constant depth guess in practice. The 10× row shows the cliff:
scale the step badly enough and each correction overshoots what the next
measurement can retract, the ordinary stability-versus-gain failure from
lesson 2.2 arriving through a parameter labelled "depth" instead of one
labelled "gain". Feedback through the image forgives calibrated ignorance;
it does not forgive an effective loop gain of ten.

## D. From ML to robotics

The temptation is to regress camera velocity directly from images, and it works. What is worth keeping from the classical formulation is the **structure**: the interaction matrix says exactly how each degree of freedom moves each feature, and that is a strong inductive bias a network otherwise has to learn from data.

The practical hybrid, and what most modern systems do: learn the *features* — which points to track, which are stable under lighting and viewpoint — and keep the classical control law. The learned part handles perception, where learning is strong; the analytic part handles control, where guarantees matter and the physics is known.

## E. Practice

<code-exercise src="man-l5-ibvs"></code-exercise>

## F. In production

ViSP is the reference implementation and worth reading even if you write your own. What the textbooks understate:

- **Feature tracking is the hard part.** The control law is twenty lines; keeping four features reliably identified across viewpoint and lighting change is the project.
- **Depth can be crude.** A constant approximate `Z` for all features is a standard and surprisingly effective choice, precisely because of the scaling argument above.
- **Eye-in-hand versus eye-to-hand** changes the sign conventions and the hand-eye transform, and mixing them up produces a loop that diverges immediately — which is at least a fast failure.

## G. Experiment

Sweep the depth error from 0.1× to 8× at a fixed gain and record the final feature error. The stable region is wide and lopsided: everything below 1× converges, overestimates converge up to about 3.5×, and beyond that the loop oscillates and then stalls. Now repeat the sweep at a third of the gain and watch the unstable region disappear — evidence that it is the product that matters.

Then give a PBVS controller the same erroneous depth and watch it converge confidently to the wrong pose. That contrast is the argument for image-based control in one figure: one degrades, the other is quietly wrong.

## H. Failure modes

- **Features leaving the frame.** IBVS keeps them in view for small motions and has no such guarantee for large ones. Mitigate with a path in image space rather than a straight line to the goal.
- **The 180° retreat.** Large rotations about the optical axis produce absurd world trajectories. Partitioned or hybrid schemes exist precisely for this.
- **Local minima.** With more features than degrees of freedom the image error can stall at a non-zero minimum that is not the target.
- **Losing feature correspondence.** Swap two features and the loop drives confidently to a mirrored configuration.
- **Overestimating depth.** It inflates the effective gain and destabilises a loop that was well tuned at the true `Z`. Guess low when unsure.
- **Ignoring the arm's own limits.** The control law outputs a camera velocity; joint limits, singularities and self-collision all still apply, and the servo loop knows about none of them.

## I. Questions

<quiz-bank src="man-l5-quiz"></quiz-bank>

## J. References

- Chaumette & Hutchinson, *Visual Servo Control, Part I: Basic Approaches* (2006) — the standard tutorial, and the source of the interaction matrix as written above.
- Chaumette & Hutchinson, *Part II: Advanced Approaches* (2007) — partitioned and hybrid schemes, including the fixes for the retreat problem.
- Marchand et al., *ViSP* (2005) — the library.
- Levine et al., *Learning Hand-Eye Coordination for Robotic Grasping* (2016) — the learned end of the spectrum, and a useful contrast in what each approach assumes.

## K. Graded work & portfolio extension

**Graded:** the exercise above.

**Portfolio:** build the depth-robustness figure from section G — IBVS feature error against iteration for several wrong depths, beside PBVS converging confidently to the wrong pose with the same bad estimate. It demonstrates a property that is genuinely counter-intuitive, and explaining why the loop tolerates a 5× depth error is a good test of whether you understand what the interaction matrix is doing.
