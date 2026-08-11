# 9.7 Lab: the policy that memorized

**Status:** Code verified · **Prereqs:** lessons 9.1–9.6 · **Time:** ~2 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this lab exists

Six lessons, six ways a learned policy goes wrong. This lab puts them in one room and hands you the diagnostic job.

The premise is the module's recurring one: **every policy here has low held-out error.** That number is the field's default report and it separates none of these cases. What separates them is a *panel* of probes, chosen so that each pathology fails a different one.

## B. The diagnostic table

| Symptom | Pathology | Lesson |
|---|---|---|
| Low validation error, fails long episodes; failure rate grows super-linearly with horizon | **Compounding error** — no data from the states the policy reaches | [9.1](01-behavior-cloning.md) |
| Policy does something **no demonstrator ever did**, confidently, in an ordinary state | **Mode averaging** — MSE on multimodal demonstrations | [9.2](02-multimodality.md) |
| Works in the region the data covered, adrift just outside it | **Coverage gap** — collection never went there | [9.1](01-behavior-cloning.md), [9.3](03-data-engine.md) |
| Perfect nominally, degrades under noise or small parameter shifts | **No margin** — tuned to nominal conditions | [9.4](04-sim-to-real.md) |
| Benchmark climbing, new site failing | **Flywheel narrowing** — the policy shaped its own training data | [9.3](03-data-engine.md) |
| Planner drives toward regions the real system handles badly | **Model exploitation** — optimizing against a learned model's errors | [9.5](05-world-models.md) |
| High success rate, poor precision | **Wrong metric** — binary success can't see a precision collapse | [9.6](06-vla-evaluation.md) |

## C. The clinic

Four policies. One healthy, three broken differently, all with low held-out error. Build the probes and name each disease.

<code-exercise src="rl-l7-diagnose"></code-exercise>

The signatures you should end up with — note that **no single column separates all four**:

| policy | nominal | wider range | more noise | novel actions |
|---|---|---|---|---|
| A | 1.00 | 1.00 | 0.99 | 0.00 |
| B | 0.00 | 0.00 | 0.00 | **1.00** |
| C | 1.00 | **0.53** | 0.96 | 0.00 |
| D | 0.99 | 0.99 | **0.70** | 0.00 |

## D. Diagnosis drills

<quiz-bank src="rl-l7-drills"></quiz-bank>

## E. Debrief

Three habits generalize out of this module:

1. **Never report held-out error alone.** It is measured on the expert's distribution, and every pathology above survives it. Closed-loop rollouts are the minimum, and lesson 10.1's intervals are the honest version.
2. **Ask whether the policy did something absent from the data.** This single question separates mode averaging — the dangerous failure, because it invents an invalid action — from ordinary error, which resembles the demonstrations. It is cheap to check and almost nobody does it.
3. **Stress along more than one axis.** A wider range and more noise expose different diseases; a policy that passes one and fails the other has told you which. Choose probes that can *disagree*.

The unifying idea across all of Module 9 is worth stating once more, because it is the same shape every time: **composing an imperfect function with itself makes error grow, and something has to periodically re-ground it in reality.** For a policy, that regrounding is intervention data (9.1, 9.3). For a simulator, it is randomization spanning the truth (9.4). For a world model, it is replanning from a measured state (9.5). For a benchmark, it is real hardware (9.6). Remove the regrounding and the failure is always the same, only the victim changes.

And the module's measured numbers, kept as a set, because each is one clause
of that idea with a price on it: 0.00008 of offline MSE separates a policy
that lives forever from one that always dies (9.1); forty on-policy labels
beat twelve hundred off-policy ones (9.1); the mean of two 100% strategies
scores 0% (9.2); a thousand labels on the wrong distribution buy nothing
(9.3); randomisation over ±0.6 transfers 0% to a reality at 1.5 (9.4);
open-loop imagination at horizon 16 is twenty times worse than replanning
(9.5); and a tokenizer that destroys precision is invisible to a success
metric that reads 0.97 (9.6).

## F. Graded work & portfolio extension

**Graded:** the four-policy clinic is this module's synthesis, and its probes transfer to any learned controller.

**Portfolio:** run the panel against your own capstone stacks. They are hand-written rather than learned, so the interesting result is which probes they pass and which they don't — v3's published operating envelope, for example, is exactly a "no margin under stress" finding, discovered by running the noise probe before anyone asked for it.
