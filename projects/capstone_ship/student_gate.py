"""Stage 2: YOUR regression gate. Start here.

    python student_gate.py --episodes 48

Stage 1 answered "is this candidate worse." This stage builds the thing that
runs on *every* future change, and the question that matters is not whether
there is a difference — it is **what size of regression this gate would
miss.**

--------------------------------------------------------------------------
WHAT YOU BUILD

  paired_bootstrap          a confidence interval on the per-seed difference
  minimum_detectable_effect what this design can actually resolve
  gate                      the verdict, and the order the checks go in

Two ideas carry the stage.

**Pairing.** Run both stacks on the same seeds and compare per-seed. This
removes the variance the two arms SHARE, so what it buys you depends
entirely on how correlated they are — and you should measure that rather
than assume it. Against this incumbent it buys almost nothing, because it
succeeds on 46 of 48 episodes and a near-ceiling arm has no variance to
share. Pairing pays when both stacks struggle on the same scenarios, which
is the usual case for successive versions of one policy.

**Power.** A gate that cannot detect the regression it guards is theatre: it
passes everything, everyone trusts it, and it is not doing its job. So the
gate reports its own minimum detectable effect — and the ORDER of the checks
is the part worth thinking about before you write it.
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

import numpy as np

CAPSTONE_NAV = Path(__file__).resolve().parent.parent / "capstone_nav"
sys.path.insert(0, str(CAPSTONE_NAV))
sys.path.insert(0, str(CAPSTONE_NAV / "solutions"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "solutions"))

import eval.__main__ as harness  # noqa: E402, F401
from evaluate import build_suite  # noqa: E402


def paired_outcomes(stack_a: str, stack_b: str, suite: list[dict]):
    """Given: run both stacks on the SAME seeds, return two boolean arrays."""
    mod_a = importlib.import_module(stack_a)
    mod_b = importlib.import_module(stack_b)
    a = [bool(harness.run_episode(mod_a, p["seed"])["success"]) for p in suite]
    b = [bool(harness.run_episode(mod_b, p["seed"])["success"]) for p in suite]
    return np.array(a), np.array(b)


def paired_bootstrap(a, b, n_boot=20000, seed=0, alpha=0.05) -> dict:
    """Bootstrap CI on the paired difference (a - b).

    Return {"diff", "lo", "hi", "n"}.

    Resample the PAIR — draw episode indices once and index both arms with
    them. Resampling the two arms independently discards the correlation the
    design was built to exploit, and silently turns this into the unpaired
    comparison.

    TODO.
    """
    raise NotImplementedError("student_gate: paired_bootstrap")


def minimum_detectable_effect(n, base_rate, discordance, alpha=0.05,
                              power=0.80) -> float:
    """Smallest true regression this design can detect, as a rate difference.

    In a paired binary comparison all the information about the difference
    lives in the DISCORDANT pairs — episodes where exactly one stack
    succeeded. Concordant pairs carry none, which is why a suite everything
    passes tells you nothing however long you run it.

    Normal approximation to McNemar's test:
        MDE ~= (z_{alpha/2} + z_power) * sqrt(discordance / n)
    with z_{0.025} = 1.96 and z_{0.80} = 0.8416.

    TODO.
    """
    raise NotImplementedError("student_gate: minimum_detectable_effect")


def gate(incumbent, candidate, tolerance=0.05, seed=0) -> dict:
    """Return {"verdict", "reason", "mde", "discordance", ...}.

    `tolerance` is the largest regression you are willing to ship.

    Three verdicts — BLOCK, INCONCLUSIVE, PASS — and the ORDER of the checks
    is the design decision. Think about it before writing:

      * If the interval already excludes the tolerance, the design was
        evidently powerful enough for THIS effect. Reporting "inconclusive"
        because the MDE happens to be large would be absurd.
      * "No regression detected" is only meaningful if you COULD have
        detected one. An underpowered gate must not hand back a PASS.

    So power gates one verdict and not the other. Which one?

    TODO.
    """
    raise NotImplementedError("student_gate: gate")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=48)
    ap.add_argument("--seed", type=int, default=1000)
    ap.add_argument("--tolerance", type=float, default=0.05)
    args = ap.parse_args()

    suite = build_suite(args.episodes, args.seed)
    inc, cand = paired_outcomes("reference_stack", "bc_stack", suite)
    g = gate(inc, cand, tolerance=args.tolerance)
    print(f"\n{len(suite)} paired episodes")
    print(f"  incumbent {inc.mean():.3f}   candidate {cand.mean():.3f}")
    print(f"  discordant {g['discordance']:.3f}   mde {g['mde']:.3f}")
    print(f"\n  {g['verdict']}: {g['reason']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
