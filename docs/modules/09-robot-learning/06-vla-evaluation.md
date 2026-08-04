# 9.6 Vision-language-action models: inference and honest evaluation

**Status:** Code verified · **Prereqs:** lessons 9.2, 10.1 · **Time:** ~2 h · **Verified:** 2026-08-02

---

## A. Why this matters

VLAs are what most people mean when they say "robot foundation model": a vision-language model fine-tuned to emit robot actions, trained on large multi-robot datasets, prompted in natural language. They are the most visible thing in robotics right now.

This lesson treats them as something to **run and evaluate**, not to train. That is a deliberate stance, and the [frontier research](../../frontier.md) supports it on two grounds. Training one is a lab-scale endeavour with a large capital requirement. Evaluating one honestly is tractable, in demand, and — as lesson 10.1 documented — something the field is currently *bad at*, with roughly 80% of published claims failing a significance check.

The unglamorous truth worth carrying: a VLA runs at 3–10 Hz on top of the classical stack you built. Its outputs become setpoints for controllers, its beliefs come from filters, and its failures are caught by watchdogs. Courses I–II are the floor under this, not its predecessor.

## B. Mental model

**A VLA is next-token prediction with actions in the vocabulary.** Images and an instruction go in; a sequence of action tokens comes out; the tokens are decoded into joint or end-effector commands. Three design choices define the family:

1. **How actions are represented.** Discretized into tokens (RT-1/RT-2 use 256 bins per dimension), or generated continuously by a diffusion or flow-matching head (π0-line). This is lesson 9.2's multimodality question, answered architecturally.
2. **How much is predicted at once.** Single actions compound badly (lesson 9.1), so everything modern emits **chunks** — shortening the effective decision horizon.
3. **What the backbone was pretrained on.** The 2026 surprise was that general VLM capability is a *poor* predictor of downstream control, and that **vision, not language, is the limiting component** — instruction-following in these models is often doing far less work than the name suggests.

The exercise makes the tokenization choice concrete, and it produces a result worth internalizing beyond VLAs:

| action bins | task success | time within tolerance |
|---:|---|---|
| exact (continuous) | 1.00 | 0.92 |
| 4 | 0.97 | **0.24** |
| 16 | 1.00 | 0.79 |
| 256 | 1.00 | **0.92** |

Two lessons in one table. **256 bins is indistinguishable from continuous control** — which is why RT chose it. And a coarse tokenizer is **nearly invisible to the success metric** (0.97!) while destroying precision. If your evaluation is binary success, you cannot see this failure at all.

## C. The 2026 landscape

Dated, because it changes fast — check the [frontier map](../../frontier.md) before relying on any of it.

- **Open weights**: LingBot-VLA 2.0 (Apache-2.0, 6B, ~130 ms on an RTX 4090D), Galaxea G0Plus, Wall-OSS, NVIDIA GR00T N1.7.
- **Closed but influential**: π0.7 (first credible compositional generalization), Gemini Robotics 2 (whole-body control; adapts to a new embodiment from under 200 examples).
- **The architectural shift**: world-action models (DreamZero, Cosmos 3) that denoise video and actions jointly, at 590–800 ms per action chunk versus ~190 ms for lighter models.
- **The capability ceiling**, from DeepMind's own published numbers on dexterous hands: unscrew a bulb 92%, but tie a trash bag 44%, ziplock 40%, dustpan 32%. A task that succeeds a third of the time is not deployable labour.

## D. Evaluating one honestly

This is the actionable skill, and it is Module 10 applied to a specific target:

1. **Refuse saturated benchmarks.** LIBERO appears in 300+ papers and sits above 95%; its scores collapse from ~95% to under 30% under modest perturbation, and a 0.09B probe with no language encoder matches state of the art. A number from it tells you almost nothing.
2. **Report intervals, not points.** Real-robot evaluations typically use ≤25 rollouts. Lesson 10.1's arithmetic applies unchanged.
3. **Compare pairwise on shared hardware.** Absolute success rates aren't comparable across labs because reset procedures, lighting, and object sets differ — which is why RoboArena went double-blind and pairwise.
4. **Perturb.** Move the camera, change the initial state, swap a distractor. A model that memorized trajectories reveals itself immediately.
5. **Test the language channel.** Give a deliberately wrong instruction. If behaviour doesn't change, the model isn't conditioning on it — a documented finding, not a hypothetical.
6. **Measure the right thing.** The table in section B is the warning: binary success can hide a precision collapse entirely.

## E. Practice

<code-exercise src="rl-l6-tokenization"></code-exercise>

## F. Running one

The practical path is LeRobot: pull an open checkpoint, run inference on recorded observations, and — the part that matters — wire it into a closed-loop evaluation harness like the capstone's rather than eyeballing rollouts. Budget for latency: a 6B model at ~130 ms on a consumer GPU sets your control rate, and the classical stack underneath must remain stable at that rate.

## G. Questions

<quiz-bank src="rl-l6-vla"></quiz-bank>

## H. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| [What are we actually benchmarking? (arXiv:2606.04233)](https://arxiv.org/pdf/2606.04233) | paper | intermediate | The audit that should precede trusting any VLA number |
| [VLA-REPLICA (arXiv:2605.20774)](https://arxiv.org/html/2605.20774) | paper | intermediate | A $1,050 reproducible rig; best model 54% in-distribution |
| Brohan et al., *RT-2* (2023) | paper | intermediate | Action tokenization and the VLM-to-VLA recipe |

## I. Graded work & portfolio extension

**Graded:** the tokenization exercise is the mechanical core, and its evaluation lesson generalizes well beyond VLAs.

**Portfolio:** take an open VLA checkpoint and evaluate it against the six checks in section D, publishing what its numbers do and don't support. In a field where most published claims can't clear that bar, doing it carefully on someone else's model is a genuinely useful contribution — and considerably more tractable than training one.
