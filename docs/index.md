# Robotics for AI Engineers

I'm a data and ML engineer teaching myself robotics, and these are the notes I wish I'd been able to read when I started.

The material I found assumed either much less than I knew — long preambles on Python and linear algebra — or much more, jumping straight to screw theory and Lie groups. Very little was written for someone who is comfortable with Bayesian inference and production systems but has genuinely never had to think about which frame a coordinate is expressed in. So I started writing that, and kept going.

**This is a self-study curriculum, published in case you're on the same path.** Free, no signup, and the code runs in this page.

## Who this is for

Data scientists, data engineers, and ML engineers moving toward robotics and embodied AI. I assume you're comfortable with:

- Python, NumPy, and a deep-learning framework
- Supervised learning and model evaluation
- Data pipelines, Docker, CI/CD

I assume you know **nothing** about coordinate frames, kinematics, feedback control, state estimation, or robotics simulation. That's the gap this is trying to close.

## Why it's built this way

Teaching yourself something has one dominant failure mode: you read an explanation, it makes sense, and you walk away believing you've learned it. Nearly every structural decision here is a defense against that.

1. **Your ML knowledge is the on-ramp.** Every concept arrives attached to something you already understand — Kalman filters as recursive Bayesian inference, costmaps as reward shaping, RRT as the same argument for random over grid search you already accept for hyperparameters.
2. **You write the code, in the page.** Real CPython via Pyodide, with hidden tests. Reading an implementation and writing one turn out to be very different experiences.
3. **The autograders randomize.** A solution tuned to one scenario fails the next — I built them that way after repeatedly catching myself pattern-matching instead of understanding.
4. **Everything converges on one robot.** Each module contributes a real component to an autonomous navigation stack that is *scored*, across many randomized worlds, against a published rubric. "It worked when I ran it" stopped being an acceptable result, and that changed what I learned.

## The ML → robotics bridge

| You already know… | The robotics counterpart |
|---|---|
| Hidden-state models | Robot state estimation |
| Bayesian inference | Kalman and particle filters |
| Data pipelines | Sensor-processing pipelines |
| Feature engineering | Geometric and visual representations |
| Model serving | On-robot inference |
| Distributed systems | ROS 2 nodes, topics, and services |
| Experiment tracking | Simulation experiments |
| Offline evaluation | Closed-loop evaluation |
| Reinforcement learning | Robot policy learning |
| Data drift | Environment and sensor-domain shift |

## The path

```mermaid
graph TD
    A[Python simulation] --> B[2D mobile robot]
    B --> C[State estimation]
    C --> D[Mapping & planning]
    D --> E[ROS 2 integration]
    E --> F[Camera & LiDAR perception]
    F --> G[Manipulation]
    G --> H[Robot learning]
    H --> I[Integrated autonomy project]
```

## Start here

- New to robotics entirely? Begin with [Module 0: From ML to Robotics](modules/00-transition/index.md).
- Want to see where it ends up first? The [capstone](modules/capstone/index.md) and the [engineering log](capstone-log.md) are the most concrete pages here.
- Comfortable already? Take the [curriculum map](curriculum.md) and pick a track.

## What exists today

All four courses are complete. Every one of the fourteen modules has lessons, in-browser exercises, a question bank, and a diagnostic lab where you're handed working-*looking* code with a real bug. Nine of them add an autograded mini-project; the other five are graded by their lab or by the capstone they feed.

- **82 lessons** across fourteen modules: geometry, control, estimation, mapping & SLAM, planning, ROS 2, perception, manipulation, robot learning, evaluation, deployment, data infrastructure, and systems performance
- **117 coding exercises** and **84 question banks** (546 questions), every reference solution executed against its own tests in CI
- **14 diagnostic labs** — each one a working-looking system with a real defect, and a debrief on what the defect was evidence of
- **9 autograded mini-projects** (`python -m grader`, randomized scenarios each run)
- **Three capstones**, one per course from II onward: an [autonomous 2D navigation stack](modules/capstone/index.md) in five versions, a [perception-to-grasp arm](modules/capstone-3/index.md), and the [infrastructure that decides whether a policy ships](modules/capstone-2/index.md) — plus an [engineering log](capstone-log.md) of the debugging campaigns behind them
- A [Course I exam](course-1-exam.md), a [Course II exam](course-2-exam.md), and a researched [frontier map](frontier.md) of where the field is heading

Everything above is verified by **22 CI gates** on every push — linting, tests, content integrity, a strict docs build, every mini-project's reference solution, and every capstone rubric.

The ROS 2 track (Module 6) is written to run in the browser like everything else, and deliberately does not re-explain the official tutorials' mechanics — it covers why a synchronous service call stalls a control loop, why two nodes with compatible-looking QoS never connect, and where your callbacks actually run. Installing ROS 2 is optional and nothing in the module waits for it.

A loop-closure version of the navigation capstone was investigated and deliberately not shipped: the pose-graph back end is built and tested, and the capstone's single-traverse task never revisits anywhere, so there is no loop to close. [Note 14](capstone-log.md) has the measurement. Nothing else is outstanding.

## Honest caveats

Everything here is **simulation only** — nothing has touched real hardware, and that gap matters. The code is tested, but the teaching is one person's opinion about what makes these ideas click, and my framing of the field is a learner's current understanding rather than expert consensus. The material was written with AI assistance, with every code path executed and verified in CI and every failure documented from real debugging.

If you find something wrong, [please tell me](https://github.com/paulyonghaoli/robotics-for-ai-engineers/issues) — robotics is full of conventions that are easy to state confidently and get backwards, and I'd much rather be corrected than become the source of someone else's bug.

Each lesson carries a status badge: **Draft** → **Technically reviewed** → **Code verified** → **Reproducible**.
