"""Reference solution for the planning mini-project."""

from __future__ import annotations

import heapq

import numpy as np
from world import DIAG, NEIGHBORS, segment_hits


def inflate(grid: np.ndarray, cells: int) -> np.ndarray:
    out = grid.copy()
    for _ in range(cells):
        nxt = out.copy()
        nxt[1:, :] |= out[:-1, :]
        nxt[:-1, :] |= out[1:, :]
        nxt[:, 1:] |= out[:, :-1]
        nxt[:, :-1] |= out[:, 1:]
        out = nxt
    return out


def _octile(a, b) -> float:
    dr, dc = abs(a[0] - b[0]), abs(a[1] - b[1])
    return (dr + dc) + (DIAG - 2.0) * min(dr, dc)


def _reconstruct(parent, cell):
    path = [cell]
    while cell in parent:
        cell = parent[cell]
        path.append(cell)
    return path[::-1]


def astar(grid: np.ndarray, start, goal):
    start, goal = tuple(start), tuple(goal)
    if grid[start] or grid[goal]:
        return None
    rows, cols = grid.shape
    g = {start: 0.0}
    parent = {}
    pq = [(_octile(start, goal), 0.0, start)]
    closed = set()
    while pq:
        _, cost, cell = heapq.heappop(pq)
        if cell in closed:
            continue
        if cell == goal:
            return _reconstruct(parent, cell)
        closed.add(cell)
        for dr, dc, w in NEIGHBORS:
            nxt = (cell[0] + dr, cell[1] + dc)
            if not (0 <= nxt[0] < rows and 0 <= nxt[1] < cols) or grid[nxt]:
                continue
            ng = cost + w
            if ng < g.get(nxt, np.inf) - 1e-12:
                g[nxt] = ng
                parent[nxt] = cell
                heapq.heappush(pq, (ng + _octile(nxt, goal), ng, nxt))
    return None


def costmap(grid: np.ndarray, decay: float = 3.0) -> np.ndarray:
    # Chamfer distance to the nearest occupied cell, in cell units.
    big = float(grid.shape[0] + grid.shape[1])
    d = np.where(grid, 0.0, big)
    for _ in range(2):
        for r in range(d.shape[0]):
            for c in range(d.shape[1]):
                v = d[r, c]
                if r > 0:
                    v = min(v, d[r - 1, c] + 1.0)
                    if c > 0:
                        v = min(v, d[r - 1, c - 1] + DIAG)
                    if c < d.shape[1] - 1:
                        v = min(v, d[r - 1, c + 1] + DIAG)
                if c > 0:
                    v = min(v, d[r, c - 1] + 1.0)
                d[r, c] = v
        d = d[::-1, ::-1].copy()
    out = np.exp(-d / decay)
    out[grid] = np.inf
    return out


def astar_costed(grid: np.ndarray, cost: np.ndarray, start, goal, weight: float = 6.0):
    start, goal = tuple(start), tuple(goal)
    if grid[start] or grid[goal]:
        return None
    rows, cols = grid.shape
    g = {start: 0.0}
    parent = {}
    pq = [(_octile(start, goal), 0.0, start)]
    closed = set()
    while pq:
        _, c_so_far, cell = heapq.heappop(pq)
        if cell in closed:
            continue
        if cell == goal:
            return _reconstruct(parent, cell)
        closed.add(cell)
        for dr, dc, w in NEIGHBORS:
            nxt = (cell[0] + dr, cell[1] + dc)
            if not (0 <= nxt[0] < rows and 0 <= nxt[1] < cols) or grid[nxt]:
                continue
            ng = c_so_far + w + weight * float(cost[nxt])
            if ng < g.get(nxt, np.inf) - 1e-12:
                g[nxt] = ng
                parent[nxt] = cell
                heapq.heappush(pq, (ng + _octile(nxt, goal), ng, nxt))
    return None


def rrt(grid: np.ndarray, start, goal, iters: int = 4000, step: float = 6.0,
        goal_bias: float = 0.08, seed: int = 0):
    rng = np.random.default_rng(seed)
    # Work in integer cells throughout. Planning in continuous coordinates and
    # rounding only at the end lets a rounded segment clip a corner the
    # continuous one cleared — the planner must guarantee what it returns.
    start = np.array(start, dtype=int)
    goal_a = np.array(goal, dtype=int)
    nodes = [start]
    parent = {0: None}
    rows, cols = grid.shape

    for _ in range(iters):
        sample = goal_a if rng.random() < goal_bias else np.array(
            [rng.uniform(0, rows - 1), rng.uniform(0, cols - 1)])
        arr = np.array(nodes)
        i = int(np.argmin(np.linalg.norm(arr - sample, axis=1)))
        near = nodes[i]
        direction = sample - near
        dist = float(np.linalg.norm(direction))
        if dist < 1e-9:
            continue
        new = np.round(near + direction / dist * min(step, dist)).astype(int)
        new = np.clip(new, [0, 0], [rows - 1, cols - 1])
        if np.array_equal(new, near) or segment_hits(grid, near, new):
            continue
        nodes.append(new)
        parent[len(nodes) - 1] = i

        if np.linalg.norm(new - goal_a) <= step and not segment_hits(grid, new, goal_a):
            nodes.append(goal_a)
            parent[len(nodes) - 1] = len(nodes) - 2
            path, k = [], len(nodes) - 1
            while k is not None:
                path.append(tuple(int(v) for v in nodes[k]))
                k = parent[k]
            return path[::-1]
    return None
