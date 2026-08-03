"""Planning mini-project — implement the five pieces below.

    python -m grader

NumPy only (plus `heapq` if you want it). Do not import robotics_ai.
"""

from __future__ import annotations

import numpy as np
from world import (  # noqa: F401
    DIAG,
    GRID_N,
    INFLATE_CELLS,
    NEIGHBORS,
    RESOLUTION,
    ROBOT_RADIUS,
    segment_hits,
)


def inflate(grid: np.ndarray, cells: int) -> np.ndarray:
    """Grow every obstacle by `cells`, so the robot can be planned as a point.

    Return a new boolean array; do not modify `grid`. A cell is occupied in
    the result if any cell within `cells` steps (4-connected growth, applied
    `cells` times) is occupied in the input.

    TODO.
    """
    raise NotImplementedError("student: inflate")


def astar(grid: np.ndarray, start: tuple[int, int], goal: tuple[int, int]):
    """8-connected A*. Return a list of cells from start to goal, or None.

    Costs: 1.0 for an orthogonal step, sqrt(2) for a diagonal one.

    Use the OCTILE heuristic, not Euclidean and not Manhattan:

        h = (dx + dy) + (sqrt(2) - 2) * min(dx, dy)

    Manhattan overestimates on an 8-connected grid — it is inadmissible, and
    an inadmissible heuristic gives you a fast search that returns
    non-optimal paths, which is a much worse failure than a slow one because
    nothing looks broken. Euclidean is admissible but loose, so it expands
    far more nodes than it needs to. Octile is exactly the cost of the
    cheapest unobstructed path, which makes it both admissible and tight.

    Return None when no path exists — not an empty list, and not a partial
    path to the closest reachable cell.

    TODO.
    """
    raise NotImplementedError("student: astar")


def costmap(grid: np.ndarray, decay: float = 3.0) -> np.ndarray:
    """A float cost per cell that falls off with distance from obstacles.

    Occupied cells cost `np.inf`. Free cells cost `exp(-d / decay)`, where d
    is the distance in cells to the nearest occupied cell.

    This is what makes a planner prefer the middle of a corridor to scraping
    along one wall: both routes are collision-free and the same length, so
    only the cost distinguishes them.

    TODO.
    """
    raise NotImplementedError("student: costmap")


def astar_costed(grid: np.ndarray, cost: np.ndarray, start, goal,
                 weight: float = 6.0):
    """A* again, but paying `weight * cost[cell]` to enter each cell.

    Same search, different edge cost: step_cost + weight * cost[next_cell].
    Keep the octile heuristic — it stays admissible because the extra term
    is non-negative.

    TODO.
    """
    raise NotImplementedError("student: astar_costed")


def rrt(grid: np.ndarray, start, goal, iters: int = 4000, step: float = 6.0,
        goal_bias: float = 0.08, seed: int = 0):
    """Sampling-based planner. Return a list of cells, or None.

    Grow a tree from `start`: sample a random cell (with probability
    `goal_bias`, sample the goal instead), find the nearest node already in
    the tree, step `step` cells toward the sample, and keep the new node if
    `segment_hits` says the connecting segment is clear. When a new node is
    within `step` of the goal and the segment to it is clear, connect and
    return the path by walking parents back to the start.

    The goal bias is what makes this finish. With pure uniform sampling the
    tree explores the whole free space and only stumbles onto the goal by
    luck; a modest bias pulls it there without destroying the exploration
    that gets it through the gap in the wall.

    Work in integer cells throughout and return integer cells. Planning in
    continuous coordinates and rounding only at the end is a real trap: a
    rounded segment can clip a corner that the continuous one cleared, so the
    path you hand back is not the path you collision-checked.

    Use `np.random.default_rng(seed)` so results are reproducible.

    TODO.
    """
    raise NotImplementedError("student: rrt")
