"""Shared world for the planning mini-project. Given to you."""

from __future__ import annotations

import heapq

import numpy as np

RESOLUTION = 0.1
GRID_N = 100
WORLD = GRID_N * RESOLUTION
ROBOT_RADIUS = 0.25
INFLATE_CELLS = int(np.ceil(ROBOT_RADIUS / RESOLUTION))

DIAG = float(np.sqrt(2.0))
NEIGHBORS = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
             (-1, -1, DIAG), (-1, 1, DIAG), (1, -1, DIAG), (1, 1, DIAG)]


def make_world(seed: int) -> tuple[np.ndarray, tuple[int, int], tuple[int, int]]:
    """Grid with a solid border, a few boxes, and a wall with one gap."""
    rng = np.random.default_rng(seed)
    grid = np.zeros((GRID_N, GRID_N), dtype=bool)
    grid[0, :] = grid[-1, :] = grid[:, 0] = grid[:, -1] = True

    # A dividing wall with a single passable gap: the interesting case for
    # both A* and RRT, because greedy exploration wants to go straight.
    wall_c = int(rng.integers(42, 58))
    gap_r = int(rng.integers(20, GRID_N - 20))
    grid[:, wall_c:wall_c + 3] = True
    grid[gap_r - 7:gap_r + 7, wall_c:wall_c + 3] = False

    for _ in range(rng.integers(3, 6)):
        h, w = rng.integers(6, 16), rng.integers(6, 16)
        r = int(rng.integers(6, GRID_N - 6 - h))
        c = int(rng.integers(6, wall_c - 6 - w)) if rng.random() < 0.5 else \
            int(rng.integers(wall_c + 6, GRID_N - 6 - w))
        grid[r:r + h, c:c + w] = True

    inflated = _inflate(grid, INFLATE_CELLS)
    start = _free_cell(inflated, rng, 4, wall_c - 4)
    goal = _free_cell(inflated, rng, wall_c + 6, GRID_N - 4)
    return grid, start, goal


def _inflate(grid: np.ndarray, cells: int) -> np.ndarray:
    out = grid.copy()
    for _ in range(cells):
        nxt = out.copy()
        nxt[1:, :] |= out[:-1, :]
        nxt[:-1, :] |= out[1:, :]
        nxt[:, 1:] |= out[:, :-1]
        nxt[:, :-1] |= out[:, 1:]
        out = nxt
    return out


def _free_cell(grid, rng, c_lo, c_hi) -> tuple[int, int]:
    for _ in range(5000):
        r = int(rng.integers(4, GRID_N - 4))
        c = int(rng.integers(c_lo, c_hi))
        if not grid[r, c]:
            return (r, c)
    raise RuntimeError("no free cell")


def dijkstra_cost(grid: np.ndarray, start, goal) -> float:
    """True 8-connected shortest-path cost. The oracle A* is checked against."""
    dist = {start: 0.0}
    pq = [(0.0, start)]
    while pq:
        d, cell = heapq.heappop(pq)
        if cell == goal:
            return d
        if d > dist.get(cell, np.inf):
            continue
        for dr, dc, w in NEIGHBORS:
            nxt = (cell[0] + dr, cell[1] + dc)
            if not (0 <= nxt[0] < grid.shape[0] and 0 <= nxt[1] < grid.shape[1]):
                continue
            if grid[nxt]:
                continue
            nd = d + w
            if nd < dist.get(nxt, np.inf) - 1e-12:
                dist[nxt] = nd
                heapq.heappush(pq, (nd, nxt))
    return float("inf")


def path_cost(path) -> float:
    """Sum of 8-connected step costs along a cell path."""
    if path is None or len(path) < 2:
        return 0.0
    a = np.asarray(path, dtype=float)
    d = np.abs(np.diff(a, axis=0))
    return float(np.sum(np.where(d.max(axis=1) == 0, 0.0,
                                 np.where(d.min(axis=1) > 0, DIAG, 1.0))))


def segment_hits(grid: np.ndarray, p0, p1, step: float = 0.4) -> bool:
    """True if the straight segment between two CELL points crosses an obstacle."""
    p0 = np.asarray(p0, dtype=float)
    p1 = np.asarray(p1, dtype=float)
    n = max(2, int(np.ceil(np.linalg.norm(p1 - p0) / step)))
    for t in np.linspace(0.0, 1.0, n + 1):
        r, c = np.round(p0 + t * (p1 - p0)).astype(int)
        if not (0 <= r < grid.shape[0] and 0 <= c < grid.shape[1]) or grid[r, c]:
            return True
    return False
