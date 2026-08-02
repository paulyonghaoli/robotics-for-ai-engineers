# 4.5 Lab: the SLAM failure gallery

**Status:** Code verified · **Prereqs:** lessons 4.1–4.4 · **Time:** ~2 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this lab exists

SLAM fails in a small number of highly characteristic ways, and every one of them produces a map that looks *plausible*. There is no exception thrown, no assertion tripped — just a floor plan with a kink in it, or a corridor that's 30 cm too long. This lab is the gallery: each exercise hands you a failure and asks you to name it from the evidence, then fix it properly.

The through-line: **an optimizer will always give you an answer**. Your job is knowing when that answer is a consistent solution to an inconsistent problem.

## B. The diagnostic table

| Symptom | Prime suspect | Where it was taught |
|---|---|---|
| Map globally rotated/translated vs ground truth, internally crisp | **Not a bug** — gauge freedom; nothing anchors the map to the world | [4.3](03-ekf-slam.md) |
| Map "folds" catastrophically after adding place recognition | **False loop closure** — a confident lie the back-end must satisfy | [4.4](04-pose-graphs.md) |
| Pose slides 10–30 cm along a featureless corridor between matches | **Scan-matching degeneracy** — the cost surface is a valley, not a bowl | [4.2](02-scan-matching.md) |
| Walls smeared into arcs; map degrades with distance travelled | **Pose drift** — the mapper faithfully integrates a lying localizer | [4.1](01-occupancy-grids.md) |
| Alignment drifts toward a person who walked through the scan | **Untrimmed outliers** in ICP correspondence | [4.2](02-scan-matching.md) |
| Landmark estimates all shift together after one bad observation | **Data association error** propagating through the joint covariance | [4.3](03-ekf-slam.md) |

## C. The gallery

### Case 1: the confident lie

A pose graph with sixteen honest odometry edges, one honest loop closure — and one **false** closure claiming two different places are the same. Least squares will dutifully deform the entire trajectory to satisfy it. Your job: make the back-end robust enough to notice.

<code-exercise src="map-l5-false-closure"></code-exercise>

### Case 2: the corridor that slides

Scan matching in a featureless corridor converges to a confident, wrong answer along the corridor axis. The residual looks fine — because the cost surface really is flat in that direction. Your job: **detect the degeneracy before trusting the match**, and report honest uncertainty instead of a point estimate.

<code-exercise src="map-l5-degeneracy"></code-exercise>

## D. Diagnosis drills

<quiz-bank src="mapping-l5-drills"></quiz-bank>

## E. Debrief

Three habits generalize from this gallery to any estimation back-end you ever touch:

1. **Distrust confident residuals.** In both cases above, the optimizer's own reported error was small. A low residual means "consistent with my constraints," not "correct" — a distinction that costs a lot of debugging time to learn the hard way.
2. **Measure conditioning, not just the answer.** Degeneracy is visible *before* it corrupts anything, in the eigenvalues of the cost Hessian. Production scan matchers publish this; when the small eigenvalue collapses, they widen the covariance they hand the filter instead of hiding it. That's the [Module 3 consistency lesson](../03-estimation/06-consistency-lab.md) again: honesty about what you don't know is a first-class output.
3. **Assume some inputs are lies.** Robust kernels, χ² gates, and outlier trimming are the same idea at three layers — back-end, filter, and correspondence. A system with no mechanism for rejecting its own inputs will eventually be destroyed by one.

The capstone's [field notes 7 and 8](../../capstone-log.md) are this lab's live-fire version: moving obstacles produced exactly the "some of my measurements are lies" problem, and the fix was the same trimming logic in a third costume.

## F. Graded work & portfolio extension

**Graded:** robust pose-graph optimization is the designated back-end for capstone v4 (simultaneous SLAM).

**Portfolio:** the triptych from [lesson 4.4's experiment](04-pose-graphs.md) — underweighted honest closure, well-weighted closure, and a confident lie with and without a Huber kernel — plotted side by side. Robust back-ends are an active research area and you'll have both the failure and the fix in hand.
