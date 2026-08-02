"""Capstone v1 stack: particle-filter lidar localization + A* + pure pursuit.

The noisy pose sensor is used ONCE, to seed the initial belief (a robot
usually knows roughly where it starts). Afterward the stack localizes
purely from commanded odometry and lidar scans matched against the known
map via a likelihood field (distance transform of the occupancy grid) —
the same construction AMCL's likelihood_field model uses.
"""

from __future__ import annotations

import numpy as np
from sim import (
    DT,
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
from robotics_ai.geometry import wrap_angle
from robotics_ai.planning import astar_grid, inflate_grid

N_PARTICLES = 1800
BEAM_STRIDE = 1          # all 36 rays: heading observability needs the density,
                         # and the latency budget has 50x headroom
LIK_SIGMA = 0.35         # likelihood-field sharpness (m)
MOTION_V_SIGMA = 0.10
MOTION_W_SIGMA = 0.08
LOOKAHEAD = 0.8
CRUISE_V = 0.9


def distance_field(grid: np.ndarray) -> np.ndarray:
    """Chamfer distance (meters) to the nearest obstacle *surface*.

    Seeding at boundary cells (occupied with a free 4-neighbor) rather than
    all occupied cells matters: with solid obstacles, an all-occupied seed
    gives depth-0 everywhere inside a box, so a mislocalized particle whose
    scan endpoints land deep inside obstacles scores as well as the truth.
    Surface seeding makes endpoint depth cost likelihood.
    """
    free = ~grid
    boundary = grid & (
        np.roll(free, 1, 0) | np.roll(free, -1, 0)
        | np.roll(free, 1, 1) | np.roll(free, -1, 1)
    )
    inf = 1e9
    d = np.where(boundary, 0.0, inf)
    rows, cols = d.shape
    w1, w2 = 1.0, np.sqrt(2.0)
    for y in range(rows):
        for x in range(cols):
            v = d[y, x]
            if y > 0:
                v = min(v, d[y - 1, x] + w1)
                if x > 0:
                    v = min(v, d[y - 1, x - 1] + w2)
                if x < cols - 1:
                    v = min(v, d[y - 1, x + 1] + w2)
            if x > 0:
                v = min(v, d[y, x - 1] + w1)
            d[y, x] = v
    for y in range(rows - 1, -1, -1):
        for x in range(cols - 1, -1, -1):
            v = d[y, x]
            if y < rows - 1:
                v = min(v, d[y + 1, x] + w1)
                if x > 0:
                    v = min(v, d[y + 1, x - 1] + w2)
                if x < cols - 1:
                    v = min(v, d[y + 1, x + 1] + w2)
            if x < cols - 1:
                v = min(v, d[y, x + 1] + w1)
            d[y, x] = v
    return d * RESOLUTION


class PFStack:
    def __init__(self, grid: np.ndarray, goal: np.ndarray) -> None:
        self.grid = grid
        self.goal = np.asarray(goal, dtype=float)
        self.inflated = inflate_grid(grid, INFLATE_CELLS)
        self.dist_field = distance_field(grid)
        self.rng = np.random.default_rng(12345)
        self.particles: np.ndarray | None = None
        self.weights = np.full(N_PARTICLES, 1.0 / N_PARTICLES)
        self.path: np.ndarray | None = None
        self.last_cmd = (0.0, 0.0)
        self.last_estimate: np.ndarray | None = None
        self.recovery_steps = 0
        self.bearings = np.arange(0, N_RAYS, BEAM_STRIDE) * (2 * np.pi / N_RAYS)

    # ---------------- particle filter ----------------

    def _init_particles(self, pose_hint: np.ndarray) -> None:
        p = np.tile(pose_hint, (N_PARTICLES, 1))
        p[:, 0] += self.rng.normal(0, 0.25, N_PARTICLES)
        p[:, 1] += self.rng.normal(0, 0.25, N_PARTICLES)
        p[:, 2] = wrap_angle(p[:, 2] + self.rng.normal(0, 0.15, N_PARTICLES))
        self.particles = p

    def _motion_update(self) -> None:
        v_cmd, w_cmd = self.last_cmd
        v = self.rng.normal(v_cmd, MOTION_V_SIGMA, N_PARTICLES)
        w = self.rng.normal(w_cmd, MOTION_W_SIGMA, N_PARTICLES)
        p = self.particles
        th = p[:, 2]
        straight = np.abs(w) < 1e-9
        w_safe = np.where(straight, 1.0, w)
        r = v / w_safe
        p[:, 0] = np.where(
            straight, p[:, 0] + v * np.cos(th) * DT,
            p[:, 0] + r * (np.sin(th + w * DT) - np.sin(th)),
        )
        p[:, 1] = np.where(
            straight, p[:, 1] + v * np.sin(th) * DT,
            p[:, 1] - r * (np.cos(th + w * DT) - np.cos(th)),
        )
        p[:, 2] = wrap_angle(th + w * DT)

    def _measurement_update(self, scan: np.ndarray) -> None:
        p = self.particles
        log_lik = np.zeros(N_PARTICLES)
        for i, bearing in zip(range(0, N_RAYS, BEAM_STRIDE), self.bearings, strict=True):
            r = scan[i]
            if r >= MAX_RANGE - 0.25:
                # Miss-rejection margin must exceed ~4 sigma of range noise:
                # a true max-range MISS with noise below a tight cutoff gets
                # treated as a hit at ~6 m, projecting a phantom endpoint into
                # open space whose huge penalty dominates the whole scan.
                continue
            ex = p[:, 0] + r * np.cos(p[:, 2] + bearing)
            ey = p[:, 1] + r * np.sin(p[:, 2] + bearing)
            fx, fy = ex / RESOLUTION, ey / RESOLUTION
            cx = np.clip(fx.astype(int), 0, GRID_N - 1)
            cy = np.clip(fy.astype(int), 0, GRID_N - 1)
            # Endpoints projected outside the map must PAY for the overshoot:
            # clipping alone lands them on border-wall surface cells (d = 0),
            # which silently rewards beliefs that drift toward the map edge.
            over = (
                np.maximum(fx - (GRID_N - 1), 0) + np.maximum(-fx, 0)
                + np.maximum(fy - (GRID_N - 1), 0) + np.maximum(-fy, 0)
            ) * RESOLUTION
            d = self.dist_field[cy, cx] + over
            log_lik += -0.5 * (d / LIK_SIGMA) ** 2
        w = self.weights * np.exp(log_lik - log_lik.max())
        s = w.sum()
        self.weights = np.full(N_PARTICLES, 1.0 / N_PARTICLES) if s < 1e-300 else w / s

    def _resample_if_needed(self) -> None:
        if 1.0 / np.sum(self.weights**2) < N_PARTICLES / 2:
            positions = (self.rng.random() + np.arange(N_PARTICLES)) / N_PARTICLES
            cs = np.cumsum(self.weights)
            cs[-1] = 1.0
            self.particles = self.particles[np.searchsorted(cs, positions)]
            self.weights = np.full(N_PARTICLES, 1.0 / N_PARTICLES)
            # Roughening: resampling clones particles, and with strong beams
            # the cloud collapses to ~1 cm — too inbred to re-adapt when the
            # environment goes feature-poor. Post-resample jitter keeps a
            # minimum diversity floor.
            self.particles[:, 0] += self.rng.normal(0, 0.01, N_PARTICLES)
            self.particles[:, 1] += self.rng.normal(0, 0.01, N_PARTICLES)
            self.particles[:, 2] = wrap_angle(
                self.particles[:, 2] + self.rng.normal(0, 0.005, N_PARTICLES)
            )

    def _estimate(self) -> np.ndarray:
        p, w = self.particles, self.weights
        x = w @ p[:, 0]
        y = w @ p[:, 1]
        th = np.arctan2(w @ np.sin(p[:, 2]), w @ np.cos(p[:, 2]))
        return np.array([x, y, th])

    # ---------------- navigation ----------------

    def _nearest_free_cell(self, cell: tuple[int, int]) -> tuple[int, int]:
        """Snap to the closest non-inflated cell — after a collision the robot
        (and its estimate) legitimately sits inside the inflation skirt."""
        if not self.inflated[cell]:
            return cell
        for radius in range(1, 8):
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    y, x = cell[0] + dy, cell[1] + dx
                    if 0 <= y < GRID_N and 0 <= x < GRID_N and not self.inflated[y, x]:
                        return (y, x)
        return cell

    def _plan(self, from_xy: np.ndarray) -> None:
        start = self._nearest_free_cell(world_to_cell(from_xy))
        cells = astar_grid(self.inflated, start, world_to_cell(self.goal))
        if cells is None:
            raise RuntimeError("no path in inflated map")
        pts = np.array([cell_to_world(c) for c in cells])
        pts[-1] = self.goal
        self.path = pts

    def step(self, obs: dict) -> tuple[float, float]:
        if obs["collided"]:
            # The commanded motion did NOT execute — the sim blocked it.
            # Propagating it anyway decouples belief from reality and spirals
            # (estimate marches on, controller pushes into the wall forever).
            self.last_cmd = (0.0, 0.0)
            self.recovery_steps = 8
            self.path = None  # replan once re-localized after recovery
        if self.particles is None:
            self._init_particles(obs["pose_meas"])  # the only use of the pose sensor
        else:
            self._motion_update()
        self._measurement_update(obs["scan"])
        est = self._estimate()
        self._resample_if_needed()
        self.last_estimate = est

        if self.recovery_steps > 0:
            # Rotate in place (always collision-safe: current pose is valid)
            # to face the replanned path before driving again.
            self.recovery_steps -= 1
            self.last_cmd = (0.0, 1.2)
            return self.last_cmd

        if self.path is None:
            self._plan(est[:2])
        dist_goal = float(np.hypot(*(est[:2] - self.goal)))
        if dist_goal < GOAL_TOLERANCE * 0.8:
            self.last_cmd = (0.0, 0.0)
            return self.last_cmd
        w = pure_pursuit(est, self.path, LOOKAHEAD, CRUISE_V)
        v = CRUISE_V / (1.0 + 0.8 * abs(w))
        v = min(v, max(0.25, dist_goal))
        self.last_cmd = (float(v), float(w))
        return self.last_cmd


def make_stack(sim) -> PFStack:
    return PFStack(sim.grid, sim.goal)
