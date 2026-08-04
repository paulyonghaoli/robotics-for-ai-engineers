"""2D pose-graph SLAM back end: loop detection and graph optimization.

Lesson 4.4 in code. v4's scan matcher bounds drift it cannot remove — a
constant odometry bias is invisible to incremental matching, because
correcting it means recognizing a place you mapped before you drifted.
That recognition is a *loop closure*, and applying it to everything that
came between is a *pose graph*.

Kept separate from any stack so the ablation harness and the v5 stack use
exactly the same back end, and so the optimizer can be tested against
graphs whose answer is known by construction.
"""

from __future__ import annotations

import numpy as np

from robotics_ai.geometry import wrap_angle

# --- loop detection -------------------------------------------------------

LOCAL_HALF = 6.5          # half-width of a keyframe's local grid, metres
LOCAL_RES = 0.15          # its resolution
LOOP_MIN_GAP = 12         # keyframes that must separate a candidate pair
LOOP_RADIUS = 3.0         # only consider keyframes believed to be this close
LOOP_WINDOW_XY = 1.60     # search half-width — accumulated drift may be large
LOOP_WINDOW_TH = 0.50
LOOP_SIGMA = 0.30
LOOP_GATE = 1.2
LOOP_QUALITY = 0.62       # below this the closure is refused, not applied
LOOP_MIN_BEAMS = 14


def scan_points(scan: np.ndarray, bearings: np.ndarray, max_range: float,
                miss_margin: float) -> np.ndarray:
    """A scan as a local point cloud, misses dropped."""
    hit = scan < max_range - miss_margin
    r, b = scan[hit], bearings[hit]
    return np.stack([r * np.cos(b), r * np.sin(b)], axis=1)


def _local_field(points: np.ndarray) -> np.ndarray:
    """Truncated distance field over a keyframe's own local grid.

    Small and square: the cloud is one scan, so the field is cheap and its
    extent is bounded by the sensor rather than by the world.
    """
    n = int(2 * LOCAL_HALF / LOCAL_RES)
    occ = np.zeros((n, n), dtype=bool)
    ix = ((points[:, 0] + LOCAL_HALF) / LOCAL_RES).astype(int)
    iy = ((points[:, 1] + LOCAL_HALF) / LOCAL_RES).astype(int)
    keep = (ix >= 0) & (ix < n) & (iy >= 0) & (iy < n)
    occ[iy[keep], ix[keep]] = True

    cells = int(np.ceil(LOOP_GATE / LOCAL_RES)) + 1
    big = float(cells + 1)
    d = np.where(occ, 0.0, big)
    diag = np.sqrt(2.0)
    for _ in range(cells):
        best = d
        for axis in (0, 1):
            for shift in (1, -1):
                nb = np.roll(d, shift, axis).copy()
                idx = [slice(None), slice(None)]
                idx[axis] = 0 if shift == 1 else -1
                nb[tuple(idx)] = big
                best = np.minimum(best, nb + 1.0)
        for sy in (1, -1):
            for sx in (1, -1):
                nb = np.roll(np.roll(d, sy, 0), sx, 1).copy()
                nb[0 if sy == 1 else -1, :] = big
                nb[:, 0 if sx == 1 else -1] = big
                best = np.minimum(best, nb + diag)
        d = np.minimum(d, best)
    return np.minimum(d, big) * LOCAL_RES


def _sample_local(field: np.ndarray, px: np.ndarray, py: np.ndarray):
    n = field.shape[0]
    fx = (px + LOCAL_HALF) / LOCAL_RES - 0.5
    fy = (py + LOCAL_HALF) / LOCAL_RES - 0.5
    x0 = np.floor(fx).astype(int)
    y0 = np.floor(fy).astype(int)
    inside = (x0 >= 0) & (x0 + 1 < n) & (y0 >= 0) & (y0 + 1 < n)
    xc, yc = np.clip(x0, 0, n - 2), np.clip(y0, 0, n - 2)
    wx = np.clip(fx - xc, 0.0, 1.0)
    wy = np.clip(fy - yc, 0.0, 1.0)
    top = field[yc, xc] * (1 - wx) + field[yc, xc + 1] * wx
    bot = field[yc + 1, xc] * (1 - wx) + field[yc + 1, xc + 1] * wx
    return top * (1 - wy) + bot * wy, inside


def relative_pose(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """b expressed in a's frame."""
    c, s = np.cos(a[2]), np.sin(a[2])
    dx, dy = b[0] - a[0], b[1] - a[1]
    return np.array([c * dx + s * dy, -s * dx + c * dy, wrap_angle(b[2] - a[2])])


def compose(a: np.ndarray, rel: np.ndarray) -> np.ndarray:
    """The pose obtained by applying `rel` in a's frame."""
    c, s = np.cos(a[2]), np.sin(a[2])
    return np.array([a[0] + c * rel[0] - s * rel[1],
                     a[1] + s * rel[0] + c * rel[1],
                     wrap_angle(a[2] + rel[2])])


def match_scan_to_scan(ref_points: np.ndarray, cur_points: np.ndarray,
                       guess: np.ndarray, field: np.ndarray | None = None
                       ) -> tuple[np.ndarray, float]:
    """Best relative pose taking `cur_points` into the reference frame.

    Scan-to-SCAN, deliberately, not scan-to-map: by the time a loop is
    worth closing the map has been built through the drift, so matching
    against it would measure the drift against itself. Two raw scans have
    no such contamination.

    The window is far wider than the incremental matcher's, because what
    it is being asked to absorb is the accumulated error of a whole lap.
    """
    if len(ref_points) < LOOP_MIN_BEAMS or len(cur_points) < LOOP_MIN_BEAMS:
        return guess, 0.0
    if field is None:
        field = _local_field(ref_points)

    pose, quality = np.asarray(guess, dtype=float), 0.0
    for scale in (1.0, 0.30, 0.10):
        offs = np.linspace(-LOOP_WINDOW_XY * scale, LOOP_WINDOW_XY * scale, 7)
        ths = np.linspace(-LOOP_WINDOW_TH * scale, LOOP_WINDOW_TH * scale, 7)
        cand = np.array([[pose[0] + a, pose[1] + c, wrap_angle(pose[2] + e)]
                         for a in offs for c in offs for e in ths])
        ct = np.cos(cand[:, 2])[:, None]
        st = np.sin(cand[:, 2])[:, None]
        px = cand[:, 0][:, None] + cur_points[None, :, 0] * ct - cur_points[None, :, 1] * st
        py = cand[:, 1][:, None] + cur_points[None, :, 0] * st + cur_points[None, :, 1] * ct
        d, inside = _sample_local(field, px, py)
        lik = np.where(inside & (d < LOOP_GATE),
                       np.exp(-(d ** 2) / (2 * LOOP_SIGMA ** 2)), 0.0).sum(axis=1)
        # No odometry prior here. The whole point of a loop closure is to
        # disagree with odometry; anchoring it to the incoming guess would
        # pull the measurement back toward the drift it exists to correct.
        best = int(np.argmax(lik))
        pose = cand[best]
        quality = float(lik[best] / len(cur_points))
    return pose, quality


# --- the graph ------------------------------------------------------------

class PoseGraph:
    """Keyframe poses, the constraints between them, and Gauss-Newton."""

    def __init__(self) -> None:
        self.poses: list[np.ndarray] = []
        self.scans: list[np.ndarray] = []       # local point clouds
        self.raws: list[np.ndarray | None] = []  # raw ranges, for rebuilding
        self.edges: list[tuple[int, int, np.ndarray, np.ndarray]] = []
        self.loops = 0
        self.rejected = 0
        self._fields: dict[int, np.ndarray] = {}

    def field(self, j: int) -> np.ndarray:
        """A keyframe's local distance field, built once.

        Loop detection tries every nearby keyframe, so without this the
        same field is rebuilt tens of times per closure attempt and the
        back end costs more than the front end.
        """
        f = self._fields.get(j)
        if f is None:
            f = _local_field(self.scans[j])
            self._fields[j] = f
        return f

    def add_keyframe(self, pose: np.ndarray, points: np.ndarray,
                     raw: np.ndarray | None = None) -> int:
        i = len(self.poses)
        self.poses.append(np.asarray(pose, dtype=float).copy())
        self.scans.append(points)
        self.raws.append(None if raw is None else np.asarray(raw).copy())
        if i > 0:
            # Odometry constraint: whatever the front end believes the
            # relative motion was. Weak in rotation, because that is where
            # a systematic bias hides.
            z = relative_pose(self.poses[i - 1], self.poses[i])
            info = np.diag([1.0 / 0.05 ** 2, 1.0 / 0.05 ** 2, 1.0 / 0.06 ** 2])
            self.edges.append((i - 1, i, z, info))
        return i

    def find_loop(self, k: int) -> tuple[int, np.ndarray, float] | None:
        """Best acceptable closure for keyframe `k`, or None.

        Candidates are old keyframes the estimate believes are nearby. The
        estimate is drifted, which is why the search radius is generous and
        the match window wider still.
        """
        best = None
        for j in range(0, k - LOOP_MIN_GAP):
            if np.hypot(*(self.poses[k][:2] - self.poses[j][:2])) > LOOP_RADIUS:
                continue
            guess = relative_pose(self.poses[j], self.poses[k])
            z, q = match_scan_to_scan(self.scans[j], self.scans[k], guess,
                                      field=self.field(j))
            if q >= LOOP_QUALITY and (best is None or q > best[2]):
                best = (j, z, q)
            elif q > 0.0:
                self.rejected += 1
        return best

    def add_loop(self, j: int, k: int, z: np.ndarray) -> None:
        # Stronger than odometry: this constraint is the only thing in the
        # graph that has seen the same place twice.
        info = np.diag([1.0 / 0.03 ** 2, 1.0 / 0.03 ** 2, 1.0 / 0.03 ** 2])
        self.edges.append((j, k, np.asarray(z, dtype=float), info))
        self.loops += 1

    def optimize(self, iterations: int = 8) -> None:
        """Gauss-Newton on SE(2), node 0 held fixed.

        Node 0 is the gauge. Absolute pose is unobservable (lesson 4.3), so
        something has to be pinned or H is singular; pinning the first
        keyframe keeps the optimized trajectory in the map frame the rest
        of the stack already uses.
        """
        n = len(self.poses)
        if n < 2 or not self.edges:
            return
        x = np.concatenate([p.astype(float) for p in self.poses])

        for _ in range(iterations):
            H = np.zeros((3 * n, 3 * n))
            b = np.zeros(3 * n)
            for i, j, z, info in self.edges:
                xi, xj = x[3 * i:3 * i + 3], x[3 * j:3 * j + 3]
                ci, si = np.cos(xi[2]), np.sin(xi[2])
                cz, sz = np.cos(z[2]), np.sin(z[2])
                Ri = np.array([[ci, -si], [si, ci]])
                Rz = np.array([[cz, -sz], [sz, cz]])
                dRi = np.array([[-si, -ci], [ci, -si]])   # dR(theta)/dtheta
                dt = xj[:2] - xi[:2]

                e = np.empty(3)
                e[:2] = Rz.T @ (Ri.T @ dt - z[:2])
                e[2] = wrap_angle(xj[2] - xi[2] - z[2])

                A = np.zeros((3, 3))
                A[:2, :2] = -Rz.T @ Ri.T
                A[:2, 2] = Rz.T @ dRi.T @ dt
                A[2, 2] = -1.0
                B = np.zeros((3, 3))
                B[:2, :2] = Rz.T @ Ri.T
                B[2, 2] = 1.0

                H[3*i:3*i+3, 3*i:3*i+3] += A.T @ info @ A
                H[3*i:3*i+3, 3*j:3*j+3] += A.T @ info @ B
                H[3*j:3*j+3, 3*i:3*i+3] += B.T @ info @ A
                H[3*j:3*j+3, 3*j:3*j+3] += B.T @ info @ B
                b[3*i:3*i+3] += A.T @ info @ e
                b[3*j:3*j+3] += B.T @ info @ e

            H[0:3, 0:3] += np.eye(3) * 1e9        # pin the gauge
            H += np.eye(3 * n) * 1e-6             # Levenberg damping
            try:
                dx = np.linalg.solve(H, -b)
            except np.linalg.LinAlgError:
                return
            x = x + dx
            for i in range(n):
                x[3 * i + 2] = wrap_angle(x[3 * i + 2])
            if np.max(np.abs(dx)) < 1e-6:
                break

        self.poses = [x[3 * i:3 * i + 3].copy() for i in range(n)]
