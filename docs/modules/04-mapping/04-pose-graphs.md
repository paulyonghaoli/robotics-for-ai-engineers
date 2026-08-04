# 4.4 Pose graphs and loop closure: SLAM as least squares

**Status:** Code verified · **Prereqs:** lessons 4.2–4.3 · **Time:** ~2.5 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

EKF-SLAM hit an \(O(N^2)\) wall because it maintained one dense joint belief *at all times*. The modern reformulation keeps the history instead: every past pose is a node, every measurement is an **edge** (a constraint between two nodes), and SLAM becomes a big, gloriously **sparse** least-squares problem solved on demand. This is how essentially every shipping SLAM system works — `slam_toolbox`, Cartographer, ORB-SLAM, the lot — and for an ML engineer it's the most natural formulation of all: *SLAM is just an optimization problem with a graph-shaped loss.*

## B. Mental model

Think of the trajectory as a chain of poses connected by springs:

- **Odometry edges** link consecutive poses: "pose k+1 sits ~0.5 m ahead of pose k" — short springs, each slightly wrong; errors *compound* down the chain (the drift you've met everywhere).
- A **loop-closure edge** links two *distant* poses: scan matching (4.2!) recognizes "this is the same doorway as pose 12" and adds one long spring across the chain.

Before closure: an open chain, drifted into a crooked arc. Adding the loop edge and *relaxing all the springs at once* pulls the whole trajectory straight — the error doesn't get patched at the closure point, it gets **redistributed along the entire loop** in proportion to each edge's stiffness (= confidence). The map (rendered from corrected poses, 4.1-style) snaps from a smeared spiral into clean walls. Same cinematic moment as EKF-SLAM's ripple — now scalable to millions of edges, because each edge only touches two nodes: the loss is a *sparse* sum.

## C. Mathematical formulation

\[
\min_{x_1 \dots x_n} \sum_{(i,j) \in \text{edges}} \big\| z_{ij} \ominus (x_j \ominus x_i) \big\|^2_{\Omega_{ij}}
\]

Each edge contributes a residual (measured relative pose vs current relative pose), weighted by its information matrix \(\Omega\) (stiff springs = confident measurements). With angles involved it's nonlinear — solved by Gauss–Newton/Levenberg–Marquardt over sparse normal equations; for position-only graphs (the exercise) it's *literally linear least squares*, one `np.linalg.solve`. One gauge subtlety: the whole graph can float freely (4.3's fact C1), so you pin the first pose.

The pipeline division of labor: the **front-end** (scan matching, place recognition) proposes edges; the **back-end** (this optimization) makes them consistent. Front-end lies — a wrong loop closure — are the catastrophic failure, so robust back-ends downweight implausible edges (switchable constraints, robust kernels: Huber and friends — your robust-loss instincts apply directly).

## D. From ML to robotics

- **A pose graph is a factor graph, and optimizing it is MAP inference** — the same object as a CRF, solved by the same sparse Gauss–Newton you'd use for any structured least squares. SLAM's "modern era" is largely the realization that the estimation problem *is* an optimization problem.
- **Ω-weighting is heteroscedastic loss weighting**; robust kernels against bad loop closures are outlier-robust losses; and "one wrong confident edge ruins the map" is the mislabeled-example-with-tiny-loss-weight pathology, at map scale.
- **Front-end/back-end is retrieval + reasoning**: place recognition (is this the same doorway?) is a retrieval problem — increasingly solved with learned embeddings (Module 7 territory) — feeding a classical optimizer that enforces global consistency. This split is the architecture of modern SLAM *and* a fair sketch of RAG.

## E. Minimal implementation & practice

<code-exercise src="map-l4-posegraph"></code-exercise>

## F. Robotics-framework implementation

`slam_toolbox` = correlative scan matching front-end + sparse pose-graph back-end (Ceres), with lifelong-mapping modes that continue optimizing old graphs. Cartographer adds submaps; g2o/GTSAM are the general-purpose back-end libraries (GTSAM's factor-graph API reads like the math above). When you meet "bundle adjustment" in Module 7, you'll recognize it instantly: the same sparse least squares with cameras and 3D points as nodes.

## G. Experiment

The exercise's square loop, extended: sweep the loop-closure edge's information weight Ω across four orders of magnitude and plot final trajectory error. Too soft: drift barely corrected. Well-matched: near-truth. Then the important one — add a *wrong* loop closure (connect two poses that aren't actually the same place) with high confidence, and watch it fold the map like bad origami. Repeat with a Huber kernel on the edges and watch the lie get quarantined. That triptych — underweighted truth, well-weighted truth, confident lie — is the entire robust-SLAM literature in one afternoon.

## H. Failure modes

- **False loop closures**: the catastrophic one — a confident wrong edge folds the map. Defense in depth: conservative place recognition, geometric verification, robust kernels.
- **Underconstrained graphs**: forgetting to pin the gauge → singular normal equations (the solver's error message is your first pose-graph rite of passage).
- **Drift beyond the closure's basin**: if odometry drifted too far, the loop-closure scan match (4.2) itself lands in the wrong basin — front-end and back-end failures compounding.
- **Optimizing at the wrong cadence**: full optimization every scan wastes compute; only at closures risks operating long on a crooked map. Production systems optimize incrementally (iSAM-style) or on closure events.

## I. Questions

1. *(Concept)* Why does loop closure distribute the correction along the whole loop rather than snapping only the closing pose?
2. *(Calculation)* A 4-pose 1-D chain with odometry edges of 1.0 each (measured) and a loop edge saying pose 3 is at 2.4. With equal weights and pose 0 pinned at 0: where does least squares put pose 3?
3. *(Debugging)* After adding place recognition, maps are usually better but occasionally fold catastrophically in repetitive warehouses. Explain both halves.
4. *(System design)* Design the capstone's v4 SLAM: what makes edges, what triggers optimization, and which of Module 3's tools guards the front-end's proposals?

??? note "Answer sketches"
    **1.** Because the objective is a sum over *all* edges, not a constraint to satisfy at one node. Snapping only the closing pose would zero the loop edge's residual at the price of one enormous residual on the odometry edge next to it, and squared cost punishes that concentration hard — \(k\) small residuals beat one \(k\)-sized residual. The stationary point instead spreads the disagreement around the cycle in inverse proportion to each edge's stiffness \(\Omega\), so every spring stretches a little and confident edges stretch least.

    **2.** Pinned \(x_0 = 0\); three chain edges want steps of 1.0 (sum 3.0), the loop edge wants \(x_3 = 2.4\) — a 0.6 disagreement across four equally-weighted edges. Least squares gives each edge a residual of 0.15: steps shrink to 0.85, so \(x_3 = 2.55\) (and the loop edge is missed by 0.15 too). The correction is *distributed*, not dumped at the closure.

    **3.** Better usually: genuine closures add long edges that cancel accumulated odometry drift, so global error drops everywhere the loop touches. Catastrophic occasionally: repetitive warehouses are perceptual aliasing machines — aisle 7 looks exactly like aisle 3, so the front-end proposes a confident edge between poses that are not the same place, and the back-end, having no way to doubt it, folds the map to satisfy the lie. Both halves are the same mechanism (edges are trusted at their stated \(\Omega\)); the defense is geometric verification before accepting a proposal plus a robust kernel so a surviving lie can be downweighted.

    **4.** Nodes are keyframes, added every ~0.5 m or 30° of travel rather than every scan (a graph is cheap, but not free). Odometry edges come from scan matching (4.2) between consecutive keyframes with covariance from the match's Hessian — including the degeneracy inflation from that lesson. Loop-closure edges come from scan-matching the current keyframe against past keyframes inside the current pose covariance's search ellipse, seeded by the drifted estimate. Optimize on closure events (plus a cheap incremental pass between them), not per scan. The Module 3 guard on the front-end is the \(\chi^2\) gating test from 3.5: score the proposed relative pose against the graph's predicted relative pose and its covariance, and reject proposals that are statistically implausible before they ever reach the back-end — Huber kernels are the second line, not the first.

### Interactive quiz

<quiz-bank src="mapping-l4-posegraph"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Grisetti et al., *"A tutorial on graph-based SLAM"* (2010) | paper | intermediate | The canonical modern-SLAM entry point |
| Dellaert & Kaess, *Factor Graphs for Robot Perception* (2017) | book | advanced | The factor-graph worldview, from GTSAM's authors |
| [`slam_toolbox` docs](https://github.com/SteveMacenski/slam_toolbox) | docs | intermediate | The production shape of everything above |

## K. Graded work & portfolio extension

**Graded:** pose-graph optimization is the designated engine for capstone v3's SLAM stage.

**Portfolio:** the section G triptych (soft closure / good closure / confident lie / Huber rescue, plotted) — robust back-ends are a live research area, and you'll have the failure demo *and* the fix in hand.
