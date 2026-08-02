"""Localization project — implement the four functions below.

Your particle filter localizes a wandering robot from noisy odometry and
range-bearing landmark observations. The harness (world.py) runs the loop;
you supply the filter's organs. See README.md for the rubric.

Conventions: particles are an (N, 3) array of (x, y, theta); angles wrap
to (-pi, pi]. Constants (noise sigmas etc.) are imported from world.
"""

import numpy as np  # noqa: F401  (you'll want this)
from world import (  # noqa: F401
    BEARING_SIGMA,
    ODOM_V_SIGMA,
    ODOM_W_SIGMA,
    RANGE_SIGMA,
    WORLD_SIZE,
    arc_step,
    wrap,
)


def motion_update(particles, v, omega, dt, rng):
    """Propagate every particle through the noisy motion model.

    Sample per-particle actuation noise: v_i ~ N(v, ODOM_V_SIGMA),
    w_i ~ N(omega, ODOM_W_SIGMA), then arc-integrate over dt
    (world.arc_step handles vectorized poses). Return the new (N, 3) array.
    """
    raise NotImplementedError


def measurement_likelihood(particles, observations, landmarks):
    """p(observations | particle) for each particle -> (N,) array.

    observations: list of (landmark_id, range, bearing) with bearing
    measured relative to the robot's heading. Model both range and bearing
    as independent Gaussians (RANGE_SIGMA, BEARING_SIGMA) and multiply
    across observations. Two classics to get right:
      - wrap the bearing residual (predicted - measured) before squaring;
      - add a tiny floor (e.g. 1e-300) so no particle hits exact zero.
    """
    raise NotImplementedError


def systematic_resample(weights, rng):
    """Low-variance resampling: return (N,) integer indices."""
    raise NotImplementedError


def inject_random(particles, frac, rng):
    """Replace a random `frac` of particles with uniform poses in the world.

    The kidnapped-robot insurance: without it, a converged filter cannot
    recover from being wrong. Return the modified (N, 3) array.
    """
    raise NotImplementedError
