"""Reference implementation the grader compares against.

Yes, you can read this file. The scenarios are randomized per run, so the
only way to score 100 is to make your own functions actually correct —
at which point you didn't need this file.
"""

import numpy as np


def wrap_angle(theta):
    return float(-(np.mod(-theta + np.pi, 2 * np.pi) - np.pi))


def _se2(x, y, theta):
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s, x], [s, c, y], [0, 0, 1.0]])


def sensor_to_map(points, robot_pose, mount_pose):
    T = _se2(*robot_pose) @ _se2(*mount_pose)
    pts = np.asarray(points, dtype=np.float64)
    return pts @ T[:2, :2].T + T[:2, 2]


def heading_error(current, target):
    return wrap_angle(target - current)


def chain_poses(deltas):
    T = np.eye(3)
    for d in deltas:
        T = T @ _se2(*d)
    return float(T[0, 2]), float(T[1, 2]), wrap_angle(np.arctan2(T[1, 0], T[0, 0]))
