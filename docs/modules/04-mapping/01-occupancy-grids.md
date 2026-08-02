# 4.1 Occupancy grids and the inverse sensor model

**Status:** Code verified · **Prereqs:** Module 1, lesson 3.1 · **Time:** ~2 h · **Verified:** 2026-08-01, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Every "map" your robot plans against — Nav2 costmaps, SLAM outputs, the capstone's world — is at heart an **occupancy grid**: the world discretized into cells, each holding a belief about being occupied. The elegance is that a grid map is just *thousands of tiny independent Bayesian estimators* (lesson 3.1, miniaturized), each updated by a sensor model run backwards: not "what would I measure given the world" but "what does this measurement say about the world" — the **inverse sensor model**.

## B. Mental model

A lidar beam tells you two different things about two different regions: **everything along the beam up to the hit is probably free** (the light got through), and **the cell at the hit is probably occupied** (the light stopped). One ray therefore *carves* free space and *deposits* one occupied cell. Thousands of rays from a moving robot cross-check each other, and the map emerges — including the honest gray of "never observed."

Work in **log-odds** and Bayes becomes addition: free evidence subtracts, hit evidence adds, and clamping the sum keeps any cell from becoming so certain it can never change its mind — that last part is what lets maps heal after a parked truck drives away.

## C. Mathematical formulation

Per cell, with \(l = \log \frac{p}{1-p}\):

\[
l_{cell} \leftarrow \operatorname{clip}\big(l_{cell} + l_{sensor}(z),\ -l_{max},\ l_{max}\big), \qquad
l_{sensor} = \begin{cases} l_{occ} > 0 & \text{cell at beam end (hit)} \\ l_{free} < 0 & \text{cell along beam} \end{cases}
\]

Recover probability with the logistic \(p = 1 - \frac{1}{1 + e^{l}}\). The independence assumption between cells is false (walls are contiguous!) and the algorithm works anyway — a lesson in itself about useful wrong models. Traversing the beam's cells is **Bresenham's line algorithm** — 1965 raster graphics, still in every mapper.

Asymmetry worth noticing: \(|l_{occ}| > |l_{free}|\) in practice (a hit is stronger evidence than a pass-through, since thin obstacles can be missed but rarely hallucinated).

## D. From ML to robotics

- **A grid map is a Naive Bayes ensemble**: per-cell independent posteriors from a stream of weak evidence, wrong independence assumption included. Your instincts about when NB works (and how it fails: correlated evidence double-counts) transfer directly — a robot spinning in place re-observes the same wall and grows overconfident exactly like duplicated training rows.
- **Log-odds accumulation ≈ additive score aggregation** (logit stacking); the clamp is a learning-rate floor that preserves adaptability — same reason you don't let momentum fully saturate.
- **The map/localization chicken-and-egg** — mapping assumes known pose, localization assumes known map — is robotics' EM: alternate the two and you have (a caricature of) SLAM, this module's destination.

## E. Minimal implementation

Library: [`robotics_ai/mapping/occupancy.py`](https://github.com/paulyonghaoli/robotics-for-ai-engineers/blob/main/robotics_ai/mapping/occupancy.py) — Bresenham traversal, log-odds updates, clamping, world↔cell transforms. The test suite includes the map-healing case (sustained free evidence reclaims a wrongly-occupied cell) — the behavior the clamp exists to buy.

### Practice — write and run code here

<code-exercise src="map-l1-bresenham"></code-exercise>

<code-exercise src="map-l1-logodds"></code-exercise>

## F. Robotics-framework implementation

Nav2's costmap layers are occupancy machinery in production dress: an *obstacle layer* does exactly this lesson from live scans, a *static layer* loads the SLAM-built map, the *inflation layer* is lesson 1.5, and layers compose by maximum cost. `slam_toolbox` builds its maps with the same inverse-model core plus the pose-graph corrections of lesson 4.4. The capstone's v2 stage swaps its known map for this mapper, fed by the simulator's lidar.

## G. Experiment

Drive the capstone simulator's robot on a fixed loop while mapping with **ground-truth poses**, then repeat with the noisy pose sensor, then with poses offset by slow drift (+2 cm/s). Compare the three maps against the true grid (cell-wise F1). Truth: crisp walls. Noise: fuzzy-but-usable walls. Drift: walls *smeared into arcs* — the signature that motivates SLAM, produced by your own hands. Keep the drifted map; lesson 4.4's loop closure will fix it and the before/after is the module's money shot.

## H. Failure modes

- **Pose error becomes map error** — the experiment's point: the mapper faithfully integrates whatever lie the localizer tells it. Maps are only as good as the trajectory.
- **Unclamped log-odds**: a cell observed occupied 10,000 times needs 10,000 free observations to flip — the parked-truck ghost that never leaves.
- **Beam endpoint bookkeeping**: forgetting that a max-range reading is *all free, no hit* deposits phantom obstacles at the sensor's range limit in every open area.
- **Resolution economics**: halving cell size quadruples memory and beam-traversal cost. 5 cm indoors, 10–20 cm warehouses — and the planner inherits whatever you pick (a 10 cm grid cannot represent an 8 cm gap between shelves).

## I. Questions

1. *(Concept)* Why is a hit stronger evidence than a pass-through, and how does the \(l_{occ}/l_{free}\) asymmetry encode that?
2. *(Calculation)* A cell starts at \(p = 0.5\) and receives 3 hits (\(l_{occ} = 0.85\)) and 1 free pass (\(l_{free} = -0.4\)). Compute its probability.
3. *(Debugging)* Your map shows a faint ring of obstacles at exactly 6 m radius around everywhere the robot has been. What's the bug?
4. *(System design)* A delivery robot's map must "forget" parked cars within ~10 minutes but keep buildings forever. Design the update rule.

??? note "Answer sketch for Q2"
    \(l = 3(0.85) - 0.4 = 2.15\); \(p = 1 - 1/(1+e^{2.15}) \approx 0.896\).

### Interactive quiz

<quiz-bank src="mapping-l1-grids"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Thrun et al., *Probabilistic Robotics*, ch. 9 | book | intermediate | Occupancy mapping, canonically |
| Moravec & Elfes (1985) | paper | introductory | Where grid mapping began — striking how much was right the first time |
| [Nav2 costmap docs](https://docs.nav2.org/configuration/packages/configuring-costmaps.html) | docs | intermediate | The production layer architecture |

## K. Graded work & portfolio extension

**Graded:** the capstone's v2 stage (online mapping) is scored by the same scenario rubric — a bad map shows up as collisions and failed episodes.

**Portfolio:** the three-maps experiment (truth/noise/drift, F1 scores, side-by-side renders) — the cleanest possible demonstration that you understand *why SLAM exists*, which is a better interview signal than claiming you understand SLAM.
