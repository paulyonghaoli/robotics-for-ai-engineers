"""Stage 4: the rollout — canary sizing, drift detection, and a safety monitor.

    python solutions/rollout.py

Stages 1-3 decided the candidate is not shippable. This stage builds the
machinery you would need *if* it were, and the machinery is what keeps you
safe when the next candidate looks fine and isn't.

Three pieces, each with a number attached rather than an intention:

  canary        how many episodes must run before a regression of the size
                you care about would be visible
  drift         how many episodes after the world changes before you notice
  safety        a runtime monitor that vetoes unsafe actions and falls back
                to a trusted controller — scored on collisions AND on
                whether the robot still does its job

That last pairing is the point. A monitor evaluated only on violations is
trivially satisfied by a robot that never moves, so every safety number here
is reported beside a liveness number.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

CAPSTONE_NAV = Path(__file__).resolve().parent.parent.parent / "capstone_nav"
sys.path.insert(0, str(CAPSTONE_NAV))
sys.path.insert(0, str(CAPSTONE_NAV / "solutions"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import bc_stack  # noqa: E402
import reference_stack  # noqa: E402
from gate import minimum_detectable_effect  # noqa: E402
from sim import MAX_RANGE, N_RAYS, ROBOT_RADIUS, Simulator  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
BEARINGS = np.arange(N_RAYS) * (2 * np.pi / N_RAYS)


# ---------------- canary sizing ----------------

def canary_size(tolerance: float, discordance: float = 0.30) -> int:
    """Smallest canary that can resolve a regression of `tolerance`.

    Inverts stage 2's minimum detectable effect. The number is usually
    larger than people expect, and quoting it is what stops a canary being
    installed as a formality.
    """
    for n in range(10, 20001, 10):
        if minimum_detectable_effect(n, 0.9, discordance) <= tolerance:
            return n
    return 20000


# ---------------- drift detection ----------------

def scan_statistic(scan: np.ndarray) -> float:
    """One scalar per episode: the mean of the beams that returned a hit.

    Deliberately crude. A drift monitor is not a perception system — it is a
    tripwire, and a tripwire that needs tuning is one nobody will maintain.
    """
    hit = scan < MAX_RANGE - 0.25
    return float(np.mean(scan[hit])) if hit.any() else float(MAX_RANGE)


class CUSUM:
    """One-sided cumulative-sum detector on a running statistic.

    CUSUM rather than a threshold because the interesting drifts are small
    and persistent, not large and instantaneous — a per-episode threshold
    loose enough to avoid false alarms is far too loose to catch a 5% shift
    that is nonetheless ruining you.
    """

    def __init__(self, baseline: float, sigma: float, k: float = 0.5,
                 h: float = 5.0) -> None:
        self.baseline, self.sigma = baseline, max(sigma, 1e-9)
        self.k, self.h = k, h
        self.pos = self.neg = 0.0

    def update(self, x: float) -> bool:
        z = (x - self.baseline) / self.sigma
        self.pos = max(0.0, self.pos + z - self.k)
        self.neg = max(0.0, self.neg - z - self.k)
        return bool(self.pos > self.h or self.neg > self.h)


def drift_detection_latency(shift: float, n_baseline: int = 40,
                            n_after: int = 120, seed: int = 0) -> int | None:
    """Episodes between a world change and the monitor noticing it."""
    rng = np.random.default_rng(seed)
    base = [scan_statistic(_episode_scan(1000 + 7 * i, 0.0, rng))
            for i in range(n_baseline)]
    mon = CUSUM(float(np.mean(base)), float(np.std(base) + 1e-9))
    for i in range(n_after):
        s = scan_statistic(_episode_scan(9000 + 7 * i, shift, rng))
        if mon.update(s):
            return i + 1
    return None


def _episode_scan(seed: int, shift: float, rng) -> np.ndarray:
    """One episode's scan, with an optional multiplicative range shift.

    The shift stands in for a real environmental change — a reflective floor,
    a recalibrated sensor, a different site.
    """
    sim = Simulator(seed)
    obs = sim.reset()
    scan = obs["scan"].copy()
    hit = scan < MAX_RANGE - 0.25
    scan[hit] = scan[hit] * (1.0 + shift)
    return scan


# ---------------- safety monitor ----------------

def predicted_min_clearance(scan: np.ndarray, v: float, w: float,
                            horizon: float = 1.0, steps: int = 10) -> float:
    """Closest the robot would come to a scan return if it held (v, w).

    Roll the commanded twist forward in the ROBOT's frame and measure
    against the current scan endpoints. Crude, verifiable, and cheap — which
    is what a monitor has to be, because the thing you reason about must be
    simpler than the thing you are protecting against.
    """
    hit = scan < MAX_RANGE - 0.25
    if not hit.any():
        return float(MAX_RANGE)
    pts = np.stack([scan[hit] * np.cos(BEARINGS[hit]),
                    scan[hit] * np.sin(BEARINGS[hit])], axis=1)
    x = y = th = 0.0
    dt = horizon / steps
    worst = float(MAX_RANGE)
    for _ in range(steps):
        x += v * np.cos(th) * dt
        y += v * np.sin(th) * dt
        th += w * dt
        worst = min(worst, float(np.min(np.linalg.norm(pts - [x, y], axis=1))))
    return worst


class MonitoredStack:
    """Runtime assurance: a learned policy behind a verifiable veto.

    The monitor knows nothing about the policy. It checks the proposed
    action against a simple forward model and, if that action would bring
    the robot inside `margin`, substitutes a trusted fallback. This is why
    the architecture is worth having — the thing you have to trust is thirty
    lines of arithmetic instead of a network.
    """

    def __init__(self, sim, margin: float, fallback: str = "reference") -> None:
        self.inner = bc_stack.make_stack(sim)
        self.fallback = (reference_stack.make_stack(sim)
                         if fallback == "reference" else None)
        self.margin = margin
        self.vetoes = 0
        self.steps = 0
        self.fallback_failures = 0
        self.last_estimate = None
        self.path = None

    def step(self, obs):
        self.steps += 1
        v, w = self.inner.step(obs)
        self.last_estimate = obs["pose_meas"]
        if predicted_min_clearance(obs["scan"], v, w) < self.margin + ROBOT_RADIUS:
            self.vetoes += 1
            if self.fallback is not None:
                try:
                    return self.fallback.step(obs)
                except Exception:
                    # The "trusted" fallback is not always available. The
                    # primary can drive the robot outside the set the safety
                    # controller was verified over — here, into a pocket the
                    # planner cannot route out of — and then there is nothing
                    # to fall back TO. A simplex architecture is only as good
                    # as the region its safety controller actually covers, and
                    # that region has to be checked against the states the
                    # PRIMARY can reach, not the ones you designed for.
                    self.fallback_failures += 1
            return (0.0, 1.2)          # last resort: stop and rotate
        return (v, w)


def score_monitor(margin: float, episodes: int, fallback: str = "reference",
                  base_seed: int = 1000) -> dict:
    """Collisions AND task success. Never one without the other."""
    succ, coll, vetoed, fb_fail = [], [], [], []
    for i in range(episodes):
        sim = Simulator(base_seed + 17 * i)
        obs = sim.reset()
        stack = MonitoredStack(sim, margin, fallback)
        done = False
        while not done:
            v, w = stack.step(obs)
            obs, done = sim.step(v, w)
        succ.append(bool(sim.at_goal))
        coll.append(sim.collisions == 0)
        vetoed.append(stack.vetoes / max(stack.steps, 1))
        fb_fail.append(stack.fallback_failures > 0)
    return {"margin": margin, "success": float(np.mean(succ)),
            "collision_free": float(np.mean(coll)),
            "veto_rate": float(np.mean(vetoed)),
            "fallback_unavailable": float(np.mean(fb_fail))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=16)
    args = ap.parse_args()
    out = {}

    print("\n1. CANARY SIZING — how many episodes to see a regression")
    sizes = {t: canary_size(t) for t in (0.20, 0.10, 0.05, 0.02)}
    for t, n in sizes.items():
        print(f"   detect a {t:.2f} regression:  {n:>6} episodes")
    print("   Halving the effect you want to catch roughly quadruples the")
    print("   canary. A canary sized by convenience detects nothing.")
    out["canary"] = sizes

    print("\n2. DRIFT DETECTION — episodes from world change to alarm")
    lat = {}
    for shift in (0.02, 0.05, 0.10, 0.20):
        n = drift_detection_latency(shift)
        lat[shift] = n
        print(f"   {shift:+.0%} range shift:  "
              f"{'never (within 120)' if n is None else f'{n} episodes'}")
    out["drift"] = {str(k): v for k, v in lat.items()}

    print(f"\n3. SAFETY MONITOR — {args.episodes} episodes per margin")
    out["monitor"] = {}
    for fb, label in (("reference", "fallback = the trusted classical stack"),
                      ("stop", "fallback = stop and rotate (no controller)")):
        print(f"\n   {label}")
        print(f"   {'margin':>7} {'collision-free':>15} {'success':>9} "
              f"{'veto rate':>11} {'fb unavail':>11}")
        rows = []
        for margin in (0.00, 0.10, 0.25, 0.50, 1.00):
            r = score_monitor(margin, args.episodes, fallback=fb)
            rows.append(r)
            print(f"   {margin:>7.2f} {r['collision_free']:>15.3f} "
                  f"{r['success']:>9.3f} {r['veto_rate']:>11.3f} "
                  f"{r['fallback_unavailable']:>11.3f}")
        out["monitor"][fb] = rows

    ref, stop = out["monitor"]["reference"], out["monitor"]["stop"]
    print("\n   Three things fall out, and only one is the textbook one.\n")
    print("   (a) THE TRADEOFF IS REAL ONLY WITH A NULL FALLBACK. Stopping and")
    print(f"       rotating moves collision-free {stop[0]['collision_free']:.2f} -> "
          f"{stop[-1]['collision_free']:.2f} and success")
    print(f"       {stop[0]['success']:.2f} -> {stop[-1]['success']:.2f}. Safe and useless is a "
          "real operating point,")
    print("       and a monitor scored only on violations calls it best.\n")
    print("   (b) WITH A GOOD FALLBACK THERE IS NO TRADEOFF — AND THAT IS BAD")
    print(f"       NEWS. Success RISES with margin ({ref[0]['success']:.2f} -> "
          f"{ref[-1]['success']:.2f}), because every veto")
    print("       hands control to a controller simply better than the thing")
    print("       being guarded. At the widest margin the monitor is running")
    print("       the robot. That is not a safety result, it is a verdict on")
    print("       the candidate: if the fallback dominates it everywhere,")
    print("       ship the fallback.\n")
    print("   (c) THE FALLBACK IS NOT ALWAYS AVAILABLE. At margin 0.00 the")
    print(f"       trusted controller could not produce an action in "
          f"{ref[0]['fallback_unavailable']:.0%} of")
    print("       episodes — the primary had already driven the robot into a")
    print("       pocket the planner could not route out of. A simplex")
    print("       architecture is only as good as the region its safety")
    print("       controller covers, and that region has to be checked against")
    print("       the states the PRIMARY can reach. Intervening earlier keeps")
    print("       the recovery set reachable: from margin 0.10 up, it never")
    print("       failed.")

    with open(HERE / "rollout_results.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
