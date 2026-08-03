# Module 5 mini-project — Planning

Global planning on a grid: inflation, A*, costmaps, and a sampling planner.

```bash
cd projects/planning_mini
python -m grader
```

100 points across seven checks, random seed each run unless you pass `--seed N`.

## What you implement

All in [`student.py`](student.py):

| | Points | |
|---|---:|---|
| `inflate` | 10 | Grow obstacles by the robot radius |
| `astar` | 35 | Octile heuristic, 8-connected, `None` when unreachable |
| `costmap` | 10 | Distance-decayed cost around obstacles |
| `astar_costed` | 20 | Same search, cost-aware edges |
| `rrt` | 25 | Sampling planner with goal bias |

## Why the heuristic is worth 25 points

A* is graded against a Dijkstra oracle on the same grid — your path must cost
no more than the true optimum. Manhattan distance on an 8-connected grid
**overestimates**, which makes it inadmissible: the search still terminates,
still returns a path, still looks entirely healthy, and quietly returns a
suboptimal route. A slow planner announces itself. A silently suboptimal one
does not, and that is the failure worth learning to avoid.

Octile — `(dx + dy) + (sqrt(2) - 2)·min(dx, dy)` — is exactly the cost of the
cheapest unobstructed path, so it is both admissible and tight.

## The RRT trap

Plan in integer cells and return integer cells. It is tempting to grow the
tree in continuous coordinates and round at the end, and it passes almost
every test — until a rounded segment clips a corner that the continuous
segment cleared. The path you hand back is then not the path you
collision-checked. Two of ten seeds caught exactly this while the reference
solution was being written.

## Portfolio extension

Plot A*'s expanded-node set under Euclidean, octile, and Manhattan heuristics
on the same world, with the resulting path cost annotated. The Manhattan panel
is the interesting one: fewest nodes expanded, and a path that is not optimal.
