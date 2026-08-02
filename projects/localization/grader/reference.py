"""Reference solution the grader validates itself against.

Readable, as ever — and as ever, the randomized scenarios mean the only
way through is making your own implementation correct.
"""

import numpy as np
from world import (
    BEARING_SIGMA,
    ODOM_V_SIGMA,
    ODOM_W_SIGMA,
    RANGE_SIGMA,
    WORLD_SIZE,
    arc_step,
    wrap,
)


def motion_update(particles, v, omega, dt, rng):
    n = len(particles)
    v_i = rng.normal(v, ODOM_V_SIGMA, n)
    w_i = rng.normal(omega, ODOM_W_SIGMA, n)
    return arc_step(particles, v_i, w_i, dt)


def measurement_likelihood(particles, observations, landmarks):
    lik = np.ones(len(particles))
    for lm_id, r_meas, b_meas in observations:
        d = landmarks[lm_id] - particles[:, :2]
        r_pred = np.hypot(d[:, 0], d[:, 1])
        b_pred = wrap(np.arctan2(d[:, 1], d[:, 0]) - particles[:, 2])
        r_res = (r_pred - r_meas) / RANGE_SIGMA
        b_res = wrap(b_pred - b_meas) / BEARING_SIGMA
        lik = lik * np.exp(-0.5 * (r_res**2 + b_res**2))
    return lik + 1e-300


def systematic_resample(weights, rng):
    n = len(weights)
    positions = (rng.random() + np.arange(n)) / n
    cs = np.cumsum(weights)
    cs[-1] = 1.0
    return np.searchsorted(cs, positions)


def inject_random(particles, frac, rng):
    n = len(particles)
    k = max(1, int(frac * n))
    idx = rng.choice(n, k, replace=False)
    particles = particles.copy()
    particles[idx, 0] = rng.uniform(0, WORLD_SIZE, k)
    particles[idx, 1] = rng.uniform(0, WORLD_SIZE, k)
    particles[idx, 2] = rng.uniform(-np.pi, np.pi, k)
    return particles
