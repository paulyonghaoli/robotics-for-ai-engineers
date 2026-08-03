"""Shared camera model for the perception mini-project. Given to you."""

from __future__ import annotations

import numpy as np

FX, FY = 600.0, 600.0
CX, CY = 320.0, 240.0
WIDTH, HEIGHT = 640, 480
K = np.array([[FX, 0.0, CX], [0.0, FY, CY], [0.0, 0.0, 1.0]])

K1, K2 = -0.28, 0.09          # radial distortion of a fairly ordinary lens
BASELINE = 0.12               # metres between the stereo optical centres
SIGMA_D = 0.25                # pixels of disparity uncertainty
MIN_DISPARITY = 0.5


def look_at(eye, target, up=(0.0, 0.0, 1.0)):
    """Extrinsics (R, t) mapping world -> camera, camera looking down +Z."""
    eye = np.asarray(eye, dtype=float)
    fwd = np.asarray(target, dtype=float) - eye
    fwd = fwd / np.linalg.norm(fwd)
    right = np.cross(fwd, np.asarray(up, dtype=float))
    right = right / np.linalg.norm(right)
    down = np.cross(fwd, right)
    R = np.stack([right, down, fwd])
    return R, -R @ eye


def synth_stereo(points_cam):
    """(N,3) camera-frame points -> rectified (left_px, right_px)."""
    pts = np.asarray(points_cam, dtype=float)
    z = pts[:, 2]
    return (np.stack([FX * pts[:, 0] / z + CX, FY * pts[:, 1] / z + CY], axis=1),
            np.stack([FX * (pts[:, 0] - BASELINE) / z + CX,
                      FY * pts[:, 1] / z + CY], axis=1))


def synth_depth_image(rng, h=48, w=64):
    """A small depth image: a ground plane, a box, and some invalid pixels."""
    depth = np.full((h, w), 8.0)
    depth += np.linspace(0.0, 4.0, h)[:, None]          # ground receding
    depth[h // 3:2 * h // 3, w // 3:2 * w // 3] = 3.0   # a box in the middle
    depth += rng.normal(0.0, 0.01, size=(h, w))
    depth[rng.random((h, w)) < 0.05] = 0.0              # dropouts read as zero
    return depth
