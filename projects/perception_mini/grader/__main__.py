"""Autograder for the perception mini-project.

Usage (from projects/perception_mini/):
    python -m grader [--seed N] [--reference]
"""

from __future__ import annotations

import argparse
import secrets
import sys
import time
import traceback

import numpy as np
from optics import (
    BASELINE,
    CX,
    CY,
    FX,
    FY,
    HEIGHT,
    K1,
    K2,
    SIGMA_D,
    WIDTH,
    K,
    look_at,
    synth_depth_image,
    synth_stereo,
)

from grader import reference as ref


def _to_norm(px):
    px = np.atleast_2d(np.asarray(px, dtype=float))
    return np.stack([(px[:, 0] - CX) / FX, (px[:, 1] - CY) / FY], axis=1)


def _to_px(xy):
    xy = np.atleast_2d(np.asarray(xy, dtype=float))
    return np.stack([xy[:, 0] * FX + CX, xy[:, 1] * FY + CY], axis=1)


def _check_project(mod, seed):
    rng = np.random.default_rng(seed)
    R, t = look_at([0.0, 0.0, 1.5], [5.0, 0.0, 1.5])
    on_axis = mod.project(np.array([[5.0, 0.0, 1.5]]), K, R, t)
    assert np.allclose(on_axis[0], [CX, CY], atol=1e-6), (
        f"a point on the optical axis must land on (cx, cy), got "
        f"{np.round(on_axis[0], 2)}")

    near = mod.project(np.array([[5.0, 1.0, 1.5]]), K, R, t)[0]
    far = mod.project(np.array([[10.0, 1.0, 1.5]]), K, R, t)[0]
    assert abs((near[0] - CX) - 2.0 * (far[0] - CX)) < 1e-6, (
        "offset from the principal point must scale as 1/Z")

    behind = mod.project(np.array([[-5.0, 0.0, 1.5]]), K, R, t)
    assert np.all(np.isnan(behind)), (
        "points behind the camera must be NaN — dividing by a negative Z "
        "produces a plausible-looking pixel in front of you")

    for _ in range(5):
        eye = rng.uniform(-3, 3, 3)
        tgt = eye + np.array([4.0, 0.0, 0.0]) + rng.uniform(-1, 1, 3) * [1, 1, 0.2]
        Rr, tt = look_at(eye, tgt)
        p = mod.project(np.atleast_2d(tgt), K, Rr, tt)
        assert np.allclose(p[0], [CX, CY], atol=1e-6), (
            "the look-at target must always project to the principal point")


def _check_unproject(mod, seed):
    rays = np.asarray(mod.unproject(np.array([[CX, CY], [500.0, 100.0], [0.0, 0.0]]), K))
    assert rays.shape == (3, 3), f"unproject must return (N,3), got {rays.shape}"
    assert np.allclose(np.linalg.norm(rays, axis=1), 1.0, atol=1e-9), (
        "ray directions must be unit length")
    assert np.allclose(rays[0], [0.0, 0.0, 1.0], atol=1e-9), (
        "the principal point unprojects to the optical axis")

    rng = np.random.default_rng(seed)
    R, t = look_at([0.0, 0.0, 1.5], [5.0, 0.0, 1.5])
    px = np.stack([rng.uniform(20, WIDTH - 20, 50),
                   rng.uniform(20, HEIGHT - 20, 50)], axis=1)
    dirs = np.asarray(mod.unproject(px, K))
    for s in (0.4, 3.0, 30.0):
        world = (R.T @ (dirs * s - t).T).T
        back = mod.project(world, K, R, t)
        assert np.allclose(back, px, atol=1e-6), (
            f"round trip failed at depth {s:.1f} — every point along a ray must "
            f"project back to its own pixel")


def _check_distortion(mod, seed):
    rng = np.random.default_rng(seed)
    assert np.allclose(mod.distort(np.array([[0.0, 0.0]]), K1, K2),
                       [[0.0, 0.0]], atol=1e-12), "the optical axis is undistorted"

    centre = np.array([[330.0, 245.0]])
    corner = np.array([[630.0, 470.0]])
    dc = np.linalg.norm(_to_px(mod.distort(_to_norm(centre), K1, K2)) - centre)
    de = np.linalg.norm(_to_px(mod.distort(_to_norm(corner), K1, K2)) - corner)
    assert dc < 0.5, f"near the centre the shift should be sub-pixel, got {dc:.2f}"
    assert de > 15.0, (
        f"at the corner the shift should be tens of pixels, got {de:.2f} — check "
        f"the factor uses r^2, not r")

    px = np.stack([rng.uniform(0, WIDTH, 400), rng.uniform(0, HEIGHT, 400)], axis=1)
    ideal = _to_norm(px)
    rt = mod.undistort(mod.distort(ideal, K1, K2), K1, K2)
    err = np.linalg.norm(_to_px(rt) - _to_px(ideal), axis=1)
    assert err.max() < 0.01, (
        f"distort/undistort round trip is off by up to {err.max():.4f} px — the "
        f"iteration must recompute r2 from the current estimate each pass")
    same = np.linalg.norm(_to_px(mod.undistort(ideal, K1, K2)) - _to_px(ideal), axis=1)
    assert same.max() > 5.0, "undistort appears to return its input unchanged"


def _check_triangulate(mod, seed):
    rng = np.random.default_rng(seed)
    pts = np.stack([rng.uniform(-1.5, 1.5, 40), rng.uniform(-1.0, 1.0, 40),
                    rng.uniform(1.5, 15.0, 40)], axis=1)
    L, R = synth_stereo(pts)
    got = np.asarray(mod.triangulate(L, R))
    assert got.shape == (40, 3), f"must return (N,3), got {got.shape}"
    assert np.allclose(got, pts, atol=1e-6), (
        "triangulation does not recover the input points")

    bad = mod.triangulate(np.array([[320.0, 240.0], [300.0, 240.0]]),
                          np.array([[320.0, 240.0], [320.0, 240.0]]))
    assert np.all(np.isnan(bad)), (
        "disparity at or below MIN_DISPARITY must be NaN, not an enormous "
        "finite depth")


def _check_depth_sigma(mod, seed):
    z = np.array([2.0, 5.0, 10.0, 20.0])
    s = np.asarray(mod.depth_sigma(z))
    expect = z ** 2 * SIGMA_D / (FX * BASELINE)
    assert np.allclose(s, expect, rtol=1e-9), (
        f"sigma_Z should be Z^2*sigma_d/(fx*B); got {np.round(s, 4)}")
    assert abs(s[3] / s[1] - 16.0) < 1e-6, (
        f"doubling the range twice must multiply sigma by 16, got {s[3] / s[1]:.2f}")


def _check_depth_to_cloud(mod, seed):
    rng = np.random.default_rng(seed)
    depth = synth_depth_image(rng)
    cloud = np.asarray(mod.depth_to_cloud(depth, K))
    assert cloud.ndim == 2 and cloud.shape[1] == 3, (
        f"depth_to_cloud must return (M,3), got {cloud.shape}")
    n_valid = int((depth > 0).sum())
    assert len(cloud) == n_valid, (
        f"expected {n_valid} points (one per valid pixel) but got {len(cloud)} — "
        f"zero-depth pixels are sensor dropouts and must be dropped, not "
        f"back-projected to the origin")
    assert np.all(cloud[:, 2] > 0), "every returned point must have positive depth"
    assert not np.any(np.all(np.abs(cloud) < 1e-9, axis=1)), (
        "there is a point at the origin — a dropout was back-projected")

    probe = np.zeros((5, 7))
    probe[2, 3] = 4.0
    K_probe = np.array([[FX, 0.0, 3.0], [0.0, FY, 2.0], [0.0, 0.0, 1.0]])
    one = np.asarray(mod.depth_to_cloud(probe, K_probe))
    assert one.shape == (1, 3) and np.allclose(one[0], [0.0, 0.0, 4.0], atol=1e-9), (
        f"a pixel at the principal point with depth 4 must map to (0,0,4), got "
        f"{np.round(one[0], 4)}")

    strided = np.asarray(mod.depth_to_cloud(depth, K, stride=2))
    assert len(strided) < len(cloud), "stride must subsample the image"

    big = np.full((HEIGHT, WIDTH), 5.0)
    t0 = time.perf_counter()
    mod.depth_to_cloud(big, K)
    dt = (time.perf_counter() - t0) * 1000.0
    assert dt < 300.0, (
        f"took {dt:.0f} ms for a single 640x480 frame — that is a Python loop "
        f"over pixels; vectorize it")


TASKS = [
    ("project (incl. behind camera)", 15, _check_project),
    ("unproject + ray round trip", 15, _check_unproject),
    ("distortion round trip", 20, _check_distortion),
    ("stereo triangulation", 20, _check_triangulate),
    ("depth error model", 10, _check_depth_sigma),
    ("depth image -> point cloud", 20, _check_depth_to_cloud),
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
            print("Could not import student.py — run from projects/perception_mini/")
            return 2

    total = earned = 0
    width = max(len(n) for n, _, _ in TASKS)
    print(f"Perception mini-project — seed {seed}\n")
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
