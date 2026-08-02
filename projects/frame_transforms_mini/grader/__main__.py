"""Autograder for the Frame Transforms mini-project.

Usage (from projects/frame_transforms_mini/):
    python -m grader [--seed N] [--reference]

Scenario parameters are randomized per run (seeded for reproducibility with
--seed). --reference grades the built-in reference solution — used by CI to
prove the grader itself is sound.
"""

from __future__ import annotations

import argparse
import secrets
import sys
import traceback

import numpy as np

from grader import reference as ref


def _check_wrap_angle(mod, rng):
    fixed = [np.pi, -np.pi, 0.0, 2 * np.pi, 3 * np.pi, -5 * np.pi / 2]
    rand = list(rng.uniform(-20, 20, size=8))
    for theta in fixed + rand:
        got, want = mod.wrap_angle(theta), ref.wrap_angle(theta)
        assert abs(got - want) < 1e-9, f"wrap_angle({theta:.4f}) = {got!r}, expected {want:.6f}"


def _check_sensor_to_map(mod, rng):
    for _ in range(6):
        pts = rng.normal(scale=3.0, size=(int(rng.integers(1, 30)), 2))
        robot = tuple(rng.uniform(-5, 5, 3))
        mount = tuple(rng.uniform(-1, 1, 3))
        got = np.asarray(mod.sensor_to_map(pts, robot, mount))
        want = ref.sensor_to_map(pts, robot, mount)
        assert got.shape == want.shape, f"shape {got.shape}, expected {want.shape}"
        assert np.allclose(got, want, atol=1e-8), (
            f"points mismatch for robot_pose={tuple(round(v, 3) for v in robot)}, "
            f"mount_pose={tuple(round(v, 3) for v in mount)} "
            f"(max err {np.abs(got - want).max():.2e}) — check composition order and convention"
        )


def _check_heading_error(mod, rng):
    cases = [(np.pi - 0.05, -np.pi + 0.05), (0.0, np.pi), (-3.0, 3.0)]
    cases += [tuple(rng.uniform(-10, 10, 2)) for _ in range(8)]
    for cur, tgt in cases:
        got, want = mod.heading_error(cur, tgt), ref.heading_error(cur, tgt)
        assert abs(got - want) < 1e-9, (
            f"heading_error({cur:.3f}, {tgt:.3f}) = {got!r}, expected {want:.6f} "
            "— shortest arc, signed, wrapped"
        )


def _check_chain_poses(mod, rng):
    for _ in range(6):
        n = int(rng.integers(1, 60))
        deltas = [tuple(rng.normal(scale=0.4, size=3)) for _ in range(n)]
        got = np.array(mod.chain_poses(deltas), dtype=float)
        want = np.array(ref.chain_poses(deltas))
        assert got.shape == (3,), f"expected a 3-tuple (x, y, theta), got {got!r}"
        assert np.allclose(got[:2], want[:2], atol=1e-7), (
            f"final position {got[:2]} != expected {want[:2]} over {n} increments "
            "— increments compose in the *current* frame, not the world frame"
        )
        assert abs(ref.wrap_angle(got[2] - want[2])) < 1e-7, (
            f"final heading {got[2]:.5f} != expected {want[2]:.5f} (wrapped?)"
        )


TASKS = [
    ("wrap_angle", 20, _check_wrap_angle),
    ("sensor_to_map", 35, _check_sensor_to_map),
    ("heading_error", 20, _check_heading_error),
    ("chain_poses", 25, _check_chain_poses),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=None, help="reproduce a specific run")
    ap.add_argument("--reference", action="store_true", help="grade the reference solution")
    args = ap.parse_args()

    seed = args.seed if args.seed is not None else secrets.randbelow(10**6)
    if args.reference:
        mod = ref
    else:
        try:
            import student as mod  # noqa: PLC0415
        except ImportError:
            print("Could not import student.py — run from projects/frame_transforms_mini/")
            return 2

    total = earned = 0
    width = max(len(n) for n, _, _ in TASKS)
    print(f"Frame Transforms mini-project — seed {seed}\n")
    for name, points, check in TASKS:
        total += points
        try:
            check(mod, np.random.default_rng(seed))
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
    if not args.reference and earned == total:
        print("  Full marks — rerun with a different --seed to be sure, then move on.")
    return 0 if earned == total else 1


if __name__ == "__main__":
    sys.exit(main())
