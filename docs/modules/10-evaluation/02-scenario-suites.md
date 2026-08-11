# 10.2 Scenario-suite design: what to randomize, and what not to

**Status:** Code verified · **Prereqs:** lesson 10.1 · **Time:** ~2 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Lesson 10.1 showed how many episodes a claim needs. This lesson is about *which* episodes. A suite of 500 randomized worlds that are all structurally similar tells you one thing very precisely — and tells you nothing about the case that will break the robot in production.

Every autonomy team eventually builds a scenario suite, and the design decisions are always the same four: what varies, what stays fixed, how hard the cases are, and how you know the suite covers anything. Get them wrong and you get a number that improves while the robot gets worse.

## B. Mental model

**A scenario suite is a sampling design over the space of situations your robot can encounter.** Three failure shapes:

- **Too narrow** — everything randomized within a tight band. Metrics are precise and meaningless; you've measured performance on one situation 500 times. Our capstone's first worlds had this problem: random boxes, but always the same density.
- **Too wide** — randomize everything including things the robot was never designed for. Now every run fails somewhere and the metric is dominated by cases you don't care about. You cannot tell improvement from noise.
- **Unstratified** — the hard cases exist but are rare, so a 5%-of-episodes failure mode is invisible until it's 5% of *deliveries*.

The fix for the third is **stratification**: deliberately sample difficulty bands and report per-band, rather than hoping uniform sampling finds the tail. A suite that is 90% easy and 10% hard, reported as one aggregate, hides the number you actually need.

**What to hold fixed** is the underrated half. Randomizing the robot's own parameters (sensor noise, actuator limits) alongside the world makes regressions un-attributable: when the score drops you cannot tell whether the planner got worse or the sampler drew harder robots. Randomize the *world*; fix the *robot*; seed everything.

## C. Formulation

For a scenario space with parameters \(\theta\) (obstacle density, corridor width, start–goal distance, mover count), a suite is a set \(\{\theta_i\}\) plus a seed per scenario. Three properties worth measuring:

- **Coverage** — the fraction of the parameter space's cells that contain at least one scenario. Cheap to compute, and immediately exposes "we never test narrow corridors."
- **Stratification** — episodes per difficulty band. Report per band; aggregate only after.
- **Discrimination** — does the suite separate two stacks you *know* differ? A suite where every stack scores 100% has no discriminating power, and neither does one where everything scores 0%.

Discrimination is the property people forget. A benchmark that everything passes has stopped being a measurement — which is exactly how LIBERO saturated (lesson 10.1).

### A suite that everyone passes ranks nobody — measured

Discrimination is a property a suite either has or lacks, and it is
measurable. Take two policies with a genuine skill gap (0.70 against 0.85 on
this lesson's scale) and ask each suite to rank them, 120 episodes per
policy, 200 independent comparisons:

| Suite | Better policy scores | Weaker policy scores | Ranks them correctly |
|---|---|---|---|
| Trivial (difficulty 0.10) | 100% | 99% | **63%** |
| Balanced (difficulty 0.70) | 74% | 48% | **100%** |
| Brutal (difficulty 1.15) | 9% | 3% | 97% |

The trivial suite — the one whose dashboard looks best, where everything is
green — ranks a genuinely better policy above a genuinely worse one barely
more often than a coin flip, because both saturate the ceiling and the 1%
separation left over drowns in binomial noise. The information a suite
extracts lives in the *variance* of its outcomes, and variance dies at both
extremes: the brutal suite keeps most of its discrimination (97%) only
because 9% versus 3% is still a threefold ratio on the floor.

The design rule falls out directly: **a scenario suite should be tuned so
current policies score in the middle of the range**, and a suite your fleet
passes at 99% has stopped being an instrument — it is a regression tripwire
at best. This is also the honest reading of any public leaderboard whose top
entries cluster above 95%: the benchmark is no longer measuring what its
axis label claims, and the fix is harder scenarios, not more episodes.

## D. From ML to robotics

- **This is test-set design**, with the same pathologies: a test set drawn from one distribution, class imbalance hiding rare-case failure, and the slow leak of test information into design decisions as you iterate against it.
- **Stratified reporting is per-slice evaluation.** You would not ship a classifier on aggregate accuracy while a critical class sat at 40%; a robot suite reported only in aggregate is the same mistake.
- **Coverage metrics are the robotics analogue of feature-space coverage checks** in data validation — cheap, mechanical, and they catch the embarrassing gaps before a reviewer does.

## E. Practice

<code-exercise src="eval-l2-coverage"></code-exercise>

<code-exercise src="eval-l2-discrimination"></code-exercise>

## F. In production

Waymo and Zoox both build scenario libraries mined from real driving plus procedurally generated variations, and report per-scenario-class rather than one number. Nav2's regression suites fix the robot and vary the world exactly as argued in section B. The 2026 benchmark [RoboDojo](https://arxiv.org/html/2607.04434v1) went further and standardized the *physical* protocol — lighting, workspace layout, reset procedure — after finding those unstated variables dominated cross-lab differences.

Our own capstone harness is a small worked example: `make_world(seed)` varies obstacle count, size, and goal position; the robot's noise parameters are module constants and never randomized; every episode is reproducible from its seed.

## G. Experiment

Take the capstone's world generator and compute coverage over (obstacle count × start–goal distance). You'll find the corners are thin — very open worlds and very dense worlds are both rare under uniform sampling. Add a stratified generator that forces equal episodes per density band, re-run the v1 and v3 stacks, and compare per-band success. The aggregate barely moves; the hard band tells a different story.

## H. Failure modes

- **Randomizing the robot with the world** — regressions become unattributable.
- **Unseeded scenarios** — a failure you cannot reproduce is a failure you cannot fix. Every scenario needs a seed, and the seed belongs in the failure report.
- **Iterating against the suite** until it passes — the suite becomes a training set. Hold out scenarios you never tune against.
- **Aggregate-only reporting** — hides exactly the tail you built the suite to find.
- **Suites that no longer discriminate** — when everything passes, the suite is done measuring and needs harder cases, not celebration.

## I. Questions

1. *(Concept)* Why fix the robot's parameters while randomizing the world?
2. *(Calculation)* A suite is 90% easy (98% success) and 10% hard (40% success). What's the aggregate, and what does it hide?
3. *(Debugging)* Your suite's aggregate score improved 4 points after a change, but field failures went up. Give two suite-design explanations.
4. *(System design)* Design a 200-episode nightly suite for the capstone: which parameters vary, which are held out, how you stratify, and what triggers a build failure.

??? note "Answer sketches"
    **1.** Because a score change has to be attributable. If the sampler draws the robot's noise and actuator limits alongside the world, a drop between runs could be the planner getting worse or simply a harder robot, and the two are inseparable after the fact. Fixing the robot leaves the world as the only random factor, so seeds can be paired across stacks and the residual difference belongs to the code.

    **2.** \(0.9(0.98) + 0.1(0.40) = 0.922\) — a healthy-looking 92%, concealing a hard-case failure rate of 60%. If hard cases are 10% of the suite but 30% of real deliveries, the aggregate is not just optimistic, it's the wrong estimator.

    **3.** (a) The suite is unstratified and reported in aggregate, so a change that helps the dominant easy band by 5 points while degrading the rare hard band still moves the headline up — and the hard band is what the field encounters; (b) the suite has been iterated against until it passes and is now effectively a training set, so the 4 points measure fit to those fixed scenarios rather than generalization. Both are diagnosed the same way: report per band, and check the change against held-out scenarios you have never tuned on.

    **4.** Vary the world only — obstacle count and size, corridor width, start–goal distance, goal placement, mover count — and hold the robot fixed (sensor-noise constants, actuator limits, controller gains stay module constants), with a recorded seed per episode. Stratify into 4 density bands of 40 episodes each, and reserve one seed block of 40 (10 per band) as a holdout you never tune against. Report per-band success with intervals plus a coverage number over (density × start–goal distance); fail the build when any band's Wilson lower bound falls below its pinned floor or the holdout diverges from the tuned blocks by more than a few points — never on the aggregate alone, which is the number this design exists to distrust.

### Interactive quiz

<quiz-bank src="eval-l2-suites"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| [RoboDojo (arXiv:2607.04434)](https://arxiv.org/html/2607.04434v1) | paper | intermediate | Standardizing the physical protocol, not just the tasks |
| [Waymo safety methodology](https://waymo.com/safety/impact/) | docs | introductory | Scenario-based evaluation at real scale |
| Koopman & Wagner, *"Challenges in Autonomous Vehicle Testing"* | paper | intermediate | Why mileage is not a safety argument |

## K. Graded work & portfolio extension

**Graded:** the capstone's evaluation harness is a scenario suite; adding stratified reporting to `python -m eval` is the natural contribution.

**Portfolio:** the section G study — coverage heatmap plus per-band success for two stacks — demonstrates that you evaluate systems rather than run demos.
