"""Frame Transforms mini-project — implement the four functions below.

Conventions (same as the curriculum):
- Angles in radians; wrapped interval is (-pi, pi].
- A pose (x, y, theta) of frame B in frame A is T_A_B: it maps points
  expressed in B into A.
- Point sets are (N, 2) float arrays.

NumPy only. Do not import robotics_ai.
"""

import numpy as np


def wrap_angle(theta: float) -> float:
    """Wrap a scalar angle to (-pi, pi]. wrap_angle(pi) == pi; wrap_angle(-pi) == pi."""
    raise NotImplementedError


def sensor_to_map(
    points: np.ndarray,
    robot_pose: tuple[float, float, float],
    mount_pose: tuple[float, float, float],
) -> np.ndarray:
    """Project sensor-frame points (N, 2) into the map frame.

    robot_pose: (x, y, theta) of the base in the map frame.
    mount_pose: (x, y, theta) of the sensor in the base frame (static mount).
    """
    raise NotImplementedError


def heading_error(current: float, target: float) -> float:
    """Signed shortest-arc error (target - current), wrapped to (-pi, pi]."""
    raise NotImplementedError


def chain_poses(deltas: list[tuple[float, float, float]]) -> tuple[float, float, float]:
    """Compose relative pose increments, starting from the origin (0, 0, 0).

    Each delta (dx, dy, dtheta) is expressed in the frame reached by the
    previous increment (classic wheel-odometry accumulation). Return the
    final (x, y, theta) in the world frame, theta wrapped to (-pi, pi].
    """
    raise NotImplementedError
