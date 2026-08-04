# 13.5 Lab: the optimization that didn't help

**Status:** Code verified · **Prereqs:** lessons 13.1–13.4 · **Time:** ~2 h · **Verified:** 2026-08-03, Python 3.13

---

## A. Why this lab exists

A quarter of performance work shipped. Five optimizations, all of them real engineering, all of them competently executed. One of the five was worth keeping.

Nothing here is a bug. Every one of these changes did exactly what it was designed to do — the accelerator is faster, the batch is bigger, the cache hits, the port is C++. Four of them made no difference or made the robot worse anyway, and the profile taken *before* the quarter began predicted every outcome.

That is the skill this module has been building toward: reading a profile well enough to know which work is worth doing, in a domain where the intuitions imported from ML training are calibrated for a machine the robot is not.

## B. The diagnostic table

| Symptom | Cause | Lesson |
|---|---|---|
| Nothing moved; the stage touched was a library call | **Already compiled** — same instructions either way | [13.3](03-hot-path.md) |
| Nothing moved; the term optimized was a sliver of the frame | **Not the bottleneck** — Amdahl's ceiling was 4% | [13.1](01-performance-model.md) |
| Throughput up, per-frame latency up | **Wrong metric** — a robot has one frame and needs it now | [13.1](01-performance-model.md) |
| Mean down, maximum up, misses up | **Mean not max** — a fast path with a slow fallback | [13.2](02-real-time.md) |
| Mean and maximum both down, deadline holds | **It worked** | — |

## C. The quarter

<code-exercise src="sys-l5-optimizations"></code-exercise>

The verdicts:

| optimization | mean | max | fps | misses | verdict |
|---|---:|---:|---:|---:|---|
| bigger accelerator | ×1.00 | ×1.00 | ×1.00 | 2% → 2% | not-the-bottleneck |
| batch 8 | ×0.42 | ×0.48 | **×3.33** | 2% → **100%** | wrong-metric |
| cache the expensive stage | **×1.34** | ×0.32 | ×1.34 | 2% → 9% | mean-not-max |
| C++ port of `undistort` | ×1.00 | ×1.00 | ×1.00 | 2% → 2% | already-compiled |
| graph capture | **×7.06** | **×6.77** | ×7.06 | 2% → **0%** | **worked** |

Two are worth dwelling on.

**Batch 8** is the most defensible mistake in the table. Throughput went up 3.3×, which is a real improvement to a real number, and it is the number every ML benchmark reports. It is also the number a robot does not have: there is one camera and one frame, and batching means each frame waits for seven that do not exist yet. Per-frame latency went from 16 ms to 39 ms against a 20 ms deadline, so *every* frame is now late. The optimization worked perfectly and the metric was wrong.

**The cache** is the most dangerous, because it improved the number the team was tracking. Mean frame time fell 25%. A cache is by construction a fast path with a slow fallback, and the fallback is the new maximum: the worst frame tripled, and deadline misses went from 2% to 9%. Against a deadline, an optimization that trades tail for mean is a regression that reports as an improvement — which is [13.2](02-real-time.md)'s argument arriving as a quarter of work.

And the one that worked touched no hardware and wrote no C++. It removed per-op dispatch, which the first profile said was most of the frame.

## D. Diagnosis drills

<quiz-bank src="sys-l5-drills"></quiz-bank>

## E. Debrief

Three habits close out the module, and Course IV.

**1. Compute the ceiling before starting.** Every entry in that table could have been predicted from one profile. The accelerator was 4% of the frame, so its ceiling was 4%. `undistort` was a library call, so its ceiling was the Python call overhead. Amdahl is an afternoon of arithmetic and it is the difference between a quarter of work and a week.

**2. Optimize the metric the system is scored on.** A robot's control loop is scored on whether every frame arrives before its deadline. Mean latency is a proxy for that, throughput is not a proxy for it at all, and both of them can improve while the thing you care about gets worse. State the requirement as a maximum and a deadline, and check optimizations against that statement rather than against the dashboard.

**3. Report the max alongside the mean, always.** Two of the four failures in this table are visible immediately in a two-column report and invisible in a one-column one. It costs nothing, and it removes the entire class of optimization that buys an average by selling the tail.

And the thread running through Module 13: **the performance intuitions you brought from ML are correct for a machine you are not deploying to.** Large batch, high bandwidth, throughput-scored, mean-optimized, a host CPU that is never the bottleneck — every one of those is false on a robot, and each one has a corresponding wrong decision that looks obviously right until you do the arithmetic.

## F. Graded work & portfolio extension

**Graded:** the five-optimization triage closes Module 13, and the probes transfer directly — `mean_gain`, `max_gain`, `throughput_gain` and a deadline check are a complete performance-review harness in four functions.

**Portfolio:** take one optimization you have already made to your capstone and evaluate it honestly against all four. Report mean, maximum, throughput and deadline-miss rate before and after, and state whether you would keep it. An optimization you *reverted*, with the measurement that justified reverting it, is a stronger portfolio entry than three that shipped — because it is evidence you measured rather than assumed.
