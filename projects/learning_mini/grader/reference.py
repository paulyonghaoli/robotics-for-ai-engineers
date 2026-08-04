"""Reference implementation for the robot-learning mini-project."""

from __future__ import annotations

import numpy as np
from learnkit import (
    CLEARANCE_RAD,
    NOMINAL_FRICTION,
    OUT_OF_DISTRIBUTION_SUCCESS,
    REAL_FRICTION,
    sim_success,
)

# --- 1. Mean collapse -----------------------------------------------------

def mse_optimal(actions):
    """The single action minimizing squared error over the demonstrations.

    It is the mean, always, whatever the shape of the distribution.
    """
    return float(np.mean(np.asarray(actions, dtype=float)))


def mse_of(prediction, actions):
    a = np.asarray(actions, dtype=float)
    return float(np.mean((a - float(prediction)) ** 2))


def is_feasible(action):
    """True if the steering angle clears the obstacle."""
    return bool(abs(float(action)) >= CLEARANCE_RAD)


# --- 2. Discretization ----------------------------------------------------

def action_histogram(actions, edges):
    """Empirical action distribution over fixed bins."""
    counts = np.histogram(np.asarray(actions, dtype=float), bins=edges)[0]
    return counts / max(counts.sum(), 1)


def bin_centers(edges):
    e = np.asarray(edges, dtype=float)
    return 0.5 * (e[:-1] + e[1:])


def argmax_action(actions, edges):
    """The most likely action under the discretized distribution."""
    p = action_histogram(actions, edges)
    return float(bin_centers(edges)[int(np.argmax(p))])


def sample_action(actions, edges, rng):
    """Draw from the discretized distribution."""
    p = action_histogram(actions, edges)
    c = bin_centers(edges)
    return float(rng.choice(c, p=p))


def feasible_rate(candidates):
    return float(np.mean([is_feasible(a) for a in candidates]))


# --- 3. Sim-to-real -------------------------------------------------------

def covers(width, real=REAL_FRICTION, nominal=NOMINAL_FRICTION):
    """True if the training range contains the value the robot actually
    has."""
    return bool(abs(float(real) - float(nominal)) <= float(width))


def real_success(width):
    """Success on the robot.

    Inside the training range the policy behaves as it does in simulation.
    Outside it, it is extrapolating and the number is whatever it is.
    """
    w = np.atleast_1d(np.asarray(width, dtype=float))
    inside = np.array([covers(x) for x in w])
    out = np.where(inside, sim_success(w), OUT_OF_DISTRIBUTION_SUCCESS)
    return float(out[0]) if np.isscalar(width) or np.ndim(width) == 0 else out


def best_width(widths, objective):
    """The randomization width maximizing `objective` (a function of
    width). Ties resolve to the smallest width."""
    w = np.asarray(widths, dtype=float)
    scores = np.array([float(np.atleast_1d(objective(x))[0]) for x in w])
    return float(w[int(np.argmax(scores))])


# --- 4. Checkpoint selection ----------------------------------------------

def best_by(checkpoints, key, maximize=True):
    """The checkpoint that wins on `key`."""
    pick = max if maximize else min
    return pick(checkpoints, key=lambda c: c[key])


def pearson(xs, ys):
    x = np.asarray(xs, dtype=float)
    y = np.asarray(ys, dtype=float)
    if x.std() == 0 or y.std() == 0:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def selection_regret(checkpoints):
    """Success given up by early-stopping on validation loss."""
    by_loss = best_by(checkpoints, "val_mse", maximize=False)
    by_success = best_by(checkpoints, "success", maximize=True)
    return float(by_success["success"] - by_loss["success"])
