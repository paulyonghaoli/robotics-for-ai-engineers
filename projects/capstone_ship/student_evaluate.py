"""YOUR evaluation infrastructure. Start here.

    python student_evaluate.py --episodes 48

In Capstone I you built a robot. Here you don't. The robot exists
(`../capstone_nav`), a candidate policy exists (`bc_stack.py`, already
trained), and someone wants to ship the candidate to the fleet.

You build the thing that decides whether they can.

--------------------------------------------------------------------------
WHAT YOU'RE GIVEN

    policy.py      the candidate's architecture and featurizer
    collect.py     gathers expert demonstrations and trains policy.npz
    bc_stack.py    wraps the policy in capstone_nav's stack contract
    policy.npz     a trained candidate. Validation MSE 0.052.

That validation number is the whole problem. It looks good. Your job is to
find out what it's worth.

--------------------------------------------------------------------------
WHAT YOU BUILD (stage 1)

A scenario suite. Not a single aggregate success rate — that number is the
one everyone reports and the one that tells you least. Two policies at 0.75
can differ completely in *which* quarter they fail, and the one that fails
in tight corridors is a different product from the one that fails on long
routes.

So: stratify the worlds before you score them, and report an interval for
every rate, because a stratum holds a dozen episodes and a point estimate
from twelve trials is decoration (lesson 10.1).

Fill in the five functions below, then run:

    python student_evaluate.py --stacks bc_stack reference_stack

You should end up able to answer, with evidence:
  - is the candidate worse than the incumbent, and by how much
  - *where* is it worse
  - is your sample big enough to say so at all

The last one is the question that separates this from a benchmark table.
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

import numpy as np  # noqa: F401

CAPSTONE_NAV = Path(__file__).resolve().parent.parent / "capstone_nav"
sys.path.insert(0, str(CAPSTONE_NAV))
sys.path.insert(0, str(CAPSTONE_NAV / "solutions"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Imported for you — the TODOs below are meant to use these.
import eval.__main__ as harness  # noqa: E402, F401, I001
from pf_stack import distance_field  # noqa: E402, F401
from robotics_ai.planning import astar_grid, inflate_grid  # noqa: E402, F401
from sim import INFLATE_CELLS, RESOLUTION, Simulator, cell_to_world, world_to_cell  # noqa: E402, F401


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for k successes in n trials.

    Use this rather than the normal approximation p +- z*sqrt(p(1-p)/n),
    which returns the degenerate interval [1.0, 1.0] for 8/8 and [0, 0]
    for 0/20 — precisely the small-sample cases you care about.

    Sanity checks once you've written it:
        wilson(8, 8)   -> upper 1.0, lower about 0.68  (NOT [1, 1])
        wilson(0, 20)  -> lower 0.0, upper about 0.16  (NOT [0, 0])

    TODO.
    """
    raise NotImplementedError("student_evaluate: wilson")


def world_properties(seed: int) -> dict:
    """Difficulty descriptors for one world, computed WITHOUT simulating.

    Return {"seed", "clearance_m", "length_m"}.

    Stratifying on outcomes would be circular — you'd be defining "hard"
    as "the ones it failed." These are properties of the world alone.

      clearance_m: how tight the route is. Take `distance_field(sim.grid)`
                   (metres, after scaling by RESOLUTION), sample it along
                   the A*-optimal path, and summarize. Prefer a low
                   percentile over the raw minimum — one grazed corner
                   shouldn't define a whole world.
      length_m:    the A*-optimal path length.

    Use astar_grid(inflate_grid(sim.grid, INFLATE_CELLS), start, goal) with
    world_to_cell / cell_to_world. Return NaN clearance if no path exists.

    TODO.
    """
    raise NotImplementedError("student_evaluate: world_properties")


def build_suite(episodes: int, base_seed: int) -> list[dict]:
    """Assign every world a stratum label.

    Cut at the pool's own medians rather than fixed constants, so the
    design doesn't silently change meaning when the world generator does.
    Four strata: {tight,open} x {long,short}.

    TODO.
    """
    raise NotImplementedError("student_evaluate: build_suite")


def summarize(rows: list[dict], key: str = "success") -> dict:
    """Aggregate episode rows into {"k", "n", "rate", "lo", "hi"}.

    `key="success"` counts successes; anything else counts
    collision-free episodes (`r["collisions"] == 0`).

    TODO.
    """
    raise NotImplementedError("student_evaluate: summarize")


def check(results: list[dict]) -> int:
    """Return 0 if the candidate is demonstrably worse, 1 otherwise.

    Three claims, and the third is the one that matters:

      1. the incumbent hasn't regressed          (rate >= 0.85)
      2. the candidate is below the ship bar     (rate <= 0.70)
      3. the intervals DO NOT OVERLAP

    Without (3) you have a difference in point estimates, which is not the
    same as having shown a difference. If your sample is too small to
    resolve the gap, this must fail — a gate that reports an unearned
    difference is worse than no gate, because people believe it.

    TODO.
    """
    raise NotImplementedError("student_evaluate: check")


# ---------------- given: harness plumbing ----------------

def score(stack_name: str, suite: list[dict]) -> dict:
    """Run one stack over the suite using the incumbent's own harness.

    Note what this does NOT do: invent a new scoring path. The candidate is
    judged by the same harness, the same seeds and the same rubric as the
    stack it wants to replace. A candidate evaluated by its own bespoke
    script is not comparable to anything.
    """
    mod = importlib.import_module(stack_name)
    return {"stack": stack_name,
            "episodes": [{**harness.run_episode(mod, p["seed"]),
                          "stratum": p["stratum"]} for p in suite]}


def report(results: list[dict], suite: list[dict]) -> None:
    strata = sorted({p["stratum"] for p in suite})
    print(f"\nscenario suite — {len(suite)} worlds\n")
    for res in results:
        print(f"\n{res['stack']}")
        for st in strata + ["ALL"]:
            rows = (res["episodes"] if st == "ALL"
                    else [r for r in res["episodes"] if r["stratum"] == st])
            s = summarize(rows)
            print(f"  {st:<12} {s['k']:>3}/{s['n']:<3} [{s['lo']:.2f}-{s['hi']:.2f}]")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stacks", nargs="+", default=["bc_stack", "reference_stack"])
    ap.add_argument("--episodes", type=int, default=48)
    ap.add_argument("--seed", type=int, default=1000,
                    help="held out from collect.py's training pool by default")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    suite = build_suite(args.episodes, args.seed)
    results = [score(s, suite) for s in args.stacks]
    report(results, suite)
    return check(results) if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
