# Module 6 · Robotics Software with ROS 2

**Status:** In progress · **Parallel track — not a prerequisite** · **Pinned distro:** ROS 2 Jazzy

!!! info "This module is optional for Courses I–II"
    Everything through the capstone runs in pure Python; you never need a ROS installation to finish the classical stack. Take this track whenever you want industrial integration skills. Worth knowing from the [frontier research](../../frontier.md): ROS 2 is mandatory at Agility, Boston Dynamics, and Amazon Robotics, and conspicuously absent from frontier VLA-lab job postings — it's a platform/integration credential, not a robot-learning one.

If you know distributed systems, you already understand half of ROS 2: nodes are services, topics are pub/sub, QoS is delivery semantics, bags are event logs. This module maps those concepts explicitly, then covers TF2, URDF, launch files, lifecycle nodes, and testing/observability for robot software.

We reference the [official ROS 2 tutorials](https://docs.ros.org/en/jazzy/Tutorials.html) for mechanics and focus our lessons on *why each concept matters inside a production autonomy architecture*.

## Lessons

1. [The node graph: a robot is a distributed system](01-node-graph.md) — **available**
2. [QoS: the settings that silently drop your data](02-qos.md) — **available**
3. Executors and callback groups: where your callbacks actually run — *planned*
4. tf2: the transform tree as a service — *planned*
5. Launch, parameters, and the configuration surface — *planned*
6. Lab: the node that worked alone — *planned*

## How this module is taught

Every lesson here runs in the browser, like the rest of the curriculum, and none of them require a ROS 2 installation. That is a deliberate choice rather than a limitation: the mechanics — `ros2 topic echo`, building a workspace, writing a package — are covered well by the [official tutorials](https://docs.ros.org/en/jazzy/Tutorials.html) and badly by a second retelling. What those tutorials do *not* cover is why a synchronous service call stalls a control loop, why two nodes with compatible-looking QoS never connect, or where your callbacks actually run. Those are modelled here, in code you can execute and modify.

Install ROS 2 whenever you want the hands-on half. Nothing in this module waits for it.
