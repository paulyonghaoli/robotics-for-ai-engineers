"""The candidate: a behavior-cloning policy, in NumPy.

Deliberately small and dependency-free. This capstone is not about the
policy — it is about the apparatus that decides whether the policy ships —
and a policy you can train in twenty seconds on a laptop keeps the whole
loop reproducible inside CI.

What the policy sees is *less* than what the expert saw, and that is a
design choice worth being explicit about. `reference_stack` plans A* over
the true occupancy grid using a pose sensor. This policy gets a lidar scan
and the goal in its own frame — no map, no global plan. So there are two
distinct reasons it can fail:

  1. **Compounding error** (lesson 9.1). Small action errors move the robot
     to states the expert never visited, where errors are larger. O(eps*T^2).

  2. **The expert is not realizable.** No function of a single lidar scan
     can reproduce a decision that depended on a global plan. Around a
     concave obstacle the expert turns based on map structure the policy
     cannot see, so the *same observation* maps to different expert actions
     in different worlds.

Those two need separating, because they have different fixes — (1) wants
more on-policy data (DAgger), (2) wants a different observation space or
architecture, and no amount of data solves it. Stage 3 of the capstone
turns that distinction into a measurement rather than an opinion.
"""

from __future__ import annotations

import numpy as np

N_RAYS = 36
MAX_RANGE = 6.0
OBS_DIM = N_RAYS + 4        # scan + [goal range (scaled), sin, cos, 1/(1+range)]
ACT_DIM = 2                 # (v, w)


def featurize(scan: np.ndarray, pose: np.ndarray, goal: np.ndarray) -> np.ndarray:
    """Observation -> feature vector, in the ROBOT's frame.

    Body-frame goal, not world-frame: a policy fed world coordinates has to
    learn the rotation itself and generalizes poorly across start headings.
    This is lesson 1.1's point arriving as a modelling decision.
    """
    d = goal - pose[:2]
    rng = float(np.hypot(*d))
    bearing = float(np.arctan2(d[1], d[0]) - pose[2])
    return np.concatenate([
        np.clip(scan, 0.0, MAX_RANGE) / MAX_RANGE,
        [min(rng, 20.0) / 20.0, np.sin(bearing), np.cos(bearing), 1.0 / (1.0 + rng)],
    ])


class MLPPolicy:
    """Two hidden layers, tanh, trained with Adam. Nothing clever."""

    def __init__(self, hidden: int = 64, seed: int = 0) -> None:
        rng = np.random.default_rng(seed)
        dims = [OBS_DIM, hidden, hidden, ACT_DIM]
        pairs = list(zip(dims, dims[1:], strict=False))
        self.W = [rng.normal(0, np.sqrt(2.0 / a), (a, b)) for a, b in pairs]
        self.b = [np.zeros(b) for b in dims[1:]]
        self.x_mean = np.zeros(OBS_DIM)
        self.x_std = np.ones(OBS_DIM)

    # ---------------- inference ----------------

    def __call__(self, x: np.ndarray) -> np.ndarray:
        single = x.ndim == 1
        h = (np.atleast_2d(x) - self.x_mean) / self.x_std
        for W, b in zip(self.W[:-1], self.b[:-1], strict=True):
            h = np.tanh(h @ W + b)
        out = h @ self.W[-1] + self.b[-1]
        return out[0] if single else out

    # ---------------- training ----------------

    def _forward(self, x: np.ndarray):
        acts = [x]
        h = x
        for W, b in zip(self.W[:-1], self.b[:-1], strict=True):
            h = np.tanh(h @ W + b)
            acts.append(h)
        return acts, h @ self.W[-1] + self.b[-1]

    def fit(self, X: np.ndarray, Y: np.ndarray, epochs: int = 60,
            batch: int = 256, lr: float = 3e-3, seed: int = 0,
            val_frac: float = 0.15, verbose: bool = False) -> dict:
        rng = np.random.default_rng(seed)
        self.x_mean, self.x_std = X.mean(0), X.std(0) + 1e-6
        Xn = (X - self.x_mean) / self.x_std

        n_val = int(len(Xn) * val_frac)
        perm = rng.permutation(len(Xn))
        vi, ti = perm[:n_val], perm[n_val:]
        Xtr, Ytr, Xva, Yva = Xn[ti], Y[ti], Xn[vi], Y[vi]

        mW = [np.zeros_like(w) for w in self.W]
        vW = [np.zeros_like(w) for w in self.W]
        mb = [np.zeros_like(b) for b in self.b]
        vb = [np.zeros_like(b) for b in self.b]
        step = 0
        history = []

        for ep in range(epochs):
            order = rng.permutation(len(Xtr))
            for s in range(0, len(order), batch):
                idx = order[s:s + batch]
                xb, yb = Xtr[idx], Ytr[idx]
                acts, pred = self._forward(xb)
                g = 2.0 * (pred - yb) / len(idx)

                gW = [None] * len(self.W)
                gb = [None] * len(self.b)
                gW[-1] = acts[-1].T @ g
                gb[-1] = g.sum(0)
                delta = g @ self.W[-1].T
                for li in range(len(self.W) - 2, -1, -1):
                    delta = delta * (1.0 - acts[li + 1] ** 2)
                    gW[li] = acts[li].T @ delta
                    gb[li] = delta.sum(0)
                    if li > 0:
                        delta = delta @ self.W[li].T

                step += 1
                bc1, bc2 = 1 - 0.9 ** step, 1 - 0.999 ** step
                for li in range(len(self.W)):
                    mW[li] = 0.9 * mW[li] + 0.1 * gW[li]
                    vW[li] = 0.999 * vW[li] + 0.001 * gW[li] ** 2
                    self.W[li] -= lr * (mW[li] / bc1) / (np.sqrt(vW[li] / bc2) + 1e-8)
                    mb[li] = 0.9 * mb[li] + 0.1 * gb[li]
                    vb[li] = 0.999 * vb[li] + 0.001 * gb[li] ** 2
                    self.b[li] -= lr * (mb[li] / bc1) / (np.sqrt(vb[li] / bc2) + 1e-8)

            if (ep + 1) % 10 == 0 or ep == epochs - 1:
                tr = float(np.mean((self._forward(Xtr)[1] - Ytr) ** 2))
                va = float(np.mean((self._forward(Xva)[1] - Yva) ** 2))
                history.append({"epoch": ep + 1, "train_mse": tr, "val_mse": va})
                if verbose:
                    print(f"  epoch {ep + 1:>3}  train {tr:.5f}  val {va:.5f}")
        return {"history": history,
                "final_train_mse": history[-1]["train_mse"],
                "final_val_mse": history[-1]["val_mse"],
                "n_train": int(len(Xtr)), "n_val": int(len(Xva))}

    # ---------------- persistence ----------------

    def save(self, path: str) -> None:
        np.savez(path, x_mean=self.x_mean, x_std=self.x_std,
                 **{f"W{i}": w for i, w in enumerate(self.W)},
                 **{f"b{i}": b for i, b in enumerate(self.b)})

    @classmethod
    def load(cls, path: str) -> MLPPolicy:
        z = np.load(path)
        n = sum(1 for k in z.files if k.startswith("W"))
        p = cls()
        p.W = [z[f"W{i}"] for i in range(n)]
        p.b = [z[f"b{i}"] for i in range(n)]
        p.x_mean, p.x_std = z["x_mean"], z["x_std"]
        return p
