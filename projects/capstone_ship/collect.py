"""Stage 0: demonstrations from the incumbent, and the policy trained on them.

    python collect.py --episodes 60          # gather + train + save policy.npz

The expert is `reference_stack` — A* over the true map with a pose sensor.
It is a good expert: 20/20 on the rubric. That matters, because a weak
expert would confound "cloning is hard" with "the demonstrations were bad",
and this capstone needs those separated.

Features are recorded from the SAME observation the policy will get at
serving time -- the noisy `pose_meas`, not the simulator's true pose.
Training on privileged state you will not have in the field is train/serve
skew, and it produces a policy that validates beautifully and degrades the
moment it is deployed. The *labels* are the expert's actions, and the
expert is welcome to have used privileged information to choose them: that
asymmetry is what behavior cloning is. The features are not.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

CAPSTONE_NAV = Path(__file__).resolve().parent.parent / "capstone_nav"
sys.path.insert(0, str(CAPSTONE_NAV))
SOLUTIONS = CAPSTONE_NAV / "solutions"
sys.path.insert(0, str(SOLUTIONS))

import reference_stack  # noqa: E402
from policy import MLPPolicy, featurize  # noqa: E402
from sim import Simulator  # noqa: E402

HERE = Path(__file__).resolve().parent


def collect(episodes: int, base_seed: int = 0) -> tuple[np.ndarray, np.ndarray, dict]:
    X, Y = [], []
    reached = 0
    for i in range(episodes):
        seed = base_seed + 17 * i
        sim = Simulator(seed)
        obs = sim.reset()
        expert = reference_stack.make_stack(sim)
        done = False
        while not done:
            v, w = expert.step(obs)
            X.append(featurize(obs["scan"], obs["pose_meas"], sim.goal))
            Y.append([v, w])
            obs, done = sim.step(v, w)
        reached += bool(sim.at_goal)
    meta = {"episodes": episodes, "expert_success": reached / episodes,
            "samples": len(X)}
    return np.array(X), np.array(Y), meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=60)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--out", default=str(HERE / "policy.npz"))
    args = ap.parse_args()

    print(f"collecting {args.episodes} expert episodes...")
    X, Y, meta = collect(args.episodes, args.seed)
    print(f"  {meta['samples']} state-action pairs, "
          f"expert success {meta['expert_success']:.3f}")

    print("training behavior-cloning policy...")
    pol = MLPPolicy(seed=0)
    stats = pol.fit(X, Y, epochs=args.epochs, seed=0, verbose=True)
    pol.save(args.out)

    report = {**meta, **{k: v for k, v in stats.items() if k != "history"}}
    with open(HERE / "training_report.json", "w", encoding="utf-8") as f:
        json.dump({**report, "history": stats["history"]}, f, indent=1)
    print(f"\nsaved {args.out}")
    print(f"  val MSE {stats['final_val_mse']:.5f} on {stats['n_val']} held-out pairs")
    print("  NOTE: this number is what stage 1 exists to distrust.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
