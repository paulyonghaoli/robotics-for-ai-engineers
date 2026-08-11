# 7.3 Point clouds: unordered, metric, and mostly empty

**Status:** Code verified · **Prereqs:** lesson 7.2 · **Time:** ~2 h · **Verified:** 2026-08-03, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

A point cloud breaks nearly every assumption a CNN is built on. It has no grid, no fixed size, no canonical ordering, and its coordinates carry physical units. Two clouds of the same scene taken a moment apart do not even have the same number of points.

That is the awkward part. The useful part is that a cloud carries something an image never does: **empty space is a measurement.** A ray that travelled 12 m before hitting something has certified everything along the way as free. An image has no equivalent — a pixel says what is at the end of the ray and nothing about the journey.

Most of what a perception stack does before detection is exploiting that structure: throwing away redundancy, separating the ground from what is standing on it, and turning an unordered set into something a downstream algorithm can index.

## B. Mental model

Three properties, and each one dictates a preprocessing step:

| Property | Consequence | The step it forces |
|---|---|---|
| **Unordered** | any function of the cloud must be permutation-invariant | symmetric aggregation (max/sum per voxel or pillar) |
| **Non-uniform density** | near surfaces have hundreds of returns per m², far ones a handful | voxel downsampling, so cost doesn't track proximity |
| **Dominated by ground** | 40–70% of returns are the floor, and it is never what you want | ground segmentation before anything else |

**Density is the one that surprises people.** A lidar's angular resolution is fixed, so returns per unit area fall off as 1/Z². The floor two metres away can easily contribute more points than every object in the scene combined — and a naive pipeline spends most of its compute on the least informative part of the frame while an object at 30 m is represented by eleven points.

## C. Formulation

**Voxel downsampling.** Quantise each point to a cell of side `v`, then keep one representative per occupied cell:

$$
\text{key}(\mathbf{p}) = \left\lfloor \frac{\mathbf{p} - \mathbf{p}_{\min}}{v} \right\rfloor
$$

Keeping the *centroid* of each voxel rather than an arbitrary member is worth the small extra cost: it is unbiased, and it partially averages away range noise. Keeping "the first point encountered" makes your output depend on input ordering, which quietly breaks reproducibility.

**Plane fitting by RANSAC.** A plane is $\mathbf{n}\cdot\mathbf{p} + d = 0$ with $\|\mathbf{n}\|=1$; a point's distance to it is $|\mathbf{n}\cdot\mathbf{p} + d|$. RANSAC:

1. sample 3 points, solve for the plane through them
2. count inliers within a distance threshold $\tau$
3. keep the best hypothesis, refit on its inliers

The number of iterations needed for confidence $p$ with inlier ratio $w$ and sample size 3:

$$
N = \frac{\log(1-p)}{\log(1 - w^3)}
$$

With $w = 0.5$ and $p = 0.99$ that is 35 iterations. RANSAC is cheap; the expensive mistake is not running enough of them and quietly accepting a bad hypothesis.

### The biggest plane is a wall — measured

Ground extraction sounds like a solved problem — "RANSAC the biggest plane" —
and this lesson's corridor scene is built to break exactly that recipe. The
scene has 2,500 floor points and 6,000 wall points, because tall walls
subtend more of a lidar's field of view than the floor does, which is the
ordinary indoor case rather than a contrived one. Running the standard
recipes:

| Method | Plane tilt from horizontal | Ground → obstacle | Obstacle → ground |
|---|---|---|---|
| Least squares over all points | 0.4° | 0.0% | 40.9% |
| Vanilla RANSAC, biggest plane wins | **88.9° — it found a wall** | 97.2% | — |
| RANSAC + normal gate (\|n·up\| > 0.9) | 0.54° | 0.0% | 5.2% |

The middle row is the punchline: vanilla RANSAC returned a plane with 2,984
inliers — one wall, whose 3,000 points outnumber the floor's inlier count —
tilted 89° from horizontal, and then the 15 cm height cut classified
essentially the entire floor as an obstacle. Nothing failed numerically;
RANSAC answered the question it was asked, which was "biggest plane", not
"ground". The one-line fix is a **normal gate**: reject candidate planes
whose normal is not near vertical before counting inliers, after which the
fit lands at half a degree and the residual 5.2% obstacle-to-ground leakage
is almost entirely the 4.9% of obstacle points that genuinely sit below
15 cm — the inherent floor of any height cut, not an error of the plane.

Prior knowledge — the ground is roughly below you and roughly horizontal — is
not cheating; it is the difference between the question you meant and the
question you asked. Production ground segmenters all encode it, and now you
know what happens on the day someone removes it.

## D. From ML to robotics

**What transfers:** if you have worked with PointNet, PointPillars, VoxelNet or any sparse-convolution detector, the encoder story is exactly this — quantise, aggregate symmetrically, hand a dense tensor to a conventional network.

**What doesn't:** the instinct to treat sparsity as missing data to be imputed. In a point cloud, sparsity is *signal*. Filling in empty voxels destroys the free-space information that the planner in [Module 5](../05-planning/02-costmaps.md) depends on.

**The one to unlearn hardest:** normalising coordinates. Dividing by the scene extent is reflexive after years of image work, and it throws away the metric scale that makes the whole thing useful. A 1.8 m object is 1.8 m regardless of how far away it is; that is the property you are being handed for free.

## E. Practice

<code-exercise src="per-l3-voxel"></code-exercise>

<code-exercise src="per-l3-ground"></code-exercise>

## F. In production

Open3D and PCL both give you voxel grids, RANSAC segmentation, KD-trees and normal estimation off the shelf, and you should use them. What they will not do is choose your parameters:

- **Voxel size** is a resolution decision with a downstream cost. Too coarse and a pedestrian at 30 m becomes two points; too fine and you have not actually reduced anything.
- **Ground threshold** must accommodate the real world's slope, kerbs and ramps. A single global plane is wrong on any real site, which is why production stacks fit a plane per angular sector, or use a grid of local height estimates.
- **Ordering.** Many library functions do not promise a stable output order. If your downstream code cares, sort explicitly rather than hoping.

## G. Experiment

Take a synthetic cloud with a ground plane and a few objects, and sweep voxel size from 0.02 m to 0.5 m. Plot points retained against voxel size on one axis, and the number of points remaining *on the smallest object* on the other. The two curves diverge sharply — total compression looks excellent long after the small object has been erased. That gap is why voxel size is a detection-range decision, not a memory-budget one.

## H. Failure modes

- **Ground removal that eats short objects.** A threshold generous enough to absorb a sloping floor also absorbs a kerb, a pallet, or a child.
- **A single global ground plane.** Real sites slope. The residual grows with distance from wherever the fit was anchored, so the far field gets systematically misclassified.
- **RANSAC finding the wrong plane.** In a corridor the largest planar structure may be a wall. Constrain the normal — if you know roughly where "up" is, reject hypotheses that disagree with it.
- **Voxel downsampling before ground removal.** The ground dominates the voxel occupancy, so you spend your point budget on the floor and then delete it.
- **Ordering-dependent output.** "First point per voxel" produces different clouds for the same scene depending on how the driver happened to serialise the frame.

## I. Questions

<quiz-bank src="per-l3-quiz"></quiz-bank>

## J. References

- Rusu & Cousins, *3D is here: Point Cloud Library* (2011) — the paper behind PCL, and a good map of what the standard operations are.
- Fischler & Bolles, *Random Sample Consensus* (1981) — the original, and unusually readable for a paper of that vintage.
- Zhou, Park & Koltun, *Open3D* (2018) — the library most new work uses; the tutorials are the fastest way in.
- Zermas et al., *Fast Segmentation of 3D Point Clouds* (2017) — the sector-wise ground fitting that production stacks actually use.

## K. Graded work & portfolio extension

**Graded:** the two exercises above.

**Portfolio:** build the figure from section G — retention versus voxel size, overlaid with points-on-the-smallest-object, with your detector's minimum-points-per-object requirement drawn across it. The crossing point is your maximum detection range as a function of voxel size, which is a parameter choice most teams make by feel and never justify.
