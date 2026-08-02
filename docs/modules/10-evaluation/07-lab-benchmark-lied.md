# 10.7 Lab: the benchmark that lied

**Status:** Code verified · **Prereqs:** lessons 10.1–10.6 · **Time:** ~2 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this lab exists

Every other diagnostic lab in this curriculum hands you broken *code*. This one hands you a broken *measurement* — a benchmark result that is arithmetically correct, reproducible, and completely misleading. That is the harder skill, and per lesson 10.1 it's the one the field is currently short of: roughly 80% of published manipulation SOTA claims don't survive a significance check.

You are the reviewer. Four results land on your desk, each with a number attached. Your job is to decide which ones you believe.

## B. The diagnostic table

| Symptom | What's really happening | Lesson |
|---|---|---|
| Impressive score, ~25 rollouts, no interval | The claim isn't supported at that sample size | [10.1](01-statistical-rigor.md) |
| Everything scores 95%+ | Benchmark saturated; it stopped discriminating | [10.2](02-scenario-suites.md) |
| Score collapses under a small perturbation | Evaluated on the training distribution and reported as generalization | [10.1](01-statistical-rigor.md) |
| Nightly gate fires constantly, aggregate flat | Cliff-edge scenarios flipping on noise | [10.3](03-regression-from-logs.md) |
| Metric improved, field failures rose | Suite over-samples easy cases; aggregate hides the trade | [10.2](02-scenario-suites.md) |
| A trivial baseline matches SOTA | The benchmark isn't measuring the capability it claims to | [10.1](01-statistical-rigor.md) |
| Model wins on the leaderboard, loses on the rig | Cross-lab protocol differences dominate the comparison | [10.2](02-scenario-suites.md) |

## C. The audit

Four submitted results, one honest. Work out which — and, for each of the others, name the specific defect.

<code-exercise src="eval-l7-audit"></code-exercise>

## D. Diagnosis drills

<quiz-bank src="eval-l7-drills"></quiz-bank>

## E. Debrief

The reviewer's checklist, in the order that catches the most problems soonest:

1. **How many trials, and what's the interval?** Almost never reported, and it invalidates more claims than everything else combined.
2. **Is there a trivial baseline?** If a linear probe or a constant policy matches the result, the benchmark isn't measuring what its name says. A 0.09B-parameter probe with no language encoder matching SOTA on LIBERO is the field's most useful embarrassment.
3. **Does it survive perturbation?** Move the camera, change the initial state. A 95%→30% collapse means the number described memorization.
4. **Was the suite tuned against?** Months of iterating on an evaluation set turns it into a training set, invisibly.
5. **Is the comparison paired?** Unpaired cross-condition comparisons need far more samples than anyone runs.

And the meta-point worth carrying out of this module: **every one of these defects produces a number that is arithmetically correct.** There is no bug to find, no exception, no stack trace. The only defense is a habit of asking what a measurement can and cannot support — which is a form of honesty before it is a form of statistics.

## F. Graded work & portfolio extension

**Graded:** apply the checklist to your own capstone results. The v3 stack's published operating envelope — reaching every goal at ten movers while being collision-free only half the time — exists because this audit was run on my own numbers and the aggregate was hiding it.

**Portfolio:** audit a published robotics result you find interesting, and write up what its numbers do and don't support. Done fairly and without dunking, it's a genuinely useful artifact and demonstrates a skill that shows up in very few portfolios.
