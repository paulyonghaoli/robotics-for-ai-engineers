"""Shared world for the mapping mini-project. Given to you.

A small 2D world with solid rectangular obstacles, a lidar that ray-casts
against it, and helpers for grid indexing. Nothing here needs modifying.
"""

from __future__ import annotations

import numpy as np

RESOLUTION = 0.1                 # metres per cell
GRID_N = 120                     # 12 m square
WORLD = GRID_N * RESOLUTION
MAX_RANGE = 5.0
RANGE_SIGMA = 0.02
N_RAYS = 72

LOG_ODDS_HIT = 0.85
LOG_ODDS_MISS = -0.4
LOG_ODDS_CLAMP = 8.0


def wrap(theta):
    """Wrap angle(s) to (-pi, pi]."""
    wrapped = np.mod(-np.asarray(theta, dtype=float) + np.pi, 2.0 * np.pi)
    result = -(wrapped - np.pi)
    return float(result) if np.ndim(theta) == 0 else result


def world_to_cell(xy) -> tuple[int, int]:
    """(x, y) metres -> (row, col). Row is y, column is x."""
    return (int(np.floor(xy[1] / RESOLUTION)), int(np.floor(xy[0] / RESOLUTION)))


def cell_to_world(cell) -> np.ndarray:
    """(row, col) -> the metric centre of that cell."""
    return np.array([(cell[1] + 0.5) * RESOLUTION, (cell[0] + 0.5) * RESOLUTION])


def make_world(seed: int) -> np.ndarray:
    """A boolean occupancy grid: solid border plus a few boxes."""
    rng = np.random.default_rng(seed)
    grid = np.zeros((GRID_N, GRID_N), dtype=bool)
    grid[0, :] = grid[-1, :] = grid[:, 0] = grid[:, -1] = True
    for _ in range(rng.integers(4, 7)):
        h, w = rng.integers(8, 20), rng.integers(8, 20)
        r, c = rng.integers(12, GRID_N - 12 - h), rng.integers(12, GRID_N - 12 - w)
        grid[r:r + h, c:c + w] = True
    return grid


def free_pose(grid: np.ndarray, rng) -> np.ndarray:
    """A random pose in open space, at least 5 cells from any obstacle."""
    while True:
        xy = rng.uniform(1.5, WORLD - 1.5, size=2)
        r, c = world_to_cell(xy)
        if not grid[r - 5:r + 6, c - 5:c + 6].any():
            return np.array([xy[0], xy[1], rng.uniform(-np.pi, np.pi)])


def lidar_scan(pose: np.ndarray, grid: np.ndarray, rng=None) -> np.ndarray:
    """N_RAYS ranges, evenly spaced from the robot's heading, CCW.

    A ray that hits nothing within MAX_RANGE returns exactly MAX_RANGE —
    which is a *non-detection*, not a measurement of an obstacle at 5 m.
    """
    bearings = pose[2] + np.arange(N_RAYS) * (2 * np.pi / N_RAYS)
    out = np.full(N_RAYS, MAX_RANGE)
    step = RESOLUTION * 0.5
    for i, b in enumerate(bearings):
        d = step
        cb, sb = np.cos(b), np.sin(b)
        while d < MAX_RANGE:
            r, c = world_to_cell((pose[0] + d * cb, pose[1] + d * sb))
            if not (0 <= r < GRID_N and 0 <= c < GRID_N) or grid[r, c]:
                out[i] = d
                break
            d += step
    if rng is not None:
        hit = out < MAX_RANGE
        out[hit] = np.clip(out[hit] + rng.normal(0, RANGE_SIGMA, hit.sum()),
                           0.05, MAX_RANGE)
    return out


def scan_endpoints(pose: np.ndarray, scan: np.ndarray) -> np.ndarray:
    """(K, 2) world-frame endpoints of the beams that actually hit something."""
    bearings = pose[2] + np.arange(N_RAYS) * (2 * np.pi / N_RAYS)
    hit = scan < MAX_RANGE - 4 * RANGE_SIGMA
    b, r = bearings[hit], scan[hit]
    return np.stack([pose[0] + r * np.cos(b), pose[1] + r * np.sin(b)], axis=1)
