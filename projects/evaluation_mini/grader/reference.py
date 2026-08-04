"""Reference implementation for the evaluation mini-project."""

from __future__ import annotations

import numpy as np


def coverage_gaps(suite, factors):
    """Factor combinations the suite never exercises.

    Returns a sorted list of tuples, one per missing cell, with the values
    in the order the factor names appear in `factors`.
    """
    names = list(factors)
    present = {tuple(s[n] for n in names) for s in suite}
    everything = [()]
    for n in names:
        everything = [c + (v,) for c in everything for v in factors[n]]
    return sorted(c for c in everything if c not in present)


def stratified_rates(results, key="stratum"):
    """Per-stratum (successes, n, rate) plus the pooled rate.

    Returns {"strata": {name: (successes, n, rate)}, "pooled": rate}.
    """
    strata = {}
    for r in results:
        s, n = strata.get(r[key], (0, 0))
        strata[r[key]] = (s + int(bool(r["success"])), n + 1)
    out = {k: (s, n, s / n) for k, (s, n) in strata.items()}
    total_s = sum(s for s, _, _ in out.values())
    total_n = sum(n for _, n, _ in out.values())
    return {"strata": out, "pooled": total_s / total_n if total_n else 0.0}


def simpson_reversal(a_results, b_results, key="stratum"):
    """True when B beats A in every shared stratum and loses on the pooled
    rate — the aggregate disagreeing with every part of itself.
    """
    a = stratified_rates(a_results, key)
    b = stratified_rates(b_results, key)
    shared = set(a["strata"]) & set(b["strata"])
    if not shared:
        return False
    every = all(b["strata"][k][2] > a["strata"][k][2] for k in shared)
    return bool(every and b["pooled"] < a["pooled"])


def dedupe_failures(records, tol):
    """One representative per cluster of near-identical failures.

    Greedy in input order: a record joins the first existing cluster whose
    representative is within `tol`, otherwise it starts one. Returns the
    representatives, in the order they were first seen.
    """
    reps = []
    for r in records:
        f = np.asarray(r["features"], dtype=float)
        if any(float(np.linalg.norm(f - np.asarray(p["features"], dtype=float))) <= tol
               for p in reps):
            continue
        reps.append(r)
    return reps


def coreset(points, k):
    """Farthest-point traversal: k indices that spread over the pool.

    Seeded with the point farthest from the mean, then greedily adding the
    point whose distance to the nearest already-chosen point is largest.
    Ties resolve to the lowest index.
    """
    x = np.asarray(points, dtype=float)
    if k <= 0 or len(x) == 0:
        return []
    d0 = np.linalg.norm(x - x.mean(axis=0), axis=1)
    chosen = [int(np.argmax(d0))]
    dist = np.linalg.norm(x - x[chosen[0]], axis=1)
    while len(chosen) < min(k, len(x)):
        nxt = int(np.argmax(dist))
        chosen.append(nxt)
        dist = np.minimum(dist, np.linalg.norm(x - x[nxt], axis=1))
    return chosen


def cusum(x, target, k, h):
    """One-sided upper CUSUM. Returns the first index at which the
    statistic exceeds `h`, or None.

        S_0 = 0,  S_t = max(0, S_{t-1} + (x_t - target) - k)
    """
    s = 0.0
    for i, v in enumerate(np.asarray(x, dtype=float)):
        s = max(0.0, s + (float(v) - target) - k)
        if s > h:
            return i
    return None


def psi(expected, actual, edges):
    """Population stability index between two samples over fixed bin edges.

        PSI = sum_i (a_i - e_i) * ln(a_i / e_i)

    Empty bins are floored at a small epsilon so the logarithm is finite.
    """
    eps = 1e-6
    e = np.asarray(expected, dtype=float)
    a = np.asarray(actual, dtype=float)
    ec = np.histogram(e, bins=edges)[0].astype(float)
    ac = np.histogram(a, bins=edges)[0].astype(float)
    ep = np.maximum(ec / max(ec.sum(), 1.0), eps)
    ap = np.maximum(ac / max(ac.sum(), 1.0), eps)
    return float(np.sum((ap - ep) * np.log(ap / ep)))
