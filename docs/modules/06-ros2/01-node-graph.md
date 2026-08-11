# 6.1 The node graph: a robot is a distributed system

**Status:** Code verified · **Prereqs:** lesson 0.2 · **Time:** ~2 h · **Verified:** 2026-08-03, Python 3.13

---

## A. Why this matters

If you have built distributed systems, ROS 2 will feel familiar in a way that is mostly correct and slightly dangerous. Nodes are processes, topics are pub/sub, services are RPC, bags are event logs, and the discovery layer is service discovery. All of that transfers.

What does not transfer is the deadline. A backend that answers in 200 ms instead of 20 ms is a slow page; a control loop that answers in 200 ms instead of 20 ms has stopped steering the robot. The single most common ROS 2 mistake — a synchronous service call in a periodic callback — is a mistake precisely because of that, and it looks like completely ordinary code.

## B. Three ways for nodes to talk

| | shape | caller waits | you use it for |
|---|---|---|---|
| **topic** | pub/sub, many-to-many, no reply | no | sensor streams, commands, state |
| **service** | request/response, one-to-one | **yes, for the whole call** | short queries and settings |
| **action** | goal → feedback → result, cancellable | no (a goal is submitted) | anything long-running |

The choice looks like a matter of taste and is not. It follows from properties you can measure before writing anything:

```
nothing comes back                             -> topic
something comes back, and it is long-running
   or something you would want to cancel       -> action
otherwise                                      -> service
```

**Cancellability is the property that does the work.** A map fetch takes 45 ms — slow, and still a service, because nobody has ever wanted to abort one halfway. `navigate_to` takes four seconds and someone absolutely will want to abort it. Duration alone gets this wrong in both directions.

## C. What the wrong choice costs

From the exercise, on a 50 Hz control loop with a 20 ms period and 4 ms of its own work:

| interaction, as… | caller blocked | control loop |
|---|---:|---|
| `cmd_vel` as a topic | 0 ms | 50 Hz |
| `get_map` as a service, called from the control callback | 45 ms | **misses every period** |
| `navigate_to` as a service | 4000 ms | **0.25 Hz for four seconds** |
| `navigate_to` as an action | 1 ms | 50 Hz |

The third row is the one to hold onto. The robot is not being steered while it waits to be told it has arrived — for four seconds, at speed. And the code that does this is one line, reads naturally, and works perfectly in a test where nothing else is running.

Note what the last row does *not* claim: the navigation still takes four seconds. The action did not make anything faster. It moved the waiting off the thread that had a deadline, which is the entire trick.

Note also the second row's framing. A 45 ms map fetch is not a bug. Calling it from *here* is the bug, and no amount of optimizing the map server fixes a design that cannot tolerate 45 ms.

### The discovery bill, in arithmetic

DDS discovery is peer-to-peer: every participant announces itself and probes
every other, so the wiring work scales as \(N(N-1)/2\) pairs. That is
harmless prose until you put numbers on it. Ten nodes is 45 pairs; forty
nodes — an unremarkable robot once every driver, filter and visualiser is
counted — is **780 pairs**, each exchanging endpoint listings for every topic
it touches; a hundred-node fleet segment sharing one network domain is 4,950.
This quadratic is why a robot that boots cleanly on the bench can take tens
of seconds to "find itself" on a congested WiFi network, why multi-robot
deployments partition `ROS_DOMAIN_ID` rather than sharing one graph, and why
discovery servers (a return to a broker, quietly) exist for large systems.
The graph is flat and brokerless at *data* time precisely by paying a
quadratic bill at *discovery* time — an architectural trade, not a free
lunch.

## D. The other budget: bandwidth

The same exercise adds up what the graph actually carries:

```
total: 225.3 Mbit/s, dominated by camera_raw
everything else on the robot together: 3.7 Mbit/s
```

**One topic is 98% of the bus.** A 640×480 RGB frame at 30 Hz is 221 Mbit/s, and lidar, odometry, commands, diagnostics and the rest sum to under 2% of it. That single fact explains most of ROS 2's transport machinery: compressed `image_transport`, intra-process communication and zero-copy loaned messages exist because serializing that stream between two nodes on the same computer is pure waste.

It also tells you where to look first when the robot's CPU is saturated, and it will not be where the interesting code is.

## E. Practice

<code-exercise src="ros-l1-graph"></code-exercise>

## F. In production

- **Draw the graph before writing nodes.** `rqt_graph` will show you what you built; a whiteboard shows you what you meant.
- **A node should have one reason to exist.** The pressure is always toward one large node because sharing state is easier that way, and the cost arrives later, when you want to run half of it on a different machine or restart one piece.
- **Never call a service synchronously from a callback.** Use an action, or a future with a callback, or a separate callback group — [6.3](03-executors.md) is about why the naive fix deadlocks.
- **Compressed image transport by default**, and intra-process composition for nodes that will always be co-located.
- **Namespace and remap from launch, not in code.** A node with hard-coded topic names can be used once.

## G. Experiment

Take the capstone stack and write down its node graph as if you were going to implement it in ROS 2: which nodes, which topics, which of the interactions are actually services or actions. Then compute its bus bandwidth from the message sizes you already know. The exercise is worth doing on paper because the answer — how few nodes it needs and how much of the bandwidth is one sensor — is a useful surprise before you have built anything.

## H. Failure modes

- **A synchronous service call in a periodic callback.** The default failure of the module.
- **An action where a topic would do**, because actions felt more thorough. Now every command has a goal handle, a result callback, and a state machine.
- **One giant node.** Easier to write, impossible to distribute, and it fails as a unit.
- **Publishing raw images between co-located nodes.** Serializing 221 Mbit/s to hand it to a process on the same machine.
- **Hard-coded topic names.** Works until the second robot.
- **Treating the graph as free.** Every topic is discovery traffic, a queue, and a QoS negotiation that can silently fail — which is [6.2](02-qos.md).

## I. Questions

<quiz-bank src="ros-l1-quiz"></quiz-bank>

## J. References

- The [official ROS 2 tutorials](https://docs.ros.org/en/jazzy/Tutorials.html) for the mechanics — this module deliberately does not re-explain `ros2 topic echo`.
- ROS 2 design docs on topics, services and actions, particularly the discussion of why actions are not just long services.
- `image_transport` and the ROS 2 intra-process communication design notes — the machinery behind section D.
- Lesson [11.1](../11-deployment/01-latency-budgets.md) — the deadline argument these choices are ultimately about.

## K. Graded work & portfolio extension

**Graded:** the exercise above.

**Portfolio:** publish the node graph you drew in section G with the bandwidth annotated on each edge, and one paragraph on which interactions you made actions and why. The reasoning is the artifact — a graph without it is a picture, and the choice between a service and an action is the part that separates someone who has read the tutorials from someone who has debugged a stalled control loop.
