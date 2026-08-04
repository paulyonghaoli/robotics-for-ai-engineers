# Module 10 mini-project — The evaluation harness

The machinery that decides whether the robot got better. Nothing here trains
anything or runs a simulation.

```bash
cd projects/evaluation_mini
python -m grader
```

100 points across six checks, random seed each run unless you pass `--seed N`.

## What you implement

All in [`student.py`](student.py):

| | Points | |
|---|---:|---|
| `coverage_gaps` | 15 | Which factor combinations the suite can never fail on |
| `stratified_rates` | 10 | Per-stratum and pooled success |
| `simpson_reversal` | 15 | The aggregate disagreeing with every part of itself |
| `dedupe_failures` | 20 | 400 failure reports are 12 bugs |
| `coreset` | 20 | Farthest-point curation over an embedding |
| `cusum` + `psi` | 20 | Change detection, and the threshold nobody qualifies |

## The theme

Every check is a way of being confidently wrong with correct arithmetic.

- **A suite can be large and blind.** Seventy-two scenarios that only ever run
  in daylight leave sixteen of twenty-four cells untested. Suite size is not
  suite coverage, and the check for it is one function.
- **A pooled rate can disagree with every stratum it contains.** Policy B wins
  the easy scenarios and the hard ones, and loses overall, because it was run
  on four times as many hard ones. The pooled number is a statement about the
  mix rather than about the policies — and the mix changes whenever somebody
  adds scenarios between two runs.
- **A regression suite built from raw logs tests the loudest bug twenty times
  and the rarest one never.** Deduplication is the step between "we have four
  hundred failures" and "we have twelve".
- **Uniform sampling from an embedding pool returns the dense middle.** The
  rim is 10% of the pool and all of the interesting episodes.
- **`k` in a CUSUM is not a tuning knob**, it is a statement about the smallest
  shift you care about. Set it above the shift and the statistic never
  accumulates anything, forever, silently.
- **"PSI below 0.1 means stable" has a sample size attached that nobody
  quotes.** The grader measures the noise floor at n=300 directly: two halves
  of the *same* distribution average about 0.095. At that sample size the rule
  of thumb fires on pure noise.

## `evalkit.py`

Given, not modified: the scenario factor definitions, the synthetic fleet
failure log (with ground-truth bug labels used only for scoring), the
embedding pool, and the drifting stream.

## Relationship to Capstone IV

This project deliberately avoids what [Capstone IV](../capstone_ship/) already
covers — Wilson intervals, paired bootstrap, and minimum detectable effect
live there. The two fit together: the capstone decides whether a *difference*
is real, and this decides whether the *suite, the data and the monitoring*
around that decision are worth trusting.
