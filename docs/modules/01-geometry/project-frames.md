# Mini-project: Frame Transforms (autograded, 100 pts)

**Status:** Code verified · **Prereqs:** lesson 1.1 · **Time:** ~1–2 h

Your first OMSCS-style autograded assignment. You implement four functions; a grader scores them against **randomized** scenarios — hard-coding an answer scores once and fails the next run.

## Setup

The assignment lives in the repository at `projects/frame_transforms_mini/`:

```bash
git clone https://github.com/paulyonghaoli/robotics-for-ai-engineers
cd robotics-for-ai-engineers/projects/frame_transforms_mini
```

Implement the stubs in `student.py`, then grade yourself:

```bash
python -m grader
```

```
Frame Transforms mini-project — seed 483920

  wrap_angle      20/20   ok
  sensor_to_map    0/35   FAIL: points mismatch for robot_pose=(1.2, -3.4, 0.7)... — check composition order and convention
  heading_error   20/20   ok
  chain_poses      0/25   not implemented

  TOTAL: 40/100
```

## Tasks and rubric

| Function | Points | The skill being graded |
|---|---|---|
| `wrap_angle` | 20 | Boundary-correct angle arithmetic — the (−π, π] half-open interval |
| `sensor_to_map` | 35 | Two-stage frame composition applied to a point set (the lesson's core skill) |
| `heading_error` | 20 | Shortest-arc signed error — what every heading controller consumes |
| `chain_poses` | 25 | Dead-reckoning accumulation: increments compose in the **current** frame, not the world frame |

Rules: NumPy only; no `robotics_ai` imports (the library is your answer key *after* you've earned full marks). Reproduce a run with `--seed N`; `--reference` proves the grader against its own reference solution — reading that file is allowed and won't help you, which is rather the point.
