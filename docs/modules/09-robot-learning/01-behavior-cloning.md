# 9.1 Behavior cloning and the compounding-error problem

**Status:** Code verified · **Prereqs:** Modules 1–2, lesson 10.1 *(read ahead)* · **Time:** ~2.5 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Behavior cloning is the simplest thing that works: record an expert driving, fit a policy mapping observations to actions, deploy. It is supervised learning, you already know how to do it, and it is the backbone of essentially every imitation-learning system shipping today — ACT, diffusion policies, and the VLA families are all behavior cloning with better architectures and far more data.

It also fails in a way that has no analogue in your supervised-learning experience, and the failure is *structural* rather than a matter of insufficient data. Understanding it is the difference between "my policy has 2% validation error but crashes" and knowing exactly why those two facts are compatible.

## B. Mental model

Train a classifier and the test data arrives independently of your predictions. Deploy a policy and **your predictions determine what you see next** — lesson 0.1's closed loop, now biting the learner.

A small action error puts the robot in a state slightly off the expert's distribution. There, the policy is extrapolating rather than interpolating, so its error is larger. That larger error moves it further off-distribution. The error compounds along the trajectory rather than averaging out.

The arithmetic is unforgiving. With per-step error probability ε over a horizon of T steps, the expected number of mistakes for a supervised learner on i.i.d. data is \(O(\epsilon T)\); for behavior cloning in a closed loop it is \(O(\epsilon T^2)\). That quadratic is the whole lesson: **doubling your task length quadruples your trouble**, and no amount of clean demonstration data changes the exponent.

The intuition that sticks: *your expert never showed you how to recover, because your expert never got into trouble.* The demonstrations contain no examples of the states your imperfect policy will actually visit.

## C. Formulation

Given demonstrations \(\mathcal{D} = \{(o_i, a_i)\}\) from expert \(\pi^*\), behavior cloning solves

\[
\hat{\pi} = \arg\min_\pi \sum_i \ell\big(\pi(o_i),\, a_i\big)
\]

which minimizes error under the *expert's* state distribution \(d_{\pi^*}\), while performance at deployment depends on error under the *policy's own* distribution \(d_{\hat\pi}\). Those differ, and the gap grows with horizon. This distribution mismatch is the formal statement of section B.

**DAgger** (Dataset Aggregation) attacks it directly: roll out the current policy, have the expert label the states *it* visited, add those to the dataset, retrain, repeat. You are deliberately collecting data from \(d_{\hat\pi}\) — the distribution that actually matters. Its cost is that the expert must remain available to label new states, which for a robot means a human on the loop, which is precisely why the data engine (lesson 9.3) is where the money goes.

## D. From ML to robotics

- **This is covariate shift you caused yourself.** You've met distribution shift as something the world does to you; here the policy generates it, every rollout, by construction.
- **Validation loss stops being a proxy for performance.** A policy at 2% held-out error can fail every episode, because held-out error is measured on the expert's distribution. The only honest evaluation is closed-loop rollouts — which brings Module 10's entire apparatus to bear, and explains why the field's evaluation crisis and its imitation-learning practice are the same problem.
- **DAgger is active learning with a very expensive oracle.** The query strategy is "wherever my policy went," and the annotator is a human with a teleoperation rig at roughly $118/hour.

## E. Practice

<code-exercise src="rl-l1-compounding"></code-exercise>

<code-exercise src="rl-l1-dagger"></code-exercise>

## F. In production

Every shipping imitation system is behavior cloning plus mitigations. ACT predicts *action chunks* rather than single steps, which shortens the effective horizon and blunts compounding. Diffusion policies fix a different problem (lesson 9.2) but also chunk. The 2026 fleet-scale systems close the loop with interventions — a human corrects, the correction becomes training data — which is DAgger with the expert on-call rather than in the room. Physical Intelligence's RL post-training and the "learning while deploying" line of work are the same insight industrialized.

## G. Experiment

Train a cloned policy on the capstone's reference stack, then vary the horizon: evaluate on episodes truncated at 25, 50, 100, and 200 steps and plot failure rate against horizon. The relationship should look super-linear. Then add a small DAgger budget — relabel the 50 states where the policy deviated most — and watch the curve flatten. That's the entire lesson in two plots, on your own robot.

## H. Failure modes

- **Trusting validation loss.** It measures the wrong distribution. Report closed-loop success or report nothing.
- **Ignoring horizon.** A policy that works for 20 steps and fails at 200 is not "almost working" — it's exhibiting the expected quadratic.
- **Demonstrations with no recoveries.** A flawless expert produces data that teaches nothing about error states. Deliberately imperfect demonstrations, or explicit recovery data, outperform pristine ones.
- **Idle-action collapse.** If demonstrations contain many near-zero actions (pauses, waits), the loss is minimized by predicting "do nothing," and the policy learns to freeze. Balance or reweight.
- **Averaging multimodal demonstrations** — serious enough that it gets its own lesson (9.2).

## I. Questions

1. *(Concept)* Why does behavior-cloning error grow as \(O(\epsilon T^2)\) when supervised error grows as \(O(\epsilon T)\)?
2. *(Calculation)* Per-step error probability 1%. Roughly what fraction of 200-step episodes complete without a compounding failure, treating steps as independent?
3. *(Debugging)* Your policy has 1.5% validation error and fails 80% of episodes. What is the single most informative next measurement?
4. *(System design)* You have 40 hours of teleoperation budget for a task with a 300-step horizon. How do you split it between fresh demonstrations and DAgger-style corrections, and why?

??? note "Answer sketches"
    **1.** Supervised error accumulates linearly because each test state is drawn independently — a mistake at step *k* doesn't change the state at step *k+1*. In a closed loop it does: an action error moves the robot off the expert's distribution, where the policy is extrapolating and its error rate is *higher*, which moves it further off. One factor of *T* counts the steps, the second counts the growing per-step error rate as the state drifts, giving \(O(\epsilon T^2)\).

    **2.** Treating steps as independent, \(0.99^{200} \approx 0.134\) — about 13% of episodes survive. That's the *optimistic* bound, because it assumes the per-step error rate stays at 1% even off-distribution, which is exactly the assumption compounding violates. The real number is worse.

    **3.** Closed-loop rollouts with the *states* logged. Validation error is measured on the expert's distribution and is therefore uninformative about deployment; what you need is where the policy's own trajectories diverge from expert states, and how early. If divergence begins at a consistent point (a turn, a doorway), you have a coverage gap to fill with targeted data; if it accumulates smoothly from step one, you have classic compounding and need DAgger or action chunking.

    **4.** Roughly 30% fresh demonstrations to establish coverage, then 70% on DAgger corrections, allocated to the states the policy actually reaches. At a 300-step horizon the quadratic term dominates, and corrective data from \(d_{\hat\pi}\) is worth far more per sample than more expert-distribution data — you already have plenty of that. Spend the first block, train, roll out, and let the failures direct the remaining budget rather than pre-allocating it.

### Interactive quiz

<quiz-bank src="rl-l1-bc"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Ross, Gordon & Bagnell, *DAgger* (2011) | paper | intermediate | The compounding-error analysis and its fix, from the source |
| Zhao et al., *ACT / ALOHA* (2023) | paper | intermediate | Action chunking as a practical mitigation |
| [LeRobot](https://huggingface.co/docs/lerobot) | docs | introductory | Where you'd actually run this at scale |

## K. Graded work & portfolio extension

**Graded:** the compounding-error and DAgger exercises are the module's foundation; lesson 9.3 builds the data engine around them.

**Portfolio:** the section G study — failure rate versus horizon, with and without a DAgger budget, on the capstone. It demonstrates that you understand *why* imitation learning is hard, measured on a system you built, which is considerably rarer than having fine-tuned someone else's policy.
