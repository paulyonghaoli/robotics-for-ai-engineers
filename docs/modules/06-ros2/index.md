# Module 6 · Robotics Software with ROS 2

**Status:** Planned · **Parallel track — not a prerequisite** · **Pinned distro:** ROS 2 Jazzy

!!! info "This module is optional for Courses I–II"
    Everything through the capstone runs in pure Python; you never need a ROS installation to finish the classical stack. Take this track whenever you want industrial integration skills. Worth knowing from the [frontier research](../../frontier.md): ROS 2 is mandatory at Agility, Boston Dynamics, and Amazon Robotics, and conspicuously absent from frontier VLA-lab job postings — it's a platform/integration credential, not a robot-learning one.

If you know distributed systems, you already understand half of ROS 2: nodes are services, topics are pub/sub, QoS is delivery semantics, bags are event logs. This module maps those concepts explicitly, then covers TF2, URDF, launch files, lifecycle nodes, and testing/observability for robot software.

We reference the [official ROS 2 tutorials](https://docs.ros.org/en/jazzy/Tutorials.html) for mechanics and focus our lessons on *why each concept matters inside a production autonomy architecture*.

Planned labs: sensor-processing node, action server, TF tree + URDF robot, rosbag debugging exercise, and a multi-node autonomous robot stack.
