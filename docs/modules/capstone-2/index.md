# Capstone IV · Ship a Learned Policy

**Status:** stages 0–3 live at `projects/capstone_ship/`, CI-gated; stages 4–5 in progress · **Prereqs:** Modules 9, 10, 11 and the [Course II capstone](../capstone/index.md) · **Time:** ~25 h

---

## The premise

The [Course II capstone](../capstone/index.md) asked you to build a robot. This one doesn't.

You have a working classical navigation stack. Someone on your team has trained a neural policy to replace it, and it looks good — low validation loss, smooth trajectories, and a demo video where it beats the classical planner to the goal. They want to ship it to the fleet.

**Your job is to decide whether they can.** Not to train a better policy — to build the evaluation and deployment infrastructure that turns "it looks good" into a defensible yes or no, and to be right about it.

This is deliberately the least glamorous framing in the curriculum, and it is the one [the frontier research](../../frontier.md) identifies as the highest-leverage skill for this audience. The field is in a documented evaluation crisis: policies are reported on demo reels and cherry-picked rollouts, and the people who can say *"here is the interval, here is the power, here is what would change my mind"* are rare enough that companies hire for it specifically — Figure's data-infrastructure role pays $150–400k and requires **no ML modeling at all**.

## What makes this a capstone and not an exercise

The system under test already exists and already works. `projects/capstone_nav/` gives you five stacks, a seeded simulator, and a scoring harness — so every number you produce is real, reproducible, and comparable to a strong incumbent. You are not evaluating a toy.

You also already know the answer to the headline question, which is the point. Module 9 established that behavior cloning accumulates error as O(εT²); a policy cloned from the classical stack **will** underperform it. The capstone is not a whodunnit. It is about building the apparatus that would have told you so *before* the fleet did — and that would have been just as trustworthy if the answer had come out the other way.

## The stages

Each stage produces an artifact that the next one consumes. Each maps onto lessons you have already done.

| # | Stage | You build | Draws on |
|---|---|---|---|
| 0 | **The candidate** | A behavior-cloning policy trained on demonstrations from `reference_stack` | [9.1](../09-robot-learning/01-behavior-cloning.md), [9.2](../09-robot-learning/02-multimodality.md) |
| 1 | **The scenario suite** | A stratified suite that reports per-stratum intervals, not one aggregate number | [10.1](../10-evaluation/01-statistical-rigor.md), [10.2](../10-evaluation/02-scenario-suites.md) |
| 2 | **The regression gate** | Paired comparison against the incumbent, with a power analysis that states what it can and cannot detect | [10.3](../10-evaluation/03-regression-from-logs.md) |
| 3 | **The data engine** | Failure mining → coreset curation → intervention-style retraining, and evidence the loop closed | [9.3](../09-robot-learning/03-data-engine.md), [10.4](../10-evaluation/04-dataset-lifecycle.md) |
| 4 | **The rollout** | Canary with a permanent holdout, a drift monitor, and a safety monitor with a trusted fallback | [11.3](../11-deployment/03-rollout-rollback.md), [10.5](../10-evaluation/05-drift-monitoring.md), [11.5](../11-deployment/05-safety-cases.md) |
| 5 | **The incident** | Diagnosis of a field regression from telemetry alone, written as a blameless post-mortem | [11.4](../11-deployment/04-telemetry-forensics.md), [11.6](../11-deployment/06-lab-the-incident.md) |

## What stages 0–1 already show

The reference implementation is far enough along to make the point concrete.

**Stage 0.** `collect.py` gathers 17,562 state–action pairs from 60 expert episodes and trains a two-layer MLP on them. It converges cleanly to a **validation MSE of 0.052**, which is the number that would go in the slide deck.

Two modelling decisions in there are worth more than the architecture. Features are taken in the robot's *body frame*, so the policy doesn't have to learn a rotation it can't generalize over. And features come from the same noisy `pose_meas` the policy will have at serving time — training on the simulator's true pose would be train/serve skew, and would produce a policy that validates beautifully and degrades on contact with the field.

**Stage 1.** `evaluate.py` scores the candidate on 48 held-out worlds, stratified by corridor clearance and route length, using the incumbent's own harness:

| stratum | candidate success | incumbent |
|---|---|---|
| open / short | 8/14 `[0.33–0.79]` | 13/14 |
| open / long | 5/10 `[0.24–0.76]` | 10/10 |
| tight / short | 4/10 `[0.17–0.69]` | 9/10 |
| **tight / long** | **3/14 `[0.08–0.48]`** | 14/14 |
| **ALL** | **20/48 `[0.29–0.56]`** | **46/48 `[0.86–0.99]`** |

Collisions: **13,435 for the candidate, 1,156 for the incumbent.**

Three things fall out, and none of them are visible in the validation loss:

1. **A healthy validation MSE bought a 0.42 success rate.** Offline loss is measured on the expert's state distribution; the policy is deployed on its own. That divergence *is* [lesson 9.1's](../09-robot-learning/01-behavior-cloning.md) compounding error, in a number.
2. **The aggregate hides the diagnosis.** 0.42 overall says "worse." The stratification says *where*: tight corridors on long routes, at 0.21 — exactly where a long horizon and a small margin compound. That is a specific, actionable failure mode, and it took a suite design to see.
3. **The incumbent is not perfect either** (46/48, 1,156 collisions), which is the honest baseline. A capstone that compared against a flawless oracle would teach you to expect one.

The CI gate asserts the *relationship*, not the numbers: the incumbent stays above 0.85, the candidate stays below 0.70, and their intervals must not overlap. That last clause is the interesting one — if the sample is too small to resolve the gap, the gate fails rather than reporting a difference it hasn't earned.

## What stage 2 adds

The gate that runs on *every* future change, where the question is not "is there a difference" but **"what size of regression would this miss?"**

Two results worth carrying:

**Pairing is not free power — it is power proportional to correlation.** Running both stacks on the same seeds removes the variance they *share*. Measured here it removes essentially none, because the incumbent succeeds on 46 of 48 episodes and a near-ceiling arm has no variance to share. A simulation in the same tool shows what it *is* worth as correlation rises: −1%, +4%, +18%, +56% at ρ = 0, 0.3, 0.6, 0.9. Pairing pays when both stacks struggle on the same scenarios — which is the normal regression-gate case of successive versions of one policy, and not this one.

**The order of the checks is the design.** A first draft reported INCONCLUSIVE on a 0.542 regression because the minimum detectable effect (0.298) exceeded the tolerance. That is backwards. If the interval already excludes the tolerance, the design was evidently powerful enough for *this* effect. Power gates only the reassuring verdict: "no regression detected" means nothing unless you could have detected one. So `BLOCK` is checked first, then `INCONCLUSIVE`, then `PASS`.

The minimum detectable effect itself depends on the **discordant** pairs — episodes where exactly one stack succeeded. Concordant pairs carry no information about the difference, which is why a scenario suite everything passes tells you nothing however long you run it.

## What stage 3 found, and why it is the most useful stage

Stage 3 is the data engine: mine the failures, curate a coreset, relabel at the learner's own states, retrain. It is DAgger, and the expected outcome is that success climbs.

It did not. Across three rounds, on 48 held-out episodes:

| round | dataset | val MSE | success |
|---|---:|---:|---:|
| 0 (plain BC) | 8,957 | 0.051 | 0.396 |
| 1 | 10,457 | 0.068 | 0.354 |
| 2 | 11,957 | 0.073 | 0.333 |
| 3 | 13,457 | 0.077 | 0.292 |

Success fell monotonically and validation loss *rose* monotonically as data was added — reproduced on two independent evaluation pools.

The diagnostic explains it. `aliasing()` measures how much expert action variance survives *within a neighbourhood of near-identical observations*: **0.227**. Nearly a quarter of what the expert does is not a function of anything the policy can see, because the expert plans A* over a map the policy was never given. No amount of data makes a function of the observation reproduce that.

So the two failure modes really are different things, and the distinction is not academic:

- **Compounding error** is a problem with the state *distribution*. DAgger fixes it by labelling where the learner goes.
- **An unrealizable expert** is a problem with *observability*. On-policy labels then add contradiction rather than coverage — which is exactly why validation loss rose, and it is [lesson 9.2's](../09-robot-learning/02-multimodality.md) mode averaging arriving as a measured effect rather than a warning.

The engineering conclusion is to **change the observation, not the dataset size** — give the policy the map, or a global plan, or history. The value of the aliasing measurement is that it says so *before* you spend three rounds of compute making the fit worse.

This is the stage most worth doing carefully, because "collect more data" is the default response to a weak policy and here it was the wrong one, provably.

## Doing it yourself

Two starters, one per stage:

- `student_evaluate.py` (stage 1) — five TODOs: `wilson`, `world_properties`, `build_suite`, `summarize`, `check`.
- `student_gate.py` (stage 2) — three TODOs: `paired_bootstrap`, `minimum_detectable_effect`, `gate`. The last one asks you to decide the order of the verdicts before writing it.

Both come with the contract and the reasoning documented, and the harness plumbing given.

The candidate policy, its training pipeline and its trained weights are handed
to you. They are the *system under test*, not the exercise. Reference
implementations live in `solutions/`, and reading them is not cheating — but
attempt yours first, because the point of the `check` function only lands once
you have written a gate and watched it refuse to call a difference it hadn't
earned.

## The deliverable

A **ship / no-ship decision report**. Not a model, not a notebook — a document that a skeptical staff engineer would sign off on, containing:

- the decision, stated in one sentence, with the interval it rests on
- what the gate can detect, and what it would have missed
- the failure modes found, and which ones the data engine actually fixed
- the conditions under which the decision would change

"No, and here is the specific experiment that would change my mind" is a **passing** report. "Yes" with a point estimate and no interval is not.

## The rubric

Note what is being scored. Not the policy — the *infrastructure*. A capstone whose rubric rewarded policy performance would teach exactly the wrong lesson.

| Metric | Bar | Why |
|---|---|---|
| **Regression detection** | Gate fires on an injected regression of stated size, at stated power | A gate that cannot detect the thing it exists to detect is theatre |
| **False-positive rate** | Gate does **not** fire on a known-null change, across repeated trials | The failure mode nobody measures; a flaky gate trains everyone to override it |
| **Interval discipline** | Every reported rate carries an interval; no bare point estimates | [10.1](../10-evaluation/01-statistical-rigor.md) — 8/8 successes bounds you at 0.68, not 1.0 |
| **Drift detection latency** | Injected distribution shift caught within a stated number of episodes | Detection you cannot put a number on is not a monitor |
| **Safety monitor liveness** | Zero violations **and** task success stays within tolerance of the incumbent | A robot that never moves has zero collisions; safety without liveness is not safety |
| **Decision traceability** | Every claim in the report links to a reproducible command | The whole point |

## Why this and not a perception or manipulation capstone

An honest note on sequencing, since the module numbers suggest otherwise.

Modules 7 (perception) and 8 (manipulation) are not written yet, and a capstone that depends on them would have to wait. Modules 9, 10 and 11 **are** complete, and they are the part of this curriculum least duplicated by the dozens of existing robotics courses — perception and manipulation are extremely well covered elsewhere, and evaluation infrastructure is barely covered anywhere.

There is also a structural argument. This capstone's system under test is the Course II capstone, which means the two compose: the classical stack you built becomes the incumbent you must beat and the oracle you must clone from. That only works in this order.

A perception/manipulation capstone remains worth building once Modules 7 and 8 land. It is not the one that should come first.
