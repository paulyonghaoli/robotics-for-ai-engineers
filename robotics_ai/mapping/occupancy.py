"""Log-odds occupancy grid mapping.

Each cell holds the log-odds of being occupied. A range-sensor ray updates
cells along its beam (Bresenham traversal): cells before the endpoint get
the *free* update, the endpoint (if a hit) gets the *occupied* update.
Log-odds make the Bayesian update a literal addition and are clamped to
avoid saturated cells that can never change their mind.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]


def bresenham(y0: int, x0: int, y1: int, x1: int) -> list[tuple[int, int]]:
    """Integer cells on the segment from (y0,x0) to (y1,x1), inclusive."""
    cells = []
    dy, dx = abs(y1 - y0), abs(x1 - x0)
    sy, sx = (1 if y1 >= y0 else -1), (1 if x1 >= x0 else -1)
    err = dx - dy
    y, x = y0, x0
    while True:
        cells.append((y, x))
        if (y, x) == (y1, x1):
            return cells
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy


class OccupancyGridMap:
    """Log-odds occupancy grid over a world rectangle anchored at origin."""

    def __init__(
        self,
        size_cells: tuple[int, int],
        resolution: float,
        origin: tuple[float, float] = (0.0, 0.0),
        l_free: float = -0.4,
        l_occ: float = 0.85,
        l_clamp: float = 6.0,
    ) -> None:
        self.log_odds: FloatArray = np.zeros(size_cells, dtype=np.float64)
        self.resolution = resolution
        self.origin = np.asarray(origin, dtype=np.float64)
        self.l_free, self.l_occ, self.l_clamp = l_free, l_occ, l_clamp

    def world_to_cell(self, xy: FloatArray) -> tuple[int, int]:
        c = (np.asarray(xy) - self.origin) / self.resolution
        return int(c[1]), int(c[0])  # (row=y, col=x)

    def in_bounds(self, cell: tuple[int, int]) -> bool:
        return 0 <= cell[0] < self.log_odds.shape[0] and 0 <= cell[1] < self.log_odds.shape[1]

    def update_ray(self, origin_xy: FloatArray, end_xy: FloatArray, hit: bool) -> None:
        """Integrate one beam: free space along it, occupied at the end if hit."""
        c0 = self.world_to_cell(origin_xy)
        c1 = self.world_to_cell(end_xy)
        cells = bresenham(*c0, *c1)
        for cell in cells[:-1]:
            if self.in_bounds(cell):
                self.log_odds[cell] += self.l_free
        if hit and self.in_bounds(cells[-1]):
            self.log_odds[cells[-1]] += self.l_occ
        elif not hit and self.in_bounds(cells[-1]):
            self.log_odds[cells[-1]] += self.l_free
        np.clip(self.log_odds, -self.l_clamp, self.l_clamp, out=self.log_odds)

    def probability(self) -> FloatArray:
        """Occupancy probability per cell: p = 1 - 1/(1 + exp(l))."""
        return 1.0 - 1.0 / (1.0 + np.exp(self.log_odds))

    def occupied_mask(self, threshold: float = 0.65) -> npt.NDArray[np.bool_]:
        return self.probability() > threshold
