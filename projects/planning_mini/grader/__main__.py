"""Autograder for the planning mini-project.

Usage (from projects/planning_mini/):
    python -m grader [--seed N] [--reference]
"""

from __future__ import annotations

import argparse
import secrets
import sys
import traceback

import numpy as np
from world import (
    INFLATE_CELLS,
    dijkstra_cost,
    make_world,
    path_cost,
    segment_hits,
)

from grader import reference as ref


def _valid_path(grid, path, start, goal):
    assert path is not None, "returned None where a path exists"
    assert tuple(path[0]) == tuple(start), f"path starts at {path[0]}, not {start}"
    assert tuple(path[-1]) == tuple(goal), f"path ends at {path[-1]}, not {goal}"
    a = np.asarray(path)
    assert not grid[a[:, 0], a[:, 1]].any(), "path passes through an obstacle"
    steps = np.abs(np.diff(a, axis=0)).max(axis=1)
    assert np.all(steps <= 1), "path has a discontinuity (steps of more than one cell)"


def _check_inflate(mod, seed):
    g = np.zeros((11, 11), dtype=bool)
    g[5, 5] = True
    out = mod.inflate(g, 1)
    assert out is not g and not g[4, 5], "must not modify the input grid"
    assert out[5, 5] and out[4, 5] and out[6, 5] and out[5, 4] and out[5, 6], \
        "4-connected neighbours must be inflated"
    assert out.sum() == 5, f"one pass should give a plus shape (5 cells), got {out.sum()}"
    out2 = mod.inflate(g, 2)
    assert out2.sum() == 13, f"two passes should give 13 cells, got {out2.sum()}"

    edge = np.zeros((8, 8), dtype=bool)
    edge[0, 0] = True
    e = mod.inflate(edge, 2)
    assert e[0, 2] and e[2, 0], "inflation must work against the array border"


def _check_astar_optimal(mod, seed):
    grid, start, goal = make_world(seed)
    g = mod.inflate(grid, INFLATE_CELLS)
    path = mod.astar(g, start, goal)
    _valid_path(g, path, start, goal)
    got = path_cost(path)
    best = dijkstra_cost(g, start, goal)
    assert got <= best + 1e-6, (
        f"path costs {got:.3f} but the optimal is {best:.3f} — an "
        "inadmissible heuristic (Manhattan on an 8-connected grid) returns "
        "quickly and returns the wrong answer")


def _check_astar_no_path(mod, seed):
    g = np.zeros((30, 30), dtype=bool)
    g[:, 15] = True                      # a wall with no gap at all
    out = mod.astar(g, (5, 5), (5, 25))
    assert out is None, (
        f"must return None when no path exists, got {type(out).__name__} "
        f"of length {len(out) if out is not None else 0}")
    blocked = np.zeros((10, 10), dtype=bool)
    blocked[3, 3] = True
    assert mod.astar(blocked, (3, 3), (5, 5)) is None, "start inside an obstacle -> None"
    assert mod.astar(blocked, (5, 5), (3, 3)) is None, "goal inside an obstacle -> None"
    same = mod.astar(np.zeros((6, 6), dtype=bool), (2, 2), (2, 2))
    assert same is not None and len(same) == 1, "start == goal should give a 1-cell path"


def _check_costmap(mod, seed):
    g = np.zeros((21, 21), dtype=bool)
    g[10, 10] = True
    cm = mod.costmap(g, decay=3.0)
    assert np.isinf(cm[10, 10]), "occupied cells must cost inf"
    assert cm[10, 12] < cm[10, 11], "cost must fall off with distance from obstacles"
    assert cm[10, 15] < cm[10, 12], "…monotonically"
    assert abs(cm[10, 11] - np.exp(-1 / 3.0)) < 1e-6, (
        f"cost at distance 1 should be exp(-1/decay) = {np.exp(-1/3.0):.4f}, "
        f"got {cm[10, 11]:.4f}")
    assert np.all(np.isfinite(cm[~g])), "free cells must be finite"


def _check_costed_prefers_clearance(mod, seed):
    """A corridor twice as wide as the robot: the costed plan should
    hug the middle, the plain one has no reason to."""
    g = np.zeros((41, 41), dtype=bool)
    g[14, :] = True
    g[26, :] = True                      # 11-cell corridor between rows 15..25
    start, goal = (20, 3), (20, 37)
    cm = mod.costmap(g, decay=3.0)
    costed = mod.astar_costed(g, cm, start, goal, weight=6.0)
    _valid_path(g, costed, start, goal)
    rows = np.asarray(costed)[:, 0]
    mean_offset = float(np.abs(rows - 20).mean())
    assert mean_offset < 1.0, (
        f"costed path strays {mean_offset:.2f} cells from the corridor centre "
        "on average — the cost term isn't influencing the search")
    # And it must still be a sane length.
    assert path_cost(costed) < 1.6 * dijkstra_cost(g, start, goal), \
        "costed path is wildly longer than necessary"


def _check_rrt(mod, seed):
    grid, start, goal = make_world(seed)
    g = mod.inflate(grid, INFLATE_CELLS)
    path = mod.rrt(g, start, goal, iters=6000, seed=seed)
    assert path is not None, (
        "no path found in 6000 samples through a world A* solves — check the "
        "goal bias, without which the tree wanders instead of finishing")
    assert tuple(path[0]) == tuple(start), f"path starts at {path[0]}"
    assert tuple(path[-1]) == tuple(goal), f"path ends at {path[-1]}"
    a = np.asarray(path)
    assert not g[a[:, 0], a[:, 1]].any(), "an RRT waypoint is inside an obstacle"
    for p, q in zip(a[:-1], a[1:], strict=True):
        assert not segment_hits(g, p, q), (
            f"the straight segment {(int(p[0]), int(p[1]))}->"
            f"{(int(q[0]), int(q[1]))} crosses an obstacle; collision-check "
            "the segment you actually return, not a continuous one you then "
            "round")


def _check_rrt_deterministic(mod, seed):
    grid, start, goal = make_world(seed)
    g = mod.inflate(grid, INFLATE_CELLS)
    a = mod.rrt(g, start, goal, iters=6000, seed=7)
    b = mod.rrt(g, start, goal, iters=6000, seed=7)
    assert a is not None and b is not None, "both runs should find a path"
    assert [tuple(x) for x in a] == [tuple(x) for x in b], (
        "same seed must give the same tree — use np.random.default_rng(seed) "
        "rather than the global numpy random state")


TASKS = [
    ("inflate", 10, _check_inflate),
    ("A* optimality", 25, _check_astar_optimal),
    ("A* returns None correctly", 10, _check_astar_no_path),
    ("costmap", 10, _check_costmap),
    ("costed A* prefers clearance", 20, _check_costed_prefers_clearance),
    ("RRT finds a path", 20, _check_rrt),
    ("RRT is reproducible", 5, _check_rrt_deterministic),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--reference", action="store_true")
    args = ap.parse_args()

    seed = args.seed if args.seed is not None else secrets.randbelow(10**6)
    if args.reference:
        mod = ref
    else:
        try:
            import student as mod  # noqa: PLC0415
        except ImportError:
            print("Could not import student.py — run from projects/planning_mini/")
            return 2

    total = earned = 0
    width = max(len(n) for n, _, _ in TASKS)
    print(f"Planning mini-project — seed {seed}\n")
    for name, points, check in TASKS:
        total += points
        try:
            check(mod, seed)
            earned += points
            print(f"  {name:<{width}}  {points:>3}/{points:<3}  ok")
        except NotImplementedError:
            print(f"  {name:<{width}}  {0:>3}/{points:<3}  not implemented")
        except AssertionError as e:
            print(f"  {name:<{width}}  {0:>3}/{points:<3}  FAIL: {e}")
        except Exception:
            tb = traceback.format_exc(limit=2).strip().splitlines()[-1]
            print(f"  {name:<{width}}  {0:>3}/{points:<3}  ERROR: {tb}")

    print(f"\n  TOTAL: {earned}/{total}")
    return 0 if earned == total else 1


if __name__ == "__main__":
    sys.exit(main())
