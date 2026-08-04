"""Autograder for the deployment mini-project.

Usage (from projects/deployment_mini/):
    python -m grader [--seed N] [--reference]
"""

from __future__ import annotations

import argparse
import secrets
import sys
import traceback

import numpy as np
from deploykit import (
    BASE_FRAME_MS,
    CLOCK_FLOOR,
    FLEET_SIZE,
    FRAME_PERIOD_MS,
    ROLLOUT_PLANS,
    stage_traces,
    weight_tensor,
)

from grader import reference as ref


def _check_pipeline(mod, seed):
    rng = np.random.default_rng(seed)
    stages = stage_traces(rng)

    p = np.asarray(mod.pipeline_samples(stages))
    assert p.shape == next(iter(stages.values())).shape, (
        "one pipeline latency per frame")
    manual = sum(np.asarray(v) for v in stages.values())
    assert np.allclose(p, manual), (
        "the stages run in series: frame i costs the sum of the stages' "
        "frame-i costs, not a sum of independently drawn samples")

    p99 = float(np.percentile(p, 99))
    stage_p99_max = max(float(np.percentile(v, 99)) for v in stages.values())
    summed = mod.sum_of_stage_p99(stages)

    assert abs(summed - sum(float(np.percentile(v, 99)) for v in stages.values())) < 1e-9

    assert p99 < 0.8 * summed, (
        f"the pipeline's p99 is {p99:.1f} ms and the sum of the stage p99s is "
        f"{summed:.1f} ms — a {100*(summed/p99-1):.0f}% overstatement, because "
        f"the stages do not spike on the same frames. Adding tail percentiles "
        f"is not a bound anybody should quote.")
    assert p99 > stage_p99_max, (
        f"...and it is larger than any single stage's p99 ({stage_p99_max:.1f} ms), "
        f"so the per-stage dashboard understates it too. Only the pipeline's "
        f"own distribution answers the question.")

    assert mod.tail_driver(stages) == "track", (
        f"the tail is driven by `track` (p99 - p50 is largest there), got "
        f"{mod.tail_driver(stages)!r}")
    assert mod.mean_driver(stages) == "undistort", (
        f"the MEAN is dominated by `undistort`, got {mod.mean_driver(stages)!r}")
    assert mod.tail_driver(stages) != mod.mean_driver(stages), (
        "the stage that owns the average and the stage that owns the tail are "
        "different stages, which is why a mean-sorted profile aims the work "
        "at the wrong one")

    over = float(np.mean(p > FRAME_PERIOD_MS))
    assert 0.005 < over < 0.05, (
        f"{100*over:.1f}% of frames miss the 20 ms deadline — the pipeline is "
        f"comfortable on average and late often enough to matter")


def _check_quantization(mod, seed):
    rng = np.random.default_rng(seed)

    x = rng.uniform(-1.0, 1.0, size=5000)
    s, z = mod.quant_params(x, 8)
    assert abs(s - (x.max() - x.min()) / 255.0) < 1e-12, "scale is range / (2^bits - 1)"
    assert 0 <= z <= 255, f"zero point {z} must be representable"
    xq = np.asarray(mod.fake_quant(x, s, z, 8))
    assert np.max(np.abs(xq - x)) <= s * 0.5 + 1e-9, (
        "round-trip error cannot exceed half a step")
    assert abs(float(np.mean(xq - x))) < 0.01 * s, "rounding should not bias the tensor"

    const = np.full(64, 0.7)
    cs, _cz = mod.quant_params(const, 8)
    assert cs > 0 and np.all(np.isfinite(mod.fake_quant(const, cs, _cz, 8))), (
        "a constant tensor has no range — return a usable scale instead of "
        "dividing by zero")

    w = weight_tensor(rng)
    e_tensor = mod.per_tensor_error(w)
    e_channel = mod.per_channel_error(w)
    assert e_channel > 0.0, "quantization is lossy; the error is not zero"
    assert e_tensor > 5.0 * e_channel, (
        f"per-tensor RMS error {e_tensor:.5f} against per-channel "
        f"{e_channel:.5f}. One channel with a hundred times the dynamic range "
        f"sets the scale for all 64, and the other 63 lose most of their bits "
        f"to a range they never use.")

    w4 = mod.per_channel_error(w, 4)
    w8 = mod.per_channel_error(w, 8)
    assert w4 > 8.0 * w8, (
        f"four bits should be far worse than eight ({w4:.5f} vs {w8:.5f}) — "
        f"halving the bit width is not halving the error")


def _check_rollout(mod, seed):
    rate, k = 0.02, 5.0

    ship = mod.detect(ROLLOUT_PLANS["ship-it"], rate, k, FLEET_SIZE)
    canary = mod.detect(ROLLOUT_PLANS["canary-first"], rate, k, FLEET_SIZE)
    assert ship is not None and canary is not None, "both plans reach the alarm"

    assert abs(ship["robot_hours"] - canary["robot_hours"]) < 1e-6, (
        f"the two plans expose the SAME number of robot-hours to the bad "
        f"version before the alarm — {ship['robot_hours']:.0f} against "
        f"{canary['robot_hours']:.0f}. Failures accrue with exposure, so a "
        f"threshold of {k:.0f} failures always costs k/rate robot-hours "
        f"whatever the schedule. A staged rollout does not reduce how much "
        f"bad service you deliver.")
    assert abs(ship["robot_hours"] - k / rate) < 1e-6, (
        f"and that number is k/rate = {k/rate:.0f} exactly")

    assert ship["hours"] < canary["hours"] / 10.0, (
        f"shipping to the whole fleet finds the problem FASTER in wall-clock "
        f"({ship['hours']:.1f} h against {canary['hours']:.1f} h) — the thing "
        f"a staged rollout costs you")
    assert ship["fraction"] == 1.0 and canary["fraction"] <= 0.10, (
        f"...and what it buys is the blast radius: {100*ship['fraction']:.0f}% "
        f"of the fleet is on the bad version when the alarm fires under "
        f"ship-it, against {100*canary['fraction']:.0f}% under canary-first")

    # A rate low enough that the plan finishes without ever tripping.
    assert mod.detect(ROLLOUT_PLANS["canary-first"], 1e-6, k, FLEET_SIZE) is None, (
        "a plan that ends before the alarm returns None, not a guess")

    # The alarm can fire partway through a stage.
    mid = mod.detect([(0.50, 100.0)], 0.02, 5.0, FLEET_SIZE)
    assert abs(mid["hours"] - 1.0) < 1e-6, (
        f"5 failures at 0.02/robot-hour over 250 robots is 1.0 h, got "
        f"{mid['hours']:.3f} — solve within the stage rather than rounding to "
        f"its boundary")


def _check_thermal(mod, seed):
    assert abs(mod.frame_ms(0.0) - BASE_FRAME_MS) < 1e-9, "cold, the frame is 11 ms"
    assert abs(mod.frame_ms(1e9) - BASE_FRAME_MS / CLOCK_FLOOR) < 1e-6, (
        "fully soaked, it is 22 ms")

    b30 = mod.mean_fps(30.0)
    b600 = mod.mean_fps(600.0)
    sus = mod.sustained_fps()
    assert abs(b30 - 1000.0 / BASE_FRAME_MS) < 1e-6, (
        f"a 30-second benchmark never leaves the boost window and reports "
        f"{b30:.1f} fps")
    assert b600 < b30, "a ten-minute run reports less"
    assert abs(sus - 1000.0 * CLOCK_FLOOR / BASE_FRAME_MS) < 1e-6, (
        f"the sustained rate is {1000.0*CLOCK_FLOOR/BASE_FRAME_MS:.1f} fps, got {sus:.1f}")
    assert b30 > 1.9 * sus, (
        f"the benchmark number is {b30/sus:.1f}x the number that is still true "
        f"after five minutes. Both are measurements; only one belongs on a "
        f"datasheet.")

    breach = mod.deadline_breach_time(FRAME_PERIOD_MS)
    assert breach is not None, "the 50 Hz deadline is eventually missed"
    assert 250.0 < breach < 320.0, (
        f"the deadline first breaks at {breach:.0f} s — a 30-second benchmark "
        f"is clean, a 60-second one is clean, and the robot cannot hold 50 Hz "
        f"after about five minutes of continuous operation")
    assert mod.deadline_breach_time(25.0) is None, (
        "a 40 Hz loop survives the throttle entirely — the deadline you chose "
        "is what decides whether this hardware works")


TASKS = [
    ("pipeline tail vs per-stage tails", 25, _check_pipeline),
    ("INT8 quantization, per-tensor vs per-channel", 25, _check_quantization),
    ("rollout exposure and blast radius", 25, _check_rollout),
    ("thermal throttling and the datasheet number", 25, _check_thermal),
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
            print("Could not import student.py — run from projects/deployment_mini/")
            return 2

    total = earned = 0
    width = max(len(n) for n, _, _ in TASKS)
    print(f"Deployment mini-project — seed {seed}\n")
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
