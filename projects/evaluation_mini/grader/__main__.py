"""Autograder for the evaluation mini-project.

Usage (from projects/evaluation_mini/):
    python -m grader [--seed N] [--reference]
"""

from __future__ import annotations

import argparse
import secrets
import sys
import traceback

import numpy as np
from evalkit import (
    FACTORS,
    drifting_stream,
    embedding_pool,
    failure_log,
    full_factorial,
    stratified_results,
    suite_with_gaps,
)

from grader import reference as ref


def _check_coverage(mod, seed):
    rng = np.random.default_rng(seed)

    assert mod.coverage_gaps(full_factorial(), FACTORS) == [], (
        "a full-factorial suite has no gaps")

    suite = suite_with_gaps(rng, n_missing=5)
    gaps = mod.coverage_gaps(suite, FACTORS)
    assert len(gaps) == 5, f"expected 5 uncovered cells, got {len(gaps)}"
    assert gaps == sorted(gaps), "the result must be sorted"
    assert all(isinstance(g, tuple) and len(g) == 3 for g in gaps), (
        "each gap is a tuple with one value per factor, in factor order")

    present = {tuple(s[n] for n in FACTORS) for s in suite}
    assert not (set(gaps) & present), "a reported gap must not be in the suite"
    assert len(present) + len(gaps) == 24, (
        "the suite plus the gaps must be the whole factorial (24 cells)")

    # A suite can be large and still blind: fifty scenarios that never vary
    # one factor leave that factor's other levels untested.
    narrow = [dict(c, lighting="day") for c in full_factorial()] * 3
    ngaps = mod.coverage_gaps(narrow, FACTORS)
    assert len(ngaps) == 16, (
        f"72 scenarios that only ever run in daylight leave 16 cells untested, "
        f"got {len(ngaps)} — suite SIZE is not suite coverage")


def _check_stratified(mod, seed):
    rng = np.random.default_rng(seed)
    a, _b = stratified_results(rng)

    ra = mod.stratified_rates(a)
    assert set(ra["strata"]) == {"easy", "hard"}
    for name, (s, n, rate) in ra["strata"].items():
        assert 0 <= s <= n and n > 0, f"{name}: bad counts"
        assert abs(rate - s / n) < 1e-12, f"{name}: rate must be successes/n"
    tot_s = sum(s for s, _, _ in ra["strata"].values())
    tot_n = sum(n for _, n, _ in ra["strata"].values())
    assert abs(ra["pooled"] - tot_s / tot_n) < 1e-12, (
        "pooled is over all records, not the mean of the per-stratum rates")
    assert tot_n == len(a), "every record belongs to exactly one stratum"


def _check_simpson(mod, seed):
    rng = np.random.default_rng(seed)
    a, b = stratified_results(rng)

    ra, rb = mod.stratified_rates(a), mod.stratified_rates(b)
    for k in ("easy", "hard"):
        assert rb["strata"][k][2] > ra["strata"][k][2], (
            f"B should win the {k} stratum ({rb['strata'][k][2]:.3f} vs "
            f"{ra['strata'][k][2]:.3f})")
    assert rb["pooled"] < ra["pooled"], (
        f"and lose the pooled rate ({rb['pooled']:.3f} vs {ra['pooled']:.3f}) — "
        f"B was run on four times as many hard scenarios")

    assert mod.simpson_reversal(a, b) is True, (
        "this is a reversal: B is better everywhere and worse overall")
    assert mod.simpson_reversal(a, a) is False, "a policy does not reverse itself"
    assert mod.simpson_reversal(b, a) is False, (
        "the relation is directional — A does not beat B in every stratum")


def _check_dedupe(mod, seed):
    rng = np.random.default_rng(seed)
    records, centers = failure_log(rng, n_bugs=12, n_records=400)

    reps = mod.dedupe_failures(records, tol=2.0)
    assert len(reps) == 12, (
        f"400 failure reports are 12 distinct bugs; got {len(reps)} "
        f"representatives")
    bugs = [r["bug"] for r in reps]
    assert len(set(bugs)) == 12, (
        f"each representative should be a different bug, got {sorted(bugs)}")

    # Order matters: the representative of each cluster is its first sighting.
    first_seen = {}
    for r in records:
        first_seen.setdefault(r["bug"], r["episode"])
    assert [r["episode"] for r in reps] == [first_seen[b] for b in bugs], (
        "each representative must be the FIRST record of its cluster, in "
        "input order — a deduplicated suite has to be reproducible")

    assert len(mod.dedupe_failures(records, tol=0.0)) == len(records), (
        "a zero tolerance keeps everything")
    assert len(mod.dedupe_failures(records, tol=1e6)) == 1, (
        "an enormous tolerance collapses to one")


def _check_coreset(mod, seed):
    rng = np.random.default_rng(seed)
    x = embedding_pool(rng, n=600)

    idx = mod.coreset(x, 30)
    assert len(idx) == 30, f"expected 30 indices, got {len(idx)}"
    assert len(set(idx)) == 30, "indices must be distinct"
    assert all(0 <= i < len(x) for i in idx), "indices must be in range"
    assert mod.coreset(x, 0) == [], "k=0 selects nothing"

    r = np.linalg.norm(x, axis=1)
    rim = r > 2.0
    picked_rim = float(np.mean(rim[np.asarray(idx)]))
    assert picked_rim > 0.5, (
        f"only {100*picked_rim:.0f}% of the selection is from the sparse rim. "
        f"The rim is 10% of the pool and all of the interesting episodes; "
        f"uniform sampling would return {100*float(np.mean(rim)):.0f}%")

    # The selection must actually spread: minimum pairwise distance beats a
    # random draw of the same size by a wide margin.
    def min_pair(sel):
        p = x[np.asarray(sel)]
        d = np.linalg.norm(p[:, None, :] - p[None, :, :], axis=-1)
        np.fill_diagonal(d, np.inf)
        return float(d.min())

    rand = rng.choice(len(x), size=30, replace=False)
    assert min_pair(idx) > 3.0 * min_pair(rand), (
        f"the coreset's closest pair is {min_pair(idx):.2f} against "
        f"{min_pair(rand):.2f} for a random draw — that ratio is the point")

    assert mod.coreset(x, 5) == idx[:5], (
        "farthest-point traversal is a prefix property: the first 5 of a "
        "30-selection are the same as a 5-selection")


def _check_drift(mod, seed):
    rng = np.random.default_rng(seed)

    stable = rng.normal(0.0, 1.0, size=600)
    assert mod.cusum(stable, target=0.0, k=0.6, h=8.0) is None, (
        "a stationary stream must not alarm at k=0.6, h=8.0")

    x = drifting_stream(rng, n=600, change_at=400, shift=1.0)
    at = mod.cusum(x, target=0.0, k=0.5, h=8.0)
    assert at is not None, "a 1 sigma shift at index 400 must be detected"
    assert at >= 400, f"detection at {at} — before the change is a false alarm"
    assert at < 480, (
        f"detection at {at}, i.e. {at-400} samples after the shift. A CUSUM "
        f"should catch this well inside 80")

    # The slack parameter is the whole design: raise k above the shift and
    # the statistic can no longer accumulate.
    assert mod.cusum(x, target=0.0, k=1.8, h=8.0) is None, (
        "with k larger than the shift, drift accumulates nothing — k is not "
        "a tuning knob, it is a statement about the smallest shift you care "
        "about")

    edges = np.linspace(-4.0, 4.0, 11)
    big = rng.normal(0.0, 1.0, size=4000)
    assert mod.psi(big[:2000], big[2000:], edges) < 0.05, (
        "two halves of the same distribution are stable")
    shifted = rng.normal(1.2, 1.0, size=2000)
    p = mod.psi(big[:2000], shifted, edges)
    assert p > 0.25, f"a 1.2 sigma shift should read as a different population, got PSI {p:.3f}"
    assert mod.psi(big, big, edges) < 1e-9, "a sample against itself is 0"

    empty_side = rng.normal(6.0, 0.1, size=200)   # entirely outside the bins
    assert np.isfinite(mod.psi(big[:2000], empty_side, edges)), (
        "a sample that misses every bin must give a finite PSI, not inf or "
        "nan — empty bins are the signal, so they cannot be the crash")

    # The rule of thumb has a sample size attached to it, and nobody quotes
    # the sample size. Measure the noise floor at n=300 directly.
    floor = float(np.mean([
        mod.psi(w[:300], w[300:], edges)
        for w in (rng.normal(0.0, 1.0, size=600) for _ in range(200))
    ]))
    assert floor > 0.06, (
        f"PSI between two halves of the SAME distribution averages {floor:.3f} "
        f"at n=300 — got {floor:.3f}, which is suspiciously low")
    assert floor > 0.5 * 0.1, (
        f"the noise floor at n=300 is {floor:.3f}, i.e. the '<0.1 is stable' "
        f"rule of thumb is at the level of pure sampling noise. The threshold "
        f"is a statement about large samples and it is always quoted without "
        f"one.")


TASKS = [
    ("scenario-suite coverage", 15, _check_coverage),
    ("stratified rates", 10, _check_stratified),
    ("Simpson reversal", 15, _check_simpson),
    ("failure-log deduplication", 20, _check_dedupe),
    ("coreset curation", 20, _check_coreset),
    ("drift detection (CUSUM + PSI)", 20, _check_drift),
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
            print("Could not import student.py — run from projects/evaluation_mini/")
            return 2

    total = earned = 0
    width = max(len(n) for n, _, _ in TASKS)
    print(f"Evaluation mini-project — seed {seed}\n")
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
