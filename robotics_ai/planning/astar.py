"""A* on occupancy grids.

Grids are boolean arrays, ``True`` = occupied, indexed ``grid[row, col]``
== ``grid[y, x]`` (world y maps to rows). Cells are nodes; motion is
8-connected with diagonal cost sqrt(2); the heuristic is octile distance —
admissible and consistent for this motion model, so the first expansion of
the goal is optimal.
"""

from __future__ import annotations

import heapq
import math

import numpy as np
import numpy.typing as npt

BoolArray = npt.NDArray[np.bool_]

SQRT2 = math.sqrt(2.0)
_NEIGHBORS = [
    (-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
    (-1, -1, SQRT2), (-1, 1, SQRT2), (1, -1, SQRT2), (1, 1, SQRT2),
]


def octile(a: tuple[int, int], b: tuple[int, int]) -> float:
    dy, dx = abs(a[0] - b[0]), abs(a[1] - b[1])
    return (dy + dx) + (SQRT2 - 2.0) * min(dy, dx)


def astar_grid(
    grid: BoolArray,
    start: tuple[int, int],
    goal: tuple[int, int],
) -> list[tuple[int, int]] | None:
    """Shortest 8-connected path from start to goal (cells, inclusive).

    Returns None if no path exists or an endpoint is occupied. Diagonal
    moves through a blocked orthogonal pair ("corner cutting") are
    forbidden — a diagonal step requires both adjacent cells free.
    """
    rows, cols = grid.shape
    for p in (start, goal):
        if not (0 <= p[0] < rows and 0 <= p[1] < cols):
            raise ValueError(f"cell {p} outside grid {grid.shape}")
    if grid[start] or grid[goal]:
        return None

    g = {start: 0.0}
    parent: dict[tuple[int, int], tuple[int, int]] = {}
    open_heap: list[tuple[float, int, tuple[int, int]]] = []
    tie = 0
    heapq.heappush(open_heap, (octile(start, goal), tie, start))
    closed: set[tuple[int, int]] = set()

    while open_heap:
        _, _, cur = heapq.heappop(open_heap)
        if cur in closed:
            continue
        if cur == goal:
            path = [cur]
            while cur in parent:
                cur = parent[cur]
                path.append(cur)
            return path[::-1]
        closed.add(cur)
        cy, cx = cur
        for dy, dx, cost in _NEIGHBORS:
            ny, nx = cy + dy, cx + dx
            if not (0 <= ny < rows and 0 <= nx < cols) or grid[ny, nx]:
                continue
            if dy and dx and (grid[cy + dy, cx] or grid[cy, cx + dx]):
                continue  # no corner cutting
            cand = g[cur] + cost
            nxt = (ny, nx)
            if cand < g.get(nxt, math.inf):
                g[nxt] = cand
                parent[nxt] = cur
                tie += 1
                heapq.heappush(open_heap, (cand + octile(nxt, goal), tie, nxt))
    return None


def inflate_grid(grid: BoolArray, radius_cells: int) -> BoolArray:
    """Dilate obstacles by a (Chebyshev) radius — the C-space construction
    from lesson 1.5: plan for a point by fattening the world."""
    if radius_cells <= 0:
        return grid.copy()
    out = grid.copy()
    occ = np.argwhere(grid)
    rows, cols = grid.shape
    for y, x in occ:
        y0, y1 = max(0, y - radius_cells), min(rows, y + radius_cells + 1)
        x0, x1 = max(0, x - radius_cells), min(cols, x + radius_cells + 1)
        out[y0:y1, x0:x1] = True
    return out


def path_length(path: list[tuple[int, int]]) -> float:
    """Total length of a cell path in cell units."""
    if not path or len(path) < 2:
        return 0.0
    p = np.asarray(path, dtype=float)
    seg = np.diff(p, axis=0)
    return float(np.hypot(seg[:, 0], seg[:, 1]).sum())
