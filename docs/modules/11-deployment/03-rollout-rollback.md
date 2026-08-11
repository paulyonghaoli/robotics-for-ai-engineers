# 11.3 Rollout and rollback across a fleet

**Status:** Code verified · **Prereqs:** lessons 10.1, 11.1 · **Time:** ~2 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

You have a new policy. It beats the old one on your evaluation suite. Now put it on 500 robots.

Everything you know about staged rollout applies — canary, percentage ramp, automatic rollback on a health signal — with three differences that change the engineering:

1. **Rollback is not instant.** A robot mid-task cannot be reverted in the middle of a grasp. Reverting means "finish or safely abort, then swap," and that takes minutes, not milliseconds.
2. **The blast radius is physical.** A bad web deploy serves errors; a bad policy drives into shelves. Damage doesn't roll back at all.
3. **Evidence accumulates slowly.** A web canary sees a million requests in an hour. A robot canary sees maybe fifty episodes in a shift, and — as this lesson's arithmetic shows — fifty episodes is close to no evidence.

## B. Mental model

**A canary is a hypothesis test, and most robot canaries are underpowered.**

You are asking: is the new policy's failure rate worse than the old one's? With a 2% baseline, here is what canary size actually buys you:

| canary episodes | detects a 2% → 5% regression | detects 2% → 3% |
|---:|---:|---:|
| 50 | **24%** | 6% |
| 100 | 38% | 8% |
| 250 | 81% | 22% |
| 500 | **98%** | 43% |
| 2000 | 100% | **87%** |

Read the first row carefully. A 50-episode canary misses a regression that **more than doubles your failure rate** three times out of four. "We ran it overnight on one robot and it looked fine" is, statistically, close to not having run a canary at all.

The second column is the harder truth: subtle regressions need enormous evidence. Catching a 2% → 3% shift reliably takes thousands of episodes, which for many fleets means weeks. That is not a reason to skip the canary — it is a reason to **know which size of regression your canary can and cannot see**, and to say so out loud when you promote.

**Size the canary from the regression you must catch**, not from the calendar.

## C. Formulation

With baseline failure rate \(p_0\), canary of \(n\) episodes, and a one-sided test at level \(\alpha\), the alarm threshold is the smallest \(k\) with \(P(X \le k) \ge 1-\alpha\) for \(X \sim \text{Binomial}(n, p_0)\). Power against a specific worse rate \(p_1\) is \(P(\text{Binomial}(n,p_1) > k)\).

Two design levers beyond size:

- **Stage the ramp** — 1 robot, then 5%, 25%, 100% — so each stage both accumulates evidence and bounds exposure. The later stages give the statistical power the first cannot.
- **Automate the rollback trigger.** A human watching a dashboard is not a control loop. Define the health signal, the threshold, and the action in advance, and make the action *safe* rather than immediate: complete-or-abort, then revert.

**The asymmetry that should shape your thresholds:** promoting a bad policy to 500 robots costs far more than delaying a good one by a day. Tune for power against the regressions you fear, and accept a higher false-alarm rate than you would in a web system.

### How big must a canary be — measured

A canary exists to catch a regression before full rollout, and its size is a
statistical decision that usually gets made by vibes. Here is the actual
detection power at a 5% false-alarm rate, for a fleet whose baseline succeeds
95% of the time:

| Canary episodes | Catches a 95%→85% regression | Catches 95%→90% |
|---|---|---|
| 20 | 35% | 13% |
| 50 | 78% | 38% |
| 100 | 94% | 55% |
| 300 | 100% | 95% |

The twenty-episode canary — a day of pilot traffic on a small fleet — misses
a *ten-point* collapse two times out of three, and a five-point one almost
seven times out of eight. It is not a safety net; it is a ritual. Reliable
detection of a ten-point regression starts around 100 episodes, and a
five-point regression, the size that actually ships past code review, needs
roughly 300. This is lesson 10.1's episodes-per-claim arithmetic wearing an
operations hat, and it sets canary duration from statistics rather than
patience: episodes per day × days = the left column, and you read the row
you can afford.

The design consequence is the one production fleets converge on: since the
canary that can catch small regressions is expensive in time, pair a small
fast canary (catching disasters at 100 episodes) with the regression gate of
lesson 10.3 running on *logged* scenarios, which replays thousands of
episodes per hour and catches the five-point class before any robot sees the
build. The canary then defends only against what replay cannot represent —
which is exactly the division of labour its size makes affordable.

## D. From ML to robotics

- **This is canary analysis** with a sample-rate problem. The methodology transfers; the episode budget is three or four orders of magnitude smaller, which changes what is detectable.
- **Health signals should be layered** exactly as in lesson 10.5: intervention rate and belief consistency move before success rate does, so a canary watching only outcomes reacts last.
- **The paired trick still helps.** If canary and control robots run the same routes, differences in route difficulty cancel (lesson 10.3), buying detection power at no extra episode cost.

## E. Practice

<code-exercise src="dep-l3-canary"></code-exercise>

## F. In production

Fleet operators stage by site and by shift, hold a control group on the previous version, and gate promotion on intervention rate rather than success rate because it moves earlier. AgiBot's 2026 fleet-scale work runs the deploy → intervene → retrain loop across 16 robots continuously, which is a rollout pipeline and a data engine (lesson 9.3) sharing one mechanism. Waymo's structured testing reruns scenario libraries against every candidate build before any vehicle sees it — offline evidence first, precisely because on-road evidence accrues so slowly.

## G. Experiment

Treat your capstone stacks as versions. Run v1 as "current" and v3 as "candidate" on the same seeds, and compute at what episode count the paired test (lesson 10.3) first detects the difference. Then repeat unpaired. The gap is how much evidence pairing buys you — and on a real fleet, evidence is time.

## H. Failure modes

- **Underpowered canaries** that provide reassurance rather than information. The table in section B is the antidote.
- **Instant rollback assumptions.** Design for complete-or-abort; a robot cannot revert mid-grasp.
- **Watching only success rate.** It moves last (lesson 10.5). Watch interventions and consistency.
- **No control group.** Without robots still on the old version, a fleet-wide dip is ambiguous — new policy, or a change in the world?
- **Promoting on "no alarms."** Absence of evidence from an underpowered canary is not evidence of absence, and the promotion note should say which regression sizes were ruled out.
- **Ignoring the asymmetry.** Symmetric thresholds under-weight the cost of shipping a bad policy to the whole fleet.

## I. Questions

1. *(Concept)* Why is a robot canary categorically harder to run than a web canary?
2. *(Calculation)* Baseline failure 2%, canary of 50 episodes. A regression to 5% is detected 24% of the time. What does "no alarm" from that canary justify?
3. *(Debugging)* Fleet-wide success drops 3 points the week after a rollout. How do you tell a bad policy from a changed world?
4. *(System design)* 500 robots, ~40 episodes/robot/day, and you must catch any regression that doubles the 2% failure rate. Design the rollout.

??? note "Answer sketches"
    **1.** Evidence accrues thousands of times more slowly — a web canary sees a million requests an hour, a robot canary perhaps fifty episodes a shift — while the cost of being wrong is physical and does not roll back. Rollback is also not instant: a robot mid-task must complete or safely abort before swapping, so the mitigation window is minutes rather than milliseconds.

    **2.** Very little. With 24% power, the canary would have stayed silent about three-quarters of the time even if the failure rate had *more than doubled*. "No alarm" here rules out only catastrophic regressions, and the honest promotion note says so explicitly rather than implying the policy was validated.

    **3.** Keep a control group. If robots still on the old version show the same 3-point drop, the world changed — weather, a new site layout, a seasonal shift in what's being handled. If only the new-version robots dropped, it's the policy. Without a control group the two are indistinguishable, which is why the ramp should always retain a holdout rather than going to 100%.

    **4.** The fleet produces 20,000 episodes/day, so evidence is not the constraint — exposure is. Stage it: 1 robot for a day (≈40 episodes, enough only for catastrophic regressions, and treated as a smoke test), then 5% for a day (≈1,000 episodes, ample power against a 2× regression), then 25%, then 100%, holding ~5% on the old version permanently as a control. Gate each promotion on intervention rate rather than success rate since it moves earlier, automate the rollback as complete-or-abort-then-revert, and record with each promotion which regression sizes that stage could actually have detected.

### Interactive quiz

<quiz-bank src="dep-l3-canary-quiz"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Kohavi et al., *Trustworthy Online Controlled Experiments* | book | intermediate | Canary and A/B methodology, rigorously |
| [Learning while Deploying (arXiv:2605.00416)](https://arxiv.org/html/2605.00416v2) | paper | advanced | Fleet-scale deploy/retrain loops in practice |
| [Waymo safety methodology](https://waymo.com/safety/impact/) | docs | introductory | Offline scenario evidence before on-road exposure |

## K. Graded work & portfolio extension

**Graded:** the canary-sizing exercise turns "run a canary" into a number you can defend.

**Portfolio:** the section G study — the episode count at which your own stacks become distinguishable, paired versus unpaired. It converts a methodological argument into a measurement on a system you built.
