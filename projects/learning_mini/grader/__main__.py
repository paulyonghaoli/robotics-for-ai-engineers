"""Autograder for the robot-learning mini-project.

Usage (from projects/learning_mini/):
    python -m grader [--seed N] [--reference]
"""

from __future__ import annotations

import argparse
import secrets
import sys
import traceback

import numpy as np
from learnkit import (
    ACTION_EDGES,
    CHECKPOINTS,
    CLEARANCE_RAD,
    MODE_OFFSET,
    OUT_OF_DISTRIBUTION_SUCCESS,
    WIDTHS,
    demonstrations,
    sim_success,
)

from grader import reference as ref


def _check_mean_collapse(mod, seed):
    rng = np.random.default_rng(seed)
    d = demonstrations(rng)

    m = mod.mse_optimal(d)
    assert abs(m - float(np.mean(d))) < 1e-9, "the MSE-optimal constant is the mean"
    assert abs(m) < 0.05, f"the two modes cancel, so the mean sits at {m:.3f} — dead centre"

    assert mod.is_feasible(MODE_OFFSET) and mod.is_feasible(-MODE_OFFSET), (
        "both demonstrated behaviours clear the obstacle")
    assert not mod.is_feasible(m), (
        f"the MSE-optimal action is {m:.3f} rad, inside the {CLEARANCE_RAD} rad "
        f"clearance — the average of 'go left' and 'go right' is 'drive into it'")

    # The part that makes this structural rather than unlucky.
    loss_mean = mod.mse_of(m, d)
    loss_left = mod.mse_of(MODE_OFFSET, d)
    loss_right = mod.mse_of(-MODE_OFFSET, d)
    assert loss_mean < loss_left and loss_mean < loss_right, (
        f"MSE at the mean is {loss_mean:.3f} against {loss_left:.3f} for either "
        f"mode. The loss STRICTLY PREFERS the action that crashes, so this is "
        f"not a training failure — a perfectly converged regressor lands here.")
    assert loss_left / loss_mean > 1.5, (
        "and it prefers it by a wide margin, so no amount of tuning moves it")


def _check_discretization(mod, seed):
    rng = np.random.default_rng(seed)
    d = demonstrations(rng)

    p = np.asarray(mod.action_histogram(d, ACTION_EDGES))
    assert len(p) == len(ACTION_EDGES) - 1, "one probability per bin"
    assert abs(float(p.sum()) - 1.0) < 1e-9, "probabilities, not counts"

    c = np.asarray(mod.bin_centers(ACTION_EDGES))
    assert len(c) == len(p), "one centre per bin"
    assert abs(c[0] - 0.5 * (ACTION_EDGES[0] + ACTION_EDGES[1])) < 1e-12

    a = mod.argmax_action(d, ACTION_EDGES)
    assert mod.is_feasible(a), (
        f"the most likely action is {a:.2f} rad and clears the obstacle. The "
        f"mode is a real behaviour; the mean is an average of two of them.")
    assert abs(abs(a) - MODE_OFFSET) < 0.1, "and it lands on one of the two modes"

    samples = [mod.sample_action(d, ACTION_EDGES, rng) for _ in range(400)]
    rate = mod.feasible_rate(samples)
    assert rate > 0.95, (
        f"sampling from the discretized distribution clears the obstacle "
        f"{100*rate:.0f}% of the time — it commits to one mode per draw "
        f"instead of interpolating between them")
    assert mod.feasible_rate([0.0, 0.1, -0.2]) == 0.0, "none of those clear"

    # The metric inversion, which is the reason this is worth 25 points.
    assert mod.mse_of(a, d) > 1.5 * mod.mse_of(mod.mse_optimal(d), d), (
        f"the discretized policy's MSE is {mod.mse_of(a, d):.3f} against "
        f"{mod.mse_of(mod.mse_optimal(d), d):.3f} for the regressor. It is "
        f"twice as bad on the metric and it is the only one of the two that "
        f"does not hit the obstacle. If you rank policies by validation loss "
        f"you will rank this one last.")


def _check_sim2real(mod, seed):
    assert not mod.covers(0.20), "0.20 does not reach a real friction of 0.85"
    assert mod.covers(0.25), "0.25 just barely does"

    assert abs(mod.real_success(0.20) - OUT_OF_DISTRIBUTION_SUCCESS) < 1e-9, (
        "outside the training range the policy is extrapolating")
    assert abs(mod.real_success(0.25) - float(sim_success(0.25))) < 1e-9, (
        "inside it, the robot behaves the way the simulator said")

    w_sim = mod.best_width(WIDTHS, sim_success)
    w_real = mod.best_width(WIDTHS, mod.real_success)
    assert abs(w_sim - float(WIDTHS.min())) < 1e-9, (
        f"simulation always prefers the NARROWEST randomization ({w_sim:.2f}), "
        f"because narrow is easier and the simulator never leaves the range it "
        f"was trained on")
    assert abs(w_real - 0.25) < 1e-9, (
        f"the robot prefers {w_real:.2f} — the narrowest width that still "
        f"covers the friction it actually has")

    assert mod.real_success(w_sim) < 0.4 < mod.real_success(w_real), (
        f"the width that looks best in simulation ({w_sim:.2f}) scores "
        f"{mod.real_success(w_sim):.2f} on the robot; the width that is best on "
        f"the robot scores {mod.real_success(w_real):.2f}. Tuning domain "
        f"randomization against simulator performance optimizes toward the "
        f"worst possible real-world result, monotonically.")

    assert mod.real_success(0.80) < mod.real_success(w_real), (
        "and randomizing everything is not the answer either — past the "
        "coverage point, extra width is capacity spent on cases the robot "
        "will never see")

    # The cliff: real-world success is discontinuous in the width, so a
    # sweep at 0.05 resolution can miss the only setting that works.
    assert mod.real_success(0.25) - mod.real_success(0.20) > 0.5, (
        "success jumps by more than 0.5 between two adjacent widths — this is "
        "a cliff, not a gradient, and 'it suddenly started working' is what it "
        "feels like from the outside")


def _check_checkpoints(mod, seed):
    by_loss = mod.best_by(CHECKPOINTS, "val_mse", maximize=False)
    by_success = mod.best_by(CHECKPOINTS, "success", maximize=True)

    assert by_loss["epoch"] == 12, "validation loss falls monotonically to the last epoch"
    assert by_success["epoch"] == 5, "on-robot success peaks at epoch 5 and then falls"
    assert by_loss["epoch"] != by_success["epoch"], (
        "early stopping on validation loss and picking the best policy are "
        "different operations here")

    r = mod.pearson([c["val_mse"] for c in CHECKPOINTS],
                    [c["success"] for c in CHECKPOINTS])
    assert abs(r) < 0.5, (
        f"the correlation between validation MSE and on-robot success across "
        f"checkpoints is {r:+.3f} — not merely weak, close to uninformative. "
        f"The metric the training loop minimizes carries almost no signal "
        f"about the thing you care about.")

    regret = mod.selection_regret(CHECKPOINTS)
    assert abs(regret - 0.23) < 1e-9, (
        f"early-stopping on validation loss gives up {regret:.2f} of success "
        f"— 0.48 instead of 0.71, from a run where the loss curve looks "
        f"textbook the whole way down")
    assert regret > 0.15, "and that is most of the gap between the best and worst checkpoint"

    flat = [{"epoch": i, "val_mse": 0.05, "success": 0.5} for i in range(4)]
    assert mod.pearson([c["val_mse"] for c in flat], [c["success"] for c in flat]) == 0.0, (
        "no variance means no correlation, not a division by zero")


TASKS = [
    ("mean collapse on multimodal demonstrations", 25, _check_mean_collapse),
    ("discretization, and the metric it loses on", 25, _check_discretization),
    ("domain randomization width", 25, _check_sim2real),
    ("checkpoint selection", 25, _check_checkpoints),
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
            print("Could not import student.py — run from projects/learning_mini/")
            return 2

    total = earned = 0
    width = max(len(n) for n, _, _ in TASKS)
    print(f"Robot-learning mini-project — seed {seed}\n")
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
