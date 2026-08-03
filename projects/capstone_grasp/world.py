"""Capstone III world: a planar arm, a table of objects, and a depth sensor.

Given to you. The arm is three revolute joints in the plane; the scene is a
few circular objects resting on a table; the sensor is a fixed depth camera
above and to the side, producing a 2D point cloud by ray casting.

Everything is pure NumPy, and the whole episode runs in well under a second,
which is what keeps the evaluation harness usable as a development loop
rather than something you run overnight.
"""

from __future__ import annotations

import numpy as np

# ---------------- the arm ----------------

LINKS = np.array([0.45, 0.35, 0.22])
LINK_RADIUS = 0.018
REACH = float(LINKS.sum())
Q_MIN = np.array([-2.9, -2.6, -2.6])
Q_MAX = np.array([2.9, 2.6, 2.6])
Q_HOME = np.array([0.9, -0.9, -0.5])

# The arm is mounted on a pedestal beside the table, not on the table itself —
# otherwise the base joint sits in the table plane and every configuration
# reports a collision.
BASE = np.array([0.0, 0.30])

# ---------------- the gripper ----------------

W_MIN, W_MAX = 0.020, 0.085      # stroke
MU = 0.5                         # friction coefficient
GRASP_TOL = 0.020                # how close the tool must get to the grasp point

# ---------------- the scene ----------------

TABLE_Y = 0.0                    # objects rest on y = TABLE_Y
TABLE_X = (0.25, 0.92)
CAMERA = np.array([0.05, 0.95])  # fixed depth sensor, looking down-right
N_RAYS = 220
RAY_SPAN = (-1.35, -0.20)        # radians, measured from +x


def wrap(a):
    w = np.mod(-np.asarray(a, dtype=float) + np.pi, 2.0 * np.pi)
    r = -(w - np.pi)
    return float(r) if np.ndim(a) == 0 else r


def joint_positions(q, links=LINKS):
    q = np.asarray(q, dtype=float)
    ang = np.cumsum(q)
    seg = np.stack([links * np.cos(ang), links * np.sin(ang)], axis=1)
    return np.vstack([BASE, BASE + np.cumsum(seg, axis=0)])


def fk(q):
    return joint_positions(q)[-1]


def jacobian(q):
    p = joint_positions(q)
    d = p[-1] - p[:-1]
    return np.stack([-d[:, 1], d[:, 0]])


def manipulability(q):
    J = jacobian(q)
    return float(np.sqrt(max(np.linalg.det(J @ J.T), 0.0)))


def make_scene(seed: int) -> dict:
    """Two to four circular objects on the table, one of them the target."""
    rng = np.random.default_rng(seed)
    n = int(rng.integers(2, 5))
    radii, centres = [], []
    for _ in range(200):
        if len(radii) == n:
            break
        r = float(rng.uniform(0.022, 0.040))
        x = float(rng.uniform(TABLE_X[0] + r, TABLE_X[1] - r))
        c = np.array([x, TABLE_Y + r])
        if all(np.linalg.norm(c - cc) > r + rr + 0.035
               for cc, rr in zip(centres, radii, strict=True)):
            radii.append(r)
            centres.append(c)
    centres = np.array(centres)
    radii = np.array(radii)
    # The target is whichever object the gripper can actually open around.
    graspable = np.nonzero(2 * radii <= W_MAX - 0.005)[0]
    target = int(graspable[rng.integers(len(graspable))]) if len(graspable) else 0
    return {"centres": centres, "radii": radii, "target": target, "seed": seed}


def depth_scan(scene: dict, rng=None) -> np.ndarray:
    """(M, 2) points on visible object surfaces, from the fixed camera.

    Rays that hit nothing contribute nothing — a non-detection is not a
    measurement, which is lesson 7.6's whole subject.
    """
    angles = np.linspace(RAY_SPAN[0], RAY_SPAN[1], N_RAYS)
    pts = []
    for a in angles:
        d = np.array([np.cos(a), np.sin(a)])
        best_t = np.inf
        for c, r in zip(scene["centres"], scene["radii"], strict=True):
            f = CAMERA - c
            b = 2.0 * float(f @ d)
            cc = float(f @ f) - r * r
            disc = b * b - 4.0 * cc
            if disc < 0:
                continue
            t = (-b - np.sqrt(disc)) / 2.0
            if 0 < t < best_t:
                best_t = t
        # The table itself, as a floor plane.
        if d[1] < -1e-9:
            t_table = (TABLE_Y - CAMERA[1]) / d[1]
            if 0 < t_table < best_t:
                best_t = t_table
        if np.isfinite(best_t):
            p = CAMERA + best_t * d
            if rng is not None:
                p = p + rng.normal(0.0, 0.0015, 2)
            pts.append(p)
    return np.array(pts) if pts else np.zeros((0, 2))


# ---------------- collision ----------------

def _point_seg(c, a, b):
    ab = b - a
    den = float(ab @ ab)
    if den < 1e-15:
        return float(np.linalg.norm(c - a))
    t = float(np.clip((c - a) @ ab / den, 0.0, 1.0))
    return float(np.linalg.norm(c - (a + t * ab)))


def _seg_seg(a1, a2, b1, b2, n=16):
    t = np.linspace(0, 1, n)[:, None]
    A = a1 + t * (a2 - a1)
    B = b1 + t * (b2 - b1)
    return float(np.min(np.linalg.norm(A[:, None, :] - B[None, :, :], axis=2)))


def collides(q, scene: dict, ignore: int | None = None) -> bool:
    """Arm against objects, the table, and itself.

    `ignore` skips one object — used for the target during the final approach,
    since touching what you are about to grasp is the point.
    """
    pts = joint_positions(q)
    segs = list(zip(pts[:-1], pts[1:], strict=True))

    for i, (a, b) in enumerate(segs):
        if min(a[1], b[1]) < TABLE_Y + LINK_RADIUS:
            return True
        for j, (c, r) in enumerate(zip(scene["centres"], scene["radii"], strict=True)):
            if j == ignore:
                continue
            if _point_seg(c, a, b) < r + LINK_RADIUS:
                return True
        # Non-adjacent links only: adjacent ones share a joint.
        for j in range(i + 2, len(segs)):
            if _seg_seg(a, b, segs[j][0], segs[j][1]) < 2 * LINK_RADIUS:
                return True
    return False


def edge_collides(q1, q2, scene, ignore=None, resolution=0.06) -> bool:
    q1 = np.asarray(q1, dtype=float)
    q2 = np.asarray(q2, dtype=float)
    n = max(2, int(np.ceil(float(np.max(np.abs(q2 - q1))) / resolution)))
    for t in np.linspace(0.0, 1.0, n + 1):
        if collides(q1 + t * (q2 - q1), scene, ignore):
            return True
    return False
