# Module 4 mini-project — Mapping & SLAM

Build the front end of a SLAM system: turn scans into a map, and turn two
scans into the motion between them.

```bash
cd projects/mapping_mini
python -m grader
```

100 points across seven checks, random seed each run unless you pass `--seed N`.

## What you implement

All in [`student.py`](student.py):

| | Points | |
|---|---:|---|
| `bresenham` | 15 | All eight octants, both endpoints, 8-connected |
| `occupied_mask` | 5 | Log-odds → probability before thresholding |
| `integrate_scan` | 35 | Ray-trace free space, mark hits — and don't invent obstacles |
| `kabsch` | 15 | Least-squares rigid fit, with the reflection guard |
| `icp` | 30 | Nearest-neighbour alignment with outlier rejection |

## The 20 points that matter most

`integrate_scan` is checked against an **empty room**. A lidar beam that hits
nothing returns exactly `MAX_RANGE`, and that is a *non-detection* — not a
measurement of an obstacle at 5 m. Record it as a hit and you paint a phantom
ring of obstacles at 5 m around every pose the robot ever occupied.

Because ranges are noisy, an equality test against `MAX_RANGE` is not enough:
a genuine miss can read fractionally under the cutoff. The margin needs to be
a few sigma. This is the single bug that cost the most time in the capstone
([engineering log](../../docs/capstone-log.md), bug 1), and it is worth
meeting here first.

## Notes on ICP

ICP is a **local** optimizer. The grader tests it twice: once from a cold
start with a small displacement, and once with a larger displacement seeded
from a simulated odometry prior — which is how every real scan matcher is
run. From a cold start, a displacement comparable to the spacing between scan
points can lock onto the wrong nearest neighbours and settle into a local
minimum that no amount of iterating escapes.

The outlier check contaminates the source with 23% points that have no
counterpart at all. Two scans from different poses genuinely see different
parts of the world, so this is not an adversarial case — it is the normal
one, and untrimmed correspondences drag the fit toward the average of two
unrelated geometries.
