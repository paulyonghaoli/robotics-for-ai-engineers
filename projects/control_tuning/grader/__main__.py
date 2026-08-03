"""Autograder for the control mini-project.

Usage (from projects/control_tuning/):
    python -m grader [--seed N] [--reference]

The seed is random unless you pass one, so the tests cannot be satisfied by
fitting a particular world. They check behaviour, not numbers.
"""

from __future__ import annotations

import argparse
import secrets
import sys
import traceback

import numpy as np
import plant
from plant import DT, U_MAX, V_REACHABLE, W_MAX, Cart, forward_kinematics, reference_path

from grader import reference as ref

# ---------------- PID ----------------

def _check_pid_basic(mod, seed):
    rng = np.random.default_rng(seed)
    pid = mod.PID(kp=1.0, ki=0.0, kd=0.0)
    assert abs(pid.step(2.0, 2.0, DT)) < 1e-9, "zero error must give zero output"
    p = mod.PID(kp=0.5, ki=0.0, kd=0.0)
    m, sp = rng.uniform(-1, 1), rng.uniform(-1, 1)
    got = p.step(m, sp, DT)
    assert abs(got - np.clip(0.5 * (sp - m), -U_MAX, U_MAX)) < 1e-9, (
        f"pure-P output {got:.4f} does not match kp*(setpoint-measurement)")

    ip = mod.PID(kp=0.0, ki=1.0, kd=0.0)
    outs = [ip.step(0.0, 0.1, DT) for _ in range(5)]
    assert all(b > a for a, b in zip(outs, outs[1:], strict=False)), (
        "with constant error the integral term must accumulate")


def _check_pid_derivative_kick(mod, seed):
    """A setpoint step must not spike the output through the D term."""
    pid = mod.PID(kp=0.0, ki=0.0, kd=1.0)
    # Measurement held constant; only the setpoint moves.
    pid.step(1.0, 1.0, DT)
    pid.step(1.0, 1.0, DT)
    kicked = pid.step(1.0, 5.0, DT)
    assert abs(kicked) < 1e-6, (
        f"output {kicked:.4f} after a setpoint step with an unchanged "
        "measurement — the D term is differentiating the error, so every "
        "new setpoint fires an impulse at the actuator. Differentiate the "
        "measurement and negate it.")

    # And it must still respond to a MOVING measurement.
    pid2 = mod.PID(kp=0.0, ki=0.0, kd=1.0)
    pid2.step(0.0, 0.0, DT)
    moving = pid2.step(0.5, 0.0, DT)
    assert moving < -1e-6, (
        f"a rising measurement must produce negative D output (damping); "
        f"got {moving:.4f} — check the sign")


def _check_pid_antiwindup(mod, seed):
    """Ask for an unreachable speed, then a reachable one."""
    def run(pid_obj):
        cart = Cart()
        v, hist = 0.0, []
        for k in range(400):
            setpoint = 3.0 * V_REACHABLE if k < 200 else 1.0
            u = pid_obj.step(v, setpoint, DT)
            v = cart.step(u)
            if k >= 200:
                hist.append(v)
        return np.array(hist)

    tail = run(mod.PID(kp=1.0, ki=2.0, kd=0.05))
    # The cart enters this window at ~V_REACHABLE, so what matters is how
    # long it takes to come DOWN to the new, reachable setpoint. A wound-up
    # integrator holds the actuator pinned positive while it unwinds.
    below = np.nonzero(tail <= 1.1)[0]
    assert len(below), (
        f"10 s after the setpoint dropped to 1.0 m/s the cart is still at "
        f"{tail[-1]:.2f} m/s. The integrator accumulated for 200 steps while "
        "the actuator was pinned at its limit, and now has to unwind before "
        "anything happens. Stop integrating when the output is clamped.")
    settle_steps = int(below[0])
    assert settle_steps < 60, (
        f"took {settle_steps} steps ({settle_steps * DT:.1f} s) to reach the "
        "new setpoint — integral windup is still being paid back")
    settled = tail[-40:]
    assert abs(settled.mean() - 1.0) < 0.15, (
        f"never settles on the reachable setpoint (mean {settled.mean():.2f}, "
        "want ~1.0)")
    assert tail.min() > 0.4, (
        f"undershoots to {tail.min():.2f} m/s — too aggressive coming down")


def _check_pid_limits(mod, seed):
    pid = mod.PID(kp=100.0, ki=0.0, kd=0.0, output_limits=(-0.5, 0.5))
    assert abs(pid.step(0.0, 10.0, DT) - 0.5) < 1e-9, "output must respect output_limits"
    assert abs(pid.step(0.0, -10.0, DT) + 0.5) < 1e-9, "…on both sides"


# ---------------- kinematics ----------------

def _check_diff_drive(mod, seed):
    rng = np.random.default_rng(seed)
    pose = np.array([rng.uniform(-3, 3), rng.uniform(-3, 3), rng.uniform(-np.pi, np.pi)])

    straight = mod.diff_drive_step(pose, 1.0, 0.0, 0.5)
    exp = pose[:2] + 0.5 * np.array([np.cos(pose[2]), np.sin(pose[2])])
    assert np.allclose(straight[:2], exp, atol=1e-9), "straight-line case is wrong"

    # Exact arc vs many Euler substeps of the same motion.
    v, w, dt = 1.0, 1.2, 0.4
    got = mod.diff_drive_step(pose, v, w, dt)
    fine = pose.astype(float).copy()
    n = 20000
    for _ in range(n):
        h = dt / n
        fine = np.array([fine[0] + v * np.cos(fine[2]) * h,
                         fine[1] + v * np.sin(fine[2]) * h,
                         fine[2] + w * h])
    assert np.allclose(got[:2], fine[:2], atol=2e-4), (
        f"turning motion lands at {got[:2].round(4)}, exact arc is "
        f"{fine[:2].round(4)} — looks like single-step Euler integration")
    assert abs(float(mod.wrap(got[2] - fine[2]))) < 1e-6, "heading is wrong"

    big = mod.diff_drive_step(np.array([0.0, 0.0, 3.0]), 1.0, 2.0, 1.0)
    assert -np.pi < big[2] <= np.pi, f"theta must stay wrapped, got {big[2]:.3f}"


def _check_ik(mod, seed):
    rng = np.random.default_rng(seed)
    l1, l2 = plant.LINKS
    # A reachable target, generated from a random reachable configuration.
    q_true = np.array([rng.uniform(0.3, 1.2), rng.uniform(0.4, 1.4)])
    target = forward_kinematics(q_true)

    q = np.array([0.1, 0.6])
    for _ in range(400):
        q = q + mod.ik_step(q, target)
    err = float(np.linalg.norm(forward_kinematics(q) - target))
    assert err < 1e-3, f"IK did not converge: end effector {err:.4f} m from target"

    # Near-singular (arm almost straight) must not explode.
    dq = mod.ik_step(np.array([0.4, 1e-6]), np.array([l1 + l2 + 0.5, 0.0]))
    assert np.all(np.isfinite(dq)) and np.linalg.norm(dq) < 50.0, (
        f"near a singularity the step blew up (|dq| = {np.linalg.norm(dq):.1f}) "
        "— use damped least squares, not a raw pseudo-inverse")


# ---------------- pursuit and tracking ----------------

def _check_pure_pursuit(mod, seed):
    straight = np.stack([np.linspace(0, 10, 100), np.zeros(100)], axis=1)
    w = mod.pure_pursuit(np.array([0.0, 0.0, 0.0]), straight, 1.0, 1.0)
    assert abs(w) < 1e-6, f"on-path and aligned should need no steering, got {w:.4f}"

    # Robot to the RIGHT of the path must steer LEFT (positive w).
    w_left = mod.pure_pursuit(np.array([0.0, -0.5, 0.0]), straight, 1.0, 1.0)
    assert w_left > 0.05, (
        f"offset right of the path, got w={w_left:.4f}; positive lateral "
        "error must steer left (check your sign)")
    w_right = mod.pure_pursuit(np.array([0.0, 0.5, 0.0]), straight, 1.0, 1.0)
    assert w_right < -0.05, "offset left of the path must steer right"

    # Scales with speed at fixed geometry.
    slow = mod.pure_pursuit(np.array([0.0, -0.5, 0.0]), straight, 1.0, 0.5)
    assert abs(w_left - 2.0 * slow) < 1e-6, "w should scale linearly with v"

    # At the very end of the path it must still aim at the goal.
    w_end = mod.pure_pursuit(np.array([9.9, -0.4, 0.0]), straight, 2.0, 1.0)
    assert abs(w_end) > 1e-6, (
        "within a lookahead of the path end, steering went to zero — aim at "
        "the last point instead of giving up")


def _check_tracking(mod, seed):
    path = reference_path()
    start = np.array([0.0, 1.2, 0.0])
    traj = mod.track(path, start, steps=900, dt=DT)
    traj = np.asarray(traj)
    assert traj.ndim == 2 and traj.shape[1] == 3, f"track must return (N, 3), got {traj.shape}"
    assert np.allclose(traj[0], start), "first row must be the starting pose"

    errs = plant.cross_track_errors(traj[:, :2], path)
    rmse = float(np.sqrt(np.mean(errs[100:] ** 2)))
    assert rmse < 0.25, (
        f"cross-track RMSE {rmse:.3f} m after convergence (want < 0.25). "
        "The loop has to settle onto the path, not just point at it.")
    reached = float(np.linalg.norm(traj[-1, :2] - path[-1]))
    assert reached < 0.35, f"ended {reached:.2f} m from the end of the path"
    assert len(traj) < 900, (
        f"used the whole {900}-step budget without terminating. The path is "
        "16 m and the budget is 45 m of driving, so a tracker with no "
        "terminal condition spends the remainder orbiting the last waypoint. "
        "Stop when you arrive.")

    ws = np.abs(np.diff(np.unwrap(traj[:, 2])) / DT)
    assert ws.max() <= W_MAX + 1e-6, (
        f"commanded yaw rate reached {ws.max():.2f} rad/s, above W_MAX={W_MAX}")


TASKS = [
    ("PID basics", 10, _check_pid_basic),
    ("PID output limits", 5, _check_pid_limits),
    ("PID derivative kick", 15, _check_pid_derivative_kick),
    ("PID anti-windup", 20, _check_pid_antiwindup),
    ("differential-drive arc", 15, _check_diff_drive),
    ("damped Jacobian IK", 15, _check_ik),
    ("pure pursuit", 10, _check_pure_pursuit),
    ("closed-loop tracking", 10, _check_tracking),
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
            print("Could not import student.py — run from projects/control_tuning/")
            return 2

    total = earned = 0
    width = max(len(n) for n, _, _ in TASKS)
    print(f"Control mini-project — seed {seed}\n")
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
