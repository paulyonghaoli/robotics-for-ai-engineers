# 4.1 Occupancy grids and the inverse sensor model

**Status:** Code verified · **Prereqs:** Module 1, lesson 3.1 · **Time:** ~2 h · **Verified:** 2026-08-01, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Every map your robot will ever plan against — the Nav2 costmap, the output of
a SLAM system, the capstone's world model — is at heart an **occupancy grid**:
the world discretised into cells, each holding a belief about whether that
patch of floor contains something solid. The representation has survived four
decades of alternatives because of one elegant property: a grid map is nothing
more than *thousands of tiny independent Bayesian estimators*, each one a
miniature of lesson 3.1's scalar filter, updated in parallel from the same
sensor stream.

The update rule comes from running the sensor model backwards. A forward
sensor model answers "what would I measure, given the world?"; mapping needs
the reverse question, "what does this measurement say about the world?", and
that reversed object is called the **inverse sensor model**. Getting it right
is most of this lesson, and getting its edge cases wrong produces two of the
most recognisable artefacts in robotics, both of which appear in section H
with their signatures attached.

!!! note "Terms defined here"

    **Occupancy grid** — a discretisation of space into cells, each carrying
    the probability that it is occupied. The value 0.5 means "never
    observed", and honest grids are mostly 0.5.

    **Inverse sensor model** — the mapping from one measurement to evidence
    about the cells it traversed, as opposed to the forward model's mapping
    from world to expected measurement.

    **Log-odds** — the representation \(l = \log\frac{p}{1-p}\), which turns
    Bayesian multiplication into addition and is how every serious grid
    mapper stores its cells.

    **Clamping** — capping \(|l|\) at a maximum, so that no cell can
    accumulate unbounded certainty. Section G measures exactly what this
    buys.

    **Bresenham's line algorithm** — the 1965 raster-graphics routine that
    enumerates the grid cells a straight line passes through, still inside
    every mapper because it visits each cell exactly once with integer
    arithmetic.

## B. Mental model

A lidar beam tells you two different things about two different regions, and
keeping them separate is the whole trick. Everything along the beam *up to*
the hit is probably free, because the light got through it; the single cell
*at* the hit is probably occupied, because the light stopped there. One ray
therefore carves out a corridor of free space and deposits one occupied cell
at its end, and a moving robot sweeping thousands of rays per second
cross-checks every cell from many directions until the map emerges — including
the honest grey of "never observed", which a planner treats very differently
from "known free".

Working in log-odds makes the accumulation trivial: free evidence subtracts,
hit evidence adds, and each cell is just a running sum. The clamp on that sum
is what keeps any cell from becoming so certain that it can never change its
mind, and that property — the ability of a map to *heal* when a parked truck
drives away — turns out to be worth measuring, because the difference between
a clamped and an unclamped mapper is not a nuance. It is three orders of
magnitude, and section G has the numbers.

## C. Mathematical formulation

Per cell, with \(l = \log \frac{p}{1-p}\):

\[
l_{cell} \leftarrow \operatorname{clip}\big(l_{cell} + l_{sensor}(z),\ -l_{max},\ l_{max}\big), \qquad
l_{sensor} = \begin{cases} l_{occ} > 0 & \text{cell at beam end (hit)} \\ l_{free} < 0 & \text{cell along beam} \end{cases}
\]

Probability is recovered with the logistic \(p = 1 - \frac{1}{1 + e^{l}}\)
whenever a human or a planner needs it, which is rarely; the arithmetic lives
its whole life in log-odds.

Two structural observations deserve more than a passing glance. First, the
independence assumption between cells is false — walls are contiguous, so
knowing one cell is occupied genuinely does tell you about its neighbour — and
the algorithm works excellently anyway, which is a standing lesson in useful
wrong models. Second, the magnitudes are deliberately asymmetric, with
\(|l_{occ}| > |l_{free}|\) in every production tuning, because a hit is
stronger evidence than a pass-through: beams stop only when something stops
them, but they can *miss* thin obstacles — a chair leg between two rays, a
glass panel — so absence of a return is weaker testimony than presence of
one. Question 1 works this through.

## D. From ML to robotics

A grid map is a Naive Bayes ensemble in the most literal sense: per-cell
independent posteriors accumulated from a stream of weak evidence, wrong
independence assumption included. Your instincts about when Naive Bayes works
transfer directly, and so do your instincts about how it fails — correlated
evidence double-counts, so a robot spinning in place re-observing the same
wall grows overconfident in exactly the way a classifier trained on
duplicated rows does.

The log-odds accumulation is additive score aggregation, and the clamp plays
the role of a learning-rate floor: it preserves the ability to adapt, for the
same reason you do not let an optimiser's accumulated state saturate.

And the chicken-and-egg at the module's heart — mapping assumes a known pose,
localisation assumes a known map — is robotics' EM algorithm. Alternate the
two and you have a caricature of SLAM, which is precisely where this module
is heading.

## E. Minimal implementation

The library lives at
[`robotics_ai/mapping/occupancy.py`](https://github.com/paulyonghaoli/robotics-for-ai-engineers/blob/main/robotics_ai/mapping/occupancy.py):
Bresenham traversal, log-odds updates, clamping, and the world-to-cell
transforms from Module 1. The test suite includes the map-healing case —
sustained free evidence reclaiming a wrongly-occupied cell — because that
behaviour is the entire reason the clamp exists.

### Practice — write and run code here

<code-exercise src="map-l1-bresenham"></code-exercise>

<code-exercise src="map-l1-logodds"></code-exercise>

## F. Robotics-framework implementation

Nav2's costmap is occupancy machinery in production dress, arranged as
composable layers: an *obstacle layer* runs exactly this lesson from live
scans, a *static layer* loads the SLAM-built map, the *inflation layer* is
lesson 1.5's configuration-space transform, and the layers compose by taking
the maximum cost per cell. `slam_toolbox` builds its maps with the same
inverse-model core plus the pose-graph corrections of lesson 4.4, and the
capstone's v2 stage swaps its known map for this mapper, fed by the
simulator's lidar.

## G. Experiment — the healing arithmetic, and the three-maps study

The clamp's value is easiest to state as a question: a truck parks against a
wall, the mapper observes it as occupied a thousand times, and then it drives
away. How many passes of free evidence does the cell need before the map
admits the space is empty? With \(l_{occ} = 0.85\) and \(l_{free} = -0.4\):

| Clamp \(l_{max}\) | Free passes to flip after 1,000 hits |
|---|---|
| 2.0 | **6** |
| 4.0 | 11 |
| 6.0 | 15 |
| unclamped | **2,125** |

The clamped mapper forgets the truck during the next drive-by. The unclamped
one carries a ghost obstacle for two thousand observations — at a revisit
every two minutes, that is three days of phantom truck, and every plan in the
interim routes around a vehicle that no longer exists. The clamp is not a
numerical nicety; it is the difference between a map that tracks the world
and a map that records its history. Choosing \(l_{max}\) is choosing a
forgetting horizon, which is why question 4 asks you to size it against a
revisit rate rather than pick a round number.

Then run the three-maps study, which needs the capstone simulator. Drive a
fixed loop while mapping with ground-truth poses, then with the noisy pose
sensor, then with poses corrupted by a slow 2 cm/s drift, and compare the
three maps cell-wise against the true grid. Truth gives crisp walls; noise
gives fuzzy-but-usable walls; drift gives walls *smeared into arcs*, because
the mapper faithfully integrates whatever lie the localiser tells it. Keep
the drifted map — lesson 4.4's loop closure will repair it, and that
before-and-after pair is the module's money shot.

## H. Failure modes

**Pose error becomes map error**, which is the three-maps study's point: the
mapper has no opinion about where the robot is and integrates whatever it is
told, so maps are exactly as good as the trajectory that built them.

**Unclamped log-odds** produce the parked-truck ghost measured above — a cell
observed occupied ten thousand times needs ten thousand frees to flip, and
nothing in the ordinary operation of a robot supplies them.

**Beam endpoint bookkeeping** is the classic: a max-range reading means
"nothing came back", which is *all free along the ray, no hit at the end*.
Feed max-range returns through the normal hit path and you deposit a phantom
obstacle at the sensor's range limit in every direction — the ring at exactly
6 m that question 3 diagnoses, and the capstone's first field note in the
wild.

**Resolution economics** compound quietly: halving the cell size quadruples
memory and beam-traversal cost, and the planner inherits whatever you pick — a
10 cm grid cannot represent an 8 cm gap between shelves, so the planner will
never find a path the robot could physically take. Indoors 5 cm is
conventional, warehouses run 10–20 cm.

## I. Questions

1. *(Concept)* Why is a hit stronger evidence than a pass-through, and how
   does the \(l_{occ}/l_{free}\) asymmetry encode that?
2. *(Calculation)* A cell starts at \(p = 0.5\) and receives 3 hits
   (\(l_{occ} = 0.85\)) and 1 free pass (\(l_{free} = -0.4\)). Compute its
   probability.
3. *(Debugging)* Your map shows a faint ring of obstacles at exactly 6 m
   radius around everywhere the robot has been. What is the bug?
4. *(System design)* A delivery robot's map must forget parked cars within
   about 10 minutes but keep buildings forever. Design the update rule.

??? note "Answer sketches"
    **1.** A beam stops only when something stops it, so a hit is a positive
    detection that is hard to fabricate; a pass-through, by contrast, is
    consistent with both "empty" and "an obstacle the beam missed" — thin
    poles, glass, grazing incidence, a chair leg between two rays. The
    inverse sensor model encodes that evidence gap directly as
    \(|l_{occ}| > |l_{free}|\), so one hit outweighs several free passes and
    thin structures survive being repeatedly carved by neighbouring rays.

    **2.** \(l = 3(0.85) - 0.4 = 2.15\);
    \(p = 1 - 1/(1+e^{2.15}) \approx 0.896\).

    **3.** Beam endpoint bookkeeping: 6 m is the lidar's max range, and
    max-range returns are being fed through the normal hit path, depositing
    \(l_{occ}\) at the far end of every unreturned ray. Classify a reading as
    max-range when \(z \ge z_{max} - \epsilon\) and update it as all free
    along the ray with no occupied endpoint — Bresenham to the range limit,
    then stop.

    **4.** Split the belief into two layers composed by maximum, Nav2-style:
    a **static layer** built offline from SLAM, saturated and never decayed
    (buildings), and a **dynamic obstacle layer** with a deliberately tight
    clamp so free evidence can win quickly. Size the clamp against the
    revisit rate using section G's arithmetic: with \(l_{max} = 2.0\) and
    \(l_{free} = -0.4\), a fully saturated cell falls below \(p = 0.5\) after
    5–6 free passes, so a route that re-observes the curb roughly every 2
    minutes forgets a departed car in about 10 — while the static layer is
    untouched by any amount of free evidence.

### Interactive quiz

<quiz-bank src="mapping-l1-grids"></quiz-bank>

## J. Annotated references

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Thrun et al., *Probabilistic Robotics*, ch. 9 | book | intermediate | Occupancy mapping, canonically |
| Moravec & Elfes (1985) | paper | introductory | Where grid mapping began — striking how much was right the first time |
| [Nav2 costmap docs](https://docs.nav2.org/configuration/packages/configuring-costmaps.html) | docs | intermediate | The production layer architecture, which is section F as configuration |

## K. Graded work and portfolio extension

**Graded:** the capstone's v2 stage — online mapping — is scored by the same
scenario rubric, so a bad map shows up as collisions and failed episodes
rather than as a bad-looking picture.

**Portfolio:** the three-maps study, presented as truth/noise/drift renders
side by side with cell-wise F1 scores. It is the cleanest possible
demonstration that you understand *why SLAM exists*, which is a better
interview signal than claiming to understand SLAM.
