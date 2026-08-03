# Module 7 mini-project — Perception geometry

The camera geometry under every perception stack. Nothing here trains a model.

```bash
cd projects/perception_mini
python -m grader
```

100 points across six checks, random seed each run unless you pass `--seed N`.

## What you implement

All in [`student.py`](student.py):

| | Points | |
|---|---:|---|
| `project` | 15 | Pinhole projection; `NaN` behind the camera |
| `unproject` | 15 | Unit rays, and the round trip that proves depth is gone |
| `distort` / `undistort` | 20 | Radial model and its iterative inverse |
| `triangulate` | 20 | Stereo depth; `NaN` below minimum disparity |
| `depth_sigma` | 10 | The Z² error model |
| `depth_to_cloud` | 20 | Back-projection, vectorized, dropouts removed |

## The theme

Three of the six checks are about the same thing: **"I measured nothing" is not
"I measured zero."**

- A point behind the camera divides by a negative Z and produces a plausible
  pixel *in front of you*.
- Disparity near zero produces a depth of kilometres, reported confidently.
- A depth sensor writes 0 where it failed, and back-projecting that puts a
  cloud of phantom points exactly at the robot.

Each is a one-line guard, and each has cost somebody a day. The same bug class
runs through the [capstone engineering log](../../docs/capstone-log.md) — it is
what note 1 is about, at a different layer of the stack.

## `optics.py`

Given, not modified: intrinsics `K`, distortion coefficients, the stereo
baseline, `look_at` for extrinsics, and synthetic scene generators for the
stereo pair and the depth image.
