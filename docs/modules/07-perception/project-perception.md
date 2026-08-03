# Mini-project: Perception geometry (autograded, 100 pts)

**Status:** Code verified · **Prereqs:** lessons 7.1–7.2 · **Time:** ~3 h · **Verified:** 2026-08-03, Python 3.13, NumPy ≥ 1.26

The camera geometry that sits under every perception stack — projection, distortion, triangulation, and back-projection to a point cloud. No model is trained, because the parts of a perception stack that break in the field are almost never the weights.

## Setup

```bash
cd robotics-for-ai-engineers/projects/perception_mini
python -m grader
```

Implement the stubs in `student.py`. `optics.py` is given: intrinsics, distortion coefficients, a stereo baseline, and synthetic scene generators.

## The marks

| Check | Points |
|---|---:|
| `project`, including points behind the camera | 15 |
| `unproject` and the ray round trip | 15 |
| Distortion round trip | 20 |
| Stereo triangulation | 20 |
| Depth error model | 10 |
| Depth image → point cloud | 20 |

## Three checks that are really about honesty

**Points behind the camera must be `NaN`.** The pinhole division does not complain about a negative Z — it returns a pixel, on the image, that looks entirely reasonable. An object behind you is silently reported in front of you. This is a one-line guard that almost nobody writes until it has cost them a day.

**Disparity below threshold must be `NaN`.** As disparity approaches zero the depth diverges, so a matcher emitting 0.01 px of disparity reports several kilometres with total confidence. Returning a number there is worse than returning nothing, because everything downstream assumes a number means a measurement.

**Zero-depth pixels must be dropped.** A depth sensor writes 0 where it failed to measure. Back-project that and you get a point at the camera origin — and a cloud with a dense blob of phantom points sitting exactly where the robot is. The grader counts your returned points against the number of valid pixels, so silently keeping them fails.

All three are the same discipline: **distinguish "I measured nothing" from "I measured zero."** It is [lesson 4.1's](../04-mapping/01-occupancy-grids.md) max-range problem in three new costumes, and it is the single most repeated bug class in this curriculum's engineering log.

## The one performance check

`depth_to_cloud` is timed on a 640×480 frame and must finish well inside a frame period. A Python loop over 307,200 pixels will not, which is the point — perception code lives in the inner loop and the vectorized form is not an optimization, it is the requirement.

## Portfolio extension

Build the calibration-sensitivity figure: perturb `fx`, `cx` and `k1` each by a realistic calibration residual, and plot the resulting world-space error against range and against image position. The three surfaces look completely different — a focal error is a scale error, a principal-point error is a bearing bias, a distortion error is an edge effect — and having them side by side answers "how good does my calibration need to be?" with numbers rather than a shrug.
