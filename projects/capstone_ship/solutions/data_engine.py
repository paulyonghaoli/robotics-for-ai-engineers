"""Stage 3: the data engine, and the ceiling it cannot pass.

    python solutions/data_engine.py --rounds 3

Stage 1 showed the candidate is worse. Stage 2 built a gate that proves it.
This stage asks the question that actually decides what to do next:
**is this fixable with more data?**

Two mechanisms produce the same symptom — a policy that scores well offline
and badly in the loop — and they have completely different responses:

  compounding error       the policy drifts to states the expert never
                          visited, where it has no training signal.
                          FIXABLE: collect labels at the learner's own
                          states. This is DAgger.

  an unrealizable expert  the expert used information the policy cannot see,
                          so the SAME observation maps to different expert
                          actions in different situations. NOT FIXABLE by
                          data: you are asking the policy to be a function
                          of something it was never given.

Telling them apart is a measurement, not an opinion, and this module makes
it: `aliasing` reports how much expert action variance survives *within* a
neighbourhood of identical observations. Variance that survives is variance
no policy of that observation can ever explain, and it sets a floor on
achievable loss that more episodes cannot lower.
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

import reference_stack  # noqa: E402
from policy import MLPPolicy, featurize  # noqa: E402
from sim import Simulator  # noqa: E402

HERE = Path(__file__).resolve().parent.parent


# ---------------- rollout and mining ----------------

def rollout(policy: MLPPolicy | None, seed: int, max_steps: int = 600) -> dict:
    """Run one episode. `policy=None` runs the expert.

    Returns the observations visited, the EXPERT's action at each of them
    (which is the DAgger label), and whether the episode succeeded.
    """
    sim = Simulator(seed)
    obs = sim.reset()
    expert = reference_stack.make_stack(sim)
    feats, labels = [], []
    done = False
    while not done:
        expert_action = expert.step(obs)          # label, always
        x = featurize(obs["scan"], obs["pose_meas"], sim.goal)
        feats.append(x)
        labels.append(list(expert_action))
        if policy is None:
            v, w = expert_action
        else:
            v, w = policy(x)
            v = float(np.clip(v, 0.0, 1.2))
            w = float(np.clip(w, -2.0, 2.0))
        obs, done = sim.step(v, w)
    return {"X": np.array(feats), "Y": np.array(labels),
            "success": bool(sim.at_goal), "seed": seed}


def mine_failures(policy, seeds) -> tuple[np.ndarray, np.ndarray, float]:
    """Roll the policy out and keep the states from episodes it FAILED.

    Failure mining rather than uniform collection: the states worth labelling
    are the ones the current policy actually gets into and cannot handle.
    """
    X, Y, ok = [], [], 0
    for s in seeds:
        r = rollout(policy, s)
        ok += r["success"]
        if not r["success"]:
            X.append(r["X"])
            Y.append(r["Y"])
    if not X:
        return np.zeros((0, 40)), np.zeros((0, 2)), ok / max(len(seeds), 1)
    return np.vstack(X), np.vstack(Y), ok / len(seeds)


# ---------------- curation ----------------

def coreset(X: np.ndarray, Y: np.ndarray, k: int, seed: int = 0):
    """Farthest-point selection: k samples spread across the feature space.

    Failure episodes are enormously redundant — a robot stuck against a wall
    produces hundreds of nearly identical frames. Taking them all buys
    storage and training time and almost no information, so pick a spread
    instead of a prefix.
    """
    n = len(X)
    if n <= k:
        return X, Y
    rng = np.random.default_rng(seed)
    picked = [int(rng.integers(n))]
    d = np.linalg.norm(X - X[picked[0]], axis=1)
    for _ in range(k - 1):
        i = int(np.argmax(d))
        picked.append(i)
        d = np.minimum(d, np.linalg.norm(X - X[i], axis=1))
    idx = np.array(picked)
    return X[idx], Y[idx]


# ---------------- the diagnostic ----------------

def aliasing(X: np.ndarray, Y: np.ndarray, radius: float = 0.25,
             sample: int = 400, seed: int = 0) -> dict:
    """How much expert action variance survives within one observation?

    For a sample of points, find every other point within `radius` in
    feature space and measure the spread of expert actions there. If the
    same observation carries different expert actions, no function of that
    observation can reproduce both — the residual is a FLOOR on achievable
    loss, and collecting more of the same data cannot lower it.

    Returns the aliased variance and the total variance; their ratio is the
    fraction of the expert's behaviour that is unexplainable from what the
    policy can see.
    """
    if len(X) < 20:
        return {"aliased_var": 0.0, "total_var": 0.0, "ratio": 0.0, "pairs": 0}
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(X), size=min(sample, len(X)), replace=False)
    within, pairs = [], 0
    for i in idx:
        d = np.linalg.norm(X - X[i], axis=1)
        near = np.nonzero(d < radius)[0]
        if len(near) < 3:
            continue
        within.append(float(np.mean(np.var(Y[near], axis=0))))
        pairs += len(near)
    if not within:
        return {"aliased_var": 0.0, "total_var": float(np.mean(np.var(Y, axis=0))),
                "ratio": 0.0, "pairs": 0}
    aliased = float(np.mean(within))
    total = float(np.mean(np.var(Y, axis=0)))
    return {"aliased_var": aliased, "total_var": total,
            "ratio": aliased / max(total, 1e-12), "pairs": pairs}


# ---------------- the loop ----------------

def train(X: np.ndarray, Y: np.ndarray, epochs: int = 60, seed: int = 0):
    p = MLPPolicy(seed=seed)
    stats = p.fit(X, Y, epochs=epochs, seed=seed)
    return p, stats


def evaluate(policy, seeds) -> float:
    return float(np.mean([rollout(policy, s)["success"] for s in seeds]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--train-episodes", type=int, default=40)
    ap.add_argument("--mine-episodes", type=int, default=24)
    ap.add_argument("--eval-episodes", type=int, default=24)
    ap.add_argument("--coreset", type=int, default=1500)
    args = ap.parse_args()

    train_seeds = [17 * i for i in range(args.train_episodes)]
    mine_seeds = [5000 + 17 * i for i in range(args.mine_episodes)]
    eval_seeds = [1000 + 17 * i for i in range(args.eval_episodes)]

    # Round 0: plain behaviour cloning on expert demonstrations.
    print("collecting expert demonstrations...")
    demos = [rollout(None, s) for s in train_seeds]
    X = np.vstack([d["X"] for d in demos])
    Y = np.vstack([d["Y"] for d in demos])
    expert_rate = float(np.mean([d["success"] for d in demos]))

    policy, stats = train(X, Y)
    history = [{"round": 0, "n": len(X), "success": evaluate(policy, eval_seeds),
                "val_mse": stats["final_val_mse"]}]
    print(f"\n  round 0: n={len(X):>6}  val_mse={stats['final_val_mse']:.4f}"
          f"  success={history[0]['success']:.3f}   (expert {expert_rate:.3f})")

    # DAgger rounds: label the states the LEARNER reaches.
    for r in range(1, args.rounds + 1):
        Xf, Yf, mined_rate = mine_failures(policy, mine_seeds)
        if len(Xf) == 0:
            print(f"  round {r}: no failures to mine")
            break
        Xc, Yc = coreset(Xf, Yf, args.coreset, seed=r)
        X = np.vstack([X, Xc])
        Y = np.vstack([Y, Yc])
        policy, stats = train(X, Y, seed=r)
        rate = evaluate(policy, eval_seeds)
        history.append({"round": r, "n": len(X), "success": rate,
                        "val_mse": stats["final_val_mse"]})
        print(f"  round {r}: n={len(X):>6}  val_mse={stats['final_val_mse']:.4f}"
              f"  success={rate:.3f}   (+{len(Xc)} mined from {mined_rate:.2f} on-policy)")

    # The diagnostic: how much of the expert is unexplainable from what the
    # policy can see?
    al = aliasing(X, Y)
    print(f"\n  observation aliasing: {al['ratio']:.3f} of expert action "
          f"variance survives within a neighbourhood")
    print(f"    (aliased {al['aliased_var']:.4f} of total {al['total_var']:.4f})")

    gained = history[-1]["success"] - history[0]["success"]
    remaining = expert_rate - history[-1]["success"]
    mse_trend = history[-1]["val_mse"] - history[0]["val_mse"]
    print(f"\n  after {len(history) - 1} rounds: success {gained:+.3f}, "
          f"val_mse {mse_trend:+.4f}, gap to expert {remaining:.3f}")

    if al["ratio"] > 0.15:
        print("\n  DIAGNOSIS: the expert is not realizable from this observation.")
        print(f"  {al['ratio']:.0%} of its action variance survives inside a "
              "neighbourhood of")
        print("  near-identical observations, so no function of that observation")
        print("  can reproduce it. DAgger assumes the problem is the state")
        print("  DISTRIBUTION and fixes it by labelling where the learner goes —")
        print("  but here the problem is OBSERVABILITY, so the new labels add")
        print("  conflict rather than coverage. That is why val_mse RISES as data")
        print("  is added: the network is averaging harder over contradictions,")
        print("  which is lesson 9.2's mode averaging.")
        print("\n  Change the observation, not the dataset size. More rounds spend")
        print("  compute to make the fit worse.")
    else:
        print("\n  DIAGNOSIS: little aliasing, so the remaining gap is coverage")
        print("  rather than observability — more on-policy rounds should help.")

    with open(HERE / "data_engine_results.json", "w", encoding="utf-8") as f:
        json.dump({"history": history, "aliasing": al,
                   "expert_rate": expert_rate}, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
