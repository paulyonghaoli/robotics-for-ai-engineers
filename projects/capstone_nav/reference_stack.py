"""Reference autonomy stack: plan once with A*, track with pure pursuit.

The honest baseline the capstone rubric is calibrated against. It uses the
known static map (v0 scope) and the noisy pose sensor; the full capstone
replaces the pose sensor with particle-filter localization from the lidar
and rebuilds the map online (see README roadmap).
"""

from __future__ import annotations

import numpy as np
from sim import GOAL_TOLERANCE, INFLATE_CELLS, cell_to_world, world_to_cell

from robotics_ai.control import pure_pursuit
from robotics_ai.planning import astar_grid, inflate_grid

LOOKAHEAD = 0.8
CRUISE_V = 0.9


class ReferenceStack:
    """plan-once A* + pure-pursuit tracker on the noisy pose sensor."""

    def __init__(self, grid: np.ndarray, goal: np.ndarray) -> None:
        self.inflated = inflate_grid(grid, INFLATE_CELLS)
        self.goal = np.asarray(goal, dtype=float)
        self.path: np.ndarray | None = None

    def _plan(self, from_xy: np.ndarray) -> None:
        start = world_to_cell(from_xy)
        goal = world_to_cell(self.goal)
        cells = astar_grid(self.inflated, start, goal)
        if cells is None:
            raise RuntimeError("no path in inflated map")
        pts = np.array([cell_to_world(c) for c in cells])
        pts[-1] = self.goal
        self.path = pts

    def step(self, obs: dict) -> tuple[float, float]:
        pose = obs["pose_meas"]
        if self.path is None:
            self._plan(pose[:2])
        dist_goal = float(np.hypot(*(pose[:2] - self.goal)))
        if dist_goal < GOAL_TOLERANCE * 0.8:
            return 0.0, 0.0
        w = pure_pursuit(pose, self.path, LOOKAHEAD, CRUISE_V)
        # Slow for tight turns and on final approach.
        v = CRUISE_V / (1.0 + 0.8 * abs(w))
        v = min(v, max(0.25, dist_goal))
        return v, float(w)


def make_stack(sim) -> ReferenceStack:
    """Factory the evaluation harness calls: receives the Simulator, may read
    its map and goal (v0 scope: known map), returns the stack object."""
    return ReferenceStack(sim.grid, sim.goal)
