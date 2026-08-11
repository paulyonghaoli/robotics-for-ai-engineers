# 9.5 World models: learn the dynamics, plan through it

**Status:** Code verified · **Prereqs:** lessons 2.6, 9.1 · **Time:** ~2.5 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Lesson 2.6 ended on a promise: *swap the physics model in sampling MPC for a learned one and you have model-based reinforcement learning.* This lesson collects on it.

A **world model** is a learned function \(\hat{f}(s, a) \to s'\). Fit it from logged experience, then plan through it exactly as you planned through the physics — sample action sequences, roll them out, score them, take the first action. That is the entire idea, and it is the core of Dreamer, of MPPI over learned dynamics, and of the world-action models that displaced VLM-backbone VLAs at the top of the 2026 leaderboards.

It is also where every theme in this module converges. The model is trained on data (lesson 9.3, so coverage decides where it is valid), its errors compound over a rollout (lesson 9.1's arithmetic, now applied to the model rather than the policy), and the only thing that saves you is re-observing the world (lesson 2.6's receding horizon).

## B. Mental model

**Planning through a learned model is imagination, and imagination drifts.**

A one-step prediction is usually excellent — that's what the model was fit to do. But planning needs *multi*-step rollouts, and each step feeds its own error into the next. The exercise measures this on a model fit to clean data:

| rollout length | mean \|predicted − actual\| |
|---:|---|
| 1 step | 0.09 |
| 2 steps | 0.47 |
| 4 steps | 0.72 |

One step is accurate. Two steps is already a fivefold degradation, and by four the imagined trajectory has drifted further than the lane is wide. And yet planning through this model **works** — provided you replan. The saving grace is that you only ever execute the *first* action of each plan, then re-observe. The model's job is not to predict the future accurately; it is to rank the immediate options correctly.

That reframing is the lesson: **a world model needs to be right about which action is best now, not about what the world will look like in two seconds.** The same measured system, open-loop versus replanning:

| horizon | plan once, execute open-loop | replan every step |
|---:|---|---|
| 4 | 0.53 | **0.08** |
| 8 | 2.12 | **0.16** |
| 16 | 2.98 | **0.15** |

Replanning is not a refinement here. It is the difference between working and not.

## C. Formulation

Fit \(\hat{f}_\theta\) by minimizing one-step prediction error on logged transitions:

\[
\min_\theta \sum_i \big\| \hat{f}_\theta(s_i, a_i) - s_i' \big\|^2
\]

then plan with the sampling MPC of lesson 2.6, substituting \(\hat{f}\) for the physics.

Two consequences deserve naming:

**One-step training, multi-step use.** You optimize one-step accuracy and then compose the model with itself H times. Nothing in the objective rewards staying accurate under composition, which is exactly why error compounds. Mitigations: train on multi-step rollouts directly, or penalize divergence over a horizon.

**The model inherits its data's coverage.** Outside the region the logs covered, \(\hat{f}\) is extrapolating, and a planner will cheerfully seek out exactly those regions — because an inaccurate model often looks *optimistic* there. This is model exploitation, and it is the planner doing its job against a flawed objective. The standard defences are penalizing uncertainty (ensembles disagreeing) and restricting the planner to stay near the data.

### Imagination decays; replanning forgives — measured

This lesson's exercise learns the plant's dynamics from logged transitions
and then plans through the learned model, and its own printed numbers carry
the whole argument. The fitted model is close but not exact —
\(x' = 1.753x + 1.001a\) against a true coefficient of 1.75 — and that small
error compounds through imagined rollouts exactly as lesson 9.1's policy
errors did: imagined-versus-real drift grows 0.09 → 0.47 → 0.72 over
horizons of 1, 2 and 4 steps, roughly multiplying per step because the plant
is unstable.

What matters is how the *planner* spends that decaying imagination:

| Planning horizon | Open-loop (execute the whole imagined plan) | Replan every step |
|---|---|---|
| 4 | 0.529 | 0.084 |
| 8 | 2.123 | 0.161 |
| 16 | **2.984** | **0.149** |

Open-loop execution gets *worse* as the horizon grows — a longer plan is a
longer stay inside a hallucination, and by horizon 16 the plan's later steps
are optimising a trajectory that no longer resembles reality. Replanning is
nearly flat across the same horizons, because it only ever *executes* one
step of imagination before checking in with the world, so the model error
never compounds beyond a single step's worth. This is lesson 2.6's
receding-horizon argument with the model now learned rather than given, and
it is the design rule of every working world-model system, from MPPI over
learned dynamics to the modern dreamer lineage: **imagine far, act once,
re-imagine.** The measured factor here — 20× better at horizon 16 — is what
that rule is worth.

## D. From ML to robotics

- **This is model-based RL**, and you have already built its planner. The only new component is the learned dynamics.
- **Compounding model error is lesson 9.1's problem with the roles swapped.** There, the policy's errors moved the state off-distribution; here, the model's errors move the *imagined* state off-distribution. Same arithmetic, different victim.
- **Model exploitation is reward hacking against a learned simulator** — the same circularity flagged in lesson 10.6 about neural evaluation. When you optimize against a model, you optimize against its mistakes too.

## E. Practice

<code-exercise src="rl-l5-world-model"></code-exercise>

## F. In production

NVIDIA's **DreamZero** adapts a video-diffusion backbone into a joint world-action model, denoising video and actions together; on the April 2026 RoboArena snapshot it led π0.5 and π0. **Cosmos 3** unifies language, image, video, audio, and action in one omnimodal model. The cost is stated plainly in NVIDIA's own writeup and is the constraint this lesson predicts: world-action models process roughly 10× longer token sequences and run at **590–800 ms per action chunk versus ~190 ms** for lighter architectures — a 3–4× slowdown in exactly the quantity (replanning rate) that compensates for model error.

Dreamer-line agents make the same trade in latent space rather than pixels, which is cheaper and less interpretable.

## G. Experiment

Fit a dynamics model to logged capstone episodes — predict the next pose from the current pose and commanded twist — then plan through it with lesson 2.6's sampling MPC and evaluate on the standard rubric. Compare against the physics-based planner. Then repeat with the model trained on only the v0 stack's logs and evaluate on worlds requiring v3-style behaviour: the model will be confidently wrong in exactly the situations it never saw, which is section C's coverage point measured on your own system.

## H. Failure modes

- **Trusting long imagined rollouts.** The horizon at which your model stays useful is measurable — measure it rather than assuming it.
- **Planning open-loop.** Without replanning, model error compounds unchecked; the table in section B is the price.
- **Model exploitation.** The planner finds the model's optimistic errors and drives toward them. Penalize uncertainty or constrain the planner to stay near the data.
- **Training one-step, evaluating one-step.** Your validation number says nothing about the composed accuracy your planner actually depends on. Report multi-step rollout error.
- **Latency eating the replanning budget.** A more accurate model that halves your replan rate can easily be a net loss, which is the trade the 2026 numbers make concrete.

## I. Questions

1. *(Concept)* Why can a world model with poor 4-step accuracy still support good control?
2. *(Calculation)* One-step prediction error is 0.09 and grows roughly 5× per step early in the compounding regime. At what horizon does predicted error exceed a 1.0-unit lane half-width?
3. *(Debugging)* Your planner consistently chooses actions driving the robot into a region where the real system performs terribly. What is happening, and what's the cheapest fix?
4. *(System design)* You can have a model that is twice as accurate but takes four times as long per query. Your controller runs at 20 Hz. Take it?

??? note "Answer sketches"
    **1.** Because control does not need an accurate future, it needs a correct *ranking* of the actions available now — and you execute only the first action of each plan before re-observing. Errors that would compound over four imagined steps never get the chance to accumulate in the real trajectory, since every step resets the rollout from a measured state. The exercise's tables show this directly: 4-step prediction error of 0.72 — wider than the lane — alongside a final tracking error of 0.08 under replanning.

    **2.** Starting at 0.09 and multiplying by five: 0.09, 0.45, 2.25 — so predicted error exceeds 1.0 between the **second and third step**. That is the honest planning horizon for this model, and it is a number you should measure rather than assume; anything beyond it is imagination being scored as if it were prediction. (Real growth eventually saturates once the model's predictions hit their clipping bounds, which flatters the numbers without making the rollout any more useful.)

    **3.** Model exploitation. The planner is doing its job against a flawed objective: outside the training data the model extrapolates, extrapolation is frequently optimistic, and an optimizer seeks optima wherever it can find them. The cheapest fix is to constrain the planner to stay near the data — reject candidate rollouts that leave the region your logs cover — before reaching for uncertainty-penalized ensembles, which cost more and are only worth it once the cheap constraint proves insufficient.

    **4.** No. At 20 Hz you have 50 ms per decision; four times the query cost forces you to either shorten the horizon drastically or drop the replanning rate, and replanning is precisely what compensates for model error (section B). Halving model error while quartering your replan rate trades away the mechanism that was covering for you. This is the trade the 2026 world-action models pay at 590–800 ms per chunk, and it is why lighter architectures remain competitive despite being less accurate per query.

### Interactive quiz

<quiz-bank src="rl-l5-world"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Hafner et al., *Dreamer* (2019–2023) | paper | advanced | Latent world models and planning in imagination |
| [NVIDIA: the rise of world-action models](https://developer.nvidia.com/blog/pretrained-to-imagine-fine-tuned-to-act-the-rise-of-world-action-models/) | blog | intermediate | DreamZero, and an unusually honest account of its cost |
| Williams et al., *MPPI* (2016) | paper | intermediate | The planner half, which you already built in lesson 2.6 |

## K. Graded work & portfolio extension

**Graded:** the world-model exercise closes the loop opened in lesson 2.6 — same planner, learned dynamics.

**Portfolio:** the section G study — a dynamics model fit to your capstone's logs, planned through with your own MPC, evaluated on the same rubric as the physics stacks. Reporting where the learned model's planning horizon runs out, measured, is a more useful artifact than a working demo.
