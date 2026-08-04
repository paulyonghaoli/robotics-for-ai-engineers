"""Ablation harness for the v4 SLAM localizer, isolated from its controller.

v4's first end-to-end run scored 0/4 with 3-13 m of localization error.
That could have been the scan matcher, or it could have been the feedback
collapse the matcher merely starts: bad pose -> bad plan -> strange motion
-> worse pose. An end-to-end number cannot tell you which.

So this cuts the loop. The reference controller drives using the TRUE
pose, and the localizer runs alongside as a pure observer. Whatever error
it accumulates is its own. Every design decision in slam_stack.py was
made against the table this prints, and the numbers quoted in
docs/capstone-log.md notes 9-13 come from here.

    python slam_ablation.py                     # all modes
    python slam_ablation.py odom lf lf+bias     # selected modes

Modes, in the order they were tried:

    odom   dead reckoning only, no map lookups at all
    raw    match every step, scored on occupancy log-odds
    clip   as raw, but clamping the commanded twist like the sim does
    occ    as clip, but scoring only occupied evidence (no free penalty)
    kf     match at keyframes instead of every step
    lf     keyframes, likelihood field, odometry prior, no clipped endpoints
    lc     as lf, plus loop closure and a pose graph (v5's back end)

Suffix any mode with '+bias' to replace perfect command playback with
wheel encoders: a constant scale error on translation and a constant
drift on rotation. Unlike white noise, that does not average out, and it
is what separates "scan matching helps" from "scan matching is bounded
by what odometry hands it".

Suffix with '+tour' to drive to the goal AND BACK. The capstone task is a
single traverse, and a single traverse never revisits a place: measured
over the six seeds below, the number of trajectory pairs more than six
seconds apart and within 1.5 m is exactly ZERO. There is no loop to
close, so loop closure is worth nothing on it, however good the back end.
A there-and-back tour is what a SLAM benchmark actually drives, and it is
the only condition under which 'lc' can be judged at all.
"""

import sys
from pathlib import Path

import numpy as np

# The reference stacks live in solutions/ so they don't sit next to the
# assignment. Putting that directory on the path keeps every command that
# names one ("--stack pf_stack") working exactly as before.
_SOLUTIONS = Path(__file__).resolve().parent / "solutions"
if str(_SOLUTIONS) not in sys.path:
    sys.path.insert(0, str(_SOLUTIONS))

import reference_stack  # noqa: E402
from pf_stack import distance_field  # noqa: E402
from posegraph import PoseGraph, scan_points  # noqa: E402
from sim import (  # noqa: E402
    DT,
    GOAL_TOLERANCE,
    GRID_N,
    MAX_RANGE,
    N_RAYS,
    RESOLUTION,
    Simulator,
)

from robotics_ai.geometry import wrap_angle  # noqa: E402
from robotics_ai.mapping import OccupancyGridMap  # noqa: E402

MISS = 0.25
BEARINGS = np.arange(N_RAYS) * (2 * np.pi / N_RAYS)
V_MAX, W_MAX = 1.2, 2.0


def predict(pose, cmd, clip):
    v, w = cmd
    if clip:
        v, w = float(np.clip(v, 0.0, V_MAX)), float(np.clip(w, -W_MAX, W_MAX))
    x, y, th = pose
    if abs(w) < 1e-9:
        return np.array([x + v * np.cos(th) * DT, y + v * np.sin(th) * DT, th])
    r = v / w
    return np.array([x + r * (np.sin(th + w * DT) - np.sin(th)),
                     y - r * (np.cos(th + w * DT) - np.cos(th)),
                     wrap_angle(th + w * DT)])


def match(guess, scan, gmap, occupied_only):
    hit = scan < MAX_RANGE - MISS
    if hit.sum() < 8:
        return guess
    r, b = scan[hit], BEARINGS[hit]
    lo = gmap.log_odds
    score_map = np.clip(lo, 0.0, None) if occupied_only else lo
    pose = guess
    for dxy, dth in ((0.20, 0.09), (0.06, 0.03)):
        cand = np.array([[pose[0] + a, pose[1] + c, wrap_angle(pose[2] + e)]
                         for a in (-dxy, 0.0, dxy) for c in (-dxy, 0.0, dxy)
                         for e in (-dth, 0.0, dth)])
        th = cand[:, 2][:, None] + b[None, :]
        ex = cand[:, 0][:, None] + r[None, :] * np.cos(th)
        ey = cand[:, 1][:, None] + r[None, :] * np.sin(th)
        cx = np.clip((ex / RESOLUTION).astype(int), 0, GRID_N - 1)
        cy = np.clip((ey / RESOLUTION).astype(int), 0, GRID_N - 1)
        pose = cand[int(np.argmax(score_map[cy, cx].sum(axis=1)))]
    return pose


def integrate(gmap, pose, scan):
    for i in range(N_RAYS):
        r = scan[i]
        is_hit = r < MAX_RANGE - MISS
        reach = r if is_hit else MAX_RANGE
        bg = pose[2] + BEARINGS[i]
        gmap.update_ray(pose[:2], pose[:2] + reach * np.array([np.cos(bg), np.sin(bg)]),
                        hit=is_hit)


def match_kf(guess, scan, gmap, dxy, dth):
    """Keyframe matcher: a window sized to plausible accumulated drift,
    sampled finely, scored on raw log-odds so free space still penalizes."""
    hit = scan < MAX_RANGE - MISS
    if hit.sum() < 8:
        return guess
    r, b = scan[hit], BEARINGS[hit]
    lo = gmap.log_odds
    pose = guess
    for scale in (1.0, 0.34):
        offs = np.linspace(-dxy * scale, dxy * scale, 5)
        ths = np.linspace(-dth * scale, dth * scale, 5)
        cand = np.array([[pose[0] + a, pose[1] + c, wrap_angle(pose[2] + e)]
                         for a in offs for c in offs for e in ths])
        th = cand[:, 2][:, None] + b[None, :]
        ex = cand[:, 0][:, None] + r[None, :] * np.cos(th)
        ey = cand[:, 1][:, None] + r[None, :] * np.sin(th)
        cx = np.clip((ex / RESOLUTION).astype(int), 0, GRID_N - 1)
        cy = np.clip((ey / RESOLUTION).astype(int), 0, GRID_N - 1)
        pose = cand[int(np.argmax(lo[cy, cx].sum(axis=1)))]
    return pose


def match_lf(guess, scan, field, dxy, dth, sigma=0.25, gate=1.0,
             prior_xy=0.06, prior_th=0.04):
    """Keyframe matching against a likelihood field built from the map so
    far — the same construction v1 used against the *known* map.

    Unlike occupancy scoring this has no plateau: unexplored space is far
    from every mapped surface, so it scores badly rather than scoring zero.
    Beams landing beyond `gate` are newly-seen geometry and are dropped,
    which is ICP's outlier rejection under another name.

    The match maximizes a *posterior*, not the scan likelihood alone: the
    odometry prior penalizes displacement from the incoming guess. Without
    it, a scan that gates out entirely leaves a flat score whose argmax is
    whichever candidate happens to come first — so an uninformative match
    silently teleports the robot instead of leaving it where it was.
    """
    hit = scan < MAX_RANGE - MISS
    if hit.sum() < 8:
        return guess, 0.0
    r, b = scan[hit], BEARINGS[hit]
    pose = guess
    for scale in (1.0, 0.34):
        offs = np.linspace(-dxy * scale, dxy * scale, 5)
        ths = np.linspace(-dth * scale, dth * scale, 5)
        cand = np.array([[pose[0] + a, pose[1] + c, wrap_angle(pose[2] + e)]
                         for a in offs for c in offs for e in ths])
        th = cand[:, 2][:, None] + b[None, :]
        ex = cand[:, 0][:, None] + r[None, :] * np.cos(th)
        ey = cand[:, 1][:, None] + r[None, :] * np.sin(th)
        ix = (ex / RESOLUTION).astype(int)
        iy = (ey / RESOLUTION).astype(int)
        # An endpoint outside the grid has NO evidence. It must not be clipped
        # onto the boundary — the boundary ring is solid wall, so clipping
        # scores every escaping beam as a perfect match and pays the matcher
        # to walk out of the world.
        inside = (ix >= 0) & (ix < GRID_N) & (iy >= 0) & (iy < GRID_N)
        d = field[np.clip(iy, 0, GRID_N - 1), np.clip(ix, 0, GRID_N - 1)]
        lik = np.where(inside & (d < gate),
                       np.exp(-(d ** 2) / (2 * sigma ** 2)), 0.0).sum(axis=1)
        dx, dy = cand[:, 0] - guess[0], cand[:, 1] - guess[1]
        dt = np.array([wrap_angle(t - guess[2]) for t in cand[:, 2]])
        prior = 0.5 * ((dx ** 2 + dy ** 2) / prior_xy ** 2 + dt ** 2 / prior_th ** 2)
        best = int(np.argmax(lik - prior))
        pose = cand[best]
    return pose, float(lik[best] / len(r))     # fraction of beams that agreed


class TourDriver:
    """The reference controller, driving to the goal and back to the start.

    Everything here uses the TRUE pose, like the rest of this harness: the
    driver is scaffolding, and the localizer under test only observes.
    """

    def __init__(self, sim):
        self.sim = sim
        # sim.start carries a heading; a planner goal is a position.
        self.waypoints = [np.asarray(sim.goal, dtype=float)[:2],
                          np.asarray(sim.start, dtype=float)[:2]]
        self.k = 0
        self.stack = reference_stack.ReferenceStack(sim.grid, self.waypoints[0])
        self.finished = False

    def step(self, obs):
        if self.finished:
            return 0.0, 0.0
        reached = np.hypot(*(self.sim.pose[:2] - self.waypoints[self.k]))
        if reached < GOAL_TOLERANCE * 0.8:
            self.k += 1
            if self.k >= len(self.waypoints):
                self.finished = True
                return 0.0, 0.0
            self.stack = reference_stack.ReferenceStack(
                self.sim.grid, self.waypoints[self.k])
        return self.stack.step(obs)


def rebuild_map(graph):
    """Re-integrate every keyframe scan at its OPTIMIZED pose.

    The map was carved through the drift. Correcting the trajectory without
    redrawing the map would leave the incremental matcher matching against
    the very error the closure just removed.
    """
    gm = OccupancyGridMap((GRID_N, GRID_N), RESOLUTION)
    for pose, raw in zip(graph.poses, graph.raws, strict=True):
        if raw is not None:
            integrate(gm, pose, raw)
    return gm


def run(seed, mode, kf_d=0.35, kf_th=0.25, win=0.10, win_th=0.05):
    """mode: 'odom' | 'raw' | 'clip' | 'occ' | 'kf' | 'lf' | 'lc',
    optionally suffixed '+bias' and/or '+tour'.

    '+bias' models wheel encoders instead of perfect command playback: a
    constant scale error on translation and a constant drift on rotation,
    fixed per episode. This is what real odometry looks like, and unlike
    white noise it does not average out.

    '+tour' drives to the goal and back, so the trajectory revisits places.
    """
    bias = "+bias" in mode
    tour = "+tour" in mode
    mode = mode.replace("+bias", "").replace("+tour", "")
    brng = np.random.default_rng(seed + 555)
    v_scale = 1.0 + (brng.normal(0, 0.05) if bias else 0.0)
    w_drift = brng.normal(0, 0.04) if bias else 0.0

    def odo(pose, cmd):
        v, w = cmd
        return predict(pose, (v * v_scale, w + w_drift), clip=False)

    sim = Simulator(seed, max_steps=1400 if tour else 600)
    obs = sim.reset()
    driver = (TourDriver(sim) if tour            # drives on the TRUE map+pose
              else reference_stack.make_stack(sim))
    gmap = OccupancyGridMap((GRID_N, GRID_N), RESOLUTION)
    est = obs["pose_meas"].copy()
    integrate(gmap, est, obs["scan"])
    cmd, errs = (0.0, 0.0), []
    since = est.copy()                            # pose at the last keyframe
    grow = 1.0                                    # search-window growth on lost lock
    graph = PoseGraph()
    if mode == "lc":
        graph.add_keyframe(est, scan_points(obs["scan"], BEARINGS, MAX_RANGE, MISS),
                           obs["scan"])

    for _ in range(1400 if tour else 600):
        obs, done = sim.step(*cmd)
        if mode == "odom":
            est = odo(est, cmd)
            integrate(gmap, est, obs["scan"])
        elif mode == "lc":
            est = odo(est, cmd)
            moved = np.hypot(*(est[:2] - since[:2]))
            turned = abs(wrap_angle(est[2] - since[2]))
            if moved > kf_d or turned > kf_th:
                occ = gmap.occupied_mask(0.65)
                if occ.sum() > 30:
                    est, q = match_lf(est, obs["scan"],
                                      distance_field(occ) * RESOLUTION,
                                      win * grow, win_th * grow)
                    grow = 1.0 if q > 0.55 else min(grow * 1.7, 12.0)
                k = graph.add_keyframe(
                    est, scan_points(obs["scan"], BEARINGS, MAX_RANGE, MISS),
                    obs["scan"])
                found = graph.find_loop(k)
                if found is not None:
                    j, z, _q = found
                    graph.add_loop(j, k, z)
                    graph.optimize()
                    est = graph.poses[-1].copy()
                    gmap = rebuild_map(graph)
                else:
                    integrate(gmap, est, obs["scan"])
                since = est.copy()
        elif mode in ("kf", "lf"):
            est = odo(est, cmd)
            moved = np.hypot(*(est[:2] - since[:2]))
            turned = abs(wrap_angle(est[2] - since[2]))
            if moved > kf_d or turned > kf_th:    # only then look at the map
                if mode == "lf":
                    occ = gmap.occupied_mask(0.65)
                    if occ.sum() > 30:            # an empty map informs nothing
                        est, q = match_lf(est, obs["scan"],
                                          distance_field(occ) * RESOLUTION,
                                          win * grow, win_th * grow)
                        # A match that convinced few beams means the window
                        # no longer contains the truth: widen it until it does.
                        grow = 1.0 if q > 0.55 else min(grow * 1.7, 12.0)
                else:
                    est = match_kf(est, obs["scan"], gmap, win, win_th)
                integrate(gmap, est, obs["scan"])
                since = est.copy()
        else:
            est = predict(est, cmd, clip=(mode != "raw"))
            est = match(est, obs["scan"], gmap, occupied_only=(mode == "occ"))
            integrate(gmap, est, obs["scan"])
        errs.append(np.hypot(*(est[:2] - sim.pose[:2])))
        cmd = driver.step(obs)                    # true-pose controller drives
        if tour:
            # The simulator ends an episode at the goal, which is the right
            # contract for the capstone and the wrong one for a tour. Here
            # the goal is a waypoint, so the driver decides when it is over.
            if driver.finished or sim.k >= sim.max_steps:
                break
        elif done:
            break
    return (float(np.sqrt(np.mean(np.square(errs)))), float(errs[-1]),
            graph.loops)


if __name__ == "__main__":
    seeds = [0, 17, 34, 51, 68, 85]
    modes = sys.argv[1:] or ["odom", "raw", "clip", "occ", "kf"]
    print(f"{'mode':<12} {'RMSE (m)':>9} {'final (m)':>10} {'loops':>6}   per-seed RMSE")
    for mode in modes:
        rs = [run(s, mode) for s in seeds]
        rmse = np.mean([r[0] for r in rs])
        fin = np.mean([r[1] for r in rs])
        loops = sum(r[2] for r in rs)
        print(f"{mode:<12} {rmse:>9.2f} {fin:>10.2f} {loops:>6}   "
              + "  ".join(f"{r[0]:.2f}" for r in rs))
    sys.exit(0)
