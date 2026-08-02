# 4.3 EKF-SLAM: the chicken and egg, solved jointly

**Status:** Code verified · **Prereqs:** lessons 3.3, 4.1 · **Time:** ~2.5 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Lesson 4.1 mapped with a known pose; Module 3 localized with a known map. Robots usually have neither — that's **SLAM**, and the founding solution (still the cleanest to *understand*) is EKF-SLAM: put the robot pose AND every landmark into **one state vector** and run lesson 3.3's machinery on the whole thing. Modern systems have moved to graphs (next lesson), but the concept EKF-SLAM teaches — *correlations between robot and map are the product, not a nuisance* — is the heart of all of them.

## B. Mental model

The state is \([x_{robot}, m_1, m_2, \dots]\) with a full joint covariance. The magic lives in the **off-diagonal blocks**: robot–landmark correlations. When you observe landmark 3, the update improves the robot estimate; but through the correlations, it *also* improves landmarks 1, 2, and 4 — places you aren't even looking. Why? Every landmark was mapped from robot poses that shared errors: if landmark 3's observation reveals the robot was actually 20 cm left, then *everything mapped from those poses* was 20 cm left too, and the filter knows it.

The cinematic consequence: drive a long loop with growing drift, re-observe the *first* landmark, and watch the correction ripple backward through the whole map — **loop closure**, performed by linear algebra. That one update snapping an entire crooked map straight is the most satisfying plot in classical robotics.

## C. Mathematical formulation

State dimension \(3 + 2N\) for \(N\) 2-D landmarks. Motion updates touch only the robot block (landmarks are static — their process noise is zero); observations of landmark \(i\) have a sparse Jacobian touching the robot block and block \(i\) — but the covariance update densifies *everything*: after enough observations, every landmark correlates with every other (through the robot). That density is both the insight and the death sentence: the update costs \(O(N^2)\), which caps EKF-SLAM at a few hundred landmarks and motivates the sparse-graph reformulation of lesson 4.4.

Two structural facts worth internalizing: (1) **the map is only determined relative to the start** — absolute uncertainty never drops below the initial pose uncertainty (nothing anchors you to the world); (2) landmark initialization inherits the robot's current uncertainty *plus* measurement noise — mapping while lost makes vague landmarks, which is the chicken-and-egg made quantitative.

## D. From ML to robotics

- **The correlation structure is a learned covariance graph** — like a multi-task model where improving one head's calibration transfers to the others through shared parameters. The robot pose is the shared trunk; landmarks are heads.
- **\(O(N^2)\) densification → sparsification** is a familiar systems arc: exact joint inference gives way to structured approximations (the pose graph is robotics' answer, the way variational families are ML's).
- **Data association** — *which* landmark am I seeing? — is the classification-inside-the-loop problem, and a single confident wrong association corrupts the joint state like a mislabeled example that gradient descent then optimizes around. Gating (3.5) is the first defense; robust SLAM backends are the deep one.

## E. Minimal implementation & practice

<code-exercise src="map-l3-ekf-slam"></code-exercise>

## F. Robotics-framework implementation

Pure EKF-SLAM ships rarely today, but its descendants are everywhere: `robot_localization` is its landmark-free core; visual-inertial odometry (MSCKF) is EKF-SLAM with features marginalized out; and every graph SLAM system (4.4) can be read as EKF-SLAM with the marginalization deferred. The concepts — joint state, correlations, loop closure, association — carry over intact.

## G. Experiment

The exercise's world, extended: drive the loop three times. Plot (a) robot uncertainty over time — sawtooth: grows between landmarks, drops at re-observations; (b) the robot–landmark correlation coefficient — watch it *build* with shared history; (c) landmark uncertainty — monotonically shrinking, floored by the initial pose uncertainty (fact C1, observed). Then break data association on one observation (swap two landmark IDs) and watch the joint state absorb the lie — one plot per claim, and claim 3 is the scary one.

## H. Failure modes

- **Wrong data association**: the filter has no "undo"; one bad match warps robot *and* map (which then mis-associates further — the death spiral shape again).
- **Linearization drift**: mapping while lost means Jacobians evaluated at bad estimates (3.3's divergence), baked permanently into landmark positions.
- **Cost wall**: \(O(N^2)\) at every update; the practical ceiling arrives fast — the honest reason the field went to graphs.
- **Static-world assumption**: a "landmark" that moves (parked car) poisons the joint state slowly and confidently.

## I. Questions

1. *(Concept)* Why does observing landmark 3 improve landmark 1's estimate? Trace the mechanism through the covariance.
2. *(Calculation)* 50 landmarks: state dimension, covariance entries, and roughly how many multiply-adds per update?
3. *(Debugging)* After a long run your map is internally crisp but globally rotated 5° from the surveyor's ground truth. Is this a bug? What structural fact explains it?
4. *(System design)* You must SLAM a warehouse with 10,000 pallet-corner landmarks. Argue from the math why EKF-SLAM is disqualified and what property the replacement must have.

??? note "Answer sketch for Q3"
    Not a bug: the map is determined only relative to the start (fact C1); a global rotation is in the unobservable gauge unless something world-anchored (GPS, a surveyed marker) pins it.

### Interactive quiz

<quiz-bank src="mapping-l3-slam"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Durrant-Whyte & Bailey, SLAM tutorial parts I–II (2006) | paper | intermediate | THE entry point; part I is EKF-SLAM |
| Thrun et al., *Probabilistic Robotics*, ch. 10 | book | intermediate | Full derivation with the correlation story told carefully |

## K. Graded work & portfolio extension

**Graded:** the exercise's correlation-ripple assertions are the module's conceptual core, machine-checked.

**Portfolio:** the three-loop experiment's plots (sawtooth, correlation build-up, loop-closure snap) — the classical-SLAM story in three figures, and exactly what "explain SLAM to me" interview askers hope you'll draw.
