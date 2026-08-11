# 7.4 3D detection: pillars, anchors and NMS

**Status:** Code verified · **Prereqs:** lesson 7.3 · **Time:** ~2.5 h · **Verified:** 2026-08-03, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

This is the lesson where your existing detection knowledge does the most work — and where the parts that *don't* transfer cause the most damage.

The architecture transfers almost completely. Pillarize the cloud into a bird's-eye grid, aggregate each cell symmetrically, and you have a dense pseudo-image you can hand to any 2D backbone you already know. That is the whole PointPillars insight, and it is why a detector designed for images can be repurposed for lidar with modest surgery.

What does not transfer is everything downstream of the network: what a box means, what overlap means when boxes have orientation, and what suppression should be allowed to remove.

## B. Mental model

**Pillars, not voxels.** A voxel grid divides x, y *and* z. A pillar grid divides only x and y and lets each cell run the full height. That sounds like a loss of information and mostly isn't, because outdoor scenes are effectively 2.5D — objects sit on the ground and rarely stack. What you gain is enormous: the output is a 2D grid, so every 2D convolution, backbone and detection head you already have applies unchanged.

**The encoder is a symmetric function.** Each pillar contains a variable number of points in arbitrary order, and the feature must not depend on that order. A small per-point MLP followed by a max over the pillar does it — permutation-invariant by construction, which is the constraint [7.3](03-point-clouds.md) established.

**Anchors carry the physical prior.** A car is about 3.9 × 1.6 × 1.5 m. Predicting that box from scratch wastes capacity on a fact you already know, so you predict a *residual* against an anchor of roughly the right size. This is the same reasoning as image anchors, except the priors here are metric and genuinely reliable — cars really are that size, whereas "objects in images are about this many pixels" depends entirely on how far away they were.

## C. Formulation

**Pillarization.** For a cloud clipped to a range `[x_min, x_max] × [y_min, y_max]` with pillar side `s`:

$$
i = \left\lfloor \frac{x - x_{\min}}{s} \right\rfloor, \qquad
j = \left\lfloor \frac{y - y_{\min}}{s} \right\rfloor
$$

Each occupied pillar aggregates its points — the classic feature set is `(x, y, z, intensity)` augmented with offsets from the pillar centre and from the pillar's own point centroid, which gives the network local geometry without needing global coordinates.

**BEV IoU.** For axis-aligned boxes in the ground plane:

$$
\text{IoU} = \frac{|A \cap B|}{|A| + |B| - |A \cap B|}
$$

with the intersection computed per axis as `max(0, min(hi) − max(lo))`.

**Non-maximum suppression.** Sort by score, take the highest, remove everything overlapping it beyond a threshold, repeat. Two details decide whether it helps or hurts:

1. **Score-threshold first.** Filtering low-confidence boxes before NMS is not just an optimisation — a low-scoring false box that survives to the NMS stage can suppress nothing, but it costs you O(N²) comparisons and clutters the output.
2. **Suppress within a class, not across** — and note *why* this matters more than it first appears. With plain IoU it barely does: a pedestrian beside a car scores an IoU of about 0.04 against it, because the union is dominated by the car, so class-agnostic NMS would leave it alone anyway.

    The danger arrives with the overlap measure production stacks actually reach for. A duplicate box nested inside a larger one also has low IoU and survives IoU-NMS as a phantom, so implementations commonly score overlap as **intersection over the smaller area** instead. That fixes nested duplicates and makes containment score 1.0 — including a pedestrian standing inside a truck's bird's-eye footprint. Now class-agnostic suppression deletes a correct detection, and the metric that notices is the one you compute at the end of the quarter.

### The sparsity that pays for everything, measured

The pillar encoding's whole justification is a distribution, so here it is
on this lesson's synthetic scene — 12,900 lidar points over an 80×80 grid of
0.25 m pillars:

| Statistic | Value |
|---|---|
| Pillars in the grid | 6,400 |
| Pillars containing any point | 4,305 (67%) |
| Points per occupied pillar, median | **1** |
| p95 | 4 |
| Maximum | 38 |

Two facts drive the architecture. First, a third of the grid is empty and
processing it densely is pure waste, which is the argument for encoding only
occupied pillars and scattering the results back into the BEV image — the
sparse-to-dense trick at PointPillars' core. Second, and less advertised: the
occupancy that does exist is savagely skewed. The *median* occupied pillar
holds a single point while the maximum holds 38, so any fixed
points-per-pillar budget is simultaneously too big and too small — pad the
median pillar 32× to reach a 32-point budget, truncate the densest one. That
skew is why the per-pillar feature net must be permutation-invariant and
robust to padding, why nearby objects (dense pillars) and distant ones
(single-return pillars) effectively pass through different networks, and one
concrete reason detection quality falls with range even before resolution
does: at distance, "a car" is a handful of pillars holding one point each,
and no encoder conjures structure from a single return.

## D. From ML to robotics

**Transfers directly:** backbone design, anchor matching, focal loss for the extreme foreground/background imbalance, and your whole intuition for detection heads.

**Changes meaning:**

- **A box is a physical claim.** An image box says "the thing is in this region of the picture." A 3D box says "there is 1.6 m of solid matter here, and I am asserting a planner may not path through it." Wrong boxes cause emergency stops.
- **Orientation is part of the output and part of the error.** A car detected with correct extent and 90° of heading error has excellent IoU by some measures and is useless for prediction, because where it will be in two seconds depends on which way it points.
- **Range-stratified metrics are mandatory.** A single mAP hides that the detector is excellent at 10 m and blind at 50 m. This is [10.2's](../10-evaluation/02-scenario-suites.md) stratification argument, and here the stratifying variable is obvious.

## E. Practice

<code-exercise src="per-l4-pillarize"></code-exercise>

<code-exercise src="per-l4-nms"></code-exercise>

## F. In production

PointPillars remains a strong default in 2026 for exactly the reason it was designed: it is fast, and the pseudo-image lets you reuse everything. CenterPoint replaced anchors with centre heatmaps and is the more common modern choice; BEVFusion and its descendants fuse camera and lidar features in the same BEV space, which is [7.5](../../curriculum.md)'s subject.

The evaluation conventions matter more than they look. nuScenes uses centre-distance thresholds rather than IoU, precisely because IoU on small distant objects is dominated by extent error rather than localisation error. KITTI uses per-class IoU thresholds — 0.7 for cars, 0.5 for pedestrians — because a 0.7 threshold on something 0.6 m wide is asking for a precision nobody achieves. When you compare numbers across papers, check which convention each used before concluding anything.

## G. Experiment

Take a set of detections and sweep the NMS IoU threshold from 0.1 to 0.9, plotting precision and recall separately for a sparse scene and a crowded one. The curves cross: the threshold that is right when objects are well separated merges neighbours in a crowd, and the threshold that preserves a crowd leaves duplicates everywhere else. Most stacks pick one number and live with it — knowing *which* regime you tuned in is the actual deliverable.

## H. Failure modes

- **Class-agnostic NMS with a containment-based overlap.** Deletes the pedestrian standing inside the truck's footprint. Harmless under plain IoU, actively destructive under intersection-over-smaller — so the bug depends on a choice made elsewhere in the file.
- **NMS threshold tuned on sparse scenes.** Works in testing, merges two people standing together in deployment.
- **Heading ambiguity.** A box and the same box rotated 180° describe identical geometry, so a naive angle loss punishes a correct-but-flipped prediction enormously. Most implementations predict the direction separately from the axis.
- **Anchors that don't match the data.** If your anchor sizes were copied from a road dataset and your robot works indoors, matching fails silently and recall collapses with no obvious error.
- **Empty-pillar handling.** Most pillars are empty. Materialising a dense tensor over the whole grid before you sparsify wastes most of your memory bandwidth on zeros.

## I. Questions

<quiz-bank src="per-l4-quiz"></quiz-bank>

## J. References

- Lang et al., *PointPillars* (2019) — the pillar encoder; still the clearest exposition of the pseudo-image idea.
- Yin, Zhou & Krähenbühl, *CenterPoint* (2021) — anchor-free 3D detection, and a good argument for why anchors were doing less work than assumed.
- Zhou & Tuzel, *VoxelNet* (2018) — the predecessor worth reading for the voxel-feature-encoder derivation.
- Caesar et al., *nuScenes* (2020) — read the metric section specifically; the choice of centre-distance over IoU is well argued and affects how you should read every number in the field.

## K. Graded work & portfolio extension

**Graded:** the two exercises above.

**Portfolio:** produce the NMS-threshold sweep from section G on synthetic scenes at two densities, with precision and recall on the same axes. Then annotate the threshold your pipeline actually uses. A tuning decision presented alongside the regime it was tuned for is a much stronger artifact than the number alone — and it is the same discipline as publishing an operating envelope in [7.2](02-stereo-depth.md).
