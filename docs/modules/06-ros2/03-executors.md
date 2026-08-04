# 6.3 Executors and callback groups: where your callbacks actually run

**Status:** Code verified · **Prereqs:** lessons 6.1, 13.2 · **Time:** ~2 h · **Verified:** 2026-08-03, Python 3.13

---

## A. Why this matters

You write five callbacks on a node. Each is short, each is correct, and none of them mentions threads. Then the control loop starts missing its deadline, and the reason is not in any of the five functions — it is in a scheduling model you never chose, because the default chose it for you.

Two facts do most of the damage:

- **A single-threaded executor runs one callback at a time**, so any callback can be delayed by the sum of all the others.
- **A multi-threaded executor changes nothing until you also change the callback groups**, because every callback lands in one mutually-exclusive group by default.

The second is why "I switched to a `MultiThreadedExecutor` and it behaved identically" is the most common report in this part of ROS 2.

## B. Utilization is the wrong number

Five callbacks on one node:

| callback | rate | duration |
|---|---:|---:|
| `control_timer` | 50 Hz | 4 ms |
| `scan_cb` | 10 Hz | 12 ms |
| `camera_cb` | 30 Hz | 18 ms |
| `diagnostics` | 1 Hz | 2 ms |
| `map_client` | 0.2 Hz | 45 ms |

Total load is **0.871 of one thread**. There is spare capacity, the numbers look healthy, and any dashboard would show a comfortable node.

The control timer's period is 20 ms and it can start **77 ms late** — the sum of every other callback's duration, because on one thread all of them can be in front of it. It misses its deadline by a factor of four while the thread it runs on is 13% idle.

**Capacity and timeliness are different questions**, and the executor is where they come apart. This is [13.2](../13-systems-perf/02-real-time.md)'s argument again, arriving from the middleware: the mean is fine, the maximum is not, and only one of them is the requirement.

## C. Groups, not threads

```
1 thread(s): control_timer waits up to  77.0 ms (period 20) -> MISSES
4 thread(s): control_timer waits up to  77.0 ms (period 20) -> MISSES
4 threads, own group:                    0.0 ms             -> ok
```

A **callback group** decides which callbacks may run *at the same time*:

- **MutuallyExclusive** — never two at once, however many threads exist. The default.
- **Reentrant** — any number at once, given threads to run them.

Every callback is in one mutually-exclusive group unless you say otherwise, so a `MultiThreadedExecutor` over the default grouping has more threads and exactly the same serialization. The middle row above is that, measured.

The fix is **both changes and neither alone**. Give the control timer its own group and it can run concurrently with the rest — but on one thread there is nothing to run concurrently *with*, so it buys nothing. Add threads without splitting the group and the group still serializes. The exercise asserts both halves, because each one on its own is a plausible fix that does nothing.

## D. The deadlock

A callback makes a synchronous service call and waits for the response. The response can only be delivered by the executor, and the executor can only deliver it by running another callback. So:

| threads | caller group | server group | result |
|---:|---|---|---|
| 1 | default | default | **deadlock** |
| 4 | default | default | **deadlock** |
| 1 | default | services | **deadlock** |
| 4 | default | services (reentrant) | returns |
| 4 | services | services (reentrant) | returns |

Row 2 is the one that costs an afternoon. Adding threads is the obvious response to a hang, it is half of the correct response, and on its own it changes nothing at all — the group is occupied by the caller, so the server callback cannot start, and the caller waits forever for something it is itself preventing.

Row 5 is worth noticing too: sharing a *reentrant* group is safe in a way sharing a mutually-exclusive one is not. That asymmetry is why reentrant groups are the usual home for service clients.

**And the option that needs no executor surgery at all:** remove the blocking call. Drop `map_client` from the node and the worst case falls from 77 ms to 32 ms without touching a single group. Still over a 20 ms period — but a reminder that the executor is not the only thing you are allowed to change, and [6.1](01-node-graph.md)'s advice to make it an action is the cheaper fix than any of this.

## E. Practice

<code-exercise src="ros-l3-executors"></code-exercise>

## F. In production

- **Give the control path its own callback group and its own thread**, and keep everything slow out of it. This is the ROS 2 spelling of "isolate the real-time work".
- **Reentrant group for service clients**, so a response can be delivered while a callback waits.
- **Prefer not to wait at all.** An async call with a result callback needs no group surgery and cannot deadlock.
- **Measure the worst case, not the average.** A callback's duration histogram is more useful than its mean, and a per-callback deadline counter more useful than either.
- **Keep callbacks short and boring.** Every long callback is head-of-line blocking for everything sharing its group.
- **Composable nodes share an executor.** Two well-behaved nodes in one container can starve each other, and neither one's code changed.

## G. Experiment

Take a node with several callbacks and log the start time of each against its expected time, for ten minutes. Plot the delay distribution per callback. Then move one callback into its own group, switch to a multi-threaded executor, and do it again. The interesting part is which *other* callbacks improved — the ones that were queued behind the one you moved — because that tells you what the grouping was actually costing.

## H. Failure modes

- **Sizing an executor by utilization.** 87% utilized and four times over the deadline.
- **Switching to a multi-threaded executor and stopping there.** More threads, same group, same behaviour.
- **A synchronous service call from a callback.** Deadlock on one thread; deadlock on four if the groups are shared.
- **One long callback among short ones.** It sets everyone else's worst case.
- **Reentrant groups everywhere.** Now your callbacks genuinely are concurrent and your shared state genuinely does need locking, which is a different problem you did not have before.
- **Assuming node boundaries are isolation boundaries.** In a composable container they are not.

## I. Questions

<quiz-bank src="ros-l3-quiz"></quiz-bank>

## J. References

- ROS 2 documentation on executors and callback groups, and the `rclcpp` executor design article — the second explains *why* the defaults are what they are.
- The `MultiThreadedExecutor` API docs for `rclpy` and `rclcpp`, read specifically for the default group behaviour.
- Lesson [13.2](../13-systems-perf/02-real-time.md) — the same mean-versus-maximum argument without the middleware.
- Liu & Layland (1973) on rate-monotonic scheduling, for what a principled answer to "which callback should preempt which" looks like.

## K. Graded work & portfolio extension

**Graded:** the exercise above.

**Portfolio:** write down your capstone's callbacks with their rates and measured durations, compute the worst-case delay for the control path, and propose a grouping. Then state which of the two changes — the group or the threads — you would make first if you could only make one, and why the answer is neither.
