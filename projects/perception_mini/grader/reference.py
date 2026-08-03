"""Reference solution for the perception mini-project."""

from __future__ import annotations

import numpy as np
from optics import BASELINE, CX, CY, FX, FY, MIN_DISPARITY, SIGMA_D


def project(points_world, K, R, t):
    pts = np.atleast_2d(np.asarray(points_world, dtype=float))
    cam = pts @ R.T + t
    hom = cam @ K.T
    out = np.full((len(pts), 2), np.nan)
    front = cam[:, 2] > 0
    out[front] = hom[front, :2] / hom[front, 2:3]
    return out


def unproject(pixels, K):
    px = np.atleast_2d(np.asarray(pixels, dtype=float))
    hom = np.concatenate([px, np.ones((len(px), 1))], axis=1)
    d = hom @ np.linalg.inv(K).T
    return d / np.linalg.norm(d, axis=1, keepdims=True)


def distort(xy, k1, k2):
    xy = np.atleast_2d(np.asarray(xy, dtype=float))
    r2 = (xy ** 2).sum(axis=1)
    return xy * (1.0 + k1 * r2 + k2 * r2 ** 2)[:, None]


def undistort(xy_d, k1, k2, iters=20):
    xy_d = np.atleast_2d(np.asarray(xy_d, dtype=float))
    xy = xy_d.copy()
    for _ in range(iters):
        # r2 from the CURRENT estimate; reusing the distorted radius is
        # accurate near the axis and wrong where distortion matters.
        r2 = (xy ** 2).sum(axis=1)
        xy = xy_d / (1.0 + k1 * r2 + k2 * r2 ** 2)[:, None]
    return xy


def triangulate(left_px, right_px):
    L = np.atleast_2d(np.asarray(left_px, dtype=float))
    R = np.atleast_2d(np.asarray(right_px, dtype=float))
    d = L[:, 0] - R[:, 0]
    out = np.full((len(L), 3), np.nan)
    ok = d >= MIN_DISPARITY
    Z = FX * BASELINE / d[ok]
    out[ok, 2] = Z
    out[ok, 0] = (L[ok, 0] - CX) * Z / FX
    out[ok, 1] = (L[ok, 1] - CY) * Z / FY
    return out


def depth_sigma(Z, sigma_d=SIGMA_D, baseline=BASELINE, fx=FX):
    return np.asarray(Z, dtype=float) ** 2 * sigma_d / (fx * baseline)


def depth_to_cloud(depth, K, stride=1):
    d = np.asarray(depth, dtype=float)[::stride, ::stride]
    h, w = d.shape
    vs, us = np.mgrid[0:h, 0:w]
    us = us * stride
    vs = vs * stride
    valid = d > 0            # zero is a dropout, not a measurement at the origin
    Z = d[valid]
    return np.stack([(us[valid] - K[0, 2]) * Z / K[0, 0],
                     (vs[valid] - K[1, 2]) * Z / K[1, 1],
                     Z], axis=1)
