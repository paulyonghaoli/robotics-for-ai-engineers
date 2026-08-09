# 0.3 Robotics roles: a field guide for ML engineers

**Status:** Technically reviewed · **Prereqs:** none · **Time:** ~1 h

---

## A. Why this matters

"Robotics engineer" is about as informative a job title as "data person". It
covers at least four distinct roles with different skill centres of gravity,
different daily work, different interview loops, and — this is the part worth
your attention — very different distances from where you are standing now.

Knowing which one you are aiming at changes three practical things:

1. **Which modules of this curriculum deserve depth and which deserve
   awareness.** Nobody has time to go deep on all fourteen. The map below
   tells you which four or five matter for your target.
2. **Which of your existing skills to lead with.** The same résumé reads as
   strong or irrelevant depending on which of these roles is reading it.
3. **What you will be expected to know that you currently don't.** Each role
   has a specific, nameable gap for someone with an ML background. Knowing the
   gap is most of closing it.

This lesson is opinionated and it is about the job market, so treat it as
informed observation rather than fact. The technical content of the curriculum
does not depend on agreeing with it.

## B. The four roles

### Perception engineer

**What the job is.** Turn raw sensor data into statements about the world:
what objects are present, where they are in three dimensions, how they are
moving, which pixels belong to the drivable surface. You own the block that
consumes cameras and LiDAR and emits tracked objects.

**Skill centre.** Computer vision, 3D geometry, deep learning, and — this one
surprises people — a great deal of C++ and often CUDA, because the inference
path has a latency budget and Python usually cannot meet it.

**What transfers from ML.** More than for any other role except robot
learning. If you have trained detectors or segmentation models, that is the
core of the job. Your instincts about data quality, class imbalance,
augmentation and evaluation all carry over intact.

**The gap.** Three things. **3D geometry** (Module 1) — projecting between
image coordinates, camera frames and world frames, which most 2D vision work
never requires. **Sensors as physical devices** — what LiDAR actually returns,
why depth cameras fail on glass, what calibration means and how it drifts.
And **real-time constraints**: a model that is 2% better and 40 ms slower is
usually a worse model here.

**Deep path:** Modules 1, 7, plus 10 for evaluation.

### Autonomy / motion-planning engineer

**What the job is.** Turn understanding into decisions and trajectories.
Given a map, a pose and a goal, produce a path that is feasible, safe and
efficient, then keep producing it as the world changes.

**Skill centre.** Search and optimisation, control theory, configuration-space
reasoning, and behaviour architectures — the state machines and behaviour
trees that decide what the robot should be trying to do at all.

**What transfers.** Your optimisation background, more than you'd expect. A*
is Dijkstra with a heuristic; trajectory optimisation is constrained
optimisation with a physical interpretation; MPC is optimisation in a loop.

**The gap.** The classical stack itself (Modules 3–5) and, more importantly,
its **failure modes**. Planners fail in specific, well-catalogued ways — the
robot freezes in a doorway, oscillates between two equally good routes,
plans through a gap it cannot physically fit. Knowing the algorithms is table
stakes; knowing how they break is the job.

**Deep path:** Modules 1–6.

### Robot-learning engineer

**What the job is.** Replace hand-engineered components with learned ones:
imitation learning, reinforcement learning, and the vision-language-action
models currently reshaping the field.

**Skill centre.** Everything an ML engineer already knows, plus simulation,
sim-to-real transfer, and — critically — the classical baselines being
replaced.

**What transfers.** The most of any role. This is the ML-est job in robotics.

**The gap.** Embodiment fundamentals and simulation fluency, plus one thing
that catches people out: **teams expect you to know the classical stack you
are claiming to beat.** "We replaced the planner with a policy" invites the
question "compared against which planner, tuned how well, and measured how?"
An answer that reveals you have never tuned a planner is a bad interview
moment. This is the single most common way strong ML candidates fail robot
learning interviews.

**Deep path:** Modules 1–3 and 9, with Module 5 as baseline literacy.

### Robotics platform engineer

**What the job is.** Build the infrastructure everyone else stands on:
middleware, data pipelines, log and bag infrastructure, simulation farms,
fleet operations, CI that can test a robot.

**Skill centre.** Distributed systems, DevOps and data engineering, at robot
constraints — which mostly means bounded latency, enormous binary payloads,
and machines that are sometimes offline in a basement.

**What transfers.** For anyone with a data-engineering or platform background,
this is nearly immediate. The concepts are ones you have; the constraints are
new.

**The gap.** ROS 2 internals, real-time Linux, hardware interfaces, and the
specific shape of robot data — time-series from many sensors at different
rates, aligned by timestamp, where the alignment itself is a source of bugs.

**Deep path:** Modules 6, 10, 12 and 13, with 1–5 as literacy.

## C. A summary table

| | Perception | Autonomy | Robot learning | Platform |
|---|---|---|---|---|
| Distance from ML background | short | long | shortest | short (if DE/platform) |
| Main gap | 3D geometry, sensors, latency | classical stack + its failure modes | embodiment, sim, classical baselines | ROS 2 internals, real-time, hardware |
| Primary language | C++ and Python | C++ | Python | Python, C++, Go |
| Deep modules | 1, 7, 10 | 1–6 | 1–3, 9 | 6, 10, 12, 13 |
| Market size | large | medium | small, growing fast | large |
| Competition from ML people | moderate | low | **very high** | low |

## D. Honest market notes

Read this section as opinion supported by job postings, not as data.

**Perception and platform roles are the most numerous.** They are also the
easiest to enter from an ML or data background, because the overlap is large
and demonstrable.

**Robot learning is the fastest-growing and by far the most competitive.**
Everyone with your résumé wants that job. The candidate pool is deep in ML and
shallow in robotics, which means the differentiator is almost never another
ML project — it is evidence you understand embodiment and can be trusted near
a real system.

**Autonomy is the most classical-heavy and the slowest to enter** from an ML
starting point, because the required depth is in material your background did
not cover at all.

**Platform roles are systematically underrated by ML people** and are often
the best entry point. The research that shaped this curriculum found data and
evaluation infrastructure to be the least crowded, best-paid area relative to
the barrier to entry — roles that pay senior-engineer money and explicitly do
not require model training. If your background is data engineering, you are
closer to a robotics job than you think.

**A route that works:** enter through perception or platform on the strength
of skills you already have, build embodied credibility on the job, then
migrate toward learning-heavy work from the inside. The portfolio this
curriculum builds is designed to support exactly that first step — not to
make you competitive for a frontier-lab robot-learning role from a standing
start, which would be a dishonest promise.

## E. How to use this lesson

Pick a target role now, provisionally. Not because you are committing, but
because the curriculum is large and a target tells you where to spend depth
versus where to skim. You can change it at any point; the first six modules
are common to all four paths anyway.

Then write down, for your chosen role, the specific gap named above. That
sentence is the honest version of what you are here to fix.

## F. Questions

<quiz-bank src="transition-l3-roles"></quiz-bank>

## G. Annotated references

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Live job postings at three companies in your target area | primary source | introductory | The only current data. Read ten and tabulate the required skills; it will disagree with any blog post, including this one |
| [docs/frontier.md](../../frontier.md) | living doc | intermediate | This project's own research into where the field is moving and which areas are least crowded |
| Any robotics team's engineering blog | blog | introductory | Useful for the texture of daily work, which job postings never convey |

## H. Portfolio extension

Take ten real job postings for your target role, and tabulate every named
technology and skill. Then map each one onto a module of this curriculum, and
mark the ones with no module at all. That gap list is worth more than any
generic advice — including this lesson — because it is current, specific to
your market, and yours.
