# 11.1 Latency budgets and the real-time contract

**Status:** Code verified · **Prereqs:** lessons 0.2, 10.1 · **Time:** ~2 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Lesson 0.2 introduced the rate hierarchy: control fast and dumb, planning slow and smart. This lesson is about what happens when a layer misses its rate — and why that is categorically different from a slow web request.

A web service that takes 400 ms instead of 40 ms is annoying. A control loop that takes 40 ms instead of 4 ms has changed the plant it is controlling: the delay enters the loop dynamics, phase margin drops, and a well-tuned controller can go unstable. **Latency in a feedback system is not a performance metric, it is a stability parameter.** That is the whole reason robotics obsesses over tails rather than averages.

## B. Mental model

Three ideas do most of the work:

**The deadline is the contract.** Every stage in the loop has a period, and the only question that matters is how often the pipeline misses it. Mean latency is nearly irrelevant to that question — the misses live entirely in the tail.

**Tails don't add the way means do.** For independent stages, end-to-end p95 is *less* than the sum of per-stage p95s, because slow moments rarely coincide. In the exercise, the stage p95s sum to 59.5 ms while the end-to-end p95 is 45.1 ms. So budgeting each stage at its p95 is conservative — usable, but it will make you over-engineer.

**The biggest mean is usually not the problem.** This is the result worth internalizing, measured in the exercise:

| stage | mean (ms) | p99 (ms) |
|---|---:|---:|
| perception | **14.4** | 27.9 |
| estimation | 3.2 | 8.1 |
| planning | 5.1 | **47.2** |
| control | 2.1 | 5.9 |

Perception has nearly three times planning's mean. But halving perception takes the 50 ms deadline-miss rate from 4.2% to 2.6%, while halving *planning* takes it to **0.4%** — six times the improvement, from the stage that looks cheap on a mean-latency dashboard. Optimize the tail, not the average.

**Jitter is worse than latency.** A pipeline that always takes 30 ms is easy to design around: the delay is constant and can be modelled, even compensated. One that usually takes 5 ms and occasionally takes 80 ms is far harder, because the controller cannot be tuned for both. Predictability beats speed.

## C. Formulation

For a loop at frequency \(f\), the period is \(T = 1/f\) and the deadline-miss rate is \(P(\sum_i L_i > T)\) over per-stage latencies \(L_i\). Two design levers:

- **Reduce the tail** of the dominant contributor — often by capping work (a planner with an iteration limit, an anytime algorithm that returns its best-so-far) rather than by making the average faster.
- **Decouple rates.** If planning cannot meet the control period, it should not be *in* the control loop. Run it asynchronously at a slower rate and let the fast loop consume its most recent output. This is the rate hierarchy as an engineering technique rather than a description.

For the delay's effect on stability: a loop delay \(\tau\) contributes roughly \(-\omega\tau\) radians of phase at frequency \(\omega\). A controller with 45° of phase margin at 10 rad/s loses all of it at \(\tau \approx 78\) ms. That is the arithmetic behind "latency is a stability parameter."

### How stage percentiles compose — measured, and gentler than feared

Allocating an end-to-end budget across stages raises a question nobody
answers from first principles: do stage p95s add? Simulating a four-stage
pipeline with log-normal latencies, 200,000 end-to-end samples:

| Stage | Mean | p95 |
|---|---|---|
| Camera | 20 ms | 27.2 |
| Perception | 45 ms | 66.9 |
| Planning | 15 ms | 26.3 |
| Control | 5 ms | 6.8 |
| **Sum of stage p95s** | | **127.2 ms** |
| **True p95 of the end-to-end sum** | | **110.1 ms** |
| True p99 end-to-end | | 124.2 ms |

Stage p95s do *not* add — they over-predict the end-to-end p95 by about 15%,
because four independent stages rarely all have a bad tick simultaneously.
That makes the naive rule conservative rather than dangerous, and it yields
a genuinely useful engineering identity you can read off the last two rows:
**budgeting each stage at p95 and summing buys you approximately the
end-to-end p99.** Allocate that way deliberately and you get tail protection
one grade stronger than the arithmetic appears to promise.

Two caveats keep the rule honest. It leans on independence, and stages
sharing a CPU, a memory bus or a garbage collector are *not* independent —
correlated stalls push the true end-to-end tail back up toward the naive
sum, which is one more reason lesson 13.2 cares about isolating the control
path. And the comfort applies only to percentiles, never to deadlines: the
110 ms p95 still means one cycle in twenty is slower, and what happens on
that cycle — skip, extrapolate, or hold last command — is a design decision
this lesson's section C insists you make explicitly rather than discover.

## D. From ML to robotics

- **You already run p95/p99 dashboards.** The transfer is direct; what changes is the consequence of a breach — a dropped frame in a feedback loop is not a slow response, it is a missing correction.
- **Anytime algorithms are the robotics answer to timeouts.** Rather than failing a request, return the best plan found so far. Weighted A\* and sampling-based planners are naturally anytime, which is a substantial part of why they're used.
- **Tail-latency intuition from distributed systems transfers wholesale** — including that a single slow component dominates a pipeline, and that retries make tails worse rather than better.

## E. Practice

<code-exercise src="dep-l1-latency"></code-exercise>

## F. In production

ROS 2's executor model and QoS settings exist for exactly this; `ros2_control` runs its update loop in a real-time thread precisely to bound jitter. Nav2 separates the global planner (0.1–1 Hz) from the local controller (10–20 Hz) so a slow replan cannot stall actuation. On the learned side, the 2026 numbers make the trade concrete: world-action models at 590–800 ms per action chunk versus ~190 ms for lighter architectures — a difference that decides what control rate is even available to you.

Our own capstone reports p95 step latency as a rubric metric for this reason, and every stack has stayed under 6 ms against a 50 ms budget.

## G. Experiment

Instrument the capstone's `dynamic_stack.step()` per phase — beam classification, particle update, resampling, DWA rollouts — and log per-stage timings across 100 episodes. Plot each stage's mean and p99. The DWA rollout loop dominates by mean; check whether it also dominates the tail, or whether an occasional A\* replan does. Then cap the expensive one and re-measure the p95 rubric metric.

## H. Failure modes

- **Budgeting on means.** They add cleanly and tell you almost nothing about misses.
- **Optimizing the biggest mean** rather than the biggest tail — the exercise's whole point.
- **Retry-on-slow.** Retries add load exactly when the system is already struggling, which turns a slow moment into a queue.
- **Unbounded work in a bounded loop.** Any planner without an iteration cap will eventually take longer than its period. Cap it and return best-so-far.
- **Measuring latency on an idle machine.** Contention is the point; measure under realistic load, or you will discover the tail in the field.
- **Ignoring jitter.** A predictable 30 ms is easier to control than an unpredictable 5–80 ms, even though the second has a better average.

## I. Questions

1. *(Concept)* Why is latency a stability parameter in a feedback loop rather than just a performance metric?
2. *(Calculation)* Four stages with p95 of 23, 6, 26, and 4 ms. Is the end-to-end p95 equal to 59 ms, more, or less — and why?
3. *(Debugging)* Your control loop misses its 50 ms deadline 4% of the time. Perception has by far the largest mean latency. Where do you look first?
4. *(System design)* Your global planner sometimes takes 300 ms; the control loop needs 20 ms. Design the architecture.

??? note "Answer sketches"
    **1.** Because a delay \(\tau\) inserts phase lag \(-\omega\tau\) into the loop, eating the phase margin the controller was tuned with. At 10 rad/s, 78 ms of delay consumes 45° of margin entirely and a stable controller becomes an oscillating one. The output isn't merely late — the correction is computed from a state the robot has already left, which is a different feedback system than the one you designed.

    **2.** **Less.** For independent stages the sum's p95 is below the sum of individual p95s, because slow moments rarely coincide — the exercise measures 45.1 ms against a 59.5 ms sum. Budgeting each stage at its p95 is therefore safe but conservative, and will push you to over-engineer stages that were never the constraint.

    **3.** At the *tail* distribution of every stage, not the means. The largest mean is frequently not the largest p99, and deadline misses live entirely in the tail — in the exercise, halving the biggest-mean stage barely helps while halving a tail-heavy stage with a third the mean cuts misses six times as much. Plot per-stage p99 alongside mean; the gap between them identifies the culprit immediately.

    **4.** Take the planner out of the control loop. Run it asynchronously at whatever rate it manages (roughly 3 Hz here) and have the 50 Hz controller consume the most recent published plan, with a defined behaviour for a stale one — continue tracking, then slow, then stop. Make the planner anytime so a 300 ms budget returns its best-so-far rather than nothing. This is lesson 0.2's rate hierarchy used as an engineering technique: the fast loop must never block on the slow one.

### Interactive quiz

<quiz-bank src="dep-l1-latency-quiz"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Dean & Barroso, *The Tail at Scale* (2013) | paper | introductory | The canonical treatment of tail latency; transfers directly |
| [ROS 2 executors and QoS](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Executors.html) | docs | intermediate | Where the real-time contract is actually configured |
| Åström & Murray, *Feedback Systems*, ch. 9 | book | intermediate | Phase margin, and what delay does to it |

## K. Graded work & portfolio extension

**Graded:** the capstone's p95 latency rubric metric is this lesson in miniature.

**Portfolio:** the section G study — per-stage mean and p99 for your own stack, with the tail-dominant stage identified and capped, and the rubric metric before and after. It's a small, complete performance investigation with a measured outcome.
