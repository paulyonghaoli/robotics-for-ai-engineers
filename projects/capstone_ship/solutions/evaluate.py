"""Stage 1: the scenario suite.

    python evaluate.py --stacks bc_stack reference_stack --episodes 48

An aggregate success rate is the number everyone reports and the number
that tells you least. Two policies at 0.75 can differ completely in *which*
quarter they fail, and the one that fails in tight corridors is a different
product from the one that fails on long traverses.

So this stratifies the seed pool before scoring, by two properties of the
world that are computable without running anything:

  * **clearance** — the tightest gap along the optimal route, from a
    distance transform of the true occupancy grid
  * **length** — the A*-optimal path length

Strata are cut at the pool's own medians rather than at fixed constants, so
the design doesn't silently change meaning when the world generator does.
Every rate is reported with a Wilson interval, because a stratum holds a
dozen episodes and a point estimate from twelve trials is decoration
(lesson 10.1).
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
SOLUTIONS = CAPSTONE_NAV / "solutions"
sys.path.insert(0, str(SOLUTIONS))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import eval.__main__ as harness  # noqa: E402
from pf_stack import distance_field  # noqa: E402
from sim import INFLATE_CELLS, RESOLUTION, Simulator, cell_to_world, world_to_cell  # noqa: E402

from robotics_ai.planning import astar_grid, inflate_grid  # noqa: E402

HERE = Path(__file__).resolve().parent.parent


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval. Handles k=0 and k=n, which is the entire
    reason not to use the normal approximation here."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def world_properties(seed: int) -> dict:
    """Difficulty descriptors for one world, computed without simulating."""
    sim = Simulator(seed)
    field = distance_field(sim.grid) * RESOLUTION
    cells = astar_grid(inflate_grid(sim.grid, INFLATE_CELLS),
                       world_to_cell(sim.start[:2]), world_to_cell(sim.goal))
    if not cells:
        return {"seed": seed, "clearance_m": float("nan"), "length_m": float("nan")}
    pts = np.array([cell_to_world(c) for c in cells])
    seg = np.diff(pts, axis=0)
    length = float(np.hypot(seg[:, 0], seg[:, 1]).sum())
    clearances = np.array([field[c] for c in cells])
    # 10th percentile, not the min: one grazed corner shouldn't define a world.
    return {"seed": seed, "clearance_m": float(np.percentile(clearances, 10)),
            "length_m": length}


def build_suite(episodes: int, base_seed: int) -> list[dict]:
    props = [world_properties(base_seed + 17 * i) for i in range(episodes)]
    props = [p for p in props if np.isfinite(p["clearance_m"])]
    c_med = float(np.median([p["clearance_m"] for p in props]))
    l_med = float(np.median([p["length_m"] for p in props]))
    for p in props:
        tight = p["clearance_m"] <= c_med
        far = p["length_m"] > l_med
        p["stratum"] = f"{'tight' if tight else 'open'}/{'long' if far else 'short'}"
    return props


def score(stack_name: str, suite: list[dict]) -> dict:
    mod = importlib.import_module(stack_name)
    rows = []
    for p in suite:
        r = harness.run_episode(mod, p["seed"])
        rows.append({**r, "stratum": p["stratum"]})
    return {"stack": stack_name, "episodes": rows}


def summarize(rows: list[dict], key: str = "success") -> dict:
    k = sum(bool(r[key]) if key == "success" else r["collisions"] == 0 for r in rows)
    n = len(rows)
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": k / n if n else 0.0, "lo": lo, "hi": hi}


def report(results: list[dict], suite: list[dict]) -> None:
    strata = sorted({p["stratum"] for p in suite})
    print(f"\nscenario suite — {len(suite)} worlds, stratified by clearance / length\n")
    for st in strata:
        n = sum(1 for p in suite if p["stratum"] == st)
        print(f"  {st:<12} {n:>3} worlds")

    for res in results:
        print(f"\n{res['stack']}")
        hdr = f"  {'stratum':<12} {'success':>16} {'coll-free':>16} {'collisions':>11}"
        print(hdr + "\n  " + "-" * (len(hdr) - 2))
        for st in strata + ["ALL"]:
            rows = (res["episodes"] if st == "ALL"
                    else [r for r in res["episodes"] if r["stratum"] == st])
            s, c = summarize(rows), summarize(rows, "collisions")
            tot = sum(r["collisions"] for r in rows)
            label = "**ALL**" if st == "ALL" else st
            print(f"  {label:<12} {s['k']:>3}/{s['n']:<3} "
                  f"[{s['lo']:.2f}-{s['hi']:.2f}] {c['k']:>4}/{c['n']:<3} "
                  f"[{c['lo']:.2f}-{c['hi']:.2f}] {tot:>11}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stacks", nargs="+", default=["bc_stack", "reference_stack"])
    ap.add_argument("--episodes", type=int, default=48)
    ap.add_argument("--seed", type=int, default=1000,
                    help="held out from collect.py's training pool by default")
    ap.add_argument("--check", action="store_true",
                    help="exit nonzero unless the documented gap still holds")
    args = ap.parse_args()

    suite = build_suite(args.episodes, args.seed)
    results = [score(s, suite) for s in args.stacks]
    report(results, suite)

    with open(HERE / "suite_results.json", "w", encoding="utf-8") as f:
        json.dump({"suite": suite, "results": results}, f, indent=1)
    print(f"\nwrote {HERE / 'suite_results.json'}")

    if args.check:
        return check(results)
    return 0


def check(results: list[dict]) -> int:
    """Assert the finding this capstone is built on still holds.

    Not "did the script run" — a gate that only checks for a crash passes
    happily while the thing it guards rots. Three claims are checked, and
    the third is the one that matters: the incumbent's advantage must be
    larger than the uncertainty in measuring it. If the intervals overlap
    we have not *shown* a gap, whatever the point estimates say.
    """
    by_name = {r["stack"]: summarize(r["episodes"]) for r in results}
    inc, cand = by_name.get("reference_stack"), by_name.get("bc_stack")
    if inc is None or cand is None:
        print("\ncheck skipped: needs both reference_stack and bc_stack")
        return 0

    failures = []
    if inc["rate"] < 0.85:
        failures.append(f"incumbent regressed: {inc['rate']:.3f} < 0.85")
    if cand["rate"] > 0.70:
        failures.append(
            f"candidate scores {cand['rate']:.3f} > 0.70 — if behavior cloning "
            "really got this good, the capstone's premise needs rewriting, "
            "not the threshold")
    if cand["hi"] >= inc["lo"]:
        failures.append(
            f"intervals overlap: candidate [{cand['lo']:.2f}-{cand['hi']:.2f}] "
            f"vs incumbent [{inc['lo']:.2f}-{inc['hi']:.2f}] — the gap is not "
            "resolved at this sample size; run more episodes before claiming it")

    print("\ncheck:")
    for f in failures:
        print(f"  FAIL  {f}")
    if not failures:
        print(f"  PASS  incumbent {inc['rate']:.3f} [{inc['lo']:.2f}-{inc['hi']:.2f}] "
              f"> candidate {cand['rate']:.3f} [{cand['lo']:.2f}-{cand['hi']:.2f}], "
              "non-overlapping")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
