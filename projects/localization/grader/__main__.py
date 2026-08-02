"""Autograder for the localization project.

Usage (from projects/localization/):
    python -m grader [--seed N] [--reference]
"""

from __future__ import annotations

import argparse
import secrets
import sys
import traceback

import numpy as np
import world
from world import wrap

from grader import reference as ref


def _check_motion_update(mod, rng_seed):
    rng = np.random.default_rng(rng_seed)
    particles = np.tile([5.0, 5.0, 0.0], (4000, 1))
    out = mod.motion_update(particles.copy(), 1.0, 0.0, world.DT, rng)
    assert out.shape == particles.shape, f"shape {out.shape}, expected {particles.shape}"
    adv = out[:, 0] - 5.0
    assert abs(adv.mean() - 1.0 * world.DT) < 0.02, (
        f"mean forward advance {adv.mean():.3f}, expected ~{world.DT:.3f} (v*dt)"
    )
    spread = adv.std()
    expected = world.ODOM_V_SIGMA * world.DT
    assert 0.5 * expected < spread < 2.0 * expected, (
        f"x-spread {spread:.4f}; expected ~{expected:.4f} — sample v per PARTICLE with ODOM_V_SIGMA"
    )
    th_spread = wrap(out[:, 2]).std()
    exp_th = world.ODOM_W_SIGMA * world.DT
    assert 0.5 * exp_th < th_spread < 2.0 * exp_th, (
        f"heading spread {th_spread:.4f}; expected ~{exp_th:.4f} — sample omega per particle too"
    )
    rng2 = np.random.default_rng(rng_seed + 1)
    curved = mod.motion_update(np.tile([5.0, 5.0, 0.0], (4000, 1)), 1.0, 0.8, world.DT, rng2)
    assert curved[:, 1].mean() > 0.01, (
        "with omega > 0 the swarm must curve left (arc model, not straight-line)"
    )


def _check_likelihood(mod, rng_seed):
    rng = np.random.default_rng(rng_seed)
    landmarks = rng.uniform(2, 18, size=(6, 2))
    true_pose = np.array([*rng.uniform(6, 14, 2), rng.uniform(-np.pi, np.pi)])
    obs = world.observe(true_pose, landmarks, np.random.default_rng(rng_seed + 1))
    assert obs, "test-world bug (no observations) — rerun with another seed"
    cands = np.vstack([
        true_pose,
        true_pose + [2.0, 0.0, 0.0],
        true_pose + [0.0, 0.0, np.pi / 2],
    ])
    lik = np.asarray(mod.measurement_likelihood(cands, obs, landmarks))
    assert lik.shape == (3,), f"must return one likelihood per particle, got shape {lik.shape}"
    assert np.all(lik > 0), "likelihoods must be strictly positive (add a tiny floor)"
    assert lik[0] > lik[1] * 10, "true pose must beat a 2 m-offset pose decisively"
    assert lik[0] > lik[2] * 10, "true pose must beat a 90deg-rotated pose (bearing term working?)"
    # The +/-pi bearing trap: heading near pi, landmark behind.
    lms = np.array([[1.0, 10.0]])
    pose_a = np.array([[5.0, 10.0, np.pi - 0.01]])
    obs_wrap = [(0, 4.0, wrap(np.pi - (np.pi - 0.01)))]
    lik_good = np.asarray(mod.measurement_likelihood(pose_a, obs_wrap, lms))[0]
    pose_b = np.array([[5.0, 10.0, -np.pi + 0.01]])
    lik_flip = np.asarray(mod.measurement_likelihood(pose_b, obs_wrap, lms))[0]
    ratio = lik_flip / lik_good
    assert ratio > 1e-3, (
        "bearing residual must be WRAPPED: two headings 0.02 rad apart got likelihood "
        f"ratio {ratio:.2e} — an unwrapped residual near +/-pi sees ~2pi of error"
    )


def _check_resample(mod, rng_seed):
    rng = np.random.default_rng(rng_seed)
    w = rng.dirichlet(np.ones(6) * 0.7)
    counts = np.zeros(6)
    for _ in range(300):
        idx = np.asarray(mod.systematic_resample(w, rng))
        assert idx.shape == (6,) and idx.dtype.kind in "iu", "must return N integer indices"
        counts += np.bincount(idx, minlength=6)
    freq = counts / counts.sum()
    assert np.allclose(freq, w, atol=0.03), (
        f"selection frequency {np.round(freq, 3)} must track weights {np.round(w, 3)}"
    )


def _check_inject(mod, rng_seed):
    rng = np.random.default_rng(rng_seed)
    particles = np.tile([5.0, 5.0, 0.0], (1000, 1))
    out = mod.inject_random(particles.copy(), 0.1, rng)
    assert out.shape == particles.shape, "shape must be preserved"
    moved = np.hypot(out[:, 0] - 5.0, out[:, 1] - 5.0) > 0.5
    frac = moved.mean()
    assert 0.05 < frac < 0.15, f"~10% of particles should be replaced (got {frac:.2%})"
    assert np.all((out[:, :2] >= 0) & (out[:, :2] <= world.WORLD_SIZE)), (
        "injected poses must stay in-world"
    )


def _check_tracking(mod, rng_seed):
    worst = 0.0
    for s in (rng_seed, rng_seed + 13, rng_seed + 77):
        errors = world.run_filter(mod, seed=s)
        mean_err = errors[15:].mean()
        worst = max(worst, mean_err)
        assert mean_err < 0.8, (
            f"tracking seed {s}: mean position error after burn-in {mean_err:.2f} m (need < 0.8)"
        )
    print(f"      tracking worst-case mean error: {worst:.2f} m")


def _check_kidnap(mod, rng_seed):
    errors = world.run_filter(mod, seed=rng_seed, steps=60, global_init=True, inject_frac=0.05)
    assert errors[30:45].mean() < 1.5, (
        f"global localization: error should converge by mid-run (got {errors[30:45].mean():.2f} m)"
    )
    errors = world.run_filter(
        mod, seed=rng_seed + 5, steps=120, kidnap_at=50, inject_frac=0.08
    )
    late = errors[105:].mean()
    assert late < 2.0, (
        f"kidnapped at step 50: must re-converge by step 105 (late error {late:.2f} m). "
        "Is inject_random actually replacing particles?"
    )


TASKS = [
    ("motion_update", 20, _check_motion_update),
    ("measurement_likelihood", 25, _check_likelihood),
    ("systematic_resample", 15, _check_resample),
    ("inject_random", 10, _check_inject),
    ("closed-loop tracking", 15, _check_tracking),
    ("global + kidnap recovery", 15, _check_kidnap),
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
            print("Could not import student.py — run from projects/localization/")
            return 2

    total = earned = 0
    width = max(len(n) for n, _, _ in TASKS)
    print(f"Localization project — seed {seed}\n")
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
