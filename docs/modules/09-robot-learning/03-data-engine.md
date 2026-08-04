# 9.3 The data engine: interventions and human-in-the-loop

**Status:** Code verified · **Prereqs:** lessons 9.1, 10.4 *(read ahead)* · **Time:** ~2.5 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Here is the fact the 2026 research keeps returning to, stated plainly: **the largest employment category in humanoid robotics is humans generating training data.** Figure runs a nine-role Data Collection department. Tesla pays $25–48/hour for people to wear motion-capture suits and walk test routes. Fully-loaded teleoperation runs about $118/hour.

That means every design decision in this lesson is a spending decision. "Collect more data" is not a plan; it's a budget line. The question a data engine answers is *which* data, and the difference between good and bad answers is measured in hundreds of thousands of dollars — recall lesson 10.4's arithmetic, where the redundant 95% of a dataset cost $380,000 to collect and bought 12% of performance.

This is also the lesson where your existing skills are worth the most. Robot data problems are data-engineering problems with expensive rows.

## B. Mental model

**The flywheel:** deploy → the policy struggles → a human intervenes → the correction becomes training data → retrain → redeploy. Each turn makes the next intervention rarer. This is DAgger (lesson 9.1) with the expert on-call rather than in the room, and it is how fleet-scale systems actually improve — AgiBot's 2026 "learning while deploying" work reports one shared policy across 16 dual-arm robots reaching 95% average success as fleet experience accumulates.

The economic insight that governs everything: **an intervention is worth far more per sample than a demonstration**, because it is a label at a state your policy actually reaches and cannot handle. A fresh demonstration is a label at a state you already cover. Same cost per hour, wildly different value.

The corollary people miss: **failures are data.** A pipeline that keeps only successful episodes throws away every example of the error states and recoveries a policy most needs — and then the field writes workshop papers about robots that can't recover. Recording an intervention costs nothing extra; you were already paying the human.

## C. Formulation

Given a labelling budget of \(B\) samples, allocate between:

- **fresh demonstrations** drawn from the expert's own distribution \(d_{\pi^*}\)
- **interventions** drawn from the deployed policy's distribution \(d_{\hat\pi}\), concentrated where it fails

Lesson 9.1's analysis says the deployment gap comes from error under \(d_{\hat\pi}\), so budget spent there attacks the actual problem. Empirically the split lands around 20–40% demonstrations (enough to establish basic coverage) and the remainder on interventions, re-allocated each round as failures move.

**What to record per intervention** — a schema worth getting right the first time, because these fields are cheap to write and expensive to reconstruct:

```
episode_id, timestamp, robot_id, policy_version,
state_before, policy_action, human_action, intervention_reason,
outcome_after (recovered | failed | ambiguous), operator_id
```

`policy_version` is the one teams forget, and without it you cannot tell whether an old intervention still describes a failure your current policy has. `intervention_reason` turns a pile of corrections into a failure taxonomy you can prioritize with.

**Weighting.** Interventions are rarer than demonstrations, so uniform sampling under-trains on them. Upweighting helps, but over-weighting produces a policy that behaves as though it is always in trouble. Treat the weight as a tuned hyperparameter with a held-out check, not a constant handed down.

## D. From ML to robotics

- **This is active learning with a $118/hour oracle**, and the query strategy is "wherever the policy struggled." The unusual part is that the labelling event and the failure event are the same event, so your annotation budget and your incident response are the same budget.
- **The flywheel is a feedback loop over your own training distribution**, with the attendant risk: the policy shapes the data that trains the policy. Deployments narrow, interventions concentrate there, and you can converge to a system excellent on a shrinking slice of the world. Hold out genuinely random scenarios to detect it.
- **Provenance is the same discipline as any lineage-tracked pipeline** (lesson 10.4), with the twist that you cannot backfill — yesterday's physical world is gone.

## E. Practice

<code-exercise src="rl-l3-budget"></code-exercise>

## F. In production

1X sells NEO with "Scheduled Expert Mode," where a human in a VR headset completes what the robot can't — and every session becomes labelled data. That is a data engine sold as a product feature. LeRobot v0.6.0 (July 2026) shipped a `lerobot-rollout` CLI with DAgger-style human corrections, making this a first-class workflow rather than bespoke infrastructure. Physical Intelligence's RL post-training and the ROVE line of work close the same loop with reinforcement rather than pure imitation.

The [frontier map](../../frontier.md) documents the hiring consequence: Figure's *Helix AI Engineer, Data Infrastructure* pays $150–400k and asks for Linux, Python, Postgres, SLURM/Kubernetes and dataset tooling — **no ML modelling required.**

## G. Experiment

Run the capstone's v1 stack and log every episode that fails, with the seed and the state where divergence began. Cluster those failure states. You will find they concentrate — feature-poor corridors, tight doorways — rather than spreading uniformly. That clustering *is* the argument for intervention-driven collection: a uniform sampler would spend most of its budget on situations the stack already handles.

## H. Failure modes

- **Discarding failed episodes.** The single most expensive habit in the list, and it looks like tidiness.
- **No `policy_version` on interventions.** You cannot tell live failures from historical ones, so stale corrections accumulate and distort training.
- **Over-weighting interventions** until the policy behaves as if perpetually in trouble — cautious, slow, and strange in ordinary conditions.
- **Flywheel narrowing.** The policy's deployments define the data, which defines the policy. Guard with held-out random scenarios.
- **Treating operators as interchangeable.** Two operators with different styles inject artificial multimodality (lesson 9.2). Record `operator_id` so you can detect it.
- **Optimizing hours collected.** Hours is an input metric. Coverage and per-source contribution are the output metrics.

## I. Questions

1. *(Concept)* Why is an intervention worth more per sample than a fresh expert demonstration, when both cost the same hour of human time?
2. *(Calculation)* A fleet runs 400 episodes/day at a 6% intervention rate. Each intervention is 90 seconds of operator time at $118/hour. What is the daily labelling cost, and how many labelled states does it buy at 10 Hz?
3. *(Debugging)* Your flywheel has run six months. Benchmark success is climbing; a new customer site performs terribly. What happened?
4. *(System design)* You have $50,000 and a policy at 70% success. Design the collection programme: what you collect, what you record, and how you decide when to stop.

??? note "Answer sketches"
    **1.** Because it is a label at a state drawn from \(d_{\hat\pi}\) — the distribution that determines deployment performance — and specifically at a state the policy could not handle. A fresh demonstration is a label from \(d_{\pi^*}\), a distribution you already cover densely; it reduces an error you were not making. Lesson 9.1's exercise is the extreme version: one round of intervention-style labelling moved success from 0% to 100%, which no volume of additional expert demonstrations would have achieved.

    **2.** 400 × 0.06 = 24 interventions/day; 24 × 90 s = 36 minutes = 0.6 h; 0.6 × $118 ≈ **$71/day**. At 10 Hz, 24 × 90 s × 10 = **21,600 labelled states per day** — for the price of a team lunch, which is the point: the flywheel is cheap precisely because you were already paying for the deployment.

    **3.** Flywheel narrowing. Six months of collecting interventions from your own deployments has concentrated the data on the situations those sites present, and the benchmark — likely built from the same deployments — narrowed with it. Both numbers are real; neither generalizes. The tell is that benchmark and field diverge, and the fix is a held-out set of genuinely randomized scenarios that never feeds training, plus deliberate collection at sites unlike your existing ones.

    **4.** At $118/hour, $50,000 is roughly 420 operator-hours. Spend ~25% establishing coverage on situations you have none for, then run the flywheel with the remainder: deploy, capture every intervention with the full schema (especially `policy_version` and `intervention_reason`), retrain in rounds, and re-allocate toward whatever the current failure taxonomy says is most common. Stop when the marginal round no longer moves held-out success by more than its confidence interval (lesson 10.1) — not when the budget runs out, and not at a predetermined success number, because the last few points may be unaffordable at any budget.

### Interactive quiz

<quiz-bank src="rl-l3-engine"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| [Learning while Deploying (arXiv:2605.00416)](https://arxiv.org/html/2605.00416v2) | paper | advanced | Fleet-scale offline→online RL: the flywheel, measured |
| [LeRobot](https://huggingface.co/docs/lerobot) | docs | introductory | Where DAgger-style correction is now a CLI command |
| [What 1,228 VLA papers say about the robot data problem](https://labelstud.io/blog/vla-robot-data-problem/) | analysis | introductory | Why composition beats volume |

## K. Graded work & portfolio extension

**Graded:** the budget-allocation exercise is this lesson's core, and it generalizes to any setting where labels are expensive and non-uniformly valuable.

**Portfolio:** build the intervention-capture path on your own capstone — log the state, the policy's action, a scripted "expert" correction, and the recovery outcome, then retrain and report success per round with intervals. That is a working data engine end to end, and it is the artifact the data-infrastructure roles are actually hiring for.
