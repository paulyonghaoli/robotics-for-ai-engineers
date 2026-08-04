# Module 13 · Systems Performance

**Status:** In progress · **Course IV**

Everything up to here has been about whether the robot does the right thing. This module is about whether it does it **in time**, on hardware that costs a few hundred dollars and shares its CPU with four other processes.

Two threads run through it, and they meet at the same question.

**The performance model.** A policy at 220 fps on a workstation runs at 62 on the robot, and the reason is almost never the one people reach for. Memory bandwidth, kernel-launch overhead, host-to-device transfers and batch-1 inference explain the gap; peak TOPS explains none of it. The analysis is the graded work here — the arithmetic is what tells you which term to attack, and getting it wrong costs a quarter.

**The C++ track.** Production robotics is overwhelmingly C++: ROS 2 nodes, real-time control loops, perception pipelines. For an ML engineer transitioning in, not writing it closes a large fraction of postings, and it is not covered by the graduate course this curriculum is built to complement. It is taught here as **ports with parity checks** — take a component that already has a verified Python reference and a published spec, re-implement it, and prove numerical equivalence plus a latency budget the Python version cannot meet. That is how a real port is validated, and it is a more honest exercise than a language tutorial.

## Lessons

1. [The performance model: why the datacenter number doesn't transfer](01-performance-model.md) — **available**
2. [Real-time: the difference between fast and on time](02-real-time.md) — **available**
3. [The hot path: what C++ buys, and what it does not](03-hot-path.md) — **available**
4. [Porting with parity: validating a rewrite you cannot trust](04-porting-parity.md) — **available**
5. Lab: the optimization that didn't help — *planned*

## What you'll build

A three-term latency model that predicts where a frame goes and which hardware change would move it; a jitter analysis that separates "fast on average" from "meets its deadline"; and a parity harness that holds a C++ port to its Python reference on shared fixtures, seed by seed.

## What transfers

The profiling instinct transfers, and the numbers do not. If your performance intuition was formed at large batch on a machine with terabytes per second of bandwidth, essentially all of it is calibrated for a regime a robot never enters. Throughput becomes latency, FLOPs stop being the currency, the host CPU becomes a first-class participant, and the tail of the distribution matters more than the mean — because a control loop that meets its deadline 99% of the time misses it once every ten seconds.
