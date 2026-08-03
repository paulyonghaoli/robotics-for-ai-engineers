"""Capstone v3: navigation among MOVING obstacles that are not in the map.

Two problems appear at once, and they are usually taught apart:

1. **Avoidance.** The global plan (A*, lesson 5.1) knows only the static map.
   Anything that moves must be handled by a local planner reacting to live
   sensor data — DWA (lesson 5.4), scoring the reachable velocity window on
   progress, clearance, and speed.

2. **Localization corruption.** The particle filter's likelihood field
   (v1) assumes a static world. A beam that stops early on a *person* looks,
   to the filter, like overwhelming evidence that the robot is somewhere
   else entirely. The fix is ICP's outlier trimming (lesson 4.2) in
   localization clothing: reject beams whose endpoint lands far from
   anything the map knows about.

Everything else — PF localization, A* on the inflated map — is inherited
from v1 unchanged.
"""

from __future__ import annotations

import numpy as np
from pf_stack import CRUISE_V, PFStack
from sim import DT, GOAL_TOLERANCE, GRID_N, MAX_RANGE, N_RAYS, RESOLUTION, ROBOT_RADIUS

# --- dynamic-beam rejection -------------------------------------------------
DYNAMIC_BEAM_DIST = 0.75   # endpoint this far from any mapped surface => not the map

# --- DWA --------------------------------------------------------------------
A_V, A_W = 1.2, 2.5        # acceleration limits (m/s^2, rad/s^2)
W_MAX_LOCAL = 1.8
N_V, N_W = 5, 11           # velocity-window sampling
HORIZON = 10               # rollout steps
SAFE_DIST = ROBOT_RADIUS + 0.12
# A scan point is a snapshot, but the thing that made it may be *moving*.
# Requiring a margin that grows with rollout time is the cheap, standard
# reachable-set hedge: by step k an unseen mover could have closed
# MAX_DYN_SPEED * k * DT metres. Without this the planner confidently
# routes through where an obstacle is about to be.
MAX_DYN_SPEED = 0.5
W_PROGRESS, W_CLEAR, W_SPEED = 2.5, 0.6, 0.25


class DynamicStack(PFStack):
    def __init__(self, grid: np.ndarray, goal: np.ndarray) -> None:
        super().__init__(grid, goal)
        self.v_cmd = 0.0
        self.w_cmd = 0.0
        self.rejected_beams = 0

    # ---------------- localization: trim the dynamic beams ----------------

    def _classify_beams(self, est: np.ndarray, scan: np.ndarray) -> np.ndarray:
        """Which beams landed somewhere the static map cannot explain?

        One classification, two consumers: the localizer must *ignore* these
        beams (they are not evidence about the robot's pose), and the local
        planner must treat them as *possibly moving* (they are the only
        evidence about where a mover is). Static map hits get the opposite
        treatment on both counts.
        """
        is_dynamic = np.zeros(N_RAYS, dtype=bool)
        bearings = est[2] + np.arange(N_RAYS) * (2 * np.pi / N_RAYS)
        hit = scan < MAX_RANGE - 0.25
        ex = est[0] + scan * np.cos(bearings)
        ey = est[1] + scan * np.sin(bearings)
        cx = np.clip((ex / RESOLUTION).astype(int), 0, GRID_N - 1)
        cy = np.clip((ey / RESOLUTION).astype(int), 0, GRID_N - 1)
        is_dynamic[hit] = self.dist_field[cy[hit], cx[hit]] > DYNAMIC_BEAM_DIST
        return is_dynamic

    def _measurement_update(self, scan: np.ndarray) -> None:
        """Drop map-inexplicable beams, then run v1's likelihood-field update."""
        if self.last_estimate is not None:
            self._is_dynamic = self._classify_beams(self.last_estimate, scan)
            self.rejected_beams = int(self._is_dynamic.sum())
            # Pushing a beam to max range makes it invisible to v1's update,
            # whose miss-rejection margin already skips max-range returns.
            scan = np.where(self._is_dynamic, MAX_RANGE, scan)
        super()._measurement_update(scan)

    # ---------------- local planning: the dynamic window ----------------

    def _scan_points(self, est: np.ndarray, scan: np.ndarray):
        """Live hits as world points, split into static (mapped) and possibly
        moving (map-inexplicable) — they earn different safety margins."""
        idx = np.flatnonzero(scan < MAX_RANGE - 0.25)
        if idx.size == 0:
            return np.empty((0, 2)), np.empty((0, 2))
        b = est[2] + idx * (2 * np.pi / N_RAYS)
        r = scan[idx]
        pts = np.column_stack([est[0] + r * np.cos(b), est[1] + r * np.sin(b)])
        dyn_mask = getattr(self, "_is_dynamic", np.zeros(N_RAYS, dtype=bool))[idx]
        return pts[~dyn_mask], pts[dyn_mask]

    @staticmethod
    def _rollout(est: np.ndarray, v: float, w: float) -> np.ndarray:
        x, y, th = est
        pts = np.empty((HORIZON, 2))
        for k in range(HORIZON):
            if abs(w) < 1e-9:
                x += v * np.cos(th) * DT
                y += v * np.sin(th) * DT
            else:
                r = v / w
                x += r * (np.sin(th + w * DT) - np.sin(th))
                y -= r * (np.cos(th + w * DT) - np.cos(th))
                th += w * DT
            pts[k] = (x, y)
        return pts

    def _dwa(self, est: np.ndarray, scan: np.ndarray) -> tuple[float, float]:
        static_pts, dyn_pts = self._scan_points(est, scan)
        goal_pt = self._local_goal(est)
        d0 = float(np.hypot(*(est[:2] - goal_pt)))

        vs = np.linspace(max(0.0, self.v_cmd - A_V * DT),
                         min(CRUISE_V, self.v_cmd + A_V * DT), N_V)
        ws = np.linspace(max(-W_MAX_LOCAL, self.w_cmd - A_W * DT),
                         min(W_MAX_LOCAL, self.w_cmd + A_W * DT), N_W)

        best, best_score = (0.0, 0.0), -np.inf
        for v in vs:
            for w in ws:
                pts = self._rollout(est, v, w)
                clearance = MAX_RANGE
                blocked = False
                # Mapped walls are static: a constant margin is correct, and
                # inflating against them is what freezes robots in doorways.
                if static_pts.size:
                    d = np.linalg.norm(pts[:, None, :] - static_pts[None, :, :], axis=2)
                    per_step = d.min(axis=1)
                    blocked = bool(np.any(per_step < SAFE_DIST))
                    clearance = min(clearance, float(per_step.min()))
                # Movers get the time-inflated reachable-set margin.
                if not blocked and dyn_pts.size:
                    d = np.linalg.norm(pts[:, None, :] - dyn_pts[None, :, :], axis=2)
                    per_step = d.min(axis=1)
                    required = SAFE_DIST + MAX_DYN_SPEED * DT * np.arange(1, HORIZON + 1)
                    blocked = bool(np.any(per_step < required))
                    clearance = min(clearance, float(per_step.min()))
                if blocked:
                    continue
                progress = d0 - float(np.hypot(*(pts[-1] - goal_pt)))
                score = (W_PROGRESS * progress
                         + W_CLEAR * min(clearance, 1.5)
                         + W_SPEED * v)
                if score > best_score:
                    best_score, best = score, (float(v), float(w))

        if best_score == -np.inf:
            # Every reachable arc is blocked. Rotating blindly is a coin flip;
            # turn toward the *most open* bearing instead (rotation in place is
            # always collision-safe — the current pose is already valid).
            return 0.0, self._open_turn(est, scan)
        return best

    @staticmethod
    def _open_turn(est: np.ndarray, scan: np.ndarray) -> float:
        """Sign of the turn toward the longest-range half of the scan."""
        bearings = np.arange(N_RAYS) * (2 * np.pi / N_RAYS)
        best = int(np.argmax(scan))
        rel = np.arctan2(np.sin(bearings[best]), np.cos(bearings[best]))
        return 1.2 if rel >= 0 else -1.2

    def _local_goal(self, est: np.ndarray) -> np.ndarray:
        """A point on the global path ~1.5 m ahead — DWA's carrot."""
        if self.path is None:
            return self.goal
        d = self.path - est[:2]
        i = int(np.argmin(np.hypot(d[:, 0], d[:, 1])))
        for j in range(i, len(self.path)):
            if np.hypot(*(self.path[j] - est[:2])) >= 1.5:
                return self.path[j]
        return self.path[-1]

    # ---------------- the loop ----------------

    def step(self, obs: dict) -> tuple[float, float]:
        if obs["collided"]:
            self.last_cmd = (0.0, 0.0)
            self.v_cmd = self.w_cmd = 0.0
            self.recovery_steps = 8
            self.path = None
        if self.particles is None:
            self._init_particles(obs["pose_meas"])
            self.last_estimate = obs["pose_meas"]
        else:
            self._motion_update()
        self._measurement_update(obs["scan"])
        est = self._estimate()
        self._resample_if_needed()
        self.last_estimate = est

        if self.recovery_steps > 0:
            self.recovery_steps -= 1
            self.last_cmd = (0.0, 1.2)
            self.v_cmd, self.w_cmd = 0.0, 1.2
            return self.last_cmd

        if self.path is None:
            self._plan(est[:2])
        if float(np.hypot(*(est[:2] - self.goal))) < GOAL_TOLERANCE * 0.8:
            self.last_cmd = (0.0, 0.0)
            self.v_cmd = self.w_cmd = 0.0
            return self.last_cmd

        v, w = self._dwa(est, obs["scan"])
        self.v_cmd, self.w_cmd = v, w
        self.last_cmd = (v, w)
        return self.last_cmd


def make_stack(sim) -> DynamicStack:
    return DynamicStack(sim.grid, sim.goal)
