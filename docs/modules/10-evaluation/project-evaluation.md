# Mini-project: The evaluation harness (autograded, 100 pts)

**Status:** Code verified · **Prereqs:** lessons 10.2–10.5 · **Time:** ~3 h · **Verified:** 2026-08-03, Python 3.13, NumPy ≥ 1.26

The machinery that decides whether the robot got better. Nothing here trains a model or runs a simulation — every check is a way of being confidently wrong with arithmetic that is entirely correct.

## Setup

```bash
cd robotics-for-ai-engineers/projects/evaluation_mini
python -m grader
```

Implement the stubs in `student.py`. `evalkit.py` is given: the scenario factor definitions, a synthetic fleet failure log, an embedding pool, and a drifting stream.

## The marks

| Check | Points |
|---|---:|
| `coverage_gaps` — which combinations the suite can never fail on | 15 |
| `stratified_rates` — per-stratum and pooled | 10 |
| `simpson_reversal` — the aggregate contradicting every part of itself | 15 |
| `dedupe_failures` — 400 reports are 12 bugs | 20 |
| `coreset` — farthest-point curation | 20 |
| `cusum` and `psi` — change detection | 20 |

## Four checks that are really about being wrong on purpose

**A suite can be large and blind.** Seventy-two scenarios that only ever run in daylight leave sixteen of twenty-four cells untested — and a suite with 72 entries reads as thorough in any summary anybody writes. The property worth reporting is not how many scenarios there are, it is which combinations the suite is *structurally incapable of failing on*. That check is one function and almost nobody has it.

**A pooled rate can disagree with every stratum it contains.** In the fixture, policy B wins the easy scenarios and wins the hard ones, and loses overall, because it was evaluated on four times as many hard ones. The pooled number is a statement about the *mix*, not about the policies. This is not a curiosity — the mix changes whenever somebody adds scenarios between two runs, which is every week, and the reversal it produces is invisible unless you stratify.

**`k` in a CUSUM is not a tuning knob.** It is a statement about the smallest shift you intend to catch. The grader sets `k` above the shift and asserts the detector *never* fires — no alarm, no error, no indication, for as long as the system runs. A monitor tuned for quiet is indistinguishable from a monitor that works, right up until the incident review.

**"PSI below 0.1 means stable" has a sample size attached that nobody quotes.** The grader measures the noise floor directly: 200 replicates of PSI between two halves of the *same* distribution at n = 300, which average about **0.095**. At that sample size the standard threshold fires on pure sampling noise, and the fix is to state the sample size next to the threshold or to stop using the threshold.

## Relationship to Capstone IV

This project deliberately avoids what [Capstone IV](../capstone-2/index.md) already covers — Wilson intervals, paired bootstrap and minimum detectable effect live there. The two fit together: the capstone decides whether a *difference* is real, and this decides whether the suite, the curation and the monitoring around that decision are worth trusting. A correct significance test on a blind suite is a confident answer to the wrong question.

## Portfolio extension

Run `coverage_gaps` against your own capstone's scenario suite and publish the gap list. Then pick the three gaps you think matter most, write those scenarios, and report whether the stack's success rate changed. If it did not, you have evidence that the gaps were harmless; if it did, you have a suite that was reporting a number about a world your robot does not operate in. Either result is worth more than the suite you started with.
