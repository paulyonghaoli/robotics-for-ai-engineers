# Module 9 mini-project — Four ways a learned policy lies to you

Nothing here trains a network. Every check is a place where the number the
training loop optimizes and the number the robot is judged on point in
different directions.

```bash
cd projects/learning_mini
python -m grader
```

100 points across four checks, random seed each run unless you pass `--seed N`.

## What you implement

All in [`student.py`](student.py):

| | Points | |
|---|---:|---|
| `mse_optimal`, `mse_of`, `is_feasible` | 25 | The loss strictly prefers the action that crashes |
| `action_histogram`, `argmax_action`, `sample_action` | 25 | The fix, and the metric it loses on |
| `covers`, `real_success`, `best_width` | 25 | Tuning randomization in sim optimizes the wrong way |
| `best_by`, `pearson`, `selection_regret` | 25 | Early stopping picks the worst checkpoint |

## The four results

**The MSE-optimal action drives into the obstacle, and it does so by a wide
margin.** Two thousand demonstrations, half steering left and half right, both
sets of them fine driving. The mean sits at 0.001 rad — dead centre — and its
MSE is 0.365 against 0.724 for either mode. The loss prefers the crash *by a
factor of two*, so this is not a training failure or a tuning problem: a
perfectly converged regressor lands there, every time, on purpose.

**The fix is worse on the metric.** Discretize the action space, take the most
likely bin, and you get −0.65 rad — a real behaviour that clears the obstacle,
and sampling from the distribution clears it 100% of the time. Its MSE is
0.789, more than twice the regressor's. If you rank policies by validation loss
you rank this one last.

**Tuning domain randomization against simulator performance optimizes toward
the worst possible real-world result.** Simulator success falls monotonically
with randomization width, so the simulator always prefers the narrowest
setting; the robot needs the width to be at least 0.25 in order to cover the
friction it actually has. Best-by-sim scores **0.25** on the robot, best-by-real
scores **0.88**, and the transition between the two happens between two
adjacent grid points. It is a cliff, not a gradient — "it suddenly started
working" is what a cliff feels like from the outside. Randomizing everything is
not the answer either: past the coverage point, extra width is capacity spent
on cases the robot will never encounter.

**Early stopping on validation loss gives up 0.23 of success.** Across twelve
checkpoints the validation curve falls monotonically and looks textbook the
whole way down. On-robot success peaks at epoch 5 and declines from there. The
correlation between the two is **−0.17** — not weak, close to uninformative.
Picking the last checkpoint gets 0.48; picking the fifth gets 0.71.

## Relationship to Capstone IV

[Capstone IV](../capstone_ship/) trains the policy, runs the data engine, and
gates the release. This project is the set of facts that make those decisions
hard, isolated so that each one can be seen on its own — and every one of them
is a reason a policy that looks good in a notebook does not work on a robot.

## `learnkit.py`

Given, not modified: the demonstration generator, the action bin edges, the
sim-to-real parameter model, and the checkpoint table.
