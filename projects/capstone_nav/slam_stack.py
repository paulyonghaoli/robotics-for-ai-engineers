"""Capstone v4: SLAM — the map AND the pose are both unknown.

v1 knew the map and localized in it. v2 knew its pose and mapped with it.
This stack has neither. It reads the pose sensor exactly once, to define
where the map's origin is, and then never again: after step 0 there is no
absolute position information of any kind.

Navigation is inherited unchanged from v2 — the optimistic planning, the
reduced inflation, the replan hysteresis are all still the right answers
and none of them are what makes this hard. v4 replaces exactly one thing:
`obs["pose_meas"]` becomes an estimate the stack has to earn.

The localizer is keyframe scan matching against a likelihood field built
from the map so far — the core of what slam_toolbox and gmapping do:

    dead-reckon from the commanded twist, every step
    every 0.20 m / 0.12 rad, correct the pose against the map so far
    every 0.35 m / 0.25 rad, integrate the scan at the corrected pose
    plan on the map, drive, repeat

Measured over 24 episodes: success 0.750, collision-free 0.792, path
ratio 0.982, p95 step latency 4.3 ms, mean localization RMSE 0.387 m.
v2 — the same navigation, handed a pose sensor — scores 1.000. Giving up
the pose sensor costs a quarter of the episodes, and the reason is exactly
that 0.39 m of drift against a 0.5 m goal tolerance: a quarter of runs
park just outside it, believing they arrived. That gap does not close by
tuning. See "known limitation" below.

Six things were measured rather than assumed, each load-bearing. The
long-form versions are docs/capstone-log.md notes 9-13.

  * Matching every step is far WORSE than not matching at all (6-29 m
    error vs 0.5 m for plain odometry). 36 beams on a 0.2 m grid is too
    little evidence to correct pose at 10 Hz; you integrate noise into the
    pose ten times a second and each bad match corrupts the map you match
    against next. Keyframes accumulate enough baseline to be well-posed.

  * Correcting the pose and rewriting the map are separate decisions and
    need separate thresholds. Matching often keeps drift small; mapping
    often re-carves the map at every slightly-wrong pose and blurs the
    geometry the matcher depends on. Splitting them: 0.50 -> 0.75 success.

  * The match maximizes a POSTERIOR, not the scan likelihood. Without the
    odometry prior, a scan carrying no information leaves a flat score
    whose argmax is whichever candidate came first — an uninformative
    match silently teleports the robot rather than leaving it alone.

  * Endpoints outside the grid are dropped, never clipped. The world's
    boundary is solid wall, so clipping out-of-range endpoints onto it
    scores every escaping beam as a *perfect* match and pays the matcher
    to walk out of the world. This one held match confidence at 0.95
    while true error grew to 14 m.

  * Scoring on occupancy directly does not work; the free-space penalty
    is the restoring force. A likelihood field is better still because
    unexplored space is far from every mapped surface, so it scores badly
    rather than scoring zero — there is no plateau to slide along. The
    field is sampled bilinearly: nearest-cell quantizes every match to
    half a cell, and those errors random-walk into ~0.8 m over an episode.

  * Keyframes trigger on elapsed time as well as motion. A purely
    motion-triggered keyframe deadlocks a stopped robot — zero command
    means zero *predicted* motion, so no keyframe fires, so the estimate
    can never be corrected, so it never learns it stopped in the wrong
    place. Two seeds sat frozen for 300 steps believing they had arrived.

Known limitation, measured: under a *systematic* odometry bias (wheel
scale error, gyro drift) this degrades to ~2.3 m and does not recover,
versus 3.3 m for dead reckoning alone — scan matching bounds drift it
cannot remove. That is not a tuning failure. A constant bias is invisible
to incremental matching because correcting it means recognizing a place
you mapped before you drifted: loop closure and a pose graph (lesson
4.4), which this stack does not have. That is what v5 would be.
"""

from __future__ import annotations

import numpy as np
from mapping_stack import MISS_MARGIN, OCC_THRESHOLD, MappingStack
from sim import GRID_N, MAX_RANGE, RESOLUTION

from robotics_ai.geometry import wrap_angle

DT = 0.1
V_MAX, W_MAX = 1.2, 2.0          # the simulator clips commands; so must we

MATCH_D, MATCH_TH = 0.20, 0.12           # motion between pose corrections
MAP_D, MAP_TH = 0.35, 0.25               # motion between map updates
WINDOW_XY, WINDOW_TH = 0.10, 0.05        # search half-width at a keyframe
PRIOR_XY, PRIOR_TH = 0.06, 0.04          # odometry prior (metres, radians)
LIK_SIGMA = 0.25                         # likelihood-field sharpness (m)
MATCH_GATE = 1.0                         # beams beyond this are new geometry
MIN_MATCH_BEAMS = 8
IDLE_MATCH = 20                          # force a match after this many idle steps
MIN_MAP_CELLS = 30                       # an empty map informs nothing
LOCK_QUALITY = 0.55                      # below this, widen the search
MAX_GROWTH = 12.0


def truncated_distance_field(occupied: np.ndarray, max_cells: int) -> np.ndarray:
    """Chamfer distance (in cells) to the nearest obstacle *surface*, capped.

    Truncated deliberately: the matcher gates beams at MATCH_GATE, so any
    distance past that is indistinguishable from "far" and computing it
    exactly is wasted. Capping turns the transform into a fixed number of
    vectorized dilations instead of the two sequential sweeps v1 used,
    which is what keeps the keyframe step inside the latency budget.

    Surface seeding (occupied cells with a free neighbour) rather than all
    occupied cells is v1's lesson: seed the interiors too and a pose whose
    endpoints land deep inside a wall scores as well as the truth.
    """
    free = ~occupied
    boundary = occupied & (
        np.roll(free, 1, 0) | np.roll(free, -1, 0)
        | np.roll(free, 1, 1) | np.roll(free, -1, 1)
    )
    big = float(max_cells + 1)
    d = np.where(boundary, 0.0, big)
    diag = np.sqrt(2.0)
    for _ in range(max_cells):
        best = d
        for axis in (0, 1):
            for shift in (1, -1):
                nb = np.roll(d, shift, axis).copy()
                idx = [slice(None), slice(None)]
                idx[axis] = 0 if shift == 1 else -1
                nb[tuple(idx)] = big          # np.roll wraps; the edge has no neighbour
                best = np.minimum(best, nb + 1.0)
        for sy in (1, -1):
            for sx in (1, -1):
                nb = np.roll(np.roll(d, sy, 0), sx, 1).copy()
                nb[0 if sy == 1 else -1, :] = big
                nb[:, 0 if sx == 1 else -1] = big
                best = np.minimum(best, nb + diag)
        d = np.minimum(d, best)
    return np.minimum(d, big)


def sample_field(field: np.ndarray, ex: np.ndarray, ey: np.ndarray):
    """Bilinearly sample the distance field at continuous world points.

    Returns (distance, inside). Points outside the grid report inside=False
    and MUST be dropped by the caller rather than clamped: the world's
    boundary is solid wall, so clamping scores every escaping beam as a
    perfect match and pays the matcher to leave the world.
    """
    fx = ex / RESOLUTION - 0.5          # continuous coords in cell-centre space
    fy = ey / RESOLUTION - 0.5
    x0 = np.floor(fx).astype(int)
    y0 = np.floor(fy).astype(int)
    inside = (x0 >= 0) & (x0 + 1 < GRID_N) & (y0 >= 0) & (y0 + 1 < GRID_N)
    xc = np.clip(x0, 0, GRID_N - 2)
    yc = np.clip(y0, 0, GRID_N - 2)
    wx = np.clip(fx - xc, 0.0, 1.0)
    wy = np.clip(fy - yc, 0.0, 1.0)
    top = field[yc, xc] * (1 - wx) + field[yc, xc + 1] * wx
    bot = field[yc + 1, xc] * (1 - wx) + field[yc + 1, xc + 1] * wx
    return top * (1 - wy) + bot * wy, inside


class SlamStack(MappingStack):
    # An estimated pose spends part of the goal tolerance on its own error,
    # so v4 drives closer to the believed goal than v2 needs to.
    GOAL_STOP_FRACTION = 0.5

    def __init__(self, goal: np.ndarray) -> None:
        super().__init__(goal)
        self.pose: np.ndarray | None = None
        self.last_cmd = (0.0, 0.0)
        self.keyframe_pose: np.ndarray | None = None
        self.matched_pose: np.ndarray | None = None
        self.growth = 1.0
        self.match_quality = 1.0
        self.steps_since_match = 0

    # ---------------- odometry ----------------

    def _dead_reckon(self, pose: np.ndarray) -> np.ndarray:
        v, w = self.last_cmd
        v = float(np.clip(v, 0.0, V_MAX))
        w = float(np.clip(w, -W_MAX, W_MAX))
        x, y, th = pose
        if abs(w) < 1e-9:
            return np.array([x + v * np.cos(th) * DT, y + v * np.sin(th) * DT, th])
        r = v / w
        return np.array([
            x + r * (np.sin(th + w * DT) - np.sin(th)),
            y - r * (np.cos(th + w * DT) - np.cos(th)),
            wrap_angle(th + w * DT),
        ])

    # ---------------- scan matching ----------------

    def _match(self, guess: np.ndarray, scan: np.ndarray,
               field: np.ndarray) -> tuple[np.ndarray, float]:
        hit = scan < MAX_RANGE - MISS_MARGIN
        if hit.sum() < MIN_MATCH_BEAMS:
            return guess, 0.0
        r = scan[hit]
        b = self.bearing_offsets[hit]
        span_xy = WINDOW_XY * self.growth
        span_th = WINDOW_TH * self.growth

        pose, quality = guess, 0.0
        for scale in (1.0, 0.34):            # coarse pass, then refine
            offs = np.linspace(-span_xy * scale, span_xy * scale, 5)
            ths = np.linspace(-span_th * scale, span_th * scale, 5)
            cand = np.array([[pose[0] + a, pose[1] + c, wrap_angle(pose[2] + e)]
                             for a in offs for c in offs for e in ths])
            th = cand[:, 2][:, None] + b[None, :]
            ex = cand[:, 0][:, None] + r[None, :] * np.cos(th)
            ey = cand[:, 1][:, None] + r[None, :] * np.sin(th)
            # Bilinear, not nearest-cell. Sampling the field at cell centres
            # quantizes every match to ~half a cell (0.1 m); those errors
            # random-walk over the ~100 matches in an episode into the
            # 0.6-1.0 m drift that was losing episodes at the goal.
            d, inside = sample_field(field, ex, ey)
            per_beam = np.where(inside & (d < MATCH_GATE),
                                np.exp(-(d ** 2) / (2 * LIK_SIGMA ** 2)), 0.0)
            lik = per_beam.sum(axis=1)
            dx, dy = cand[:, 0] - guess[0], cand[:, 1] - guess[1]
            dt = np.array([wrap_angle(t - guess[2]) for t in cand[:, 2]])
            prior = 0.5 * ((dx ** 2 + dy ** 2) / PRIOR_XY ** 2
                           + dt ** 2 / PRIOR_TH ** 2)
            best = int(np.argmax(lik - prior))
            pose = cand[best]
            quality = float(lik[best] / len(r))
        return pose, quality

    def _localize(self, scan: np.ndarray) -> None:
        """Dead-reckon every step; consult the map only at keyframes."""
        self.pose = self._dead_reckon(self.pose)

        # Correcting the pose and rewriting the map are separate decisions.
        # Matching often keeps drift small; integrating often re-carves the
        # map at every slightly-wrong pose and blurs the very geometry the
        # matcher needs. They get their own thresholds.
        moved = float(np.hypot(*(self.pose[:2] - self.matched_pose[:2])))
        turned = abs(wrap_angle(self.pose[2] - self.matched_pose[2]))
        self.steps_since_match += 1
        # Motion OR elapsed time. A purely motion-triggered keyframe deadlocks
        # a stopped robot: zero command means zero *predicted* motion, so no
        # keyframe fires, so the estimate can never be corrected, so it never
        # learns it stopped in the wrong place. Seeds 0 and 68 each sat frozen
        # for 300 steps that way, believing they had arrived.
        if moved >= MATCH_D or turned >= MATCH_TH or self.steps_since_match >= IDLE_MATCH:
            occupied = self.map.occupied_mask(OCC_THRESHOLD)
            if occupied.sum() >= MIN_MAP_CELLS:
                cells = int(np.ceil(MATCH_GATE / RESOLUTION)) + 1
                field = truncated_distance_field(occupied, cells) * RESOLUTION
                self.pose, self.match_quality = self._match(self.pose, scan, field)
                # A match few beams agreed with means the window no longer
                # contains the truth. Widen it until one does.
                self.growth = (1.0 if self.match_quality > LOCK_QUALITY
                               else min(self.growth * 1.7, MAX_GROWTH))
            self.matched_pose = self.pose.copy()
            self.steps_since_match = 0

        moved = float(np.hypot(*(self.pose[:2] - self.keyframe_pose[:2])))
        turned = abs(wrap_angle(self.pose[2] - self.keyframe_pose[2]))
        if moved >= MAP_D or turned >= MAP_TH:
            self._integrate_scan(self.pose, scan)
            self.keyframe_pose = self.pose.copy()

    # ---------------- the loop ----------------

    def step(self, obs: dict) -> tuple[float, float]:
        if self.pose is None:
            # The only use of the pose sensor: define the map frame. Lesson
            # 4.3 — absolute pose is unobservable anyway, so this is a choice
            # of gauge, not information the localizer gets to keep using.
            self.pose = obs["pose_meas"].copy()
            self.keyframe_pose = self.pose.copy()
            self.matched_pose = self.pose.copy()
            self._integrate_scan(self.pose, obs["scan"])
        else:
            self._localize(obs["scan"])

        self.last_estimate = self.pose.copy()
        # v2's navigation, verbatim, driven by the estimate instead of truth.
        self.last_cmd = self._navigate(self.pose, obs)
        return self.last_cmd


def make_stack(sim) -> SlamStack:
    # No sim.grid, and no pose sensor after step 0.
    return SlamStack(sim.goal)
