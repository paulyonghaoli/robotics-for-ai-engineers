"""The candidate, wrapped so the incumbent's harness can score it.

Same `make_stack(sim) -> obj.step(obs) -> (v, w)` contract as every stack
in capstone_nav. That is the whole point: the learned policy is judged by
the *same* harness, on the *same* seeds, against the *same* rubric as the
classical stack it wants to replace. A candidate evaluated by its own
bespoke script is not comparable to anything.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from policy import MLPPolicy, featurize

V_MAX, W_MAX = 1.2, 2.0
DEFAULT_WEIGHTS = Path(__file__).resolve().parent / "policy.npz"


class BCStack:
    def __init__(self, goal: np.ndarray, weights: str | Path = DEFAULT_WEIGHTS) -> None:
        self.goal = np.asarray(goal, dtype=float)
        self.policy = MLPPolicy.load(str(weights))
        self.last_estimate: np.ndarray | None = None
        # The harness reads `.path` when rendering. A reactive policy has no
        # plan to show, and saying so is more honest than drawing a line.
        self.path = None

    def step(self, obs: dict) -> tuple[float, float]:
        pose = obs["pose_meas"]
        self.last_estimate = pose
        x = featurize(obs["scan"], pose, self.goal)
        v, w = self.policy(x)
        return (float(np.clip(v, 0.0, V_MAX)), float(np.clip(w, -W_MAX, W_MAX)))


def make_stack(sim) -> BCStack:
    return BCStack(sim.goal)
