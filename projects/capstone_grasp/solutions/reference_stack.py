"""Capstone III reference: see it, grasp it.

The full pipeline, composed from Modules 7 and 8:

    perceive   depth scan -> cluster into objects -> fit centre and radius
    grasp      antipodal candidates, scored, filtered by the gripper stroke
    plan       RRT in configuration space to a pre-grasp, then a straight
               approach along the grasp axis
    execute    warm-started damped IK along the planned waypoints

Every stage is the thing the corresponding lesson built, with one addition
the lessons flag and do not implement: the plan is scored on the WORST
manipulability along the executed path, not merely on reaching the goal.
"""

from __future__ import annotations

import numpy as np
from world import (
    Q_MAX,
    Q_MIN,
    TABLE_Y,
    W_MAX,
    W_MIN,
    collides,
    edge_collides,
    fk,
    jacobian,
    manipulability,
)

APPROACH = 0.10          # metres of straight-line approach along the grasp axis
MIN_MANIP = 0.05


# ---------------- perceive ----------------

def cluster(points: np.ndarray, tol: float = 0.030) -> list[np.ndarray]:
    """Single-link clustering along the scan order.

    The scan is ordered by ray angle, so consecutive points on one surface
    are close together and a jump means a new object or the table behind it.
    """
    if len(points) == 0:
        return []
    groups, cur = [], [points[0]]
    for p, q in zip(points[:-1], points[1:], strict=True):
        if np.linalg.norm(q - p) > tol:
            groups.append(np.array(cur))
            cur = []
        cur.append(q)
    groups.append(np.array(cur))
    return [g for g in groups if len(g) >= 4]


def fit_circle(pts: np.ndarray) -> tuple[np.ndarray, float]:
    """Algebraic circle fit (Kasa). Returns (centre, radius)."""
    x, y = pts[:, 0], pts[:, 1]
    A = np.stack([x, y, np.ones_like(x)], axis=1)
    b = x ** 2 + y ** 2
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = sol[0] / 2.0, sol[1] / 2.0
    r = float(np.sqrt(max(sol[2] + cx * cx + cy * cy, 1e-12)))
    return np.array([cx, cy]), r


def remove_table(points: np.ndarray, height: float = 0.006) -> np.ndarray:
    """Drop returns lying on the table plane.

    This is lesson 7.3's ground removal, and it is not optional here: the
    table is continuous, so its returns bridge the gaps between objects and
    single-link clustering merges an object with the floor either side of it.
    The circle fit then sees a shallow arc plus a straight line and rejects
    the whole thing, so the object silently disappears from perception.
    """
    pts = np.atleast_2d(np.asarray(points, dtype=float))
    if not len(pts):
        return pts
    return pts[pts[:, 1] > TABLE_Y + height]


def perceive(points: np.ndarray) -> list[dict]:
    """Scan -> candidate objects, after the table is removed."""
    out = []
    for g in cluster(remove_table(points)):
        centre, r = fit_circle(g)
        # A flat table segment fits a huge circle; a real object does not.
        if not (0.012 < r < 0.070):
            continue
        resid = float(np.mean(np.abs(np.linalg.norm(g - centre, axis=1) - r)))
        if resid > 0.006:
            continue
        out.append({"centre": centre, "radius": r, "n": len(g)})
    return out


# ---------------- grasp ----------------

def grasp_candidates(obj: dict, n_angles: int = 24) -> list[dict]:
    """Antipodal pairs across a circular object, at several approach angles.

    On a circle every diametric pair is exactly antipodal, so the friction
    cone is satisfied by construction and what actually decides the answer is
    the gripper's stroke and whether the arm can get there.
    """
    c, r = obj["centre"], obj["radius"]
    width = 2.0 * r
    if not (W_MIN <= width <= W_MAX):
        return []
    out = []
    for a in np.linspace(0.0, np.pi, n_angles, endpoint=False):
        axis = np.array([np.cos(a), np.sin(a)])
        p1, p2 = c - r * axis, c + r * axis
        # Prefer approaching from above: the table is in the way from below.
        approach = np.array([-axis[1], axis[0]])
        if approach[1] < 0:
            approach = -approach
        margin = float(min(1.0, 1.0))          # exact on a circle
        score = margin * float(approach[1])    # favour a downward approach
        out.append({"p1": p1, "p2": p2, "centre": c, "axis": axis,
                    "approach": approach, "width": width, "score": score})
    out.sort(key=lambda g: -g["score"])
    return out


# ---------------- plan ----------------

def solve_ik(target, q0, scene=None, ignore=None, damping=0.04, iters=250, tol=1e-4):
    q = np.asarray(q0, dtype=float).copy()
    for _ in range(iters):
        e = np.asarray(target, dtype=float) - fk(q)
        if np.linalg.norm(e) < tol:
            return q, True
        J = jacobian(q)
        q = np.clip(q + J.T @ np.linalg.solve(J @ J.T + damping ** 2 * np.eye(2), e),
                    Q_MIN, Q_MAX)
    return q, bool(np.linalg.norm(np.asarray(target) - fk(q)) < tol)


def rrt(start, goal, scene, ignore, iters=1500, step=0.30, goal_bias=0.15, seed=0):
    rng = np.random.default_rng(seed)
    nodes, parent = [np.asarray(start, float)], {0: None}
    for _ in range(iters):
        s = goal if rng.random() < goal_bias else rng.uniform(Q_MIN, Q_MAX)
        arr = np.array(nodes)
        i = int(np.argmin(np.linalg.norm(arr - s, axis=1)))
        near = nodes[i]
        d = s - near
        n = float(np.linalg.norm(d))
        if n < 1e-9:
            continue
        new = np.clip(near + d / n * min(step, n), Q_MIN, Q_MAX)
        if edge_collides(near, new, scene, ignore):
            continue
        nodes.append(new)
        parent[len(nodes) - 1] = i
        if np.linalg.norm(new - goal) <= step and not edge_collides(new, goal, scene, ignore):
            nodes.append(np.asarray(goal, float))
            parent[len(nodes) - 1] = len(nodes) - 2
            path, k = [], len(nodes) - 1
            while k is not None:
                path.append(nodes[k])
                k = parent[k]
            return path[::-1]
    return None


def shortcut(path, scene, ignore, rng, rounds=60):
    """Replace two waypoints with a direct edge where that edge is clear."""
    path = [np.asarray(p, float) for p in path]
    for _ in range(rounds):
        if len(path) < 3:
            break
        i = int(rng.integers(0, len(path) - 2))
        j = int(rng.integers(i + 2, len(path)))
        if not edge_collides(path[i], path[j], scene, ignore):
            path = path[:i + 1] + path[j:]
    return path


# ---------------- the stack ----------------

class GraspStack:
    def __init__(self, scene: dict, seed: int = 0) -> None:
        self.scene = scene
        self.seed = seed
        self.rng = np.random.default_rng(seed + 991)

    def run(self, scan: np.ndarray, q_start: np.ndarray,
            target_hint: np.ndarray) -> dict:
        """Return the executed joint trajectory and the grasp attempted.

        `target_hint` is a rough position for the object to pick — what an
        upstream detector or an operator would give you, accurate to a few
        centimetres. Associating it with a perceived object is part of the job.
        """
        objects = perceive(scan)
        if not objects:
            return {"trajectory": [np.asarray(q_start, float)], "grasp": None,
                    "reason": "no objects perceived"}

        graspable = [o for o in objects if W_MIN <= 2 * o["radius"] <= W_MAX]
        if not graspable:
            return {"trajectory": [np.asarray(q_start, float)], "grasp": None,
                    "reason": "nothing within the gripper stroke"}
        # Associate the commanded hint with a perceived object.
        hint = np.asarray(target_hint, dtype=float)
        graspable.sort(key=lambda o: np.linalg.norm(o["centre"] - hint))
        target = graspable[0]
        t_idx = self._match_index(target)

        for cand in grasp_candidates(target)[:8]:
            traj = self._try(cand, q_start, t_idx)
            if traj is not None:
                return {"trajectory": traj, "grasp": cand, "reason": "ok"}
        return {"trajectory": [np.asarray(q_start, float)], "grasp": None,
                "reason": "no reachable grasp"}

    def _match_index(self, obj) -> int:
        """Which true object does this perceived one correspond to?"""
        d = np.linalg.norm(self.scene["centres"] - obj["centre"], axis=1)
        return int(np.argmin(d))

    def _try(self, cand, q_start, ignore):
        grasp_pt = cand["centre"]
        pre = grasp_pt + APPROACH * cand["approach"]

        q_pre, ok = solve_ik(pre, q_start)
        if not ok or collides(q_pre, self.scene):
            return None
        q_grasp, ok = solve_ik(grasp_pt, q_pre)
        # The target may be touched during the final approach; nothing else.
        if not ok or collides(q_grasp, self.scene, ignore=ignore):
            return None
        if manipulability(q_pre) < MIN_MANIP or manipulability(q_grasp) < MIN_MANIP:
            return None

        path = rrt(q_start, q_pre, self.scene, None, seed=self.seed)
        if path is None:
            return None
        path = shortcut(path, self.scene, None, self.rng)

        # Straight-line approach, warm-started so the arm stays on one branch.
        approach_traj = []
        q = path[-1]
        for t in np.linspace(0.0, 1.0, 12)[1:]:
            q, ok = solve_ik(pre + t * (grasp_pt - pre), q)
            if not ok or collides(q, self.scene, ignore=ignore):
                return None
            approach_traj.append(q)
        return [np.asarray(p, float) for p in path] + approach_traj


def make_stack(scene, seed=0):
    return GraspStack(scene, seed)
