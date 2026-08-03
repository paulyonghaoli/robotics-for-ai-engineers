"""Reference solution for the mapping mini-project."""

from __future__ import annotations

import numpy as np
from world import (
    GRID_N,
    LOG_ODDS_CLAMP,
    LOG_ODDS_HIT,
    LOG_ODDS_MISS,
    MAX_RANGE,
    N_RAYS,
    RANGE_SIGMA,
    world_to_cell,
    wrap,
)

MISS_MARGIN = 4 * RANGE_SIGMA


def bresenham(r0: int, c0: int, r1: int, c1: int) -> list[tuple[int, int]]:
    cells = []
    dr, dc = abs(r1 - r0), abs(c1 - c0)
    sr = 1 if r1 >= r0 else -1
    sc = 1 if c1 >= c0 else -1
    err = dc - dr
    r, c = r0, c0
    while True:
        cells.append((r, c))
        if r == r1 and c == c1:
            return cells
        e2 = 2 * err
        if e2 > -dr:
            err -= dr
            c += sc
        if e2 < dc:
            err += dc
            r += sr


def integrate_scan(log_odds: np.ndarray, pose: np.ndarray,
                   scan: np.ndarray) -> np.ndarray:
    bearings = pose[2] + np.arange(N_RAYS) * (2 * np.pi / N_RAYS)
    r0, c0 = world_to_cell(pose[:2])
    for i in range(N_RAYS):
        rng = float(scan[i])
        # A max-range return is a NON-detection. Give the equality test a
        # few sigma of margin, or noise turns misses into phantom hits.
        is_hit = rng < MAX_RANGE - MISS_MARGIN
        reach = rng if is_hit else MAX_RANGE
        b = bearings[i]
        end = (pose[0] + reach * np.cos(b), pose[1] + reach * np.sin(b))
        r1, c1 = world_to_cell(end)
        r1 = int(np.clip(r1, 0, GRID_N - 1))
        c1 = int(np.clip(c1, 0, GRID_N - 1))
        cells = bresenham(r0, c0, r1, c1)
        for (r, c) in cells[:-1]:
            if 0 <= r < GRID_N and 0 <= c < GRID_N:
                log_odds[r, c] += LOG_ODDS_MISS
        r, c = cells[-1]
        if 0 <= r < GRID_N and 0 <= c < GRID_N:
            log_odds[r, c] += LOG_ODDS_HIT if is_hit else LOG_ODDS_MISS
    np.clip(log_odds, -LOG_ODDS_CLAMP, LOG_ODDS_CLAMP, out=log_odds)
    return log_odds


def occupied_mask(log_odds: np.ndarray, threshold: float = 0.65) -> np.ndarray:
    return (1.0 / (1.0 + np.exp(-log_odds))) > threshold


def kabsch(source: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    src = np.asarray(source, dtype=float)
    tgt = np.asarray(target, dtype=float)
    mu_s, mu_t = src.mean(axis=0), tgt.mean(axis=0)
    H = (src - mu_s).T @ (tgt - mu_t)
    U, _, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    # Without this the SVD can hand back a reflection, which is not a
    # rigid motion and silently mirrors the scan.
    R = Vt.T @ np.diag([1.0, d]) @ U.T
    return R, mu_t - R @ mu_s


def _apply(points: np.ndarray, delta: np.ndarray) -> np.ndarray:
    c, s = np.cos(delta[2]), np.sin(delta[2])
    R = np.array([[c, -s], [s, c]])
    return points @ R.T + delta[:2]


def icp(source: np.ndarray, target: np.ndarray, init: np.ndarray | None = None,
        iters: int = 40, reject: float = 0.6) -> np.ndarray:
    src = np.asarray(source, dtype=float)
    tgt = np.asarray(target, dtype=float)
    est = np.zeros(3) if init is None else np.asarray(init, dtype=float).copy()
    if len(src) < 3 or len(tgt) < 3:
        return est

    for _ in range(iters):
        moved = _apply(src, est)
        d = np.linalg.norm(moved[:, None, :] - tgt[None, :, :], axis=2)
        idx = np.argmin(d, axis=1)
        keep = d[np.arange(len(moved)), idx] < reject
        if keep.sum() < 3:
            break
        R, t = kabsch(moved[keep], tgt[idx[keep]])
        dth = float(np.arctan2(R[1, 0], R[0, 0]))
        c, s = np.cos(dth), np.sin(dth)
        # Compose the incremental (R, t) onto the running estimate.
        est = np.array([
            c * est[0] - s * est[1] + t[0],
            s * est[0] + c * est[1] + t[1],
            float(wrap(est[2] + dth)),
        ])
        if abs(dth) < 1e-7 and np.linalg.norm(t) < 1e-7:
            break
    return est
