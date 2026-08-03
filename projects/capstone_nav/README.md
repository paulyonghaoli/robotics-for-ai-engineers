# Capstone I — Autonomous 2D Mobile Robot

The integrated system everything in Courses I–II builds toward. A
differential-drive robot must reach randomized goals in randomized obstacle
worlds, judged the way real autonomy stacks are judged — by scenario metrics,
not vibes.

**This is an assignment, not a demo.** Start in
[`student_stack.py`](student_stack.py), which carries the contract, the build
order, and the TODOs.

```bash
python -m eval run --episodes 8 --stack student_stack
```

That command is the autograder.

## The contract

A stack is any module exposing `make_stack(sim) -> object with .step(obs) ->
(v, w)`. Observations: noisy pose, 36-ray lidar scan, goal, collision flag.
Ground truth never leaves the simulator — the harness reads it only for
scoring.

## Rubric

| Metric | Threshold |
|---|---|
| Success rate | ≥ 0.85 |
| Collision-free episodes | ≥ 0.85 |
| Mean path ratio (executed / A* optimal) | ≤ 1.6 |
| p95 control-step latency | ≤ 50 ms |

Achievable — five reference stacks pass it, which is what makes the rubric a
claim rather than an aspiration.

## The five versions

Each removes something the previous one was allowed to assume. Build them in
order; every one is a real system on its own.

| | What you may assume | Result |
|---|---|---|
| **v0** | Known map, noisy pose sensor | 20/20 episodes |
| **v1** | Known map, **no pose sensor** — localize from lidar | 20/20, 6–11 cm RMSE |
| **v2** | **No map** — build it online from scans, no `sim.grid` | 20/20 |
| **v3** | No map, plus **six movers that aren't in it** | 18/18, 17/18 collision-free |
| **v4** | **Neither map nor pose** — SLAM | 18/24, 0.39 m drift |

Nothing enforces which version you're building. The rubric cannot tell whether
you read `sim.grid` when you said you didn't — exactly the position you'll be
in professionally, and why the version you *claim* matters more than the number
you report.

### v3's operating envelope (measured, not assumed)

| Movers | Success | Collision-free |
|---:|---|---|
| 0 | 20/20 | 20/20 |
| 6 | 18/18 | 17/18 |
| **10** | **6/6** | **3/6** |

At 10 movers the stack still reaches every goal but stops being collision-free.
Worth stating plainly rather than tuning until the number looks good: these
obstacles are **non-cooperative** — they walk straight through the robot and
never yield, which real people don't. At high density, contact becomes
unavoidable for a robot that is the only one avoiding. The honest claim is
"6 movers, non-cooperative."

Baseline for comparison — the v1 stack in the same 6-mover worlds: **5/6
success, 5/6 collision-free, localization RMSE degrading from 0.13 m to as much
as 3.96 m.**

### v4's envelope

v4 is scored against a separate, looser rubric (`--rubric slam`), because
judging it by a bar that assumes you were handed a map or a pose is a category
error. Its shortfall is arithmetic: 0.39 m of drift against a 0.5 m goal
tolerance parks a quarter of runs just outside it, *believing they arrived*.
Closing that needs loop closure, not tuning — see
[`slam_ablation.py`](slam_ablation.py), which measures why.

## Layout

```
sim.py             the world: dynamics, lidar, collisions, world generation
eval/              the autograder — python -m eval run --stack <name>
student_stack.py   START HERE
solutions/         five reference stacks, v0 through v4
slam_ablation.py   the experiment harness behind v4's design decisions
render.py          turns a real evaluation episode into a GIF
```

## About `solutions/`

They're in the repo on purpose, and reading them is not cheating.

But attempt each version first. The [engineering
log](../../docs/capstone-log.md) documents thirteen real bugs found while
building these — max-range miss leakage, boundary-clip reward, a filter that
stayed 95% confident while drifting 14 m — and none of it lands if you haven't
first watched your own robot do something inexplicable. The value in that
document isn't the fixes; it's the diagnostic moves, and those only mean
something to someone who has been stuck.

Two of the thirteen were the *same bug*, committed three stacks apart, by the
person who had already written the lesson about it. That's the honest argument
for attempting before reading.

## Commands

```bash
python -m eval run --episodes 8 --stack student_stack     # grade your stack
python -m eval run --episodes 8 --stack reference_stack   # the v0 reference
python -m eval run --episodes 8 --stack dynamic_stack --dynamic 6
python -m eval run --episodes 24 --stack slam_stack --rubric slam
python slam_ablation.py odom lf lf+bias                   # v4's ablations
python render.py all                                      # regenerate demos
```
