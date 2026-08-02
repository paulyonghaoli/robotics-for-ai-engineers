"""2D rigid-body transformations: SO(2) rotations and SE(2) poses.

Conventions
-----------
- Angles are in radians and wrapped to the half-open interval (-pi, pi].
- A pose ``(x, y, theta)`` of frame B relative to frame A is the transform
  ``T_A_B``: it maps points expressed in B into A. Read the subscripts
  right-to-left: "from B, into A".
- Homogeneous transforms are 3x3 float64 numpy arrays::

      | cos(t)  -sin(t)  x |
      | sin(t)   cos(t)  y |
      |   0        0     1 |

- Point sets are ``(N, 2)`` arrays; a single point may be passed as ``(2,)``.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]


def wrap_angle(theta: float | FloatArray) -> float | FloatArray:
    """Wrap an angle (or array of angles) to the interval (-pi, pi].

    This is *the* most common source of bugs in heading control and
    orientation-error computation: naive subtraction of two headings near
    +/-pi produces errors close to 2*pi and controllers that spin the robot
    the long way around.
    """
    wrapped = np.mod(-np.asarray(theta, dtype=np.float64) + np.pi, 2.0 * np.pi)
    result = -(wrapped - np.pi)
    if np.isscalar(theta) or np.ndim(theta) == 0:
        return float(result)
    return result


def rot2(theta: float) -> FloatArray:
    """Return the 2x2 SO(2) rotation matrix for angle ``theta``."""
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s], [s, c]], dtype=np.float64)


def se2(x: float, y: float, theta: float) -> FloatArray:
    """Build a 3x3 homogeneous SE(2) transform from a pose ``(x, y, theta)``."""
    T = np.eye(3, dtype=np.float64)
    T[:2, :2] = rot2(theta)
    T[:2, 2] = (x, y)
    return T


def se2_to_pose(T: FloatArray) -> tuple[float, float, float]:
    """Recover ``(x, y, theta)`` from a homogeneous SE(2) transform."""
    theta = float(np.arctan2(T[1, 0], T[0, 0]))
    return float(T[0, 2]), float(T[1, 2]), theta


def se2_inverse(T: FloatArray) -> FloatArray:
    """Invert an SE(2) transform analytically.

    Uses the closed form ``[R t; 0 1]^-1 = [R^T  -R^T t; 0 1]`` rather than
    a generic matrix inverse: cheaper, and exactly rigid by construction.
    """
    R = T[:2, :2]
    t = T[:2, 2]
    Ti = np.eye(3, dtype=np.float64)
    Ti[:2, :2] = R.T
    Ti[:2, 2] = -R.T @ t
    return Ti


def se2_compose(*transforms: FloatArray) -> FloatArray:
    """Compose transforms left to right: ``se2_compose(T_A_B, T_B_C) -> T_A_C``.

    Subscript check: adjacent inner subscripts must match, exactly like
    matrix-dimension checks. ``T_A_B @ T_B_C`` cancels the B's.
    """
    if not transforms:
        return np.eye(3, dtype=np.float64)
    result = transforms[0]
    for T in transforms[1:]:
        result = result @ T
    return result


def relative_pose(T_A_B: FloatArray, T_A_C: FloatArray) -> FloatArray:
    """Pose of frame C as seen from frame B, given both in frame A.

    ``T_B_C = (T_A_B)^-1 @ T_A_C``
    """
    return se2_inverse(T_A_B) @ T_A_C


def transform_points(T: FloatArray, points: FloatArray) -> FloatArray:
    """Apply an SE(2) transform to one point ``(2,)`` or a point set ``(N, 2)``.

    If ``T`` is ``T_A_B`` the input points must be expressed in frame B and
    the output is expressed in frame A.
    """
    pts = np.asarray(points, dtype=np.float64)
    single = pts.ndim == 1
    pts = np.atleast_2d(pts)
    if pts.shape[1] != 2:
        raise ValueError(f"expected points of shape (N, 2) or (2,), got {points.shape}")
    out = pts @ T[:2, :2].T + T[:2, 2]
    return out[0] if single else out
