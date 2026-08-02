# 11.4 Fleet telemetry and incident forensics

**Status:** Code verified · **Prereqs:** lessons 10.5, 11.3 · **Time:** ~2 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

A robot in the field did something wrong. You weren't there, nobody filmed it, and it has since driven forty minutes further. Everything you will ever know about that incident is whatever you decided to record **before it happened**.

That is the whole discipline. Forensics on a robot fleet is not an investigative skill so much as a *design* skill — the question "what would I need to diagnose this?" has to be answered in advance, under a bandwidth budget that makes recording everything impossible.

Every field note in the [capstone log](../../capstone-log.md) exists because the right thing was being logged. The max-range leakage was found by comparing measurement likelihood at the true pose against the estimate — a comparison that required the true pose, the estimate, and the raw scan to be available together at the same timestep.

## B. Mental model

**You cannot upload what the robot produces.** The exercise's numbers, which are realistic:

| strategy | sustained MB/s | fits a 2 MB/s uplink | can reconstruct an incident |
|---|---:|---|---|
| log everything | 33.16 | ✗ | ✓ |
| summaries only | 0.16 | ✓ | **✗** |
| ring buffer + trigger | 0.97 | ✓ | ✓ |

The middle row is the trap most fleets fall into: a telemetry system that fits comfortably and cannot answer a single interesting question, because the streams you need for diagnosis — camera, lidar — are precisely the expensive ones.

The answer is **capture locally, upload selectively**: keep a rolling buffer of everything on the robot, and when something trips a trigger, upload the window around it. Cheap in steady state, complete when it matters.

**And then the catch**, which is the part worth remembering:

```
triggered scheme tolerates up to 6.5 incidents/hour
  at  3/hour: 0.97 MB/s      (fine)
  at 12/hour: 3.46 MB/s      (blows a 2.0 budget)
```

Triggered telemetry's cost scales with the incident rate, so it fails **exactly when things start going wrong** — the moment you most need the data. Budget for the bad day, and give the uploader a degradation policy (prioritize, sample, or drop the lowest-value streams) rather than letting it silently queue or drop at random.

## C. What to record

The forensic minimum, learned the hard way:

- **A seed or equivalent replay key.** A failure you cannot reproduce is a failure you cannot fix. The capstone's harness makes every episode reproducible from its seed, which is why its bugs were tractable.
- **Both belief and truth where truth exists.** In simulation, log ground truth alongside the estimate; that comparison is what exposed lesson 3.6's unobservable-bias case, which no runtime signal could reveal.
- **Inputs, not just outputs.** Logging `cmd_vel` tells you what the robot did; logging the scan and the pose estimate tells you *why*.
- **Per-stage timings.** Lesson 11.1's tail analysis is impossible retroactively without them.
- **The decision, not only the trajectory.** For a planner: which plan was chosen and the scores of the alternatives. Thrash shows as an alternating sequence; freezing shows as the zero-velocity option winning. Neither is visible in the path alone.
- **Software version and config hash** on every record — lesson 9.3's `policy_version` problem, in telemetry form.

## D. From ML to robotics

- **This is observability**, with the twist that your uplink is a few megabits and the interesting signals are video-rate.
- **Triggered capture is sampling with a bias you choose.** Ordinary sampling would give you a representative view of normal operation, which is the least interesting thing you could collect.
- **Incident review is post-mortem culture**, and it works the same way: a blameless timeline, a root cause, and a change that makes the class of failure detectable next time — which usually means adding a log line you wished you'd had.

## E. Practice

<code-exercise src="dep-l4-telemetry"></code-exercise>

## F. In production

ROS 2 bags (now **MCAP**, the format worth knowing) are the standard container, with Foxglove the common viewer — and note from the [frontier research](../../frontier.md) that "mcap, ROS bags, Foxglove" appears verbatim as a bonus qualification in robot data-platform job postings. `diagnostic_aggregator` carries health status. Fleet operators run exactly the scheme in section B: continuous low-rate health, plus triggered upload of a buffer window on intervention or collision.

## G. Experiment

Add triggered capture to the capstone: keep a 50-step rolling buffer of pose, estimate, scan, and chosen plan, and dump it to JSON whenever a collision occurs or the goal is missed. Then run the v3 stack at 10 movers — the regime where its published envelope says it becomes unreliable — and diagnose the failures from the dumps alone, without re-running. That constraint is the point: field incidents don't come with a reproduction until your telemetry provides one.

## H. Failure modes

- **Telemetry that fits and explains nothing.** The summaries-only row.
- **Sizing for the average incident rate.** The scheme collapses on the bad day; budget for the spike.
- **No replay key.** Without a seed or equivalent, you have an anecdote rather than a bug report.
- **Logging outputs only.** `cmd_vel` alone can never tell you why a decision was made.
- **Unversioned records.** Telemetry that doesn't say which software produced it becomes unattributable within one release cycle.
- **Silent drops.** An uploader that discards data under pressure without saying so produces gaps exactly where the interesting events are.

## I. Questions

1. *(Concept)* Why is incident forensics on a fleet primarily a design activity rather than an investigative one?
2. *(Calculation)* Streams total 33.16 MB/s, buffer 30 s, and cheap continuous streams cost 0.14 MB/s. What sustained rate does 6 incidents/hour cost?
3. *(Debugging)* A robot froze in a doorway. You have its trajectory and `cmd_vel`. Why might that be insufficient, and what would you add?
4. *(System design)* 500 robots, 2 MB/s uplink each, and an incident rate that spikes 4× during bad weather. Design the telemetry.

??? note "Answer sketches"
    **1.** Because everything you can ever learn about an incident was fixed before it occurred — by what you chose to record. The robot has moved on, nobody observed it, and bandwidth made recording everything impossible, so the investigative phase can only work with decisions already made. The practical consequence is that "what would I need to diagnose this?" belongs in the design review, not the post-mortem.

    **2.** Each incident uploads \(33.16 \times 30 \approx 995\) MB. Six per hour is 5,970 MB over 3,600 s ≈ **1.66 MB/s**, plus 0.14 continuous ≈ **1.80 MB/s** — inside a 2 MB/s budget, but with very little headroom, which is why the scheme breaks by 12 incidents/hour.

    **3.** Because both are *outputs*. They tell you the robot chose zero velocity; they cannot tell you why. Freezing is a scoring outcome, so you need the decision: the candidate arcs considered and their score components, plus the scan and the clearance margin in force. With those, a freeze shows immediately as the zero-velocity option winning on a clearance term that no arc could satisfy — the diagnosis in lesson 5.4 — and without them you are guessing.

    **4.** Continuous low-rate health only (pose, diagnostics, intervention flags) at ~0.15 MB/s, plus a 30 s on-robot ring buffer of everything, uploaded on collision, intervention, or missed goal. Size the budget for the *spiked* rate rather than the nominal one — 4× a 3/hour baseline is 12/hour, which needs roughly 3.5 MB/s, so either raise the uplink, shorten the buffer, or define a documented degradation ladder (drop camera first, keep lidar and decisions) that engages under pressure and *reports* that it engaged. Version-stamp every record, and keep a replay key on each episode.

### Interactive quiz

<quiz-bank src="dep-l4-telemetry-quiz"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| [MCAP format](https://mcap.dev/) | docs | introductory | The container robot fleets standardized on |
| [Foxglove](https://foxglove.dev/) | docs | introductory | Where you'd actually inspect a bag |
| Beyer et al., *Site Reliability Engineering*, post-mortem chapters | book | introductory | Blameless incident review, which transfers intact |

## K. Graded work & portfolio extension

**Graded:** the telemetry-budget exercise is the module's fourth core skill, and its incident-rate catch is the part practitioners most often miss.

**Portfolio:** the section G study — triggered capture wired into your capstone, with a failure diagnosed purely from the dumps. Being able to say "I diagnosed this without re-running it" demonstrates the actual field skill, since field incidents never come with a reproduction attached.
