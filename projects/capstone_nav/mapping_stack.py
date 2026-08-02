"""Capstone v2 stack: UNKNOWN map — build the occupancy grid online.

This stack never reads the simulator's grid. It starts with a blank
log-odds map, integrates every lidar scan from the (noisy) pose sensor,
plans optimistically through unexplored space, and replans whenever the
freshly-mapped world contradicts the current path. Exploration emerges
from optimism: unknown cells are treated as free, so the planner happily
routes through the dark until the lidar says otherwise.

Localization here is the noisy pose sensor (mapping with a KNOWN pose,
lesson 4.1's setting). Doing both at once — unknown map AND unknown pose —
is SLAM, which is v3+ territory.
"""

from __future__ import annotations

import numpy as np
from sim import (
    GOAL_TOLERANCE,
    GRID_N,
    INFLATE_CELLS,
    MAX_RANGE,
    N_RAYS,
    RESOLUTION,
    cell_to_world,
    world_to_cell,
)

from robotics_ai.control import pure_pursuit
from robotics_ai.mapping import OccupancyGridMap
from robotics_ai.planning import astar_grid, inflate_grid

LOOKAHEAD = 0.8
CRUISE_V = 0.8
MISS_MARGIN = 0.25          # the v1 lesson: reject max-range misses at >= 4 sigma
REPLAN_PERIOD = 15          # steps between routine replans
OCC_THRESHOLD = 0.65


class MappingStack:
    def __init__(self, goal: np.ndarray) -> None:
        self.goal = np.asarray(goal, dtype=float)
        self.map = OccupancyGridMap((GRID_N, GRID_N), RESOLUTION)
        self.path: np.ndarray | None = None
        self.last_estimate: np.ndarray | None = None
        self.recovery_steps = 0
        self.steps_since_plan = 0
        self.bearing_offsets = np.linspace(0, 2 * np.pi, N_RAYS, endpoint=False)

    # ---------------- mapping ----------------

    def _integrate_scan(self, pose: np.ndarray, scan: np.ndarray) -> None:
        origin = pose[:2]
        for i in range(N_RAYS):
            r = scan[i]
            hit = r < MAX_RANGE - MISS_MARGIN
            reach = r if hit else MAX_RANGE
            b = pose[2] + self.bearing_offsets[i]
            end = origin + reach * np.array([np.cos(b), np.sin(b)])
            self.map.update_ray(origin, end, hit=hit)

    def _planning_grid(self, inflate: int = INFLATE_CELLS - 1) -> np.ndarray:
        """Occupied = confidently-occupied cells, inflated. Unknown = free.

        One cell LESS inflation than the known-map stacks: mapped walls carry
        a ~1-cell crust (ray endpoints land just inside surfaces), so full
        inflation seals narrow-but-legal passages — seed-51's robot spent an
        entire episode spinning inside a start pocket its own map had welded
        shut. The crust itself supplies the missing margin."""
        return inflate_grid(self.map.occupied_mask(OCC_THRESHOLD), inflate)

    # ---------------- navigation ----------------

    def _nearest_free_cell(self, grid: np.ndarray, cell: tuple[int, int]) -> tuple[int, int]:
        if not grid[cell]:
            return cell
        for radius in range(1, 10):
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    y, x = cell[0] + dy, cell[1] + dx
                    if 0 <= y < GRID_N and 0 <= x < GRID_N and not grid[y, x]:
                        return (y, x)
        return cell

    def _compute_plan(self, grid: np.ndarray, from_xy: np.ndarray) -> np.ndarray | None:
        start = self._nearest_free_cell(grid, world_to_cell(from_xy))
        goal = self._nearest_free_cell(grid, world_to_cell(self.goal))
        cells = astar_grid(grid, start, goal)
        if cells is None:
            return None
        pts = np.array([cell_to_world(c) for c in cells])
        pts[-1] = self.goal
        return pts

    @staticmethod
    def _remaining_length(path: np.ndarray, from_xy: np.ndarray) -> float:
        d = path - from_xy[None, :]
        i = int(np.argmin(np.hypot(d[:, 0], d[:, 1])))
        seg = np.diff(path[i:], axis=0)
        return float(np.hypot(seg[:, 0], seg[:, 1]).sum()) if len(seg) else 0.0

    def _plan(self, from_xy: np.ndarray, force: bool = False) -> bool:
        """Replan with hysteresis: as the map grows, fresh plans keep offering
        'shortcuts' through unexplored space that hide the same wall we just
        discovered — chasing every one of them oscillates the robot between
        routes forever (lesson 5.1's replanning thrash). Keep the committed
        path unless it's blocked/forced, or the new one is 25% shorter."""
        grid = self._planning_grid()
        candidate = self._compute_plan(grid, from_xy)
        if candidate is None:
            # Graceful degradation: shave the safety skirt before giving up.
            grid = self._planning_grid(inflate=1)
            candidate = self._compute_plan(grid, from_xy)
        self.steps_since_plan = 0
        if candidate is None:
            return False
        if not force and self.path is not None and not self._path_blocked(grid):
            cand_len = self._remaining_length(candidate, from_xy)
            cur_len = self._remaining_length(self.path, from_xy)
            if cand_len > 0.75 * cur_len:
                return True  # keep the committed route
        self.path = candidate
        return True

    def _path_blocked(self, grid: np.ndarray) -> bool:
        if self.path is None:
            return True
        for xy in self.path[:: max(1, len(self.path) // 30)]:
            if grid[world_to_cell(xy)]:
                return True
        return False

    def step(self, obs: dict) -> tuple[float, float]:
        pose = obs["pose_meas"]
        self.last_estimate = pose
        self._integrate_scan(pose, obs["scan"])
        self.steps_since_plan += 1

        if obs["collided"]:
            # Physical veto of the current plan: something unmapped (or
            # noise-displaced) is there. Mark recovery, force a fresh plan.
            self.recovery_steps = 8
            self.path = None
        if self.recovery_steps > 0:
            self.recovery_steps -= 1
            return (0.0, 1.2)

        blocked = self.path is None or self._path_blocked(self._planning_grid())
        if blocked or self.steps_since_plan >= REPLAN_PERIOD:
            if not self._plan(pose[:2], force=blocked):
                # Blocked in the *current* map: rotate to gather more world.
                self.recovery_steps = 6
                return (0.0, 1.2)

        dist_goal = float(np.hypot(*(pose[:2] - self.goal)))
        if dist_goal < GOAL_TOLERANCE * 0.8:
            return (0.0, 0.0)
        w = pure_pursuit(pose, self.path, LOOKAHEAD, CRUISE_V)
        v = CRUISE_V / (1.0 + 0.8 * abs(w))
        v = min(v, max(0.25, dist_goal))
        return (float(v), float(w))


def make_stack(sim) -> MappingStack:
    return MappingStack(sim.goal)  # note: no sim.grid — the map is earned
