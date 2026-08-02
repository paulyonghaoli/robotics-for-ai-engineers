"""3D rotations: unit quaternions and rotation matrices.

Conventions
-----------
- Quaternions are scalar-first ``[w, x, y, z]`` float64 arrays (the ROS 2
  ``geometry_msgs`` wire format is scalar-LAST ``[x, y, z, w]`` — a classic
  interop bug; convert at the boundary).
- All quaternions returned by this module are unit-normalized.
- ``q`` and ``-q`` represent the same rotation (double cover of SO(3)).
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]


def quat_normalize(q: FloatArray) -> FloatArray:
    """Normalize to a unit quaternion. Raises on a near-zero norm."""
    q = np.asarray(q, dtype=np.float64)
    n = np.linalg.norm(q)
    if n < 1e-12:
        raise ValueError("cannot normalize near-zero quaternion")
    return q / n


def quat_from_axis_angle(axis: FloatArray, angle: float) -> FloatArray:
    """Unit quaternion for a rotation of ``angle`` radians about ``axis``."""
    axis = np.asarray(axis, dtype=np.float64)
    n = np.linalg.norm(axis)
    if n < 1e-12:
        raise ValueError("rotation axis must be non-zero")
    axis = axis / n
    half = 0.5 * angle
    return np.concatenate(([np.cos(half)], np.sin(half) * axis))


def quat_multiply(q1: FloatArray, q2: FloatArray) -> FloatArray:
    """Hamilton product ``q1 * q2``: rotate by q2 first, then q1.

    Composition order matches rotation-matrix multiplication:
    ``quat_to_matrix(quat_multiply(q1, q2)) == quat_to_matrix(q1) @ quat_to_matrix(q2)``.
    """
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return np.array(
        [
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        ],
        dtype=np.float64,
    )


def quat_conjugate(q: FloatArray) -> FloatArray:
    """Conjugate ``[w, -x, -y, -z]``; the inverse for unit quaternions."""
    q = np.asarray(q, dtype=np.float64)
    return np.array([q[0], -q[1], -q[2], -q[3]], dtype=np.float64)


def quat_rotate(q: FloatArray, v: FloatArray) -> FloatArray:
    """Rotate 3-vector ``v`` by unit quaternion ``q`` (computes q v q*)."""
    v = np.asarray(v, dtype=np.float64)
    qv = np.concatenate(([0.0], v))
    return quat_multiply(quat_multiply(q, qv), quat_conjugate(q))[1:]


def quat_to_matrix(q: FloatArray) -> FloatArray:
    """Convert a unit quaternion to a 3x3 rotation matrix."""
    w, x, y, z = quat_normalize(q)
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
            [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
            [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
        ],
        dtype=np.float64,
    )


def matrix_to_quat(R: FloatArray) -> FloatArray:
    """Convert a rotation matrix to a unit quaternion (w >= 0 branch).

    Uses the numerically stable four-branch method: pick the largest of
    ``w, x, y, z`` to divide by, avoiding catastrophic cancellation when the
    trace is near -1 (rotations close to 180 degrees).
    """
    R = np.asarray(R, dtype=np.float64)
    tr = np.trace(R)
    if tr > 0.0:
        s = 2.0 * np.sqrt(tr + 1.0)
        q = np.array(
            [0.25 * s, (R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s]
        )
    elif R[0, 0] >= R[1, 1] and R[0, 0] >= R[2, 2]:
        s = 2.0 * np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2])
        q = np.array(
            [(R[2, 1] - R[1, 2]) / s, 0.25 * s, (R[0, 1] + R[1, 0]) / s, (R[0, 2] + R[2, 0]) / s]
        )
    elif R[1, 1] >= R[2, 2]:
        s = 2.0 * np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2])
        q = np.array(
            [(R[0, 2] - R[2, 0]) / s, (R[0, 1] + R[1, 0]) / s, 0.25 * s, (R[1, 2] + R[2, 1]) / s]
        )
    else:
        s = 2.0 * np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1])
        q = np.array(
            [(R[1, 0] - R[0, 1]) / s, (R[0, 2] + R[2, 0]) / s, (R[1, 2] + R[2, 1]) / s, 0.25 * s]
        )
    if q[0] < 0.0:
        q = -q
    return quat_normalize(q)


def slerp(q0: FloatArray, q1: FloatArray, t: float) -> FloatArray:
    """Spherical linear interpolation between unit quaternions.

    Takes the shortest arc (flips sign if the dot product is negative) and
    falls back to normalized linear interpolation when the quaternions are
    nearly parallel, where the sin() denominator would be ill-conditioned.
    """
    q0 = quat_normalize(q0)
    q1 = quat_normalize(q1)
    dot = float(np.dot(q0, q1))
    if dot < 0.0:
        q1, dot = -q1, -dot
    if dot > 1.0 - 1e-9:
        return quat_normalize(q0 + t * (q1 - q0))
    omega = np.arccos(np.clip(dot, -1.0, 1.0))
    s = np.sin(omega)
    return (np.sin((1.0 - t) * omega) / s) * q0 + (np.sin(t * omega) / s) * q1
