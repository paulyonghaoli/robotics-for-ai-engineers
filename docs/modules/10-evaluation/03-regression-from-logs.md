# 10.3 Regression testing a stochastic system

**Status:** Code verified · **Prereqs:** lessons 10.1–10.2 · **Time:** ~2 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Ordinary software regression testing rests on an assumption robots break: that the same input gives the same output. Run a robot twice on identical scenarios and you get different trajectories — sensor noise, actuator noise, resampling randomness. So "did this commit make things worse?" stops being a comparison and becomes a **statistical decision**, made every night, automatically, without a human reading confidence intervals.

Get this wrong in either direction and it costs you. A gate that's too loose lets real regressions through. A gate that's too tight cries wolf until the team stops reading it — and a nightly job everyone ignores is worse than no nightly job, because it looks like coverage.

## B. Mental model

Three tools, in increasing strictness:

1. **Seeded determinism** — pin every random source and require *bit-identical* trajectories. Catches any behavior change instantly and with zero statistics. It is also brittle: a NumPy version bump, a different summation order, or an intentional improvement all trip it. Use it for pure functions (transforms, planners on fixed grids), not whole stacks.
2. **Golden-metric bands** — record the reference metrics with intervals; fail when the new run falls outside. This is what a robot suite actually runs on.
3. **Paired comparison** — run old and new on the *same seeds* and test the difference (lesson 10.1's paired bootstrap). Strictly the most sensitive of the three at a fixed episode budget, because scenario difficulty cancels.

The insight worth carrying: **pairing is what makes nightly regression testing affordable.** Unpaired, detecting a 5-point regression at 95% confidence needs hundreds of episodes. Paired on identical seeds, the same detection costs a fraction of that, because you've removed the variance that comes from scenarios rather than from code.

## C. Formulation

Per scenario \(i\), outcomes \(a_i\) (baseline) and \(b_i\) (candidate) on the *same* seed. Test the mean paired difference \(\bar{d} = \overline{b - a}\) against zero with a bootstrap interval. Declare a regression when the interval lies entirely below zero — not when \(\bar{d} < 0\), which is true half the time by chance.

Two practical guards on top:

- **Effect-size floor.** Statistical significance is not operational significance. A reliably-detected 0.4-point drop is not worth blocking a release; require both "interval excludes zero" *and* "point estimate worse than δ."
- **Flake budget.** Some scenarios are near a behavioral cliff and flip on noise alone. Track per-scenario flip rates over time; a scenario that flips 40% of nights regardless of code is measuring the sampler, not the software — quarantine it rather than letting it dominate the gate.

## D. From ML to robotics

- **This is model-performance CI**, and the same rules apply: compare against a pinned baseline, use held-out data, and separate statistical from practical significance.
- **The flake budget is flaky-test triage** with a probabilistic twist — the flakes aren't infrastructure bugs, they're genuine sensitivity to initial conditions, and quarantining is a legitimate response rather than sweeping something under the rug.
- **Golden-metric bands are drift monitors on your own code**, the inward-facing version of lesson 10.5's outward-facing ones.

## E. Practice

<code-exercise src="eval-l3-regression"></code-exercise>

## F. In production

Nav2 and Autoware both run nightly simulation suites with metric thresholds. Waymo's structured-testing programme reruns scenario libraries against every candidate build. The pattern is consistent across all of them: **pin the scenarios, pin the seeds, compare paired, alert on bands rather than exact values** — and keep a quarantine list for scenarios whose flakiness has been characterized.

Our capstone harness already emits everything this needs: seeded scenarios, per-episode records, and a JSON dump.

## G. Experiment

Take the capstone's v1 stack as baseline. Introduce a deliberate small regression — lower `LOOKAHEAD` from 0.8 to 0.7 — and find the minimum episode count at which the paired test reliably detects it. Then repeat unpaired (different seeds for baseline and candidate) and observe how many more episodes you need for the same detection. The ratio is the concrete value of pairing, measured on your own system.

## H. Failure modes

- **Bit-exact gates on whole stacks** — they fail on library upgrades and on genuine improvements, so the team learns to ignore red.
- **Alerting on the point estimate** — half your nights are "worse" by chance.
- **No effect-size floor** — with enough episodes, every trivial difference becomes significant and blocks releases.
- **Unquarantined flakes** — a handful of cliff-edge scenarios dominate the signal.
- **Baseline drift** — quietly re-baselining after each small regression lets a large one accumulate one acceptable step at a time. Re-baseline deliberately, and keep the history.

## I. Questions

1. *(Concept)* Why does pairing on identical seeds reduce the episodes needed to detect a regression?
2. *(Calculation)* Nightly paired test over 100 scenarios: mean difference −0.03, 95% interval [−0.08, +0.02]. Block the release?
3. *(Debugging)* Your gate fires most nights but the flagged scenarios differ each time and the aggregate is flat. Diagnose.
4. *(System design)* Design the nightly gate for the capstone: episode count, paired or not, what blocks a merge versus what only warns, and how a scenario enters and leaves quarantine.

??? note "Answer sketch for Q2"
    No. The interval contains zero, so the observed −0.03 is consistent with no change. Blocking here trains the team to ignore the gate — and note that this is the *same* arithmetic as lesson 10.1's 18-of-25 problem, applied nightly.

### Interactive quiz

<quiz-bank src="eval-l3-regression-quiz"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| [Nav2 system tests](https://docs.nav2.org/development_guides/build_docs/index.html) | docs | intermediate | A real robotics regression suite |
| Google, *"Flaky Tests at Scale"* | paper | introductory | Quarantine as an engineering discipline |
| Efron & Tibshirani, *An Introduction to the Bootstrap* | book | intermediate | The resampling machinery under the paired test |

## K. Graded work & portfolio extension

**Graded:** the repo's own CI runs capstone evaluations on every push — the minimal version of this lesson.

**Portfolio:** implement the nightly gate against your capstone, run it across a week of commits, and show a regression it caught along with a near-miss it correctly declined to block. Demonstrating you can build a gate people *trust* is rarer than demonstrating you can compute a p-value.
