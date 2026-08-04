# 6.2 QoS: the settings that silently drop your data

**Status:** Code verified · **Prereqs:** lesson 6.1 · **Time:** ~2 h · **Verified:** 2026-08-03, Python 3.13

---

## A. Why this matters

Your node starts. It logs "subscribed to /scan". `ros2 topic list` shows the topic, `ros2 topic hz` shows 10 Hz, the publisher is publishing, the subscriber is subscribed, and the callback never fires. Not once, not slowly — never.

There is no error. There is no warning. Both nodes report healthy, and they will do so indefinitely.

This is a QoS mismatch, and it is the single most disorienting failure a ROS 2 newcomer meets, because every diagnostic you would naturally reach for says everything is fine. The rules that produce it are simple and worth knowing exactly.

## B. The contract

**A publisher OFFERS a level of service; a subscriber REQUESTS one. The connection is made only if the offer is at least as strong as the request.** Nothing is negotiated down, and nothing is reported when it fails.

| policy | levels, weakest first | over-delivery allowed? |
|---|---|---|
| **reliability** | `best_effort` → `reliable` | yes |
| **durability** | `volatile` → `transient_local` | yes |
| **deadline** | a promised maximum period | a *shorter* promise is stronger |

The asymmetry is the whole thing. A `reliable` publisher serves a `best_effort` subscriber happily — it is over-delivering. A `best_effort` publisher cannot serve a `reliable` subscriber, because it is being asked to promise something it did not offer.

Three failures from the exercise, all silent:

```
lidar_driver  -> slam_node     reliability
lidar_driver  -> rviz          connected
map_server    -> logger        connected
controller    -> base_driver   deadline

orphaned subscribers: ['base_driver', 'slam_node']
```

1. **reliability.** The lidar driver publishes `best_effort`, as sensor drivers do. The SLAM node asks for `reliable`, as a careful engineer would. They never connect.
2. **durability.** A `volatile` publisher cannot satisfy a `transient_local` request — this is the one that bites a node started *after* the map was published. `transient_local` is what makes a map or a static transform still available an hour later; without it there is nothing to receive, because the message is long gone.
3. **deadline.** The controller offers to publish every 25 ms and the base driver requires every 20 ms. A promise of 25 does not satisfy a requirement of 20, so the robot has no velocity commands at all — from two settings that each look conservative and correct.

**The default profiles are the reason this is common.** Sensor data conventionally uses `best_effort` with a shallow queue; the default profile for everything else is `reliable`. So the moment you write a node that subscribes to a sensor topic without thinking about QoS, you have written failure 1.

## C. Depth buys latency, not completeness

The second half of QoS is `history` and `depth`, and the intuition most people bring to it is wrong.

A 30 Hz camera into a detector that takes 60 ms per frame. The detector can handle 16.7 frames per second and 30 arrive:

| depth | processed | dropped | age of the frame being processed |
|---:|---:|---:|---:|
| 1 | 16.7 Hz | 13.3/s | 33 ms |
| 5 | 16.7 Hz | 13.3/s | 167 ms |
| 10 | 16.7 Hz | 13.3/s | 333 ms |
| 30 | 16.7 Hz | 13.3/s | **1000 ms** |

**Every row drops the same number of messages.** A deeper queue does not let a slow subscriber process more; the arithmetic of "30 arrive, 16.7 can be handled" does not care what the queue looks like. What the depth changes is *which* messages get dropped and how stale the survivors are — at depth 30 the detector is working on second-old frames, and a one-second-old detection on a moving robot is not a detection.

So for a stream you cannot keep up with, **the right depth is 1**: process the newest thing available and discard the backlog, because the backlog is not useful work, it is old work. Depth exists for the opposite case — a bursty producer and a subscriber that *can* keep up on average, where the queue absorbs the burst instead of losing it.

## D. From ML to robotics

- **You have met this contract before**, as consumer groups, at-least-once versus at-most-once, and retention windows. `transient_local` is a compacted topic with retention 1; `best_effort` is fire-and-forget; the deadline policy is a liveness SLA.
- **What is new is that it fails silently and by default.** Kafka tells you when a consumer cannot connect. DDS makes it a matching problem, and an unmatched endpoint is not an error condition — it is an endpoint waiting for a peer that may yet arrive.
- **Backpressure is not available.** In a data pipeline a slow consumer slows the producer. A lidar does not slow down, so the only question is which messages you lose, which is what `depth` decides.
- **The staleness table is the same argument as batch-1 inference** in [13.1](../13-systems-perf/01-performance-model.md): throughput and latency are different quantities and a robot is scored on the second.

## E. Practice

<code-exercise src="ros-l2-qos"></code-exercise>

## F. In production

- **Match the sensor's profile when subscribing to a sensor.** `rclpy.qos.qos_profile_sensor_data` exists for this; using it is the fix for failure 1.
- **`transient_local` for anything latched** — maps, static transforms, robot descriptions, configuration. If a node that starts late needs it, it is latched data.
- **Depth 1 for streams you process slower than they arrive**, deeper only for bursty producers you can keep up with on average.
- **Check for the silent case explicitly.** `ros2 topic info /topic --verbose` prints the QoS of every endpoint, and comparing them is faster than any amount of staring at logs. Note that `ros2 topic echo` uses its own defaults and can succeed where your node fails, which makes it a misleading first diagnostic.
- **Set QoS from parameters, not literals**, so a mismatch is a config change rather than a rebuild.
- **Be careful with deadline and liveliness.** They are genuinely useful and they add a way for a working system to stop connecting; if you set them, test the mismatch case deliberately.

## G. Experiment

Take any two nodes you have and deliberately break each policy in turn: publish `best_effort` to a `reliable` subscriber, publish `volatile` to a `transient_local` one, offer a longer deadline than is requested. Note what each one looks like from the outside — which diagnostics still report success, and what `ros2 topic info --verbose` shows. The goal is to recognize the signature in ten seconds the next time, rather than the hour it costs the first time.

## H. Failure modes

- **Default QoS on a sensor topic.** The most common instance of the most common failure.
- **`volatile` for latched data.** Works whenever the subscriber happens to start first, which is every time you test it by hand.
- **Deep queues to "avoid dropping data."** You drop exactly as much and process it later, which is worse.
- **Trusting `ros2 topic echo`.** Different defaults, different result, wrong conclusion.
- **Setting a deadline without testing the mismatch.** A policy that only fails when the two sides disagree needs a test where they disagree.
- **Assuming an unmatched endpoint is an error.** It is a normal state, indistinguishable from "the publisher has not started yet", which is why nothing reports it.

## I. Questions

<quiz-bank src="ros-l2-quiz"></quiz-bank>

## J. References

- ROS 2 documentation, *About Quality of Service settings* — the authoritative compatibility matrix.
- The DDS specification's Requested/Offered (RxO) semantics, which is where the asymmetry comes from and why it is not a ROS invention.
- `rclpy.qos` / `rclcpp::QoS` predefined profiles — `sensor_data`, `parameters`, `services_default`. Reading their definitions is ten minutes well spent.
- `ros2 topic info --verbose` and `rqt_graph` — the two tools that make the silent case visible.

## K. Graded work & portfolio extension

**Graded:** the exercise above.

**Portfolio:** annotate the node graph from [6.1](01-node-graph.md) with the QoS profile every edge needs, and justify each `transient_local` and each depth. Then add the one-paragraph answer to "what happens if a node on this graph starts an hour late?" — a graph that survives that question is a graph that has actually been designed.
