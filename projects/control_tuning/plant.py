"""Shared plants and reference paths for the control mini-project.

Given to you — you don't modify this file. Two systems live here:

  Cart        a saturating first-order speed plant. The actuator clips at
              U_MAX, which is the entire reason anti-windup exists. Ask it
              for a speed it cannot reach and a naive integrator will keep
              accumulating error it has no authority to fix.

  Arm         a two-link planar manipulator, for the Jacobian task.

Plus `reference_path`, a smooth path for the closed-loop tracking task.
"""

from __future__ import annotations

import numpy as np

DT = 0.05

# Cart: dv/dt = GAIN * u - DRAG * v, with u clipped to +-U_MAX.
# Reachable steady-state speed is therefore GAIN * U_MAX / DRAG = 3.75 m/s.
# Anything above that saturates the actuator forever.
U_MAX = 1.0
GAIN = 3.0
DRAG = 0.8
V_REACHABLE = GAIN * U_MAX / DRAG

# Differential drive limits, same as the capstone's.
V_MAX, W_MAX = 1.2, 2.0

# Two-link planar arm.
LINKS = (1.0, 0.8)


class Cart:
    """First-order speed plant with a hard actuator limit."""

    def __init__(self, v0: float = 0.0) -> None:
        self.v = float(v0)

    def step(self, u: float, dt: float = DT) -> float:
        u = float(np.clip(u, -U_MAX, U_MAX))
        self.v += dt * (GAIN * u - DRAG * self.v)
        return self.v


def forward_kinematics(q: np.ndarray, links: tuple[float, float] = LINKS) -> np.ndarray:
    """End-effector position of the two-link arm for joint angles q."""
    l1, l2 = links
    return np.array([
        l1 * np.cos(q[0]) + l2 * np.cos(q[0] + q[1]),
        l1 * np.sin(q[0]) + l2 * np.sin(q[0] + q[1]),
    ])


def arm_jacobian(q: np.ndarray, links: tuple[float, float] = LINKS) -> np.ndarray:
    """Analytic 2x2 Jacobian d(end-effector) / d(joint angles)."""
    l1, l2 = links
    s1, c1 = np.sin(q[0]), np.cos(q[0])
    s12, c12 = np.sin(q[0] + q[1]), np.cos(q[0] + q[1])
    return np.array([
        [-l1 * s1 - l2 * s12, -l2 * s12],
        [l1 * c1 + l2 * c12, l2 * c12],
    ])


def reference_path(n: int = 400) -> np.ndarray:
    """A smooth (N, 2) path: gentle S-curve then a tighter turn."""
    t = np.linspace(0.0, 1.0, n)
    x = 12.0 * t
    y = 2.0 * np.sin(2.0 * np.pi * t) + 0.8 * np.sin(4.0 * np.pi * t)
    return np.stack([x, y], axis=1)


def cross_track_errors(traj: np.ndarray, path: np.ndarray) -> np.ndarray:
    """Distance from each executed point to the nearest point on the path."""
    d = np.linalg.norm(traj[:, None, :] - path[None, :, :], axis=2)
    return d.min(axis=1)
