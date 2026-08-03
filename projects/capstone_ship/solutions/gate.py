"""Stage 2: the regression gate, and what it can actually detect.

    python solutions/gate.py --episodes 60

Stage 1 showed the candidate is worse. This stage builds the thing that has
to run on *every* future change, and the interesting question is not "is
there a difference" — it is **"what size of regression would this gate
miss?"**

Two ideas do the work.

**Pairing.** Run both stacks on the *same* seeds and compare per-seed. This
removes the variance the two arms SHARE — and how much that is worth depends
entirely on how correlated they are. Measured here it is worth almost
nothing, because the incumbent succeeds on 46 of 48 episodes and a near-
ceiling arm has no variance to share. Pairing pays when both stacks struggle
on the same scenarios, which is exactly the case a regression gate normally
runs on: successive versions of the same policy. The tool reports the
correlation so you can see which regime you are in rather than assuming.

**Power.** A gate that cannot detect the regression you care about is
theatre — it passes everything, everyone trusts it, and it is not doing the
job it was installed to do. So the gate reports its own minimum detectable
effect alongside its verdict, and a gate that cannot resolve the bar it is
guarding says so instead of returning a confident PASS.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

import numpy as np

CAPSTONE_NAV = Path(__file__).resolve().parent.parent.parent / "capstone_nav"
sys.path.insert(0, str(CAPSTONE_NAV))
sys.path.insert(0, str(CAPSTONE_NAV / "solutions"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import eval.__main__ as harness  # noqa: E402
from evaluate import build_suite  # noqa: E402

HERE = Path(__file__).resolve().parent.parent


def paired_outcomes(stack_a: str, stack_b: str, suite: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    """Run both stacks on the SAME seeds. Returns two boolean arrays."""
    mod_a = importlib.import_module(stack_a)
    mod_b = importlib.import_module(stack_b)
    a, b = [], []
    for p in suite:
        a.append(bool(harness.run_episode(mod_a, p["seed"])["success"]))
        b.append(bool(harness.run_episode(mod_b, p["seed"])["success"]))
    return np.array(a), np.array(b)


def paired_bootstrap(a: np.ndarray, b: np.ndarray, n_boot: int = 20000,
                     seed: int = 0, alpha: float = 0.05) -> dict:
    """Bootstrap CI on the paired difference (a - b), resampling EPISODES.

    Resampling the pair, not the two arms independently, is what preserves
    the pairing — resample them separately and you have thrown away the very
    correlation you built the design to exploit.
    """
    rng = np.random.default_rng(seed)
    d = a.astype(float) - b.astype(float)
    n = len(d)
    idx = rng.integers(0, n, size=(n_boot, n))
    means = d[idx].mean(axis=1)
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return {"diff": float(d.mean()), "lo": float(lo), "hi": float(hi), "n": n}


def unpaired_bootstrap(a: np.ndarray, b: np.ndarray, n_boot: int = 20000,
                       seed: int = 0, alpha: float = 0.05) -> dict:
    """The same comparison with the pairing discarded, for contrast."""
    rng = np.random.default_rng(seed)
    n = len(a)
    ia = rng.integers(0, n, size=(n_boot, n))
    ib = rng.integers(0, n, size=(n_boot, n))
    means = a.astype(float)[ia].mean(axis=1) - b.astype(float)[ib].mean(axis=1)
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return {"diff": float(a.mean() - b.mean()), "lo": float(lo), "hi": float(hi), "n": n}


def minimum_detectable_effect(n: int, base_rate: float, discordance: float,
                              alpha: float = 0.05, power: float = 0.80) -> float:
    """Smallest true regression this design can detect, as a rate difference.

    For a paired binary comparison the information lives entirely in the
    DISCORDANT pairs — episodes where exactly one of the two stacks
    succeeded. Concordant pairs carry no signal about the difference, which
    is why a suite of scenarios everything passes tells you nothing however
    many of them you run.

    Normal approximation to McNemar's test:
        MDE ~= (z_alpha/2 + z_power) * sqrt(discordance / n)
    """
    if n <= 0 or discordance <= 0:
        return 1.0
    z_a = 1.959963985 if abs(alpha - 0.05) < 1e-9 else _z(1 - alpha / 2)
    z_p = 0.8416212336 if abs(power - 0.80) < 1e-9 else _z(power)
    return float((z_a + z_p) * np.sqrt(discordance / n))


def _z(p: float) -> float:
    """Inverse normal CDF, Acklam's rational approximation. Adequate here."""
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    pl, ph = 0.02425, 1 - 0.02425
    if p < pl or p > ph:
        q = np.sqrt(-2 * np.log(p if p < pl else 1 - p))
        num = ((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]
        den = (((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1
        return num / den if p < pl else -num / den
    q = p - 0.5
    r = q * q
    num = (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q
    den = ((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1
    return num / den


def gate(incumbent: np.ndarray, candidate: np.ndarray, tolerance: float = 0.05,
         seed: int = 0) -> dict:
    """Ship / no-ship, with the gate's own detection limit reported.

    `tolerance` is the largest regression you are willing to ship. The gate
    must be able to RESOLVE that number — if its minimum detectable effect
    is larger than the bar it guards, it cannot do its job and says so
    rather than returning a comfortable PASS.
    """
    boot = paired_bootstrap(incumbent, candidate, seed=seed)
    disc = float(np.mean(incumbent.astype(int) != candidate.astype(int)))
    mde = minimum_detectable_effect(len(incumbent), float(incumbent.mean()), disc)

    # Order matters. Detection comes first: if the interval already excludes
    # the tolerance, the design was evidently powerful enough for THIS effect,
    # and reporting "inconclusive" because the MDE is large would be absurd.
    # Power only gates the reassuring verdict — "no regression detected" means
    # nothing unless you could have detected one.
    if boot["lo"] > tolerance:
        verdict = "BLOCK"
        why = (f"regression of {boot['diff']:.3f} "
               f"[{boot['lo']:.3f}, {boot['hi']:.3f}] exceeds the "
               f"{tolerance:.3f} tolerance")
    elif mde > tolerance:
        verdict = "INCONCLUSIVE"
        why = (f"no regression proven, but the smallest this design could "
               f"detect is {mde:.3f} — larger than the {tolerance:.3f} bar it "
               f"guards, so a PASS here would be unearned. Run more episodes.")
    else:
        verdict = "PASS"
        why = (f"regression {boot['diff']:.3f} "
               f"[{boot['lo']:.3f}, {boot['hi']:.3f}] is within tolerance, "
               f"and the design could have detected {mde:.3f}")

    return {"verdict": verdict, "reason": why, "mde": mde,
            "discordance": disc, **boot}


def _simulate_pairing(n: int, rate: float, rho: float, reps: int = 40,
                      seed: int = 3):
    """Two correlated binary arms at the same rate; returns the MEAN paired
    and unpaired interval widths over `reps` replicate datasets.

    Averaging matters: on a single draw of 48 episodes the bootstrap noise is
    larger than the effect being illustrated, and the table comes out
    non-monotone in a way that says nothing about pairing.
    """
    rng = np.random.default_rng(seed)
    wp, wu = [], []
    for _ in range(reps):
        shared = rng.random(n) < rate
        a = np.where(rng.random(n) < rho, shared, rng.random(n) < rate)
        b = np.where(rng.random(n) < rho, shared, rng.random(n) < rate)
        p = paired_bootstrap(a, b, n_boot=2000, seed=int(rng.integers(1 << 30)))
        u = unpaired_bootstrap(a, b, n_boot=2000, seed=int(rng.integers(1 << 30)))
        wp.append(p["hi"] - p["lo"])
        wu.append(u["hi"] - u["lo"])
    return float(np.mean(wp)), float(np.mean(wu))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=60)
    ap.add_argument("--seed", type=int, default=1000)
    ap.add_argument("--tolerance", type=float, default=0.05)
    args = ap.parse_args()

    suite = build_suite(args.episodes, args.seed)
    inc, cand = paired_outcomes("reference_stack", "bc_stack", suite)

    p = paired_bootstrap(inc, cand)
    u = unpaired_bootstrap(inc, cand)
    width_p, width_u = p["hi"] - p["lo"], u["hi"] - u["lo"]

    print(f"\n{len(suite)} paired episodes\n")
    print(f"  incumbent {inc.mean():.3f}   candidate {cand.mean():.3f}")
    print(f"  discordant pairs: {np.mean(inc != cand):.3f}\n")
    corr = (float(np.corrcoef(inc.astype(float), cand.astype(float))[0, 1])
            if inc.std() > 0 and cand.std() > 0 else float("nan"))
    print(f"  paired   diff {p['diff']:+.3f}  [{p['lo']:+.3f}, {p['hi']:+.3f}]"
          f"  width {width_p:.3f}")
    print(f"  unpaired diff {u['diff']:+.3f}  [{u['lo']:+.3f}, {u['hi']:+.3f}]"
          f"  width {width_u:.3f}")
    print(f"  correlation between arms: {corr:+.3f}"
          f"   -> pairing narrows by {100 * (1 - width_p / width_u):.0f}%")
    if not (corr > 0.3):
        print("     (little shared variance to remove — the incumbent is near")
        print("      the ceiling. Pairing pays when both arms struggle on the")
        print("      same scenarios, which is the usual regression-gate case.)")

    print("\n  what pairing is worth, as a function of correlation")
    print("  (simulated, same n, both arms at 0.70):")
    for rho in (0.0, 0.3, 0.6, 0.9):
        wp, wu = _simulate_pairing(len(inc), 0.70, rho)
        print(f"     rho {rho:.1f}:  paired width {wp:.3f}   unpaired {wu:.3f}"
              f"   ({100 * (1 - wp / wu):+.0f}%)")

    g = gate(inc, cand, tolerance=args.tolerance)
    print(f"\n  minimum detectable effect: {g['mde']:.3f}")
    print(f"\n  {g['verdict']}: {g['reason']}")

    with open(HERE / "gate_results.json", "w", encoding="utf-8") as f:
        json.dump({"paired": p, "unpaired": u, "gate": g}, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
