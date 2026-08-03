"""Autograder for the mapping & SLAM mini-project.

Usage (from projects/mapping_mini/):
    python -m grader [--seed N] [--reference]
"""

from __future__ import annotations

import argparse
import secrets
import sys
import traceback

import numpy as np
import world
from world import (
    GRID_N,
    MAX_RANGE,
    RESOLUTION,
    free_pose,
    lidar_scan,
    make_world,
    scan_endpoints,
)

from grader import reference as ref


def _check_bresenham(mod, seed):
    rng = np.random.default_rng(seed)
    cells = mod.bresenham(3, 4, 3, 9)
    assert cells[0] == (3, 4) and cells[-1] == (3, 9), "must include both endpoints"
    assert len(cells) == 6, f"horizontal run should be 6 cells, got {len(cells)}"

    # All eight octants: the classic bug only handles one.
    for dr, dc in ((7, 3), (7, -3), (-7, 3), (-7, -3),
                   (3, 7), (3, -7), (-3, 7), (-3, -7)):
        r0, c0 = 40, 40
        r1, c1 = r0 + dr, c0 + dc
        out = mod.bresenham(r0, c0, r1, c1)
        assert out[0] == (r0, c0), f"octant ({dr},{dc}): first cell must be the start"
        assert out[-1] == (r1, c1), (
            f"octant ({dr},{dc}): last cell must be the end, got {out[-1]} — "
            "this octant isn't handled")
        steps = np.abs(np.diff(np.array(out), axis=0)).max(axis=1)
        assert np.all(steps == 1), f"octant ({dr},{dc}): line must be 8-connected"
        assert len(out) == max(abs(dr), abs(dc)) + 1, (
            f"octant ({dr},{dc}): expected {max(abs(dr), abs(dc)) + 1} cells, "
            f"got {len(out)}")

    for _ in range(20):
        a = rng.integers(0, GRID_N, size=4)
        out = mod.bresenham(*a)
        assert out[0] == (a[0], a[1]) and out[-1] == (a[2], a[3])


def _check_occupied_mask(mod, seed):
    lo = np.array([[0.0, 1.0], [-2.0, 5.0]])
    got = mod.occupied_mask(lo, 0.65)
    # p(0)=0.5, p(1)=0.731, p(-2)=0.119, p(5)=0.993
    assert got.tolist() == [[False, True], [False, True]], (
        f"got {got.tolist()}; log-odds must be converted to probability "
        "with the logistic before thresholding")
    assert mod.occupied_mask(np.zeros((3, 3)), 0.5).sum() == 0, (
        "p == threshold should not count as occupied")


def _check_no_phantom_ring(mod, seed):
    """Beams that hit nothing must not be recorded as hits."""
    rng = np.random.default_rng(seed)
    grid = np.zeros((GRID_N, GRID_N), dtype=bool)   # totally empty world
    grid[0, :] = grid[-1, :] = grid[:, 0] = grid[:, -1] = True
    log_odds = np.zeros((GRID_N, GRID_N))
    # Jitter the heading between sweeps: 72 rays are 0.26 m apart at 3 m, so
    # a single heading leaves untraced gaps between beams.
    for k in range(8):
        pose = np.array([6.0, 6.0, 0.3 + k * 0.011])
        scan = lidar_scan(pose, grid, rng)
        log_odds = mod.integrate_scan(log_odds, pose, scan)
    pose = np.array([6.0, 6.0, 0.3])

    occ = mod.occupied_mask(log_odds)
    # Ring of cells about MAX_RANGE from the pose, well inside the walls.
    rr, cc = np.mgrid[0:GRID_N, 0:GRID_N]
    dist = np.hypot(cc * RESOLUTION + RESOLUTION / 2 - pose[0],
                    rr * RESOLUTION + RESOLUTION / 2 - pose[1])
    ring = (np.abs(dist - MAX_RANGE) < 0.3) & (dist < 5.5)
    ring &= ~grid
    phantom = int((occ & ring).sum())
    assert phantom == 0, (
        f"{phantom} cells marked occupied on a ring at ~{MAX_RANGE} m in an "
        "EMPTY room. A max-range return means the beam hit nothing; with "
        "noisy ranges an equality test isn't enough, you need a margin.")
    near = (dist < 3.0) & ~grid
    assert (~occ[near]).all(), "open space near the robot should not be occupied"
    # Only judge cells the trace actually visited — beams fan out, so cells
    # between rays are legitimately still unknown.
    free = 1.0 / (1.0 + np.exp(-log_odds))
    touched = near & (np.abs(log_odds) > 1e-9)
    assert int(touched.sum()) > 300, (
        f"only {int(touched.sum())} cells near the robot were touched at all "
        "— the ray trace isn't marking the cells it passes through")
    assert (free[touched] < 0.4).mean() > 0.9, (
        "cells the beams passed through should end up confidently FREE")


def _check_mapping_accuracy(mod, seed):
    rng = np.random.default_rng(seed)
    grid = make_world(seed)
    log_odds = np.zeros((GRID_N, GRID_N))
    poses = [free_pose(grid, rng) for _ in range(14)]
    for p in poses:
        log_odds = mod.integrate_scan(log_odds, p, lidar_scan(p, grid, rng))

    occ = mod.occupied_mask(log_odds)
    seen = np.abs(log_odds) > 1e-9
    truth = grid & seen
    pred = occ & seen
    tp = int((truth & pred).sum())
    fp = int((~truth & pred).sum())
    fn = int((truth & ~pred).sum())
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    assert precision > 0.80, (
        f"precision {precision:.2f} — too many free cells marked occupied "
        f"({fp} false positives)")
    assert recall > 0.55, (
        f"recall {recall:.2f} — real obstacle surfaces are being missed")


def _check_kabsch(mod, seed):
    rng = np.random.default_rng(seed)
    pts = rng.uniform(-3, 3, size=(30, 2))
    th = rng.uniform(-2.5, 2.5)
    c, s = np.cos(th), np.sin(th)
    R_true = np.array([[c, -s], [s, c]])
    t_true = rng.uniform(-2, 2, size=2)
    moved = pts @ R_true.T + t_true

    R, t = mod.kabsch(pts, moved)
    assert R.shape == (2, 2) and np.asarray(t).shape == (2,), "return (R, t)"
    assert np.allclose(R @ R.T, np.eye(2), atol=1e-8), "R must be orthonormal"
    assert np.linalg.det(R) > 0, (
        f"det(R) = {np.linalg.det(R):.3f} — that's a reflection, not a "
        "rotation. Guard the SVD result.")
    assert np.allclose(R, R_true, atol=1e-6), "rotation is wrong"
    assert np.allclose(pts @ R.T + t, moved, atol=1e-6), "transform doesn't fit"

    # Nearly collinear points are where the reflection guard earns its keep.
    line = np.stack([np.linspace(-3, 3, 25), rng.normal(0, 1e-3, 25)], axis=1)
    R2, _ = mod.kabsch(line, line @ R_true.T + t_true)
    assert np.linalg.det(R2) > 0, "reflection returned for near-collinear input"


def _check_icp(mod, seed):
    rng = np.random.default_rng(seed)
    grid = make_world(seed)
    pose_a = free_pose(grid, rng)
    delta = np.array([rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3),
                      rng.uniform(-0.15, 0.15)])
    pose_b = np.array([pose_a[0] + delta[0], pose_a[1] + delta[1],
                       world.wrap(pose_a[2] + delta[2])])

    scan_a = lidar_scan(pose_a, grid, rng)
    scan_b = lidar_scan(pose_b, grid, rng)
    pts_a = scan_endpoints(pose_a, scan_a)
    pts_b = scan_endpoints(pose_b, scan_b)
    if len(pts_a) < 12 or len(pts_b) < 12:
        return  # degenerate world for this seed; nothing to assert

    # Work in the sensor frame, as a real scan matcher does. In world
    # coordinates the cloud sits ~8 m from the origin, so a 0.03 rad rotation
    # about the origin displaces points by 0.24 m — comparable to the 0.33 m
    # spacing between scan points, which is not a "small" displacement at all.
    pts_a = pts_a - pts_a.mean(axis=0)

    def _perturbed(delta):
        c, s = np.cos(delta[2]), np.sin(delta[2])
        Rp = np.array([[c, -s], [s, c]])
        return pts_a @ Rp.T + delta[:2]

    def _residual(src, est):
        est = np.asarray(est)
        assert est.shape == (3,), f"icp must return (dx, dy, dtheta), got {est.shape}"
        c, s = np.cos(est[2]), np.sin(est[2])
        R = np.array([[c, -s], [s, c]])
        return float(np.linalg.norm((src @ R.T + est[:2]) - pts_a, axis=1).mean())

    def _true_inverse(delta):
        """The (dx, dy, dth) that undoes `delta`."""
        th = -delta[2]
        c, s = np.cos(th), np.sin(th)
        R = np.array([[c, -s], [s, c]])
        return np.array([*(-(R @ delta[:2])), th])

    # (a) Small displacement, cold start: comfortably inside ICP's basin.
    small = np.array([0.08, -0.06, 0.03])
    r = _residual(_perturbed(small), mod.icp(_perturbed(small), pts_a))
    assert r < 0.04, (
        f"mean residual {r:.3f} m on a small displacement from a cold start "
        "— ICP should converge easily here")

    # (b) Larger displacement, seeded from odometry — which is how every
    # real scan matcher is run. ICP is a LOCAL optimizer: from a cold start
    # a 0.3 m offset can lock onto the wrong nearest neighbours and settle
    # in a local minimum, and no amount of iterating escapes it.
    big = np.array([0.25, -0.18, 0.09])
    odom = _true_inverse(big) + rng.normal(0, [0.04, 0.04, 0.02])
    r = _residual(_perturbed(big), mod.icp(_perturbed(big), pts_a, init=odom))
    assert r < 0.05, (
        f"mean residual {r:.3f} m even when handed an odometry prior within "
        "4 cm of the answer — check that `init` is used as the starting "
        "estimate and composed with, not overwritten by, each iteration")


def _check_icp_rejects_outliers(mod, seed):
    """Points with no true partner must not drag the fit."""
    rng = np.random.default_rng(seed)
    pts = rng.uniform(-3, 3, size=(40, 2))
    perturb = np.array([0.2, -0.15, 0.08])
    c, s = np.cos(perturb[2]), np.sin(perturb[2])
    R = np.array([[c, -s], [s, c]])
    shifted = pts @ R.T + perturb[:2]
    # A quarter of the source has no counterpart at all — geometry the
    # other scan simply never saw.
    junk = rng.uniform(6, 9, size=(12, 2))
    contaminated = np.vstack([shifted, junk])

    est = np.asarray(mod.icp(contaminated, pts))
    c2, s2 = np.cos(est[2]), np.sin(est[2])
    R2 = np.array([[c2, -s2], [s2, c2]])
    resid = np.linalg.norm((shifted @ R2.T + est[:2]) - pts, axis=1).mean()
    assert resid < 0.08, (
        f"with 23% unmatched points the fit drifted to {resid:.3f} m mean "
        "residual on the points that DID match. Reject correspondences that "
        "are too far apart before solving.")


TASKS = [
    ("bresenham, all octants", 15, _check_bresenham),
    ("occupied_mask", 5, _check_occupied_mask),
    ("no phantom max-range ring", 20, _check_no_phantom_ring),
    ("map accuracy vs truth", 15, _check_mapping_accuracy),
    ("Kabsch (no reflections)", 15, _check_kabsch),
    ("ICP convergence", 15, _check_icp),
    ("ICP outlier rejection", 15, _check_icp_rejects_outliers),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--reference", action="store_true")
    args = ap.parse_args()

    seed = args.seed if args.seed is not None else secrets.randbelow(10**6)
    if args.reference:
        mod = ref
    else:
        try:
            import student as mod  # noqa: PLC0415
        except ImportError:
            print("Could not import student.py — run from projects/mapping_mini/")
            return 2

    total = earned = 0
    width = max(len(n) for n, _, _ in TASKS)
    print(f"Mapping mini-project — seed {seed}\n")
    for name, points, check in TASKS:
        total += points
        try:
            check(mod, seed)
            earned += points
            print(f"  {name:<{width}}  {points:>3}/{points:<3}  ok")
        except NotImplementedError:
            print(f"  {name:<{width}}  {0:>3}/{points:<3}  not implemented")
        except AssertionError as e:
            print(f"  {name:<{width}}  {0:>3}/{points:<3}  FAIL: {e}")
        except Exception:
            tb = traceback.format_exc(limit=2).strip().splitlines()[-1]
            print(f"  {name:<{width}}  {0:>3}/{points:<3}  ERROR: {tb}")

    print(f"\n  TOTAL: {earned}/{total}")
    return 0 if earned == total else 1


if __name__ == "__main__":
    sys.exit(main())
