# 0.3 Robotics roles: a field guide for ML engineers

**Status:** Technically reviewed · **Prereqs:** none · **Time:** ~1 h

---

## A. Why this matters

"Robotics engineer" is as vague as "data person." Teams hire for four distinct roles with different skill centers of gravity — knowing which one you're aiming at determines which modules deserve your depth versus your awareness, and which of your existing skills to lead with.

## B. The four roles

**Perception engineer** — turns sensor data into world understanding. Skill center: computer vision, 3D geometry, deep learning, C++/CUDA for the inference path. *Your leverage:* CV/DL experience transfers nearly whole; the delta is 3D geometry (Module 1), sensors, and real-time constraints. Deep path: Modules 1, 7, plus 10.

**Autonomy / motion-planning engineer** — turns understanding into decisions and trajectories. Skill center: search and optimization, control theory, C-space reasoning, behavior architecture. *Your leverage:* optimization background; the delta is the classical stack (Modules 3–5) and its failure modes. Deep path: Modules 1–6.

**Robot-learning engineer** — replaces hand-engineered components with learned ones: imitation, RL, VLA models. Skill center: everything an MLE knows, plus simulation, sim-to-real, and the classical baselines being replaced. *Your leverage:* highest — this is the ML-est role; the delta is embodiment fundamentals and simulation fluency. Deep path: Modules 1–3, 9, with 5 as baseline literacy. The catch: teams expect you to *know the classical stack you're claiming to beat.*

**Robotics platform engineer** — builds the infrastructure: middleware, data pipelines, simulation farms, fleet ops, CI for robots. Skill center: distributed systems, DevOps, data engineering — at robot-scale constraints. *Your leverage:* for DE/platform people, immediate; the delta is ROS 2 internals, real-time Linux, and hardware interfaces. Deep path: Modules 6, 10, with 1–5 as literacy.

## C. Honest market notes

Perception and platform roles are the most numerous; robot learning is the fastest-growing and most competitive (everyone with your résumé wants it); autonomy is the most classical-heavy and slowest to enter from ML. A common and effective route: enter through perception or platform on the strength of existing skills, migrate toward learning-heavy work once embodied credibility is established — the portfolio this curriculum builds is designed to support exactly that first step.

## D. Questions

<quiz-bank src="transition-l3-roles"></quiz-bank>
