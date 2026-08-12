# 13.2 Real-time: the difference between fast and on time

**Status:** Code verified · **Prereqs:** lessons 11.1, 13.1 · **Time:** ~2 h · **Verified:** 2026-08-03, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Three implementations of the same 100 Hz control step, twenty seconds each:

| | mean | p99 | max | miss rate | worst run |
|---|---:|---:|---:|---:|---:|
| A allocating | **4.29 ms** | **4.87 ms** | 27.67 ms | 0.60% | 1 |
| B preallocated | 6.21 ms | 6.62 ms | **6.82 ms** | **0.00%** | **0** |
| C preempted | 4.71 ms | 15.26 ms | 16.45 ms | 3.00% | 6 |

A wins the mean. A also wins the **p99**, against a 10 ms deadline, with 5 ms of margin. And A misses its deadline every 1.7 seconds.

You ship B, which is 45% slower and never late. That is the whole lesson, and the rest of it is why the numbers that said otherwise were the wrong numbers.

## B. Mental model

**"Fast" is a score. "On time" is a qualification.** A control loop is not graded on how quickly it produced a command; it is graded on whether it produced one before the actuator needed it. Finishing in 4 ms instead of 6 buys nothing at all — the loop still runs at 100 Hz — while finishing in 27 ms once buys a missed cycle.

**p99 is not a tail metric at control rates.** At 100 Hz, the 99th percentile is the *once-per-second* event. A pause that happens every 1.7 seconds is rarer than 1 in 100 and therefore sits entirely above p99, which reports the ordinary case and calls it a tail. To see a once-a-minute event at 100 Hz you need p99.983. Nobody computes that, and they shouldn't: **at these rates the honest tail statistic is the maximum**, over a run long enough to contain the events you care about.

**Which raises the real question: how long is long enough?** There is a practical test. Plot the observed maximum against how long you measured. For an implementation whose worst case is *bounded* — fixed-capacity buffers, no allocation, no locks — the curve plateaus and stays there. For an unbounded one it keeps climbing, because you keep sampling further into a tail with no end. The shape of that curve is the closest thing to a worst-case execution time you will get without a static analysis, and it is worth an afternoon.

**And the shape of the failure matters as much as its rate.** C misses five times as often as A and reports as a 3% miss rate, which sounds mild. Its misses arrive in runs of six: 60 ms with no new command, ten times in twenty seconds. A's twelve misses are isolated single frames the controller absorbs. A miss rate is a marginal statistic, and marginal statistics cannot see correlation — the same blindness as [12.2](../12-data-infra/02-replay-determinism.md)'s divergence count, arriving in the time domain.

## C. Where the jitter comes from

Almost none of it is your algorithm.

- **Allocation.** `malloc` is usually fast and occasionally walks a free list, requests pages from the kernel, or triggers compaction. This is implementation A: a hot path that allocates is a hot path with an unbounded worst case, and the average tells you nothing about it.
- **Page faults.** The first touch of a page costs a kernel round trip. Memory that has been swapped or never faulted in costs more. `mlockall(MCL_CURRENT | MCL_FUTURE)` at startup removes the class.
- **Scheduler preemption.** A background process, a logger, a network interrupt. This is implementation C. Fixes: a real-time policy (`SCHED_FIFO`), CPU isolation (`isolcpus`, `taskset`), and keeping the control thread off the cores that service interrupts.
- **Priority inversion.** A low-priority thread holds a lock the control thread needs, and a medium-priority thread preempts *it*. The control thread waits on work that isn't running. Priority inheritance mutexes exist for this; the famous case is Mars Pathfinder, which reset itself repeatedly on the surface for exactly this reason.
- **Garbage collection**, if any part of the loop is in a managed language. Python's reference counting is incremental, and its cycle collector is not.
- **Frequency and thermal scaling.** The governor drops the clock, and the identical code takes longer. Benchmark with clocks pinned or you are measuring the governor — the same warning as [13.1](01-performance-model.md).
- **Cache and TLB.** A data structure that fits in L2 during the benchmark and not in production has a different worst case, and nothing in the code changed.

### Mean versus deadline — the exercise's three traces, read properly

This lesson's exercise supplies three latency traces from the same nominal
50 Hz loop with a 10 ms deadline, and the summary statistics disagree about
which implementation is best in exactly the way this module exists to teach:

| Trace | Mean | p95 | p99 | Max | Deadline misses |
|---|---|---|---|---|---|
| A — allocating in the loop | **4.29 ms** | 4.60 | 4.87 | 27.7 | 12 (0.6%) |
| B — preallocated | 6.21 ms | 6.50 | 6.62 | **6.82** | **0** |
| C — occasionally preempted | 4.71 ms | 4.86 | 15.3 | 16.5 | 60 (3.0%) |

Ranked by mean, A wins comfortably and B is the *worst* of the three. Ranked
by the only statistic the plant cares about — did the command arrive before
the deadline, every single time — B is the only acceptable implementation,
because its maximum is 6.82 ms and the deadline is 10. Trace A is 45% faster
on average and misses twelve deadlines when its allocator takes a 27 ms
excursion; a controller that skips twelve commands is not "faster", it is
broken twelve times.

Trace C is the diagnostic subtlety: mean *and* p95 both look healthy, and
the 3% miss rate lives entirely between p95 and p99 — a monitoring dashboard
plotting means and p95s would show C green while one command in
thirty-three arrives late. Real-time evaluation reads the **max and the miss
count**, treats percentiles below p99 as decoration, and understands why B's
uniformly *slower* loop is the correct engineering: preallocation traded
away the fast average that nobody needed for the bounded worst case that
everything depends on. It is the same trade as lesson 2.2's derivative
filter and lesson 10.2's balanced suite — the useful property lives in the
distribution's shape, not its centre.

## D. From ML to robotics

- **Throughput is the wrong axis, and it is the only one most ML tooling reports.** A batch of 64 at 2000 samples/s is irrelevant to whether one inference finished in 10 ms.
- **The mean is what you optimize; the max is what you ship.** Most of the optimizations that improve a mean — caching, lazy initialization, adaptive batching, dynamic shapes — do it by adding a rare expensive path, which is precisely the wrong trade here.
- **Determinism has value independent of speed.** A predictable 6.2 ms is worth more than an unpredictable 4.3 ms, and that sentence is close to meaningless in a training context.
- **This is what "no allocation in the hot path" means**, and why the C++ tracks in production robotics enforce it. It is not a performance rule. It is a *variance* rule: preallocation converts an unbounded worst case into a bounded one, at the cost of a slightly worse average. Row B, in one sentence.

## E. Practice

<code-exercise src="sys-l2-jitter"></code-exercise>

## F. In production

- **Preallocate everything at startup.** Fixed-capacity containers, object pools, ring buffers. Then assert at runtime that the hot path allocates nothing.
- **`mlockall` at startup**, plus `SCHED_FIFO` for the control thread and CPU isolation for its core.
- **PREEMPT_RT** if the platform supports it — it bounds kernel-side latency, which is otherwise the floor under everything above.
- **Lock-free SPSC queues** between the control thread and everything else, so the control thread never waits on a lock a lower-priority thread holds.
- **Measure the max, in production, forever.** A per-cycle deadline counter costs nothing and is the only thing that catches a regression the day it lands. This is [11.4](../11-deployment/04-telemetry-forensics.md)'s argument in the smallest possible form.
- **Log the misses with their run lengths**, not just a rate. The rate hides the shape.

## G. Experiment

Take the max-over-duration curve seriously: run your control loop for 1, 10, 60 and 600 seconds and plot the observed maximum against duration. Then remove one allocation from the hot path and do it again. What you are looking for is not a lower curve but a *flatter* one — the point at which measuring longer stops finding anything worse is the point at which you have a bound rather than a sample.

## H. Failure modes

- **Reporting p99 for a 100 Hz loop.** It describes the ordinary case with a tail-sounding name.
- **Benchmarking for two seconds.** In the exercise, A's first 200 frames contain zero misses and a 5.6 ms maximum. The property is rare, not absent.
- **Optimizing the mean.** Usually by adding a fast path with a slow fallback, which raises the maximum you were supposed to be lowering.
- **Treating a miss rate as the whole story.** Six consecutive misses and six scattered ones are the same statistic and different incidents.
- **Benchmarking on an idle machine.** Production has a logger, a perception stack, and a ROS graph on the same cores.
- **Assuming the deadline is the algorithm's.** Most missed deadlines are the operating system's, and no amount of algorithmic work moves them.

## I. Questions

<quiz-bank src="sys-l2-quiz"></quiz-bank>

## J. References

- Liu & Layland (1973), *Scheduling Algorithms for Multiprogramming in a Hard-Real-Time Environment* — rate-monotonic scheduling and the utilization bound; the foundation.
- The Mars Pathfinder priority-inversion post-mortem — the canonical worked example, and short.
- The `PREEMPT_RT` wiki and `cyclictest` — how kernel-side latency is actually measured.
- ROS 2 real-time design documentation, and the `rclcpp` allocator and executor notes — where these constraints meet a middleware people actually use.

## K. Graded work & portfolio extension

**Graded:** the exercise above.

**Portfolio:** instrument your capstone's control loop with a per-cycle deadline counter and publish the max-over-duration curve for two versions of the loop, one allocating and one preallocated. Report the mean, the max, the miss rate and the worst run length for both, and state which one you would ship and why. The interesting part of that write-up is defending shipping the slower one.
