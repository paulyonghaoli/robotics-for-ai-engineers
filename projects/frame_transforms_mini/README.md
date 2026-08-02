# Mini-project: Frame Transforms (Module 1) — 100 points

Your first autograded assignment. Implement the functions in [`student.py`](student.py); the grader scores them against randomized test cases, OMSCS-style.

## Tasks

| Function | Points | Description |
|---|---|---|
| `wrap_angle(theta)` | 20 | Wrap scalar angle to (-π, π] — boundary behavior included |
| `sensor_to_map(points, robot_pose, mount_pose)` | 35 | Project an (N,2) array of sensor-frame points into the map frame, given the robot's pose (x, y, θ) in the map and the sensor's static mount pose in the base frame |
| `heading_error(current, target)` | 20 | Signed shortest-arc heading error (target − current), wrapped |
| `chain_poses(deltas)` | 25 | Dead-reckoning: compose a list of relative pose increments (x, y, θ) into the final pose in the world frame, starting from the origin |

Rules: NumPy only. Do not import `robotics_ai` (the point is to implement it yourself — the library is your answer key *after* submitting).

## Grading

```bash
python -m grader              # grade student.py (randomized cases, fresh each run)
python -m grader --seed 7     # reproduce a specific run
python -m grader --reference  # sanity-check the grader against its reference solution
```

The grader prints a per-task breakdown. Scenario parameters are randomized per run — a hard-coded answer scores once and fails the next run, so make the *function* correct.

Run it from this directory (`projects/frame_transforms_mini/`).
