"""Path tracking for differential-drive robots: pure pursuit.

A path is an (N, 2) polyline in the world frame. Pure pursuit chases a
goal point a fixed *lookahead* distance ahead along the path, steering
with the curvature of the circular arc through that point — geometrically
simple, remarkably robust, and the classic first trajectory follower.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from robotics_ai.geometry.transforms2d import se2, se2_inverse, transform_points

FloatArray = npt.NDArray[np.float64]


def nearest_path_index(pose_xy: FloatArray, path: FloatArray) -> int:
    """Index of the path vertex closest to the given position."""
    d = path - np.asarray(pose_xy)[None, :]
    return int(np.argmin(np.hypot(d[:, 0], d[:, 1])))


def cross_track_error(pose: FloatArray, path: FloatArray) -> float:
    """Signed lateral distance from pose to the path (positive = path is left)."""
    x, y, theta = pose
    i = nearest_path_index(np.array([x, y]), path)
    p_body = transform_points(se2_inverse(se2(x, y, theta)), path[i])
    return float(p_body[1])


def lookahead_point(pose: FloatArray, path: FloatArray, lookahead: float) -> FloatArray:
    """First path point at least `lookahead` ahead of the nearest vertex.

    Falls back to the final vertex near the path's end.
    """
    xy = np.asarray(pose[:2])
    start = nearest_path_index(xy, path)
    for j in range(start, len(path)):
        if np.hypot(*(path[j] - xy)) >= lookahead:
            return path[j]
    return path[-1]


def pure_pursuit(pose: FloatArray, path: FloatArray, lookahead: float, v: float) -> float:
    """Angular-velocity command tracking the path at speed ``v``.

    The goal point in the body frame (x_b, y_b) defines an arc of curvature
    kappa = 2 y_b / L^2 through the robot and the goal; omega = v * kappa.
    """
    if lookahead <= 0:
        raise ValueError("lookahead must be positive")
    goal = lookahead_point(pose, path, lookahead)
    x, y, theta = pose
    g_body = transform_points(se2_inverse(se2(x, y, theta)), goal)
    L2 = float(g_body @ g_body)
    if L2 < 1e-12:
        return 0.0
    kappa = 2.0 * float(g_body[1]) / L2
    return v * kappa
