# 6.6 Lab: the node that worked alone

**Status:** Code verified · **Prereqs:** lessons 6.1–6.5 · **Time:** ~2 h · **Verified:** 2026-08-03, Python 3.13

---

## A. Why this lab exists

Every node in this lab passes its own tests. Run it by itself, publish it a message by hand, and it does exactly what it should.

Then it goes into the system and six of the seven misbehave — with, between them, **not one error message**. That is the property that makes ROS 2 disorienting to people who are good at software: the failures are not in the code, they are in the space between the nodes, and that space does not raise exceptions. It has QoS contracts that do not match, a scheduler you did not choose, a name-resolution pass you did not see, and a clock argument you defaulted.

The seventh node's problem is not a middleware problem at all, and it is in the lab for that reason.

## B. The diagnostic table

| Symptom | Cause | Lesson |
|---|---|---|
| Node stopped responding entirely | **Executor deadlock** — a synchronous call it can never complete | [6.3](03-executors.md) |
| Callback never fires; nothing publishes on the resolved name | **Name mismatch** — namespace or an absolute name | [6.5](05-launch-params.md) |
| Callback never fires; a publisher is right there | **QoS mismatch** — the offer does not satisfy the request | [6.2](02-qos.md) |
| Runs at rate; uses a value nobody configured | **Parameter not applied** — a mis-keyed block | [6.5](05-launch-params.md) |
| Runs at rate; answers are wrong, worse at range | **Stale transform** — `Time(0)` instead of the stamp | [6.4](04-tf2.md) |
| Runs slow; its own work is small | **Head-of-line blocking** — other callbacks in its group | [6.3](03-executors.md) |
| Runs slow; its own work does not fit | **The code is too slow** — not a middleware problem | [13.3](../13-systems-perf/03-hot-path.md) |

## C. The seven

<code-exercise src="ros-l6-diagnose"></code-exercise>

The verdicts:

| | observed | own / blocked / period | diagnosis |
|---|---:|---|---|
| A | 0 / 10 Hz | 3 / 0 / 100 ms | qos-mismatch |
| B | 0 / 50 Hz | 2 / 0 / 20 ms | name-mismatch |
| C | 0 / 50 Hz | 4 / 0 / 20 ms | executor-deadlock |
| D | 12.4 / 50 Hz | 4 / **77** / 20 ms | head-of-line-blocking |
| E | **50 / 50 Hz** | 4 / 0 / 20 ms | **stale-transform** |
| F | **50 / 50 Hz** | 4 / 0 / 20 ms | **parameter-not-applied** |
| G | 40 / 50 Hz | **25** / 0 / 20 ms | callback-too-slow |

Three of these are worth sitting with.

**A and B are identical from inside the node.** The callback never fires; that is all you can see. One observation separates them: *is anything publishing on the name this node actually resolved to?* If yes, it is a QoS mismatch. If no, the node is listening to a topic that does not exist and the publisher is talking to nobody. This is why `ros2 topic info --verbose` **on the resolved name** is the first command to run, and why resolving the name yourself is part of the diagnosis rather than a preliminary to it.

**E and F run perfectly.** Every rate is nominal, nothing is blocked, no callback is late, and E's detections land 65 cm from the obstacle while F drives at a third of the speed somebody configured. No timing probe finds either. A healthy graph is not a correct one, and the entire class of "it works and the numbers are wrong" is invisible to the tools you reach for when something is slow.

**G is not a middleware problem.** Nothing is misconfigured, nothing is blocked, and the callback takes 25 ms in a 20 ms period. The answer is [13.3](../13-systems-perf/03-hot-path.md)'s profile, not a callback group — and reaching for an executor change here would be a week spent on a scheduler that is behaving correctly. Including it is the point: after five lessons of middleware failures the middleware becomes the default suspect, and it is not always guilty.

## D. Debrief

Three habits close out the module.

**1. Resolve the name yourself before anything else.** Namespaces, remappings and the `~`/`/`/relative rules decide what your node is actually connected to, and they run before your code does. Half the failures here — and most of the ones people meet in their first month — are answered by working out the fully qualified name and asking who else is on it.

**2. Log the effective configuration at startup.** Every declared parameter with its value *and its source*, every topic with its resolved name, the QoS profile of each endpoint. Ten lines. It converts incidents A, B and F from silent into obvious, which is a better return than any amount of defensive code.

**3. Separate "is it running" from "is it right".** The middleware's diagnostics answer the first question well and the second not at all. E and F are the reminder: a node can be perfectly scheduled, perfectly connected, and wrong. The checks that catch those are yours to write — a residual, a consistency check, a comparison against a reference — and they are the same argument as [3.6](../03-estimation/06-consistency-lab.md)'s lying filter, arriving from the middleware.

And the thread through Module 6: **ROS 2 does not fail loudly, because most of what it does is matching.** An unmatched endpoint, an unmatched parameter key, an unmatched name — none of these is an error condition. Each is a state the system is entitled to be in, indefinitely, and the only thing that distinguishes it from "the publisher has not started yet" is you.

## E. Graded work & portfolio extension

**Graded:** the seven-node triage closes Module 6, and the probes transfer directly to any ROS system you touch.

**Portfolio:** write the startup-diagnostics snippet from habit 2 — effective parameters with sources, resolved topic names, endpoint QoS — as a small reusable function, and publish it. It is fifty lines, it is the thing every one of these incidents wanted, and it does not exist in any package you can install. That combination is unusual enough to be worth having your name on.
