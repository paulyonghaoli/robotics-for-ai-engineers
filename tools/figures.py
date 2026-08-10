"""Lesson figures, generated from code at build time.

A hand-drawn diagram can disagree with the mathematics it illustrates, and
nothing would catch it. These are computed by the same NumPy the lessons use,
so a figure showing a rotation is showing an actual rotation.

Each figure is emitted twice, light and dark, and the page shows whichever
matches the reader's palette (see `.rai-fig` in interactive.css).

Run standalone to regenerate:  python tools/figures.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "docs" / "assets" / "generated" / "figures"

PALETTES = {
    "light": {"fg": "#22272e", "muted": "#6b7280", "grid": "#d8d8dd",
              "a1": "#5e35b1", "a2": "#c62828", "a3": "#2e7d32", "a4": "#ef6c00"},
    "dark": {"fg": "#e2e4e9", "muted": "#9aa0aa", "grid": "#3a3f4a",
             "a1": "#b39ddb", "a2": "#ef9a9a", "a3": "#a5d6a7", "a4": "#ffb74d"},
}

FIGURES: dict[str, callable] = {}


def figure(name: str):
    def deco(fn):
        FIGURES[name] = fn
        return fn
    return deco


def _axes(p, figsize=(6.4, 3.6), equal=True):
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(colors=p["muted"], labelsize=8)
    if equal:
        ax.set_aspect("equal")
    return fig, ax


def _arrow(ax, start, end, color, label=None, lw=2.0, ls="-", offset=(0.08, 0.08)):
    ax.annotate("", xy=end, xytext=start,
                arrowprops={"arrowstyle": "-|>", "color": color,
                            "linewidth": lw, "linestyle": ls,
                            "shrinkA": 0, "shrinkB": 0})
    if label:
        ax.text(end[0] + offset[0], end[1] + offset[1], label,
                color=color, fontsize=10, ha="left", va="bottom")


# --------------------------------------------------------------------------
# 1.1 — what a rotation matrix does to the basis vectors
# --------------------------------------------------------------------------
@figure("rotation-2d")
def _rotation_2d(p):
    theta = np.deg2rad(35.0)
    c, s = np.cos(theta), np.sin(theta)
    fig, ax = _axes(p, figsize=(6.4, 3.4))

    ax.axhline(0, color=p["grid"], lw=1)
    ax.axvline(0, color=p["grid"], lw=1)

    _arrow(ax, (0, 0), (1, 0), p["muted"], r"$e_1=(1,0)$", lw=1.6)
    _arrow(ax, (0, 0), (0, 1), p["muted"], r"$e_2=(0,1)$", lw=1.6)
    _arrow(ax, (0, 0), (c, s), p["a1"], r"$Re_1=(\cos\theta,\ \sin\theta)$")
    _arrow(ax, (0, 0), (-s, c), p["a2"], r"$Re_2=(-\sin\theta,\ \cos\theta)$",
           offset=(-0.05, 0.10))

    arc = np.linspace(0, theta, 60)
    ax.plot(0.42 * np.cos(arc), 0.42 * np.sin(arc), color=p["fg"], lw=1.2)
    ax.text(0.50 * np.cos(theta / 2), 0.50 * np.sin(theta / 2), r"$\theta$",
            color=p["fg"], fontsize=11)

    ax.set_xlim(-0.9, 1.9)
    ax.set_ylim(-0.35, 1.45)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("The columns of $R$ are where the basis vectors land",
                 color=p["fg"], fontsize=10, pad=8)
    return fig


# --------------------------------------------------------------------------
# 1.1 — one physical point, two frames, two sets of numbers
# --------------------------------------------------------------------------
@figure("frames-two-views")
def _frames_two_views(p):
    fig, ax = _axes(p, figsize=(6.4, 3.8))

    # Frame A at origin, frame B translated and rotated.
    thB = np.deg2rad(50.0)
    tB = np.array([1.6, 0.5])
    RB = np.array([[np.cos(thB), -np.sin(thB)], [np.sin(thB), np.cos(thB)]])

    for origin, R, col, name in ((np.zeros(2), np.eye(2), p["a1"], "A"),
                                 (tB, RB, p["a3"], "B")):
        _arrow(ax, origin, origin + 0.7 * R[:, 0], col, f"$x_{name}$", lw=1.8)
        _arrow(ax, origin, origin + 0.7 * R[:, 1], col, f"$y_{name}$", lw=1.8)
        ax.plot(*origin, "o", color=col, ms=5)

    P = np.array([2.6, 1.9])
    ax.plot(*P, "o", color=p["a2"], ms=8)
    ax.text(P[0] + 0.08, P[1] + 0.10, "the same physical point $P$",
            color=p["a2"], fontsize=10)

    pA = P
    pB = RB.T @ (P - tB)
    ax.plot([0, P[0]], [0, P[1]], color=p["a1"], lw=1.0, ls=":")
    ax.plot([tB[0], P[0]], [tB[1], P[1]], color=p["a3"], lw=1.0, ls=":")
    ax.text(1.15, 0.95, rf"$p_A=({pA[0]:.2f},\ {pA[1]:.2f})$",
            color=p["a1"], fontsize=10)
    ax.text(2.02, 1.10, rf"$p_B=({pB[0]:.2f},\ {pB[1]:.2f})$",
            color=p["a3"], fontsize=10)

    ax.set_xlim(-0.5, 4.2)
    ax.set_ylim(-0.5, 2.6)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("Neither pair of numbers is more correct than the other",
                 color=p["fg"], fontsize=10, pad=8)
    return fig


# --------------------------------------------------------------------------
# 1.1 — the worked composition example, drawn to scale
# --------------------------------------------------------------------------
@figure("compose-chain")
def _compose_chain(p):
    fig, ax = _axes(p, figsize=(6.4, 4.0))

    def se2(x, y, th):
        c, s = np.cos(th), np.sin(th)
        return np.array([[c, -s, x], [s, c, y], [0, 0, 1.0]])

    T_map_base = se2(1.0, 0.0, np.pi / 2)
    T_base_lidar = se2(0.5, 0.0, 0.0)
    T_map_lidar = T_map_base @ T_base_lidar
    p_map = (T_map_lidar @ np.array([2.0, 0.0, 1.0]))[:2]

    ax.axhline(0, color=p["grid"], lw=1)
    ax.axvline(0, color=p["grid"], lw=1)
    _arrow(ax, (0, 0), (0.45, 0), p["muted"], "$x_{map}$", lw=1.4)
    _arrow(ax, (0, 0), (0, 0.45), p["muted"], "$y_{map}$", lw=1.4)

    for T, col, name in ((T_map_base, p["a1"], "base"),
                         (T_map_lidar, p["a3"], "lidar")):
        o, R = T[:2, 2], T[:2, :2]
        _arrow(ax, o, o + 0.45 * R[:, 0], col, f"$x_{{{name}}}$", lw=1.8)
        ax.plot(*o, "o", color=col, ms=6)
        ax.text(o[0] + 0.10, o[1] - 0.22, f"{name}\n({o[0]:.1f}, {o[1]:.1f})",
                color=col, fontsize=9)

    ax.plot(*p_map, "*", color=p["a2"], ms=14)
    ax.text(p_map[0] + 0.10, p_map[1], f"detection\n({p_map[0]:.1f}, {p_map[1]:.1f})",
            color=p["a2"], fontsize=9, va="center")
    ax.plot([T_map_lidar[0, 2], p_map[0]], [T_map_lidar[1, 2], p_map[1]],
            color=p["a2"], lw=1.0, ls=":")

    ax.set_xlim(-0.5, 2.6)
    ax.set_ylim(-0.4, 3.0)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("2 m ahead of a sensor that is itself rotated 90°",
                 color=p["fg"], fontsize=10, pad=8)
    return fig


# --------------------------------------------------------------------------
# 1.1 — why heading subtraction needs wrapping
# --------------------------------------------------------------------------
@figure("angle-wrap")
def _angle_wrap(p):
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(7.0, 3.0))
    fig.patch.set_alpha(0.0)
    for ax in (a0, a1):
        ax.patch.set_alpha(0.0)
        for s in ax.spines.values():
            s.set_color(p["grid"])
        ax.tick_params(colors=p["muted"], labelsize=8)

    t = np.linspace(-np.pi, np.pi, 400)
    raw = t - (-t)                      # naive difference of two headings
    wrapped = -(np.mod(-raw + np.pi, 2 * np.pi) - np.pi)

    a0.plot(t, raw, color=p["a2"], lw=2)
    a0.set_title("naive $\\theta_1-\\theta_2$", color=p["fg"], fontsize=10)
    a1.plot(t, wrapped, color=p["a3"], lw=2)
    a1.set_title("wrapped to $(-\\pi,\\pi]$", color=p["fg"], fontsize=10)

    for ax in (a0, a1):
        ax.axhline(0, color=p["grid"], lw=0.8)
        ax.set_xlabel("heading (rad)", color=p["muted"], fontsize=9)
        ax.set_ylim(-7.2, 7.2)
        for y in (-np.pi, np.pi):
            ax.axhline(y, color=p["grid"], lw=0.8, ls=":")
    a0.set_ylabel("commanded turn (rad)", color=p["muted"], fontsize=9)
    a0.annotate("a 2° error reads\nas nearly 360°", xy=(2.9, 5.8), xytext=(0.2, 5.4),
                color=p["a2"], fontsize=9,
                arrowprops={"arrowstyle": "->", "color": p["a2"], "lw": 1.2})
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# 1.2 — slerp keeps angular speed constant, lerp does not
# --------------------------------------------------------------------------
@figure("slerp-vs-lerp")
def _slerp_vs_lerp(p):
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(7.0, 3.2))
    fig.patch.set_alpha(0.0)
    for ax in (a0, a1):
        ax.patch.set_alpha(0.0)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.tick_params(colors=p["muted"], labelsize=8)

    q0 = np.array([1.0, 0.0])
    ang = np.deg2rad(140.0)
    q1 = np.array([np.cos(ang), np.sin(ang)])
    ts = np.linspace(0, 1, 11)

    a0.set_aspect("equal")
    circ = np.linspace(0, 2 * np.pi, 200)
    a0.plot(np.cos(circ), np.sin(circ), color=p["grid"], lw=1)
    lerp = np.array([(1 - t) * q0 + t * q1 for t in ts])
    slerp = np.array([
        (np.sin((1 - t) * ang) * q0 + np.sin(t * ang) * q1) / np.sin(ang)
        for t in ts])
    a0.plot(lerp[:, 0], lerp[:, 1], "o-", color=p["a2"], ms=4, lw=1.4, label="lerp")
    a0.plot(slerp[:, 0], slerp[:, 1], "o-", color=p["a3"], ms=4, lw=1.4, label="slerp")
    a0.legend(frameon=False, fontsize=9, labelcolor=p["fg"], loc="lower left")
    a0.set_xticks([])
    a0.set_yticks([])
    a0.set_title("equal steps in $t$", color=p["fg"], fontsize=10)

    # Angular speed between consecutive samples.
    def speeds(pts):
        pts = pts / np.linalg.norm(pts, axis=1, keepdims=True)
        d = np.einsum("ij,ij->i", pts[:-1], pts[1:]).clip(-1, 1)
        return np.degrees(np.arccos(d))

    mid = 0.5 * (ts[:-1] + ts[1:])
    a1.plot(mid, speeds(lerp), "o-", color=p["a2"], ms=4, lw=1.4)
    a1.plot(mid, speeds(slerp), "o-", color=p["a3"], ms=4, lw=1.4)
    a1.set_xlabel("$t$", color=p["muted"], fontsize=9)
    a1.set_ylabel("degrees per step", color=p["muted"], fontsize=9)
    a1.set_title("lerp speeds up mid-arc", color=p["fg"], fontsize=10)
    a1.spines["left"].set_visible(True)
    a1.spines["left"].set_color(p["grid"])
    a1.spines["bottom"].set_visible(True)
    a1.spines["bottom"].set_color(p["grid"])
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# 1.2 — measured drift: rotation matrix vs quaternion
# --------------------------------------------------------------------------
@figure("rotation-drift")
def _rotation_drift(p):
    axis = np.array([0.3, 0.5, 0.81])
    axis = axis / np.linalg.norm(axis)
    step = np.deg2rad(1.0)

    def rot(axis, a):
        x, y, z = axis
        K = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
        return np.eye(3) + np.sin(a) * K + (1 - np.cos(a)) * (K @ K)

    def qmul(a, b):
        w1, x1, y1, z1 = a
        w2, x2, y2, z2 = b
        return np.array([w1*w2 - x1*x2 - y1*y2 - z1*z2,
                         w1*x2 + x1*w2 + y1*z2 - z1*y2,
                         w1*y2 - x1*z2 + y1*w2 + z1*x2,
                         w1*z2 + x1*y2 - y1*x2 + z1*w2])

    dR = rot(axis, step)
    dq = np.concatenate(([np.cos(step / 2)], np.sin(step / 2) * axis))
    R, q = np.eye(3), np.array([1.0, 0, 0, 0])
    n = 100_000
    xs, r_err, q_err = [], [], []
    for i in range(1, n + 1):
        R = R @ dR
        q = qmul(q, dq)
        if i % 1000 == 0:
            xs.append(i)
            r_err.append(np.abs(R @ R.T - np.eye(3)).max())
            q_err.append(abs(np.linalg.norm(q) - 1.0))

    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(p["grid"])
    ax.tick_params(colors=p["muted"], labelsize=8)
    ax.plot(xs, r_err, color=p["a2"], lw=2, label=r"matrix: $\max|RR^\top-I|$")
    ax.plot(xs, q_err, color=p["a3"], lw=2, label=r"quaternion: $|\,\|q\|-1|$")
    ax.set_yscale("log")
    ax.set_xlabel("compositions", color=p["muted"], fontsize=9)
    ax.set_ylabel("constraint violation", color=p["muted"], fontsize=9)
    ax.legend(frameon=False, fontsize=9, labelcolor=p["fg"])
    ax.set_title("Measured drift over 100,000 compositions, no renormalisation",
                 color=p["fg"], fontsize=10, pad=8)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# 1.3 — why REP 105 splits the pose across two edges
# --------------------------------------------------------------------------
@figure("odom-drift-correction")
def _odom_drift_correction(p):
    rng = np.random.default_rng(3)
    n = 500
    truth = np.zeros(n)
    drift = np.cumsum(rng.normal(0.0, 0.012, n))      # odometry random walk
    odom_base = truth + drift

    # The localiser corrects every 100 steps, so the correction edge holds
    # whatever offset is needed to make map->base agree with truth.
    correction = np.zeros(n)
    fix = 0.0
    for k in range(n):
        if k % 100 == 0 and k > 0:
            fix = -drift[k]
        correction[k] = fix
    map_base = odom_base + correction

    fig, ax = plt.subplots(figsize=(6.6, 3.2))
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(p["grid"])
    ax.tick_params(colors=p["muted"], labelsize=8)

    ax.axhline(0, color=p["grid"], lw=1, ls="--")
    ax.plot(odom_base, color=p["a4"], lw=1.8, label="odom → base  (smooth, drifts)")
    ax.plot(map_base, color=p["a1"], lw=1.8, label="map → base  (accurate, jumps)")
    ax.set_xlabel("step", color=p["muted"], fontsize=9)
    ax.set_ylabel("error vs truth (m)", color=p["muted"], fontsize=9)
    ax.legend(frameon=False, fontsize=9, labelcolor=p["fg"], loc="upper left")
    ax.set_title("The localiser's jump lands in the edge controllers do not read",
                 color=p["fg"], fontsize=10, pad=8)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# 1.4 — a constant twist traces an arc; Euler cuts the chord
# --------------------------------------------------------------------------
@figure("arc-vs-euler")
def _arc_vs_euler(p):
    v, omega = 1.0, 1.2

    def run(dt, steps, exact):
        x, y, th = 0.0, 0.0, 0.0
        out = [(x, y)]
        for _ in range(steps):
            if exact and abs(omega) > 1e-9:
                r = v / omega
                x += r * (np.sin(th + omega * dt) - np.sin(th))
                y -= r * (np.cos(th + omega * dt) - np.cos(th))
            else:
                x += v * np.cos(th) * dt
                y += v * np.sin(th) * dt
            th += omega * dt
            out.append((x, y))
        return np.array(out)

    fine = run(0.005, 1200, True)
    arc = run(0.4, 15, True)
    euler = run(0.4, 15, False)

    fig, ax = _axes(p, figsize=(6.2, 3.6))
    ax.plot(fine[:, 0], fine[:, 1], color=p["grid"], lw=3,
            label="true path (constant twist)")
    ax.plot(arc[:, 0], arc[:, 1], "o-", color=p["a3"], ms=4, lw=1.5,
            label="arc model, dt = 0.4 s")
    ax.plot(euler[:, 0], euler[:, 1], "o-", color=p["a2"], ms=4, lw=1.5,
            label="Euler, dt = 0.4 s")
    ax.legend(frameon=False, fontsize=9, labelcolor=p["fg"], loc="lower left")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("Euler cuts every corner the same way, so the error accumulates",
                 color=p["fg"], fontsize=10, pad=8)
    return fig


# --------------------------------------------------------------------------
# 1.4 — measured integration error against rate
# --------------------------------------------------------------------------
@figure("integration-error")
def _integration_error(p):
    v, omega = 1.0, 0.5

    def run(steps, T, exact):
        dt = T / steps
        x = y = th = 0.0
        for _ in range(steps):
            if exact:
                r = v / omega
                x += r * (np.sin(th + omega * dt) - np.sin(th))
                y -= r * (np.cos(th + omega * dt) - np.cos(th))
            else:
                x += v * np.cos(th) * dt
                y += v * np.sin(th) * dt
            th += omega * dt
        return np.array([x, y])

    def truth(T):
        r = v / omega
        return np.array([r * np.sin(omega * T), r * (1 - np.cos(omega * T))])

    T = (2 * np.pi / omega) * 0.75          # three quarters of a circle
    rates = np.array([2.5, 5, 10, 20, 40, 80])
    target = truth(T)
    e_arc, e_eul = [], []
    for rate in rates:
        n = int(round(T * rate))
        e_arc.append(max(float(np.linalg.norm(run(n, T, True) - target)), 1e-16))
        e_eul.append(float(np.linalg.norm(run(n, T, False) - target)))

    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(p["grid"])
    ax.tick_params(colors=p["muted"], labelsize=8)
    ax.loglog(rates, e_eul, "o-", color=p["a2"], lw=2, ms=5,
              label="Euler (halves when the rate doubles)")
    ax.loglog(rates, e_arc, "o-", color=p["a3"], lw=2, ms=5,
              label="arc model (machine precision)")
    ax.set_xlabel("integration rate (Hz)", color=p["muted"], fontsize=9)
    ax.set_ylabel("position error (m)", color=p["muted"], fontsize=9)
    ax.legend(frameon=False, fontsize=9, labelcolor=p["fg"], loc="center left")
    ax.set_title("Error after three quarters of a circle at 1 m/s, 0.5 rad/s",
                 color=p["fg"], fontsize=10, pad=8)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# 1.5 — the disk robot collapses to a point when obstacles are inflated
# --------------------------------------------------------------------------
@figure("cspace-inflation")
def _cspace_inflation(p):
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(7.0, 3.4))
    fig.patch.set_alpha(0.0)
    obstacles = [(1.0, 1.0, 0.45), (2.4, 1.8, 0.35)]
    r = 0.35
    for ax, inflate, title in ((a0, False, "workspace: a disk of radius r"),
                               (a1, True, "C-space: obstacles grown by r")):
        ax.patch.set_alpha(0.0)
        ax.set_aspect("equal")
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_xticks([])
        ax.set_yticks([])
        for (cx, cy, rad) in obstacles:
            ax.add_patch(plt.Circle((cx, cy), rad, color=p["muted"], alpha=0.55))
            if inflate:
                ax.add_patch(plt.Circle((cx, cy), rad + r, color=p["a2"],
                                        alpha=0.20))
                ax.add_patch(plt.Circle((cx, cy), rad + r, fill=False,
                                        color=p["a2"], lw=1.2, ls="--"))
        if inflate:
            ax.plot(1.9, 0.75, "o", color=p["a1"], ms=6)
        else:
            ax.add_patch(plt.Circle((1.9, 0.75), r, color=p["a1"], alpha=0.35))
            ax.add_patch(plt.Circle((1.9, 0.75), r, fill=False, color=p["a1"], lw=1.4))
            ax.plot(1.9, 0.75, "o", color=p["a1"], ms=4)
        ax.set_xlim(0, 3.2)
        ax.set_ylim(0, 2.6)
        ax.set_title(title, color=p["fg"], fontsize=10)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# 1.5 — the two-link arm's C-space obstacle map, computed
# --------------------------------------------------------------------------
@figure("cspace-map")
def _cspace_map(p):
    l1, l2 = 1.0, 0.8
    circles = [(1.15, 0.45, 0.30), (-0.30, 1.05, 0.28)]

    def arm_points(t1, t2, n=20):
        elbow = np.array([l1 * np.cos(t1), l1 * np.sin(t1)])
        hand = elbow + np.array([l2 * np.cos(t1 + t2), l2 * np.sin(t1 + t2)])
        t = np.linspace(0, 1, n)[:, None]
        return np.vstack([t * elbow, elbow + t * (hand - elbow)])

    def hit(t1, t2):
        pts = arm_points(t1, t2)
        return any(np.min(np.hypot(pts[:, 0] - cx, pts[:, 1] - cy)) < rad
                   for cx, cy, rad in circles)

    grid = np.linspace(-np.pi, np.pi, 140)
    occ = np.array([[hit(a, b) for b in grid] for a in grid])

    fig, (a0, a1) = plt.subplots(1, 2, figsize=(7.2, 3.6))
    fig.patch.set_alpha(0.0)
    for ax in (a0, a1):
        ax.patch.set_alpha(0.0)
        for s in ax.spines.values():
            s.set_color(p["grid"])
        ax.tick_params(colors=p["muted"], labelsize=8)

    a0.set_aspect("equal")
    for (cx, cy, rad) in circles:
        a0.add_patch(plt.Circle((cx, cy), rad, color=p["a2"], alpha=0.45))
    for t1, t2, col in ((0.5, 0.8, p["a1"]), (2.2, -1.1, p["a3"])):
        elbow = np.array([l1 * np.cos(t1), l1 * np.sin(t1)])
        hand = elbow + np.array([l2 * np.cos(t1 + t2), l2 * np.sin(t1 + t2)])
        a0.plot([0, elbow[0], hand[0]], [0, elbow[1], hand[1]], "-o",
                color=col, lw=2, ms=4)
        a0.plot(0, 0, "o", color=p["fg"], ms=4)
    a0.set_xlim(-2.0, 2.0)
    a0.set_ylim(-2.0, 2.0)
    a0.set_xticks([])
    a0.set_yticks([])
    a0.set_title("workspace: two obstacles, two arm poses",
                 color=p["fg"], fontsize=10)

    a1.imshow(occ.T, origin="lower", extent=[-np.pi, np.pi, -np.pi, np.pi],
              cmap="Greys", alpha=0.85, aspect="auto")
    a1.plot(0.5, 0.8, "o", color=p["a1"], ms=7)
    a1.plot(2.2, -1.1, "o", color=p["a3"], ms=7)
    a1.set_xlabel(r"$\theta_1$", color=p["muted"], fontsize=10)
    a1.set_ylabel(r"$\theta_2$", color=p["muted"], fontsize=10)
    a1.set_title("C-space: the same obstacles, in joint angles",
                 color=p["fg"], fontsize=10)
    fig.tight_layout()
    return fig


def render_all() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    written = 0
    for name, fn in FIGURES.items():
        for scheme, palette in PALETTES.items():
            fig = fn(palette)
            target = OUT / f"{name}-{scheme}.svg"
            tmp = target.with_suffix(".tmp")
            fig.savefig(tmp, format="svg", transparent=True, bbox_inches="tight")
            plt.close(fig)
            new = tmp.read_text(encoding="utf-8")
            # Strip the id/date noise matplotlib emits so unchanged figures
            # don't churn the working tree on every build.
            import re
            new = re.sub(r'\s*<dc:date>.*?</dc:date>', "", new, flags=re.S)
            tmp.unlink()
            if not target.exists() or target.read_text(encoding="utf-8") != new:
                target.write_text(new, encoding="utf-8")
                written += 1
    return written


if __name__ == "__main__":
    n = render_all()
    print(f"figures: {len(FIGURES)} x 2 schemes, {n} file(s) written -> {OUT}")
    sys.exit(0)
