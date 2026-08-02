"""Capstone simulator: differential-drive robot in a 2D occupancy world.

The contract every autonomy stack runs against:

    sim = Simulator(seed)
    obs = sim.reset()
    while not done:
        v, w = stack.step(obs)
        obs, done = sim.step(v, w)

Observations per step:
    pose_meas : noisy pose sensor (x, y, theta)  [sigma 0.10 m / 0.05 rad]
    scan      : (N_RAYS,) lidar ranges, MAX_RANGE where no hit
    goal      : (x, y) world goal
    collided  : True if the footprint touched an obstacle this step

Ground truth stays inside the simulator; the evaluation harness reads it
for scoring, stacks may not.
"""

from __future__ import annotations

import numpy as np

from robotics_ai.geometry import wrap_angle
from robotics_ai.planning import astar_grid, inflate_grid

WORLD_SIZE = 20.0
RESOLUTION = 0.2
GRID_N = int(WORLD_SIZE / RESOLUTION)  # 100
DT = 0.1
N_RAYS = 36
MAX_RANGE = 6.0
RANGE_SIGMA = 0.05
POSE_SIGMA_XY = 0.10
POSE_SIGMA_TH = 0.05
V_SIGMA = 0.08
W_SIGMA = 0.06
ROBOT_RADIUS = 0.3
GOAL_TOLERANCE = 0.5
V_MAX, W_MAX = 1.2, 2.0
INFLATE_CELLS = int(np.ceil(ROBOT_RADIUS / RESOLUTION)) + 1


def make_world(seed: int):
    """Occupancy grid with border walls + random boxes; start/goal connected."""
    rng = np.random.default_rng(seed)
    for _attempt in range(50):
        grid = np.zeros((GRID_N, GRID_N), dtype=bool)
        grid[0, :] = grid[-1, :] = grid[:, 0] = grid[:, -1] = True
        for _ in range(rng.integers(6, 10)):
            h, w = rng.integers(5, 20, 2)
            y, x = rng.integers(3, GRID_N - 3 - h), rng.integers(3, GRID_N - 3 - w)
            grid[y : y + h, x : x + w] = True
        start = np.array([2.0, 2.0, rng.uniform(-np.pi, np.pi)])
        goal = rng.uniform(WORLD_SIZE * 0.6, WORLD_SIZE - 2.0, 2)
        inflated = inflate_grid(grid, INFLATE_CELLS)
        s = world_to_cell(start[:2])
        g = world_to_cell(goal)
        if not inflated[s] and not inflated[g] and astar_grid(inflated, s, g) is not None:
            return grid, start, goal
    raise RuntimeError(f"could not generate a solvable world for seed {seed}")


def world_to_cell(xy) -> tuple[int, int]:
    c = np.asarray(xy) / RESOLUTION
    return int(c[1]), int(c[0])


def cell_to_world(cell) -> np.ndarray:
    return np.array([(cell[1] + 0.5) * RESOLUTION, (cell[0] + 0.5) * RESOLUTION])


class DynamicObstacle:
    """A moving circular obstacle that is NOT in the map — the robot can only
    know about it from live sensor data. Patrols until it meets a wall, then
    reverses (deterministic, so episodes stay reproducible)."""

    def __init__(self, pos, vel, radius=0.35):
        self.pos = np.asarray(pos, dtype=float)
        self.vel = np.asarray(vel, dtype=float)
        self.radius = radius

    def step(self, grid, dt=None):
        dt = DT if dt is None else dt
        new = self.pos + self.vel * dt
        cell = world_to_cell(new)
        blocked = (
            not (0 <= cell[0] < GRID_N and 0 <= cell[1] < GRID_N) or grid[cell]
        )
        if blocked:
            self.vel = -self.vel
            new = self.pos + self.vel * dt
        self.pos = new


def make_dynamic_obstacles(grid, start, goal, n, rng):
    """Spawn n patrolling obstacles in free space, clear of start and goal."""
    obstacles = []
    tries = 0
    while len(obstacles) < n and tries < 400:
        tries += 1
        p = rng.uniform(2.0, WORLD_SIZE - 2.0, 2)
        if grid[world_to_cell(p)]:
            continue
        if np.hypot(*(p - start[:2])) < 3.0 or np.hypot(*(p - goal)) < 2.0:
            continue
        heading = rng.uniform(-np.pi, np.pi)
        speed = rng.uniform(0.25, 0.5)
        obstacles.append(
            DynamicObstacle(p, [speed * np.cos(heading), speed * np.sin(heading)])
        )
    return obstacles


def _ray_circle_range(origin, direction, center, radius):
    """Distance along a unit ray to the near intersection with a circle, or None."""
    oc = origin - center
    b = float(oc @ direction)
    c = float(oc @ oc) - radius * radius
    disc = b * b - c
    if disc < 0.0:
        return None
    t = -b - np.sqrt(disc)
    return t if t > 0.0 else None


def lidar_scan(pose, grid, rng, obstacles=()) -> np.ndarray:
    """Ray-march N_RAYS beams against the map, then clip against any moving
    obstacles; returns noisy ranges (MAX_RANGE if no hit)."""
    ranges = np.full(N_RAYS, MAX_RANGE)
    bearings = pose[2] + np.linspace(0, 2 * np.pi, N_RAYS, endpoint=False)
    step = RESOLUTION * 0.5
    for i, b in enumerate(bearings):
        d, c, s = step, np.cos(b), np.sin(b)
        while d < MAX_RANGE:
            cell = world_to_cell([pose[0] + d * c, pose[1] + d * s])
            if not (0 <= cell[0] < GRID_N and 0 <= cell[1] < GRID_N) or grid[cell]:
                ranges[i] = d
                break
            d += step
    for ob in obstacles:
        for i, b in enumerate(bearings):
            t = _ray_circle_range(
                pose[:2], np.array([np.cos(b), np.sin(b)]), ob.pos, ob.radius
            )
            if t is not None and t < ranges[i]:
                ranges[i] = t
    return np.clip(ranges + rng.normal(0, RANGE_SIGMA, N_RAYS), 0.0, MAX_RANGE)


def footprint_collides(pose, grid, obstacles=()) -> bool:
    for ob in obstacles:
        if np.hypot(*(pose[:2] - ob.pos)) < ROBOT_RADIUS + ob.radius:
            return True
    r_cells = int(np.ceil(ROBOT_RADIUS / RESOLUTION))
    cy, cx = world_to_cell(pose[:2])
    for dy in range(-r_cells, r_cells + 1):
        for dx in range(-r_cells, r_cells + 1):
            if dy * dy + dx * dx > r_cells * r_cells:
                continue
            y, x = cy + dy, cx + dx
            if not (0 <= y < GRID_N and 0 <= x < GRID_N) or grid[y, x]:
                return True
    return False


class Simulator:
    def __init__(self, seed: int, max_steps: int = 600, n_dynamic: int = 0) -> None:
        self.seed = seed
        self.max_steps = max_steps
        self.n_dynamic = n_dynamic
        self.grid, self.start, self.goal = make_world(seed)
        self.rng = np.random.default_rng(seed + 1000)
        self.reset()

    def reset(self) -> dict:
        self.pose = self.start.copy()
        self.k = 0
        self.trajectory = [self.pose.copy()]
        self.collisions = 0
        self.obstacles = make_dynamic_obstacles(
            self.grid, self.start, self.goal, self.n_dynamic,
            np.random.default_rng(self.seed + 2000),
        )
        return self._obs(collided=False)

    def _obs(self, collided: bool) -> dict:
        noisy = self.pose + self.rng.normal(0, [POSE_SIGMA_XY, POSE_SIGMA_XY, POSE_SIGMA_TH])
        noisy[2] = wrap_angle(noisy[2])
        return {
            "pose_meas": noisy,
            "scan": lidar_scan(self.pose, self.grid, self.rng, self.obstacles),
            "goal": self.goal.copy(),
            "collided": collided,
        }

    @property
    def at_goal(self) -> bool:
        return bool(np.hypot(*(self.pose[:2] - self.goal)) < GOAL_TOLERANCE)

    def step(self, v: float, w: float) -> tuple[dict, bool]:
        for ob in self.obstacles:
            ob.step(self.grid)
        v = float(np.clip(v, 0.0, V_MAX)) + self.rng.normal(0, V_SIGMA)
        w = float(np.clip(w, -W_MAX, W_MAX)) + self.rng.normal(0, W_SIGMA)
        x, y, th = self.pose
        if abs(w) < 1e-9:
            new = np.array([x + v * np.cos(th) * DT, y + v * np.sin(th) * DT, th])
        else:
            r = v / w
            new = np.array([
                x + r * (np.sin(th + w * DT) - np.sin(th)),
                y - r * (np.cos(th + w * DT) - np.cos(th)),
                wrap_angle(th + w * DT),
            ])
        collided = footprint_collides(new, self.grid, self.obstacles)
        if collided:
            self.collisions += 1  # blocked: stay in place, count it
        else:
            self.pose = new
        self.trajectory.append(self.pose.copy())
        self.k += 1
        done = self.at_goal or self.k >= self.max_steps
        return self._obs(collided), done
