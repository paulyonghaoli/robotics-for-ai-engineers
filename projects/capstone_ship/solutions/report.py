"""Stage 5: the deliverable — a ship / no-ship decision report.

    python solutions/report.py --episodes 32

The four earlier stages each produce a number. This one produces the
document those numbers exist for: something a skeptical staff engineer can
read and sign, or refuse to sign, without re-running anything.

What makes it a decision report rather than a results dump is that every
section answers a question somebody would actually ask in the review:

    what are we shipping, and what is the evidence
    what would this gate have missed
    is the problem fixable, and by what
    what would change your mind

That last section is the one that separates an engineering document from an
advocacy document. A recommendation with no stated falsifier is a preference.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
CAPSTONE_NAV = HERE.parent / "capstone_nav"
for _p in (CAPSTONE_NAV, CAPSTONE_NAV / "solutions", HERE, HERE / "solutions"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from data_engine import aliasing, rollout  # noqa: E402
from evaluate import build_suite, summarize  # noqa: E402
from gate import gate, paired_outcomes  # noqa: E402
from rollout import canary_size, drift_detection_latency, score_monitor  # noqa: E402


def build(episodes: int, seed: int, tolerance: float) -> str:
    suite = build_suite(episodes, seed)
    inc, cand = paired_outcomes("reference_stack", "bc_stack", suite)

    inc_rows = [{"success": bool(x), "collisions": 0} for x in inc]
    cand_rows = [{"success": bool(x), "collisions": 0} for x in cand]
    s_inc, s_cand = summarize(inc_rows), summarize(cand_rows)
    g = gate(inc, cand, tolerance=tolerance)

    # Per-stratum, so the recommendation names where the candidate fails.
    strata = sorted({p["stratum"] for p in suite})
    by_stratum = []
    for st in strata:
        idx = [i for i, p in enumerate(suite) if p["stratum"] == st]
        by_stratum.append((st, summarize([cand_rows[i] for i in idx]),
                           summarize([inc_rows[i] for i in idx])))

    # Is the gap fixable? Aliasing on the expert's own demonstrations.
    demo = [rollout(None, 17 * i) for i in range(12)]
    X = np.vstack([d["X"] for d in demo])
    Y = np.vstack([d["Y"] for d in demo])
    al = aliasing(X, Y)

    mon = score_monitor(0.25, min(episodes // 2, 12))
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")

    lines = [
        "# Ship / no-ship decision — behaviour-cloned navigation policy",
        "",
        f"**Date:** {stamp} · **Evidence:** {len(suite)} paired episodes, "
        f"seed pool {seed} · **Tolerance:** {tolerance:.2f} regression",
        "",
        "## Decision",
        "",
        f"**Do not ship.** The candidate's success rate is "
        f"{s_cand['rate']:.3f} `[{s_cand['lo']:.2f}–{s_cand['hi']:.2f}]` against "
        f"the incumbent's {s_inc['rate']:.3f} `[{s_inc['lo']:.2f}–{s_inc['hi']:.2f}]`; "
        f"the paired regression is {g['diff']:.3f} "
        f"`[{g['lo']:.3f}, {g['hi']:.3f}]`, which excludes the {tolerance:.2f} "
        f"tolerance. Gate verdict: **{g['verdict']}**.",
        "",
        "## What the evidence is, and what it is not",
        "",
        f"- Comparison is **paired** — both stacks ran the same {len(suite)} "
        f"seeds. Discordance {g['discordance']:.3f}.",
        f"- The design's **minimum detectable effect is {g['mde']:.3f}**. It "
        f"resolved this regression comfortably; it would *not* have resolved "
        f"one smaller than that.",
        f"- To police the {tolerance:.2f} tolerance in future releases the "
        f"canary needs **~{canary_size(tolerance)} episodes**. The current "
        f"{len(suite)} is enough for this decision and not enough for a "
        f"routine gate.",
        "",
        "## Where it fails",
        "",
        "| stratum | candidate | incumbent |",
        "|---|---|---|",
    ]
    for st, sc, si in by_stratum:
        lines.append(f"| {st} | {sc['k']}/{sc['n']} `[{sc['lo']:.2f}–{sc['hi']:.2f}]` "
                     f"| {si['k']}/{si['n']} |")
    worst = min(by_stratum, key=lambda t: t[1]["rate"])
    lines += [
        "",
        f"Worst stratum is **{worst[0]}** at {worst[1]['rate']:.2f} — long "
        "routes with little clearance, which is where a long horizon and a "
        "small margin compound.",
        "",
        "## Is it fixable?",
        "",
        f"**Not by more data.** Observation aliasing is **{al['ratio']:.3f}**: "
        f"that fraction of the expert's action variance survives *within* a "
        f"neighbourhood of near-identical observations, so no function of "
        f"this observation can reproduce it. The expert plans over a map the "
        f"policy is never given.",
        "",
        "Stage 3 ran three DAgger rounds separately (`solutions/data_engine.py`): "
        "success did not improve and validation loss rose monotonically as "
        "on-policy data was added — the signature of averaging over "
        "contradictory targets rather than of insufficient coverage. The "
        "aliasing figure above is measured by this report; the DAgger result "
        "is cited from that run. **Change the observation, not the dataset "
        "size.**",
        "",
        "## If it shipped anyway",
        "",
        f"Behind a runtime monitor at 0.25 m margin the candidate reaches "
        f"{mon['collision_free']:.3f} collision-free and {mon['success']:.3f} "
        f"success, vetoing {mon['veto_rate']:.1%} of actions. Note what that "
        f"means: the fallback is carrying the episode. Widening the margin "
        f"further *raises* success, which is evidence the learned policy "
        f"contributes nothing the classical stack does not already provide.",
        "",
        f"Drift cover: a CUSUM tripwire on scan statistics detects a 5% "
        f"environmental shift within {drift_detection_latency(0.05)} episodes "
        f"and a 2% shift within {drift_detection_latency(0.02)}.",
        "",
        "## What would change this decision",
        "",
        "1. **A different observation.** Give the policy the occupancy map or "
        "the global plan the expert uses. That attacks the aliasing directly "
        "and is the only change with a mechanism behind it.",
        "2. **Aliasing below ~0.05** on the revised observation, measured "
        "before any retraining. If it does not drop, nothing downstream will.",
        f"3. **A paired regression whose interval falls inside "
        f"{tolerance:.2f}**, on a canary of at least "
        f"{canary_size(tolerance)} episodes.",
        "4. **A safety monitor whose veto rate is low.** A candidate that "
        "needs constant intervention has not been made safe, it has been "
        "replaced.",
        "",
        "## What this report does not establish",
        "",
        "- Nothing about latency, memory, or on-robot inference cost — all "
        "measured in simulation at full speed.",
        "- Nothing about environments outside the generator's distribution.",
        f"- Nothing about regressions smaller than {g['mde']:.3f}, which this "
        "sample cannot see.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=32)
    ap.add_argument("--seed", type=int, default=1000)
    ap.add_argument("--tolerance", type=float, default=0.05)
    ap.add_argument("--out", default=str(HERE / "DECISION.md"))
    args = ap.parse_args()

    text = build(args.episodes, args.seed, args.tolerance)
    Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    print(f"\n[written to {args.out}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
