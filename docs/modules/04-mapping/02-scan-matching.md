# 4.2 Scan matching and ICP: alignment as optimization

**Status:** Code verified · **Prereqs:** lessons 1.1, 4.1 · **Time:** ~2.5 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Odometry says "I moved about 0.5 m." The lidar can do better: *align this scan against the previous one (or the map) and read off the motion exactly*. That alignment — **scan matching** — turns a lidar into a precision odometer, and its workhorse algorithm, **ICP (Iterative Closest Point)**, is the inner loop of essentially every lidar SLAM system from 1992 to the present. It's also two ideas you already own, stapled together.

## B. Mental model

ICP alternates two steps until they agree:

1. **Correspond:** for each point in scan B, guess its partner in scan A — *nearest neighbor* under the current alignment.
2. **Align:** given correspondences, find the rigid transform that best overlays the pairs — a closed-form least-squares problem (the **Kabsch/Procrustes** solution, via SVD).

Guessed matches improve the transform; the improved transform improves the matches. If "alternate a correspondence step and a fitting step" sounds familiar, it should — **ICP is EM with hard assignments**, structurally the same loop as k-means. And it inherits k-means' character flaw: convergence to the *nearest local optimum*. ICP refines a good initial guess (from odometry); it does not find alignment from nothing. Feed it a 90° initial error and it will happily lock walls onto the wrong walls.

## C. Mathematical formulation

Given corresponded pairs \((a_i, b_i)\), minimize \(\sum_i \| R b_i + t - a_i \|^2\). Closed form: center both sets, form the cross-covariance \(H = \sum \bar{b}_i \bar{a}_i^\top\), take SVD \(H = U \Sigma V^\top\); then

\[
R = V U^\top \;(\text{fix } \det R = +1), \qquad t = \bar{a} - R\,\bar{b}
\]

(the determinant fix rejects reflections — lesson 1.6's mirror bug, preempted). Production refinements, each earning its keep: **outlier trimming** (drop the worst-matched pairs — a moving person in scan B has no honest partner in A), **point-to-plane** metrics (converges in far fewer iterations on structured scenes), and correspondence via KD-trees (the naive O(n²) search is the actual bottleneck).

## D. From ML to robotics

- **ICP = k-means' loop, Procrustes' solve.** Hard-EM structure, SVD-based alignment — you have implemented both halves in other costumes. The local-minimum caveat transfers verbatim: initialization is destiny.
- **Outlier trimming is robust regression** — trimmed least squares against non-static scene content. The "moving person corrupts the fit" failure is label noise with legs.
- **Residual-after-convergence is your fit diagnostic**: low residual + wrong alignment = converged to the wrong basin (looks exactly like a good loss on a degenerate solution); the corridor case below is the canonical example.

## E. Minimal implementation & practice

<code-exercise src="map-l2-kabsch"></code-exercise>

<code-exercise src="map-l2-icp"></code-exercise>

## F. Robotics-framework implementation

`slam_toolbox` (Nav2's default SLAM) runs correlative scan matching against the map; LOAM-family 3D lidar odometry is point-to-plane ICP with feature selection; Open3D ships production ICP you'll use in Module 7 for 3D data. All expose the same three knobs you just built: correspondence distance, outlier rejection, iteration/convergence limits.

## G. Experiment

Corridor degeneracy: match two scans of a straight featureless corridor. ICP nails the *lateral* offset and hallucinates the *longitudinal* one — the cost function is flat along the corridor axis (nothing constrains sliding). Compute the correspondence cost surface over (dx, dy) and look at the valley. This is the capstone's feature-poor drift (field notes!) and lesson 2.3's rank deficiency, reunited: degenerate geometry ⇒ unobservable directions ⇒ the fit is confident *and* unconstrained.

## H. Failure modes

- **Bad initialization → wrong basin**, with a perfectly low residual. Always seed from odometry; never cold-start.
- **Degenerate geometry** (corridors, open fields): the solution is a subspace, not a point. Detect via the cost Hessian's conditioning and *tell the estimator* (inflate covariance along the flat direction — honesty, Module 3 style).
- **Dynamic objects**: untrimmed moving points drag the alignment toward the mover.
- **Over-tight correspondence radius**: with moderate initial error, nothing corresponds, and ICP "converges" instantly to where it started.

## I. Questions

1. *(Concept)* Map the two ICP steps onto EM. What plays the role of latent variables?
2. *(Calculation)* Pairs already centered; \(H = \begin{bmatrix} 0 & -1 \\ 1 & 0 \end{bmatrix}\). What rotation does Kabsch return?
3. *(Debugging)* Your scan matcher works everywhere except a warehouse aisle, where poses slide 10–30 cm along the aisle between matches. Diagnose, and name the fix at the *estimator* level.
4. *(System design)* Design the scan-matching layer for the capstone: match against last scan or against the map? Trimming fraction? What triggers a "don't trust this match" flag?

??? note "Answer sketch for Q2"
    \(H\) is (proportional to) a 90° rotation generator; SVD gives \(R = VU^\top\) = the 90° rotation itself — a useful sanity case for your implementation.

### Interactive quiz

<quiz-bank src="mapping-l2-icp"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Besl & McKay (1992) | paper | intermediate | The original ICP — the loop has barely changed |
| Pomerleau et al., *"Comparing ICP variants"* (2013) | paper | intermediate | The empirical map of the design space |
| Zhang & Singh, *LOAM* (2014) | paper | advanced | Point-to-plane + feature selection at production quality |

## K. Graded work & portfolio extension

**Graded:** scan-matching odometry is the natural capstone v3 upgrade (replace commanded-velocity propagation in the PF's motion model).

**Portfolio:** the corridor cost-surface plot (a valley, not a bowl) next to a healthy room's surface — degeneracy made visible; pairs beautifully with the capstone's feature-poor field note.
