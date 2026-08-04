"""Given material for the robot-learning mini-project.

A multimodal demonstration set, a sim-to-real parameter model, and a
checkpoint table. Nothing here is graded.
"""

from __future__ import annotations

import numpy as np

# --- Multimodality --------------------------------------------------------
#
# One state: an obstacle 2 m directly ahead. Two valid behaviours: steer
# left or steer right. The demonstrators are split roughly evenly, and each
# individual demonstration is a fine piece of driving.

CLEARANCE_RAD = 0.30            # anything smaller hits the obstacle
MODE_OFFSET = 0.60


def demonstrations(rng: np.random.Generator, n: int = 2000) -> np.ndarray:
    """Steering angles from `n` human demonstrations at the same state."""
    left = rng.random(n) < 0.5
    return np.where(left, MODE_OFFSET, -MODE_OFFSET) + rng.normal(0.0, 0.07, size=n)


ACTION_EDGES = np.linspace(-1.2, 1.2, 25)      # 24 bins, 0.1 rad wide


# --- Sim-to-real ----------------------------------------------------------
#
# The policy is trained with a friction coefficient sampled uniformly from
# [NOMINAL - w, NOMINAL + w]. The robot's actual surface is REAL_FRICTION,
# which nobody measured before training.

NOMINAL_FRICTION = 0.60
REAL_FRICTION = 0.85
WIDTHS = np.round(np.arange(0.05, 0.85, 0.05), 3)


def sim_success(width):
    """Success in the simulator the policy was trained in.

    Always in-distribution, so the only effect of widening the
    randomization is that the policy has to cover more cases with the same
    capacity.
    """
    return 0.98 - 0.40 * np.asarray(width, dtype=float)


OUT_OF_DISTRIBUTION_SUCCESS = 0.25


# --- Checkpoint selection -------------------------------------------------
#
# Twelve checkpoints from one behaviour-cloning run. Validation loss on
# held-out demonstrations falls monotonically. On-robot success does not.

CHECKPOINTS = [
    {"epoch": 1, "val_mse": 0.0910, "success": 0.42},
    {"epoch": 2, "val_mse": 0.0740, "success": 0.55},
    {"epoch": 3, "val_mse": 0.0630, "success": 0.63},
    {"epoch": 4, "val_mse": 0.0550, "success": 0.69},
    {"epoch": 5, "val_mse": 0.0495, "success": 0.71},
    {"epoch": 6, "val_mse": 0.0450, "success": 0.68},
    {"epoch": 7, "val_mse": 0.0415, "success": 0.65},
    {"epoch": 8, "val_mse": 0.0385, "success": 0.61},
    {"epoch": 9, "val_mse": 0.0360, "success": 0.57},
    {"epoch": 10, "val_mse": 0.0340, "success": 0.53},
    {"epoch": 11, "val_mse": 0.0322, "success": 0.50},
    {"epoch": 12, "val_mse": 0.0308, "success": 0.48},
]
