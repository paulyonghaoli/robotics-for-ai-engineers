# Mini-project: Mapping & SLAM (autograded, 100 pts)

**Status:** Code verified · **Prereqs:** lessons 4.1–4.2 · **Time:** ~4 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

You build the front end of a SLAM system — occupancy mapping and scan matching — graded against randomized worlds. The seed changes every run.

## Setup

```bash
cd robotics-for-ai-engineers/projects/mapping_mini
python -m grader
```

Implement the stubs in `student.py`. `world.py` is given: a small world with solid obstacles, a ray-casting lidar, and grid helpers.

## The marks

| Check | Points |
|---|---:|
| Bresenham, all octants | 15 |
| `occupied_mask` | 5 |
| No phantom max-range ring | 20 |
| Map accuracy vs ground truth | 15 |
| Kabsch (no reflections) | 15 |
| ICP convergence | 15 |
| ICP outlier rejection | 15 |

## The phantom ring

The heaviest single check runs your mapper in an **empty room** and looks for occupied cells on a ring at 5 m. A beam that returns `MAX_RANGE` hit nothing; recording its endpoint as an obstacle paints a ring of imaginary walls around every pose the robot visits, and the map then plans around obstacles that were never there.

The trap is that an equality test looks correct. Ranges are noisy, so a genuine miss can read fractionally *under* the cutoff and pass straight through as a hit at 5 m. The margin has to be a few sigma. This is [lesson 4.1's](01-occupancy-grids.md) phantom-ring failure, and the same bug in localization clothing was the most expensive one in the [capstone engineering log](../../capstone-log.md).

## Two guards worth understanding

**Kabsch can return a reflection.** The SVD gives you the optimal *orthogonal* matrix, and orthogonal includes mirrors. Without the `det(R) < 0` correction the fit silently flips the scan whenever the geometry is close to degenerate — and a mirrored scan match produces a pose estimate that is confidently, unrecoverably wrong.

**ICP has a basin.** It is a local optimizer over nearest-neighbour correspondences, so a displacement comparable to the spacing between scan points can lock onto the wrong partners and settle somewhere no amount of iterating escapes. The grader tests both regimes: a small cold-start displacement, and a larger one seeded from an odometry prior. Real scan matchers are always seeded — [4.2](02-scan-matching.md) explains why that is a design decision rather than a crutch.

## Portfolio extension

Sweep the displacement magnitude against the fraction of unmatched points and plot ICP's convergence basin — the region where it recovers the true transform versus where it settles into a local minimum. Overlay the point spacing of your scans. The resulting figure explains, in one image, why every production scan matcher takes an odometry prior.
