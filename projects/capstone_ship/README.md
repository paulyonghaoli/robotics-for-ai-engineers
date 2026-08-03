# Capstone II — Ship a Learned Policy

Reference implementation for the [Course III capstone](../../docs/modules/capstone-2/index.md).
The system under test is [`../capstone_nav`](../capstone_nav); the candidate is a
behavior-cloning policy trained to imitate its classical stack.

The question is not "is the policy good." It is **"what apparatus would let you
say so, and be right?"**

## Run it

```bash
python collect.py --episodes 60
```

Gathers expert demonstrations, trains the candidate, writes `policy.npz` and
`training_report.json`.

```bash
python evaluate.py --episodes 48
```

Scores candidate and incumbent on held-out worlds, stratified by corridor
clearance and route length, with Wilson intervals per stratum. Writes
`suite_results.json`.

```bash
python evaluate.py --episodes 20 --check
```

The CI gate. Exits nonzero unless the incumbent stays above 0.85, the candidate
stays below 0.70, **and their intervals do not overlap** — so a sample too small
to resolve the gap fails rather than reporting a difference it hasn't earned.

## Files

| File | Stage | What it is |
|---|---|---|
| `policy.py` | 0 | NumPy MLP + body-frame featurizer. No torch, so CI trains it in seconds |
| `collect.py` | 0 | Expert rollouts → dataset → trained `policy.npz` |
| `bc_stack.py` | 0 | Wraps the policy in `capstone_nav`'s stack contract, so the same harness scores both |
| `evaluate.py` | 1 | Stratified scenario suite, Wilson intervals, the `--check` gate |

## Current results

Trained on 17,562 pairs from 60 expert episodes; **validation MSE 0.052**.

| | success | collision-free | collisions |
|---|---|---|---|
| incumbent (`reference_stack`) | 46/48 `[0.86–0.99]` | 46/48 | 1,156 |
| candidate (`bc_stack`) | 20/48 `[0.29–0.56]` | 20/48 | 13,435 |

Worst stratum for the candidate is **tight/long at 3/14 `[0.08–0.48]`** — long
horizon, small margin, which is where compounding error should bite and does.

A validation MSE of 0.052 and a success rate of 0.42 are the same policy. That
is the entire point of the capstone.

## Design notes

**Features come from `pose_meas`, not `sim.pose`.** The expert may use privileged
information to *choose* its actions — that asymmetry is what behavior cloning is.
The policy's *inputs* may not. Training on state you won't have at serving time
is train/serve skew, and it hides itself as a good validation number.

**The candidate is judged by the incumbent's harness, on the incumbent's seeds,
against the incumbent's rubric.** A candidate evaluated by its own bespoke script
is not comparable to anything.

**Two failure causes are deliberately in play and need separating.** Compounding
error (fixable with on-policy data) and an unrealizable expert — no function of a
single lidar scan reproduces a decision that depended on a global plan (not
fixable with more data). Stage 3 turns that distinction into a measurement.
