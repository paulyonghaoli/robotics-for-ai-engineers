# 11.6 Lab: the incident

**Status:** Code verified · **Prereqs:** lessons 11.1–11.5 · **Time:** ~2 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this lab exists

It's Monday. Fleet success dropped four points over the weekend. You have dashboards, a version history, and no idea yet which of five plausible stories is the real one.

Every prior lab in this curriculum gave you a broken *thing* — code, a filter, a map, a policy. This one gives you a broken *week*, and the diagnostic material is whatever your telemetry happened to capture. That constraint is the lesson: field incidents don't arrive with a reproduction, and the quality of your answer was determined before the incident began.

## B. The diagnostic table

| Symptom | Cause | Lesson |
|---|---|---|
| p99 latency crossed the deadline; both versions equally hurt | **Deadline cascade** — the loop stopped closing in time | [11.1](01-latency-budgets.md) |
| Drop concentrated on one software version | **Bad rollout** — the canary missed it, probably underpowered | [11.3](03-rollout-rollback.md) |
| Sensor statistics shifted and NIS rose; all versions hurt | **Environment or sensor drift** — the world changed, not the code | [10.5](../10-evaluation/05-drift-monitoring.md) |
| Model accuracy fine offline, worse on-robot | **Quantization or thermal** — calibration mismatch, or a cold benchmark lying | [11.2](02-edge-inference.md) |
| Zero safety violations reported, yet collisions occurred | **Monitor unsound or starved** — optimistic model, or it missed its own deadline | [11.5](05-safety-cases.md) |
| Telemetry uploads dropped during the worst hours | **Triggered-capture saturation** — cost scales with incident rate | [11.4](04-telemetry-forensics.md) |
| Real degradation; every metric you have looks normal | **Insufficient telemetry** — the honest answer | [11.4](04-telemetry-forensics.md) |

## C. The shift

Four incidents. Success dropped in all four, which is the only thing they share.

<code-exercise src="dep-l6-incident"></code-exercise>

The signatures you should arrive at:

| incident | drop | latency breach | version-correlated | NIS up | diagnosis |
|---|---:|---|---|---|---|
| A | 0.16 | ✓ | — | — | deadline cascade |
| B | 0.11 | — | ✓ | — | bad rollout |
| C | 0.13 | — | — | ✓ | environment drift |
| D | 0.11 | — | — | — | **insufficient telemetry** |

Incident D is the one worth sitting with. Every probe you have comes back clean while the robots genuinely got worse. The correct output is not a plausible story — it is *"we cannot say"*, followed by the signal you're adding so that next time you can.

## D. Diagnosis drills

<quiz-bank src="dep-l6-drills"></quiz-bank>

## E. Debrief

Three habits close out this module:

1. **Keep a control group, permanently.** Incident B is only diagnosable because some robots were still on v7. A fleet fully migrated to the new version cannot distinguish "our policy regressed" from "the world changed" — the two look identical, and you will guess.

2. **Layer your probes so they can disagree.** Latency, version, and belief consistency each catch a different cause; any one of them alone would have merged several incidents into one wrong story. This is the same panel argument as [lab 9.7](../09-robot-learning/07-lab-policy-memorized.md), arriving from operations rather than from modelling.

3. **"Insufficient telemetry" is a valid and often correct diagnosis.** It is also the only one that improves the system, because it converts an unexplained incident into a specific logging change. A confident wrong root cause closes the ticket and leaves the fault in place — which is worse than an open ticket, because now nobody is looking.

And the thread running through all of Module 11: **deployment failures are rarely failures of the algorithm.** A deadline cascade, an underpowered canary, a saturated uploader, an over-conservative monitor — every one of these is a correct component in a system whose operating conditions moved. That is the same shape as the capstone's eight field notes, at fleet scale.

## F. Graded work & portfolio extension

**Graded:** the four-incident shift is Module 11's synthesis, and its probes transfer to any deployed system.

**Portfolio:** run a self-inflicted incident on your capstone. Degrade something deliberately — inflate a sensor sigma mid-run, or ship a "regressed" stack to half the seeds — then diagnose it from telemetry alone without looking at what you changed. Write it up as a blameless post-mortem with a timeline, a root cause, and the logging change that would have caught it sooner. That document is a closer match to real robotics work than most portfolio projects ever get.
