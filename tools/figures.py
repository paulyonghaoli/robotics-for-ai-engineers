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
# Keep text as text rather than converting every glyph to a path: it cuts
# the SVGs by roughly an order of magnitude and keeps them diffable.
matplotlib.rcParams["svg.fonttype"] = "none"
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


# --------------------------------------------------------------------------
# 2.1 — the instantaneous centre of rotation
# --------------------------------------------------------------------------
@figure("icr-diffdrive")
def _icr(p):
    fig, ax = _axes(p, figsize=(6.2, 3.4))
    b = 0.5
    vr, vl = 1.2, 0.8
    vx = 0.5 * (vr + vl)
    omega = (vr - vl) / b
    r = vx / omega                       # 1.25 m

    ax.plot([0, 0], [-b / 2, b / 2], color=p["fg"], lw=3)      # axle
    for side, v in ((-b / 2, vl), (b / 2, vr)):
        ax.plot(0, side, "o", color=p["fg"], ms=7)
        _arrow(ax, (0, side), (0.45 * v, side), p["a1"],
               f"$v={v}$", lw=1.8, offset=(0.04, 0.06))

    ax.plot(0, r, "x", color=p["a2"], ms=11, mew=2.5)
    ax.text(0.12, r, "ICR", color=p["a2"], fontsize=10, va="center")
    ax.plot([0, 0], [b / 2, r], color=p["a2"], lw=1.2, ls=":")
    ax.text(0.06, (b / 2 + r) / 2, f"$r={r:.2f}$ m", color=p["a2"], fontsize=9)

    arc = np.linspace(-0.9, 0.9, 80)
    ax.plot(r * np.sin(arc), r - r * np.cos(arc), color=p["a3"], lw=1.6)
    ax.text(r * np.sin(0.9) + 0.05, r - r * np.cos(0.9), "path of the centre",
            color=p["a3"], fontsize=9)

    ax.set_xlim(-0.35, 1.5)
    ax.set_ylim(-0.6, 1.7)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("Both wheels turn about one point, at $r = v_x/\\omega$",
                 color=p["fg"], fontsize=10, pad=8)
    return fig


# --------------------------------------------------------------------------
# 2.2 — what each PID term does, measured on a first-order plant
# --------------------------------------------------------------------------
def _first_order(kp, ki, kd, steps=900, dt=0.01, tau=1.0, setpoint=1.0,
                 disturbance=0.0):
    y, integ, prev = 0.0, 0.0, None
    out = []
    for _ in range(steps):
        e = setpoint - y
        integ += e * dt
        d = 0.0 if prev is None else (e - prev) / dt
        prev = e
        u = kp * e + ki * integ + kd * d
        y += ((u + disturbance) - y) / tau * dt
        out.append(y)
    return np.array(out)


@figure("pid-terms")
def _pid_terms(p):
    dt = 0.01
    t = np.arange(900) * dt
    runs = [("P only  ($k_p$=4)", _first_order(4, 0, 0), p["a2"]),
            ("PI  ($k_i$=6)", _first_order(4, 6, 0), p["a4"]),
            ("PID  ($k_d$=0.6)", _first_order(4, 6, 0.6), p["a3"])]

    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(p["grid"])
    ax.tick_params(colors=p["muted"], labelsize=8)
    ax.axhline(1.0, color=p["grid"], lw=1.2, ls="--")
    ax.text(t[-1], 1.01, "setpoint", color=p["muted"], fontsize=8, ha="right")
    for label, y, col in runs:
        ax.plot(t, y, color=col, lw=1.8, label=label)
    final_p = runs[0][1][-1]
    ax.annotate(f"steady-state error {1 - final_p:.2f}",
                xy=(t[-1] * 0.8, final_p), xytext=(t[-1] * 0.35, 0.55),
                color=p["a2"], fontsize=9,
                arrowprops={"arrowstyle": "->", "color": p["a2"], "lw": 1.1})
    ax.set_xlabel("time (s)", color=p["muted"], fontsize=9)
    ax.set_ylabel("output", color=p["muted"], fontsize=9)
    ax.legend(frameon=False, fontsize=9, labelcolor=p["fg"], loc="lower right")
    ax.set_title("Step response of a first-order plant",
                 color=p["fg"], fontsize=10, pad=8)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# 2.2 — integral windup, and what the guard buys
# --------------------------------------------------------------------------
@figure("pid-windup")
def _pid_windup(p):
    dt, steps, u_max = 0.02, 700, 1.0
    gain, drag = 3.0, 0.8

    def run(guard):
        v, integ, trace, ints = 0.0, 0.0, [], []
        for k in range(steps):
            setpoint = 12.0 if k < 300 else 1.0     # unreachable, then reachable
            e = setpoint - v
            cand = integ + e * dt
            u_raw = 2.0 * e + 1.5 * cand
            u = float(np.clip(u_raw, -u_max, u_max))
            if not guard or u == u_raw:
                integ = cand                        # freeze while saturated
            v += dt * (gain * u - drag * v)
            trace.append(v)
            ints.append(integ)
        return np.array(trace), np.array(ints)

    t = np.arange(steps) * dt
    no_guard, _ = run(False)
    guarded, _ = run(True)

    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(p["grid"])
    ax.tick_params(colors=p["muted"], labelsize=8)
    ax.plot(t, no_guard, color=p["a2"], lw=1.8, label="no anti-windup")
    ax.plot(t, guarded, color=p["a3"], lw=1.8, label="integral frozen while saturated")
    ax.axvline(300 * dt, color=p["grid"], lw=1, ls=":")
    ax.text(300 * dt + 0.1, 4.2, "setpoint drops\n12 → 1", color=p["muted"], fontsize=8)
    ax.axhline(1.0, color=p["grid"], lw=1, ls="--")
    ax.set_xlabel("time (s)", color=p["muted"], fontsize=9)
    ax.set_ylabel("velocity (m/s)", color=p["muted"], fontsize=9)
    ax.legend(frameon=False, fontsize=9, labelcolor=p["fg"], loc="center right")
    ax.set_title("Chasing an unreachable setpoint, then a reachable one",
                 color=p["fg"], fontsize=10, pad=8)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# 2.3 — manipulability: the same arm is stiff in some directions
# --------------------------------------------------------------------------
@figure("manipulability")
def _manipulability(p):
    l1, l2 = 1.0, 0.8

    def fk(q):
        return np.array([l1 * np.cos(q[0]) + l2 * np.cos(q[0] + q[1]),
                         l1 * np.sin(q[0]) + l2 * np.sin(q[0] + q[1])])

    def jac(q):
        t1, t12 = q[0], q[0] + q[1]
        return np.array([[-l1 * np.sin(t1) - l2 * np.sin(t12), -l2 * np.sin(t12)],
                         [l1 * np.cos(t1) + l2 * np.cos(t12), l2 * np.cos(t12)]])

    fig, ax = _axes(p, figsize=(6.4, 3.6))
    poses = [(np.array([0.6, 1.5]), p["a1"], "well conditioned"),
             (np.array([0.35, 0.12]), p["a2"], "near singular (arm straight)")]
    circle = np.stack([np.cos(np.linspace(0, 2 * np.pi, 100)),
                       np.sin(np.linspace(0, 2 * np.pi, 100))])
    for q, col, label in poses:
        elbow = np.array([l1 * np.cos(q[0]), l1 * np.sin(q[0])])
        hand = fk(q)
        ax.plot([0, elbow[0], hand[0]], [0, elbow[1], hand[1]], "-o",
                color=col, lw=2.2, ms=5)
        J = jac(q)
        ell = 0.28 * (J @ circle)
        ax.plot(hand[0] + ell[0], hand[1] + ell[1], color=col, lw=1.6, ls="--")
        s = np.linalg.svd(J, compute_uv=False)
        ax.text(hand[0] + 0.06, hand[1] + 0.30,
                f"{label}\n$\\sigma_2/\\sigma_1$ = {s[1] / s[0]:.2f}",
                color=col, fontsize=9)
    ax.plot(0, 0, "o", color=p["fg"], ms=6)
    ax.set_xlim(-0.5, 2.4)
    ax.set_ylim(-1.0, 1.9)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("Unit joint velocity maps to this ellipse of tip velocity",
                 color=p["fg"], fontsize=10, pad=8)
    return fig


# --------------------------------------------------------------------------
# 2.4 — pure pursuit: lookahead trades cornering against stability
# --------------------------------------------------------------------------
@figure("pure-pursuit")
def _pure_pursuit(p):
    dt, v, w_max = 0.05, 1.0, 2.5
    path = np.stack([np.linspace(0, 60, 1200), np.zeros(1200)], axis=1)

    def run(ld, steps=400, y0=1.0):
        pose = np.array([0.0, y0, 0.0])
        ys = []
        for _ in range(steps):
            d = path - pose[:2]
            dist = np.hypot(d[:, 0], d[:, 1])
            idx = int(np.argmin(np.abs(dist - ld)))
            dx, dy = path[idx] - pose[:2]
            c, s = np.cos(-pose[2]), np.sin(-pose[2])
            _, ly = c * dx - s * dy, s * dx + c * dy
            w = float(np.clip(2 * v * ly / (ld ** 2), -w_max, w_max))
            pose = np.array([pose[0] + v * np.cos(pose[2]) * dt,
                             pose[1] + v * np.sin(pose[2]) * dt,
                             pose[2] + w * dt])
            ys.append(pose[1])
        return np.array(ys)

    t = np.arange(400) * dt
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(p["grid"])
    ax.tick_params(colors=p["muted"], labelsize=8)
    ax.axhline(0, color=p["grid"], lw=1.2, ls="--")
    for ld, col in ((0.5, p["a2"]), (1.5, p["a4"]), (4.0, p["a3"])):
        ax.plot(t, run(ld), color=col, lw=1.8, label=f"lookahead {ld} m")
    ax.set_xlabel("time (s)", color=p["muted"], fontsize=9)
    ax.set_ylabel("cross-track error (m)", color=p["muted"], fontsize=9)
    ax.legend(frameon=False, fontsize=9, labelcolor=p["fg"])
    ax.set_title("Returning to a straight path from 1 m off, at 1 m/s",
                 color=p["fg"], fontsize=10, pad=8)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# 2.6 — receding horizon: plan many, execute one
# --------------------------------------------------------------------------
@figure("mpc-horizon")
def _mpc_horizon(p):
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    for row, start in enumerate((0, 1, 2)):
        y = -row
        xs = np.arange(start, start + 8)
        plan = 0.35 * np.sin(0.5 * (xs - start)) + y
        ax.plot(xs, plan, "o--", color=p["muted"], ms=4, lw=1.2)
        ax.plot(xs[:2], plan[:2], "-", color=p["a1"], lw=3)
        ax.plot(xs[0], plan[0], "o", color=p["a1"], ms=7)
        ax.text(start - 0.6, y, f"$k={start}$", color=p["fg"], fontsize=9,
                ha="right", va="center")
        if row == 0:
            ax.text(xs[-1] + 0.2, plan[-1], "planned horizon",
                    color=p["muted"], fontsize=9, va="center")
            ax.text(xs[1] + 0.15, plan[1] + 0.22, "executed",
                    color=p["a1"], fontsize=9)
    ax.set_xlim(-2.2, 12.5)
    ax.set_ylim(-2.8, 0.9)
    ax.set_title("Each cycle re-plans the whole horizon and executes one step",
                 color=p["fg"], fontsize=10, pad=8)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# 2.1 — two IK solutions for the same target
# --------------------------------------------------------------------------
@figure("ik-branches")
def _ik_branches(p):
    l1 = l2 = 1.0
    target = np.array([1.2, 0.0])
    D = (target @ target - l1**2 - l2**2) / (2 * l1 * l2)
    fig, ax = _axes(p, figsize=(6.2, 3.4))

    for sign, col, name in ((+1, p["a1"], "elbow-up"), (-1, p["a2"], "elbow-down")):
        t2 = sign * np.arccos(D)
        t1 = (np.arctan2(target[1], target[0])
              - np.arctan2(l2 * np.sin(t2), l1 + l2 * np.cos(t2)))
        elbow = np.array([l1 * np.cos(t1), l1 * np.sin(t1)])
        ax.plot([0, elbow[0], target[0]], [0, elbow[1], target[1]], "-o",
                color=col, lw=2.2, ms=6,
                label=f"{name}: $\\theta_2$ = {np.degrees(t2):+.1f}°")

    for rad, ls in ((l1 + l2, "--"), (abs(l1 - l2) + 1e-9, ":")):
        a = np.linspace(0, 2 * np.pi, 200)
        ax.plot(rad * np.cos(a), rad * np.sin(a), color=p["grid"], lw=1, ls=ls)
    ax.text(1.45, 1.45, "reach limit", color=p["muted"], fontsize=9)

    ax.plot(*target, "*", color=p["a4"], ms=15)
    ax.text(target[0] + 0.06, target[1] - 0.22, "target (1.2, 0)",
            color=p["a4"], fontsize=9)
    ax.plot(0, 0, "o", color=p["fg"], ms=6)
    ax.legend(frameon=False, fontsize=9, labelcolor=p["fg"], loc="lower left")
    ax.set_xlim(-2.2, 2.4)
    ax.set_ylim(-1.6, 1.9)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("One target, two exact solutions",
                 color=p["fg"], fontsize=10, pad=8)
    return fig


# --------------------------------------------------------------------------
# 3.1 — prior times likelihood is posterior
# --------------------------------------------------------------------------
@figure("kalman-1d")
def _kalman_1d(p):
    x = np.linspace(-3, 9, 500)

    def g(mu, var):
        return np.exp(-0.5 * (x - mu) ** 2 / var) / np.sqrt(2 * np.pi * var)

    mu0, var0 = 2.0, 2.0          # prior
    z, varz = 6.0, 1.0            # measurement
    k = var0 / (var0 + varz)
    mu1 = mu0 + k * (z - mu0)
    var1 = (1 - k) * var0

    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(p["grid"])
    ax.tick_params(colors=p["muted"], labelsize=8)
    ax.set_yticks([])
    ax.plot(x, g(mu0, var0), color=p["a1"], lw=2,
            label=f"prior  $\\mu$={mu0:.0f}, $\\sigma^2$={var0:.0f}")
    ax.plot(x, g(z, varz), color=p["a2"], lw=2,
            label=f"measurement  $z$={z:.0f}, $\\sigma^2$={varz:.0f}")
    ax.plot(x, g(mu1, var1), color=p["a3"], lw=2.4,
            label=f"posterior  $\\mu$={mu1:.2f}, $\\sigma^2$={var1:.2f}")
    ax.fill_between(x, g(mu1, var1), color=p["a3"], alpha=0.12)
    ax.set_xlabel("position (m)", color=p["muted"], fontsize=9)
    ax.legend(frameon=False, fontsize=9, labelcolor=p["fg"])
    ax.set_title("The posterior is narrower than either input, and lies between them",
                 color=p["fg"], fontsize=10, pad=8)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# 3.1 — the covariance converges regardless of where it starts
# --------------------------------------------------------------------------
@figure("kalman-converge")
def _kalman_converge(p):
    q, r = 0.04, 1.0
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(p["grid"])
    ax.tick_params(colors=p["muted"], labelsize=8)
    finals = []
    for P0, col in ((25.0, p["a1"]), (5.0, p["a4"]), (0.01, p["a3"])):
        P, hist = P0, []
        for _ in range(30):
            P = P + q                      # predict
            K = P / (P + r)                # gain
            P = (1 - K) * P                # update
            hist.append(P)
        finals.append(hist[-1])
        ax.plot(hist, "o-", color=col, ms=3.5, lw=1.6, label=f"$P_0$ = {P0}")
    ax.axhline(finals[0], color=p["grid"], lw=1, ls="--")
    ax.text(29, finals[0] * 1.35, f"steady state ≈ {finals[0]:.3f}",
            color=p["muted"], fontsize=8, ha="right")
    ax.set_yscale("log")
    ax.set_xlabel("update", color=p["muted"], fontsize=9)
    ax.set_ylabel("variance $P$", color=p["muted"], fontsize=9)
    ax.legend(frameon=False, fontsize=9, labelcolor=p["fg"])
    ax.set_title("Three very different initial beliefs, same destination",
                 color=p["fg"], fontsize=10, pad=8)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# 3.2 — a particle cloud collapsing onto the truth
# --------------------------------------------------------------------------
@figure("particle-cloud")
def _particle_cloud(p):
    rng = np.random.default_rng(7)
    doors = np.array([3.0, 7.5, 15.0])
    n = 400
    parts = rng.uniform(0, 18, n)
    true_x = 2.0
    snapshots = {}
    for step in range(1, 13):
        parts = parts + 0.25 + rng.normal(0, 0.05, n)
        true_x = true_x + 0.25
        z = np.min(np.abs(true_x - doors)) + rng.normal(0, 0.3)
        d = np.min(np.abs(parts[:, None] - doors[None, :]), axis=1)
        w = np.exp(-0.5 * ((z - d) / 0.3) ** 2) + 1e-12
        w /= w.sum()
        parts = rng.choice(parts, size=n, p=w) + rng.normal(0, 0.05, n)
        if step in (1, 4, 12):
            snapshots[step] = (parts.copy(), true_x)

    fig, axes = plt.subplots(3, 1, figsize=(6.4, 3.6), sharex=True)
    fig.patch.set_alpha(0.0)
    for ax, (step, (pt, tx)) in zip(axes, snapshots.items(), strict=True):
        ax.patch.set_alpha(0.0)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color(p["grid"])
        ax.tick_params(colors=p["muted"], labelsize=8)
        ax.set_yticks([])
        ax.hist(pt, bins=70, range=(0, 18), color=p["a1"], alpha=0.85)
        ax.axvline(tx, color=p["a2"], lw=2)
        for d in doors:
            ax.axvline(d, color=p["a3"], lw=1, ls=":")
        ax.set_ylabel(f"step {step}", color=p["muted"], fontsize=9)
    axes[-1].set_xlabel("position (m)   ·   dotted = doors, red = truth",
                        color=p["muted"], fontsize=9)
    axes[0].set_title("Particles concentrate as door sightings accumulate",
                      color=p["fg"], fontsize=10, pad=6)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# 3.3 — linearising a curve is only safe over a small enough spread
# --------------------------------------------------------------------------
@figure("ekf-linearization")
def _ekf_linearization(p):
    x = np.linspace(0.5, 9.5, 400)
    h = lambda v: np.sqrt(v)          # noqa: E731  a mildly nonlinear sensor
    x0 = 4.0
    tangent = np.sqrt(x0) + (x - x0) / (2 * np.sqrt(x0))

    fig, (a0, a1) = plt.subplots(1, 2, figsize=(7.0, 3.1))
    fig.patch.set_alpha(0.0)
    for ax in (a0, a1):
        ax.patch.set_alpha(0.0)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(p["grid"])
        ax.tick_params(colors=p["muted"], labelsize=8)
        ax.plot(x, h(x), color=p["fg"], lw=2, label=r"true $h(x)=\sqrt{x}$")
        ax.plot(x, tangent, color=p["a2"], lw=1.8, ls="--",
                label="linearisation at $x_0$=4")
        ax.plot(x0, h(x0), "o", color=p["a1"], ms=6)
        ax.set_xlabel("$x$", color=p["muted"], fontsize=9)
    a0.axvspan(3.4, 4.6, color=p["a3"], alpha=0.18)
    a0.set_title("small spread: linearisation is fine", color=p["fg"], fontsize=10)
    a0.set_ylabel("$h(x)$", color=p["muted"], fontsize=9)
    a1.axvspan(1.0, 9.0, color=p["a2"], alpha=0.14)
    a1.set_title("large spread: the tangent lies badly", color=p["fg"], fontsize=10)
    a1.legend(frameon=False, fontsize=8, labelcolor=p["fg"], loc="lower right")
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# 3.5 — fusing two anisotropic estimates
# --------------------------------------------------------------------------
@figure("covariance-fusion")
def _covariance_fusion(p):
    P1 = np.array([[4.0, 0.0], [0.0, 0.25]])      # good in y, poor in x
    P2 = np.array([[0.25, 0.0], [0.0, 4.0]])      # good in x, poor in y
    m1 = np.array([-0.6, 0.4])
    m2 = np.array([0.7, -0.3])
    I1, I2 = np.linalg.inv(P1), np.linalg.inv(P2)
    Pf = np.linalg.inv(I1 + I2)
    mf = Pf @ (I1 @ m1 + I2 @ m2)

    a = np.linspace(0, 2 * np.pi, 200)
    unit = np.stack([np.cos(a), np.sin(a)])

    def ellipse(mean, P):
        L = np.linalg.cholesky(P)
        pts = L @ unit
        return mean[0] + pts[0], mean[1] + pts[1]

    fig, ax = _axes(p, figsize=(5.6, 3.6))
    for mean, P, col, lab in ((m1, P1, p["a1"], "estimate A"),
                              (m2, P2, p["a4"], "estimate B"),
                              (mf, Pf, p["a3"], "fused")):
        ex, ey = ellipse(mean, P)
        ax.plot(ex, ey, color=col, lw=2, label=lab)
        ax.plot(*mean, "o", color=col, ms=6)
    ax.legend(frameon=False, fontsize=9, labelcolor=p["fg"], loc="upper right")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("Each estimate is trusted where it is sharp",
                 color=p["fg"], fontsize=10, pad=8)
    return fig


# --------------------------------------------------------------------------
# 3.6 — NEES separates a tuned filter from a confident one
# --------------------------------------------------------------------------
@figure("nees-consistency")
def _nees_consistency(p):
    q_true, r_true = 0.09, 2.25

    def run(q_assumed, r_assumed, seed=13, n=600):
        rng = np.random.default_rng(seed)
        x_true, x, P = 0.0, 0.0, 10.0
        nees = []
        for _ in range(n):
            x_true += rng.normal(0, np.sqrt(q_true))
            P = P + q_assumed
            z = x_true + rng.normal(0, np.sqrt(r_true))
            y, S = z - x, P + r_assumed
            K = P / S
            x, P = x + K * y, (1 - K) * P
            nees.append((x - x_true) ** 2 / P)
        return np.array(nees[60:])

    cases = [("tuned", q_true, r_true, p["a3"]),
             ("overconfident (Q, R too small)", q_true / 8, r_true / 8, p["a2"]),
             ("underconfident (Q, R too large)", q_true * 8, r_true * 8, p["a1"])]

    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(p["grid"])
    ax.tick_params(colors=p["muted"], labelsize=8)
    labels, means = [], []
    for name, q, r, col in cases:
        m = float(np.mean(run(q, r)))
        labels.append(f"{name}\nmean NEES {m:.2f}")
        means.append(m)
        ax.barh(name.split(" (")[0], m, color=col, alpha=0.85, height=0.55)
    ax.axvline(1.0, color=p["fg"], lw=1.6, ls="--")
    ax.text(1.05, 2.35, "consistent filter: NEES ≈ 1",
            color=p["fg"], fontsize=9)
    ax.set_xscale("log")
    ax.set_xlabel("mean NEES (log scale)", color=p["muted"], fontsize=9)
    for i, m in enumerate(means):
        ax.text(m * 1.12, i, f"{m:.2f}", color=p["muted"], fontsize=9,
                va="center")
    ax.set_title("NEES needs ground truth, and reads the tuning directly",
                 color=p["fg"], fontsize=10, pad=8)
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
