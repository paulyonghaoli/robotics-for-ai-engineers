# 5.5 Planning under uncertainty

**Status:** Technically reviewed · **Prereqs:** Modules 3, lessons 5.1–5.4 · **Time:** ~1.5 h

---

## A. Why this matters

Every planner so far pretended the state was known and actions did what they said. Module 3 spent six lessons establishing that neither is true. This closing lesson is about the honest question — *plan on beliefs, not states* — and the engineering spectrum of answers, from the formally correct (and intractable) to the approximations every real robot actually ships.

## B. The spectrum

**The formal top: POMDPs.** Plan in *belief space* — states are probability distributions, actions both move the robot and change what it knows. Optimal solutions are intractable beyond tiny problems, but the *concept* reframes everything: with uncertainty, **information gathering becomes a planning action**. Driving past a landmark to relocalize before threading a doorway is optimal belief-space behavior that no known-state planner would ever produce.

**The practical middle, in increasing sophistication:**

1. **Determinize + replan** (what the capstone does): plan on the mean estimate, replan when reality disagrees. The receding-horizon insight (2.6) — replanning *is* feedback — makes this far more robust than it sounds, and it's the industry default.
2. **Inflate for uncertainty** (what costmaps quietly do): pad obstacles by localization σ; prefer clearance in proportion to how lost you might be. A costmap whose inflation grows with the localizer's covariance is a poor-man's belief-space planner — ten lines of code, most of the benefit.
3. **Chance constraints**: require P(collision) ≤ ε along the path, propagating state covariance (Module 3's P!) through the plan geometrically — clearance requirements that adapt per-segment.
4. **Belief-space heuristics**: plan paths that *stay localizable* — hug information-rich regions (landmark visibility) the way ships hugged coastlines. The capstone's feature-poor-stretch failure (field note territory) is exactly what these methods prevent.

## C. From ML to robotics

- **POMDP intractability is why the field decomposes** into estimate-then-plan — the same reason end-to-end optimality gives way to modular pipelines everywhere in ML systems: the joint problem is cleaner on paper and unbuildable in practice.
- **Determinize-and-replan is online learning's "act on current belief, update on feedback"** — regret-minimization instincts apply, including the caveat: it fails precisely when errors are *irreversible* (cliffs, one-way doors) — the cases where you must plan conservatively rather than adaptively.
- **Information-gathering actions = active learning**: spending motion to reduce uncertainty is the label-budget trade, embodied.

### What padding buys, measured

The simplest way to plan under localisation uncertainty is to inflate the
obstacles by a multiple of the position noise and plan as if certain. Here is
what that actually buys, Monte Carlo over the lesson 5.1 grids with a
localisation error of \(\sigma = 1.5\) cells, 200 executions per path:

| Obstacle padding | Collision rate |
|---|---|
| none | **79.1%** |
| 1 cell (0.7σ) | 44.6% |
| 2 cells (1.3σ) | 20.2% |
| 3 cells (2σ) | 5.2% |
| 4.5 cells (3σ) | **0.6%** |

The first row deserves a moment of respect: a *shortest* path executed under
realistic noise collides four times out of five, because shortest paths graze
obstacles by construction (lesson 5.2's first row) and any lateral error at
the graze point is a hit. The padding rows then trace the Gaussian tail
downward until the familiar engineering rule falls out of the data: **pad by
3σ and the collision rate lands near half a per cent**, which is the same
three-sigma logic as lesson 3.5's gates, applied in space instead of in
innovation. The cost is the same as the gate's, too — padding by 3σ closes
every gap narrower than \(2 \times 3\sigma\), so doorways start vanishing
from the map exactly as lesson 5.4's freezing analysis predicts. Uncertainty
does not make planning harder at the margins; it *consumes clearance*, and
clearance is the currency every lesson in this module has been trading.

## D. Where you've already met this

The capstone is a live exhibit: v1's PF drift during feature-poor stretches (a localizability problem the planner ignored), the mapped-crust inflation (uncertainty padding, ad hoc), replanning-with-hysteresis (determinize-replan with thrash control), and the collision-recovery behavior (the irreversibility hedge). This lesson is the vocabulary for decisions you already made — which is the right order to learn it.

## E. Questions

<quiz-bank src="planning-l5-uncertainty"></quiz-bank>

## F. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Kaelbling, Littman & Cassandra (1998) | paper | advanced | POMDPs — read for the framing, skim the algorithms |
| Thrun et al., *Probabilistic Robotics*, ch. 15–16 | book | advanced | Belief-space planning from the same canon as Module 3 |
| LaValle, *Planning Algorithms*, ch. 12 | book | advanced | Planning with sensing uncertainty, systematically |

## G. Graded work & portfolio extension

**Graded:** Module 5's planner-benchmark project (planned) includes an uncertainty-inflation scenario: same worlds, degraded localization, measure how each strategy's rubric metrics decay.

**Portfolio:** add covariance-scaled inflation to the capstone's mapping stack (strategy 2, ~15 lines) and publish the before/after rubric comparison under artificially degraded localization — a genuine belief-space idea, shipped and measured.
