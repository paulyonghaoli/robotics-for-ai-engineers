# Mini-project: Four ways a learned policy lies to you (autograded, 100 pts)

**Status:** Code verified · **Prereqs:** lessons 9.1–9.2, 9.4, 9.6 · **Time:** ~3 h · **Verified:** 2026-08-03, Python 3.13, NumPy ≥ 1.26

Nothing here trains a network. Every check is a place where the number the training loop optimizes and the number the robot is judged on point in different directions — which is the single most consistent reason a policy that looks good in a notebook does not work on a robot.

## Setup

```bash
cd robotics-for-ai-engineers/projects/learning_mini
python -m grader
```

Implement the stubs in `student.py`. `learnkit.py` is given: the demonstration generator, the action bin edges, the sim-to-real parameter model, and a checkpoint table.

## The marks

| Check | Points |
|---|---:|
| Mean collapse on multimodal demonstrations | 25 |
| Discretization, and the metric it loses on | 25 |
| Domain randomization width | 25 |
| Checkpoint selection | 25 |

## The four results

**The MSE-optimal action drives into the obstacle, and the loss prefers it by a factor of two.** Two thousand demonstrations at one state, half steering left and half right, every one of them fine driving. The mean sits at 0.001 rad — dead centre, inside the clearance — and its MSE is 0.365 against 0.724 for either mode.

That margin is the point of the check. It is tempting to read mean collapse as a training pathology, something a better optimizer or more data would fix. It is the opposite: a *perfectly converged* regressor lands there, because landing there is what minimizing squared error means when the target distribution has two modes. More data makes it more confident about the crash.

**The fix is worse on the metric.** Discretize the action space and take the most likely bin: −0.65 rad, a real behaviour, clears the obstacle, and sampling from the distribution clears it 100% of the time. Its MSE is 0.789 — more than twice the regressor's. Rank policies by validation loss and this one comes last. This is [9.6](06-vla-evaluation.md)'s argument in four lines of arithmetic, and it is worth having in a form you can run.

**Tuning domain randomization against simulator performance optimizes toward the worst possible real-world result.** Simulator success falls monotonically with randomization width — narrow is easier, and the simulator never leaves the range it was trained on — so a sweep scored in simulation always picks the narrowest setting. The robot needs the width to reach 0.25 to cover the friction it actually has. Best-by-sim scores **0.25** on the robot; best-by-real scores **0.88**.

The transition happens between two adjacent grid points, which is the second half of the lesson: real-world success is **discontinuous** in the randomization width. It is a cliff, not a gradient, and "it suddenly started working" is what a cliff feels like from the outside. Randomizing everything is not the answer either — past the coverage point, extra width is capacity spent on cases the robot will never encounter.

**Early stopping on validation loss gives up 0.23 of success.** Twelve checkpoints; validation loss falls monotonically and the curve looks textbook the whole way down. On-robot success peaks at epoch 5 and declines from there. The correlation between the two is **−0.17** — not weak, close to uninformative. The last checkpoint scores 0.48 and the fifth scores 0.71, and nothing visible in the training run distinguishes them.

## Relationship to Capstone IV

[Capstone IV](../capstone-2/index.md) trains the policy, runs the data engine, and gates the release. This project isolates the facts that make those decisions hard, so each can be seen on its own rather than inside a system where several are happening at once.

## Portfolio extension

Take any behaviour-cloning policy you have trained and plot on-robot success against validation loss, one point per checkpoint, with the epoch labelled. Most people have never drawn this plot for their own model, and it takes ten minutes given checkpoints you already have. If the cloud is uncorrelated, you have learned that your early-stopping criterion is a coin flip — which is a result worth writing down and one almost nobody publishes.
