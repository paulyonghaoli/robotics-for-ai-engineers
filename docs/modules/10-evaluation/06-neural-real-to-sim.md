# 10.6 Neural real-to-sim evaluation

**Status:** Technically reviewed · **Prereqs:** lessons 10.1–10.2 · **Time:** ~1.5 h

---

## A. Why this matters

Real-robot evaluation is the bottleneck of robot learning. A rollout costs minutes of hardware time plus a human to reset the scene, so teams evaluate on 25 episodes and report numbers that (lesson 10.1) cannot support the claims made from them. Everyone knows this. Nobody had a way around it.

In 2026 that changed, and it's the development in this module most likely to be new to you: **learned simulators became accurate enough to rank policies.** Not to train them — to *evaluate* them, which is a lower bar and a higher-value one.

## B. Mental model

The old pitch for simulation was **simulate to train**: generate cheap experience, transfer the policy, fight the reality gap. The new pitch is **simulate to evaluate**: you don't need the simulator to be physically correct, you need it to *preserve the ranking* of policies. That's a much weaker requirement, and weaker requirements are achievable.

Concretely: if simulator S says policy A beats policy B, and reality agrees, S is useful — even if S's absolute success rates are wrong by twenty points. Rank correlation is the metric, not fidelity.

Two families:

- **Neural simulators** — video-prediction models trained on real robot data that roll out plausible futures conditioned on actions. [RoboWorld](https://arxiv.org/html/2607.01060v3) (2026) reproduced an entire real-world leaderboard across 8 policies at **Pearson r = 0.989, Spearman ρ = 0.970**, in 100 H100-hours.
- **Real-to-sim reconstruction** — rebuild the actual scene (Gaussian splatting for appearance, a physics engine for dynamics) and evaluate there. Soft-body manipulation studies report sim/real correlation **r > 0.9**.

The economics are the point: **2,000 simulated trials per checkpoint versus 100 real ones** is a different kind of evaluation. It's the difference between lesson 10.1's ±20-point intervals and ±2.

## C. Where it breaks

This is a young technique and its failure modes are not yet folklore, so hold it loosely:

- **Rank preservation is not transitive across regimes.** A neural sim trained on tabletop manipulation ranks tabletop policies well and tells you nothing about a policy that behaves differently out of distribution — which is precisely the policy you were worried about.
- **The simulator inherits its training data's blind spots.** If no real trajectory ever knocked the mug over, the learned dynamics have no opinion about what happens next.
- **Correlation is measured on the policies that existed when it was measured.** A genuinely novel policy is out of distribution for the *evaluator*, and r = 0.989 was not measured on it.
- **It cannot discover unknown unknowns.** Real evaluation surfaces the failure nobody modeled; a learned simulator can only surface failures inside its model.

The honest position: neural evaluation is a very good *filter* — cheap enough to run per-commit, accurate enough to rank — sitting in front of a smaller, more expensive real evaluation that remains the ground truth. It replaces the middle of your funnel, not the bottom.

## D. From ML to robotics

- **This is model-based evaluation**, with the same circularity risk as using a learned reward model: you are grading with a model, so a policy can exploit the grader. Reward hacking has a direct analogue here.
- **The funnel structure is standard MLOps** — cheap offline proxy, then expensive online test. Robotics is arriving at the pattern late, because until 2026 the cheap proxy wasn't trustworthy.
- **Rank correlation over absolute fidelity** is the same insight as caring about AUC rather than calibrated probabilities when all you'll do is rank.

## E. What this means for your own work

You already have a hand-built version of this argument. The capstone harness is a physics simulator whose *only* job is to rank stacks — and this module has been treating its rankings as meaningful without ever claiming its absolute numbers transfer to a real robot. That is exactly the simulate-to-evaluate stance, arrived at from first principles.

The upgrade path, if you wanted it: log capstone episodes, fit a learned dynamics model (lesson 2.6's sampling MPC already anticipates this), and check whether the learned model preserves the v0/v1/v2/v3 ranking the physics harness produces. You have a known ground-truth ordering to validate against, which is more than most people building these have.

## F. Questions

<quiz-bank src="eval-l6-neural-sim"></quiz-bank>

## G. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| [RoboWorld (arXiv:2607.01060)](https://arxiv.org/html/2607.01060v3) | paper | advanced | The r = 0.989 leaderboard-reproduction result |
| [Real-to-sim eval with Gaussian splatting (arXiv:2511.04665)](https://arxiv.org/abs/2511.04665) | paper | advanced | Reconstruction-based evaluation for soft bodies |
| [World Labs: real-to-sim-to-real](https://www.worldlabs.ai/blog/real-to-sim-to-real) | blog | introductory | Vendor framing; note the 2,000-sim-vs-100-real protocol |

## H. Graded work & portfolio extension

**Portfolio:** the section E study — train a dynamics model on capstone logs and test whether it preserves the known stack ranking. A negative result is publishable-quality honest work here, because the technique is new enough that its limits are under-documented.
