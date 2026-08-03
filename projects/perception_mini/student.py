"""Perception mini-project — camera geometry, graded on behaviour.

    python -m grader

Nothing here trains a model. The parts of a perception stack that break in
the field are almost never the weights.

NumPy only. Do not import robotics_ai.
"""

from __future__ import annotations

from optics import (  # noqa: F401
    BASELINE,
    CX,
    CY,
    FX,
    FY,
    HEIGHT,
    K1,
    K2,
    MIN_DISPARITY,
    SIGMA_D,
    WIDTH,
)


def project(points_world, K, R, t):
    """(N,3) world points -> (N,2) pixels.

    X_cam = R @ X_world + t, then the pinhole division. Points with
    Z_cam <= 0 are BEHIND the camera: return np.nan for those. Dividing by a
    negative Z yields a perfectly plausible-looking pixel in front of you.

    TODO.
    """
    raise NotImplementedError("student: project")


def unproject(pixels, K):
    """(N,2) pixels -> (N,3) UNIT ray directions in the camera frame.

    There is no depth to return — the projection threw it away.

    TODO.
    """
    raise NotImplementedError("student: unproject")


def distort(xy, k1, k2):
    """(N,2) ideal normalized coords -> distorted normalized coords.

    factor = 1 + k1*r2 + k2*r2**2 with r2 = x**2 + y**2, applied to both
    components.

    TODO.
    """
    raise NotImplementedError("student: distort")


def undistort(xy_d, k1, k2, iters=20):
    """Inverse of `distort`. No closed form; iterate

        xy <- xy_d / (1 + k1*r2(xy) + k2*r2(xy)**2)

    recomputing r2 from the CURRENT estimate each pass. Reusing the
    distorted point's radius gives something accurate near the axis and
    wrong exactly where distortion matters.

    TODO.
    """
    raise NotImplementedError("student: undistort")


def triangulate(left_px, right_px):
    """Rectified stereo pair -> (N,3) camera-frame points.

    d = uL - uR;  Z = FX*BASELINE/d;  X,Y from the LEFT pixel.
    Rows with d < MIN_DISPARITY must be np.nan — as d -> 0 the depth
    diverges, and a matcher emitting 0.01 px of disparity is reporting
    kilometres with total confidence.

    TODO.
    """
    raise NotImplementedError("student: triangulate")


def depth_sigma(Z, sigma_d=SIGMA_D, baseline=BASELINE, fx=FX):
    """1-sigma depth uncertainty: Z**2 * sigma_d / (fx * baseline).

    TODO.
    """
    raise NotImplementedError("student: depth_sigma")


def depth_to_cloud(depth, K, stride=1):
    """(H,W) depth image -> (M,3) camera-frame points.

    Pixel (v, u) with depth Z back-projects to
        X = (u - cx) * Z / fx,  Y = (v - cy) * Z / fy,  Z = Z

    Drop pixels whose depth is <= 0: those are sensor dropouts, not
    measurements of something at the origin. Vectorize it — a Python loop
    over 640x480 will not hold a frame rate.

    `stride` subsamples both axes (stride=2 takes every other row/column).

    TODO.
    """
    raise NotImplementedError("student: depth_to_cloud")
