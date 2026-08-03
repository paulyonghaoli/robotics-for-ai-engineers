# Mini-project: Planning (autograded, 100 pts)

**Status:** Code verified · **Prereqs:** lessons 5.1–5.3 · **Time:** ~4 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

Global planning on a grid — inflation, A*, costmaps, and RRT — graded against randomized worlds with a dividing wall and a single gap. The seed changes every run.

## Setup

```bash
cd robotics-for-ai-engineers/projects/planning_mini
python -m grader
```

Implement the stubs in `student.py`. `world.py` is given, including a Dijkstra oracle the grader uses to check your A* is genuinely optimal.

## The marks

| Check | Points |
|---|---:|
| `inflate` | 10 |
| A* optimality (vs Dijkstra oracle) | 25 |
| A* returns `None` correctly | 10 |
| `costmap` | 10 |
| Costed A* prefers clearance | 20 |
| RRT finds a path | 20 |
| RRT is reproducible | 5 |

## Admissibility is graded, not discussed

Your A* is compared against a Dijkstra oracle on the same grid: the path must cost no more than the true optimum. This is the check that catches Manhattan distance on an 8-connected grid, which **overestimates** and is therefore inadmissible.

The reason that matters is the failure mode. An inadmissible heuristic doesn't crash, doesn't hang, and doesn't return an invalid path — it returns a *suboptimal* one, quickly, and everything downstream looks fine. A planner that is slow tells you it is slow. A planner that is quietly wrong does not, and grid-planning bugs of this kind survive in production for years. [Lesson 5.1](01-astar.md) derives the octile heuristic; here it is enforced.

## Clearance is a cost, not a constraint

Both routes down a corridor are collision-free and the same length, so nothing in a plain A* prefers the middle to scraping along a wall. The costed check puts a robot in an 11-cell corridor and requires the plan to stay within one cell of the centreline on average. That is [lesson 5.2's](02-costmaps.md) argument made concrete: safety margins that are not in the objective do not happen.

## The RRT trap

Plan in integer cells and return integer cells. Growing the tree in continuous coordinates and rounding at the end passes nearly every test, until a rounded segment clips a corner the continuous one cleared — and then the path you return is not the path you collision-checked. This caught the reference solution on two seeds out of ten.

## Portfolio extension

Plot A*'s expanded-node set under Euclidean, octile, and Manhattan heuristics on one world, annotating each with the resulting path cost. The Manhattan panel expands the fewest nodes and returns a path that is not optimal — a single figure that explains why admissibility is a correctness property rather than a performance one.
