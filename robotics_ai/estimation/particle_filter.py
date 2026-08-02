"""Particle filter (sequential importance resampling).

State-agnostic: particles are an (N, d) array; the caller supplies the
motion function and the measurement likelihood. Resampling is systematic
(low-variance), the standard choice in robotics.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]


class ParticleFilter:
    def __init__(self, particles: FloatArray, rng: np.random.Generator | None = None) -> None:
        self.particles = np.atleast_2d(np.asarray(particles, dtype=np.float64))
        n = len(self.particles)
        self.weights = np.full(n, 1.0 / n)
        self.rng = rng if rng is not None else np.random.default_rng()

    @property
    def n(self) -> int:
        return len(self.particles)

    def predict(self, motion_fn: Callable[[FloatArray, np.random.Generator], FloatArray]) -> None:
        """Propagate every particle through the (stochastic) motion model."""
        self.particles = np.atleast_2d(motion_fn(self.particles, self.rng))

    def update(self, likelihood_fn: Callable[[FloatArray], FloatArray]) -> None:
        """Reweight by measurement likelihood p(z | particle)."""
        lik = np.asarray(likelihood_fn(self.particles), dtype=np.float64)
        self.weights = self.weights * lik
        total = self.weights.sum()
        if total < 1e-300:
            # Degenerate: measurement killed every particle. Reset to uniform
            # rather than dividing by zero; callers should watch for this.
            self.weights = np.full(self.n, 1.0 / self.n)
        else:
            self.weights = self.weights / total

    def neff(self) -> float:
        """Effective sample size; resample when this drops below ~n/2."""
        return float(1.0 / np.sum(self.weights**2))

    def resample(self) -> None:
        """Systematic (low-variance) resampling."""
        positions = (self.rng.random() + np.arange(self.n)) / self.n
        cumsum = np.cumsum(self.weights)
        cumsum[-1] = 1.0  # guard against float round-off
        idx = np.searchsorted(cumsum, positions)
        self.particles = self.particles[idx]
        self.weights = np.full(self.n, 1.0 / self.n)

    def estimate(self) -> FloatArray:
        """Weighted-mean state estimate."""
        return self.weights @ self.particles
