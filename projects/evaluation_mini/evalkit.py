"""Given material for the evaluation mini-project.

Scenario factors, synthetic fleet logs, and the embedding used by the
curation checks. Nothing here is graded; you are not expected to modify it.
"""

from __future__ import annotations

import numpy as np

# The factors a navigation scenario suite varies. Full factorial is 24 cells.
FACTORS = {
    "lighting": ["day", "dusk", "night"],
    "weather": ["clear", "rain"],
    "traffic": ["none", "light", "heavy", "crowd"],
}


def full_factorial() -> list[dict]:
    """Every combination of every factor, in a fixed order."""
    out = []
    for light in FACTORS["lighting"]:
        for weather in FACTORS["weather"]:
            for traffic in FACTORS["traffic"]:
                out.append({"lighting": light, "weather": weather, "traffic": traffic})
    return out


def suite_with_gaps(rng: np.random.Generator, n_missing: int = 5) -> list[dict]:
    """A plausible hand-written suite: full factorial minus a few cells
    nobody thought to write down."""
    cells = full_factorial()
    drop = set(rng.choice(len(cells), size=n_missing, replace=False).tolist())
    return [c for i, c in enumerate(cells) if i not in drop]


def stratified_results(rng: np.random.Generator) -> tuple[list[dict], list[dict]]:
    """Two policies evaluated on the same strata, with unequal allocation.

    Constructed so that policy B wins in EVERY stratum and loses on the
    pooled rate, because the two policies were not run on the same mix.
    """
    strata = [
        # (name, A: n, A: rate, B: n, B: rate)
        ("easy", 800, 0.90, 200, 0.98),
        ("hard", 200, 0.40, 800, 0.55),
    ]
    a, b = [], []
    for name, na, ra, nb, rb in strata:
        for _ in range(na):
            a.append({"stratum": name, "success": bool(rng.random() < ra)})
        for _ in range(nb):
            b.append({"stratum": name, "success": bool(rng.random() < rb)})
    rng.shuffle(a)
    rng.shuffle(b)
    return a, b


def failure_log(rng: np.random.Generator, n_bugs: int = 12, n_records: int = 400):
    """A fleet failure log: `n_records` reports that are really `n_bugs`
    distinct problems, each seen many times with small variations."""
    centers = rng.uniform(-8.0, 8.0, size=(n_bugs, 4))
    # Keep the distinct bugs well separated so a threshold exists at all.
    for i in range(n_bugs):
        while True:
            d = np.linalg.norm(centers[i] - centers[:i], axis=1) if i else np.array([9e9])
            if d.min() > 4.0:
                break
            centers[i] = rng.uniform(-8.0, 8.0, size=4)

    records = []
    for j in range(n_records):
        b = int(rng.integers(n_bugs))
        records.append({
            "episode": f"e{j:04d}",
            "bug": b,                       # ground truth, for scoring only
            "features": centers[b] + rng.normal(0.0, 0.20, size=4),
        })
    rng.shuffle(records)
    return records, centers


def embedding_pool(rng: np.random.Generator, n: int = 600) -> np.ndarray:
    """An episode embedding pool with a dense blob and a sparse rim — the
    shape that makes uniform sampling a bad curation strategy."""
    dense = rng.normal(0.0, 0.35, size=(int(n * 0.9), 3))
    rim = rng.normal(0.0, 1.0, size=(n - int(n * 0.9), 3))
    rim = rim / np.linalg.norm(rim, axis=1, keepdims=True)
    rim = rim * rng.uniform(3.0, 4.0, size=(len(rim), 1))
    return np.vstack([dense, rim])


def drifting_stream(rng: np.random.Generator, n: int = 600, change_at: int = 400,
                    shift: float = 1.0) -> np.ndarray:
    """A monitored statistic that is stationary and then is not."""
    x = rng.normal(0.0, 1.0, size=n)
    x[change_at:] += shift
    return x
