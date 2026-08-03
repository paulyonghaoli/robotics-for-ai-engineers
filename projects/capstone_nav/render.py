"""Render capstone episodes as animated GIFs.

    python render.py pf         --seed 34   # v1: particle cloud collapsing
    python render.py mapping    --seed 0    # v2: the map filling in
    python render.py dynamic    --seed 1000 # v3: dodging movers
    python render.py all

These are generated from real evaluation episodes — the same code paths
`python -m eval run` scores — not from a staged demo. Whatever the robot
does here is what it does when it's being graded.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
import numpy as np

# The reference stacks live in solutions/ so they don't sit next to the
# assignment. Putting that directory on the path keeps every command that
# names one ("--stack pf_stack") working exactly as before.
_SOLUTIONS = Path(__file__).resolve().parent / "solutions"
if str(_SOLUTIONS) not in sys.path:
    sys.path.insert(0, str(_SOLUTIONS))


matplotlib.use("Agg")
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.animation import PillowWriter  # noqa: E402
from sim import (  # noqa: E402
    MAX_RANGE,
    N_RAYS,
    ROBOT_RADIUS,
    WORLD_SIZE,
    Simulator,
)

OUT = Path(__file__).resolve().parent.parent.parent / "docs" / "assets" / "demo"
BG, WALL, ROBOT_C, PATH_C, PART_C, GOAL_C, DYN_C = (
    "#12121a", "#4a4a63", "#5ec8f5", "#f5a05e", "#9b7ef0", "#5ef58f", "#f55e7a"
)


def capture(stack_name: str, seed: int, n_dynamic: int = 0, max_steps: int = 400):
    """Run one episode, recording everything needed to draw it."""
    import importlib

    mod = importlib.import_module(stack_name)
    sim = Simulator(seed, n_dynamic=n_dynamic)
    stack = mod.make_stack(sim)
    obs = sim.reset()
    frames, done, k = [], False, 0
    while not done and k < max_steps:
        v, w = stack.step(obs)
        est = getattr(stack, "last_estimate", None)
        particles = getattr(stack, "particles", None)
        omap = getattr(stack, "map", None)
        frames.append({
            "pose": sim.pose.copy(),
            "scan": obs["scan"].copy(),
            "est": None if est is None else np.asarray(est).copy(),
            "particles": None if particles is None else particles[::12, :2].copy(),
            "path": None if stack.path is None else np.asarray(stack.path).copy(),
            "prob": None if omap is None else omap.probability().copy(),
            "dyn": [ob.pos.copy() for ob in sim.obstacles],
            "dyn_r": [ob.radius for ob in sim.obstacles],
        })
        obs, done = sim.step(v, w)
        k += 1
    return sim, frames


def capture_global(seed: int, n_particles: int = 8000, inject: float = 0.15,
                   lik_sigma: float = 0.9, steps: int = 75):
    """Global localization: the filter starts with NO idea where it is.

    A known-good stack drives (so the demo isolates the *filter*), while the
    particle filter localizes from a uniform prior over free space. Two
    settings from lesson 3.2 make this work and are worth naming: random
    injection keeps hypotheses alive, and a softened likelihood stops the
    sensor model from killing diversity before evidence accumulates.
    """
    import pf_stack as pf_mod
    import reference_stack as ref_mod
    from sim import world_to_cell

    pf_mod.N_PARTICLES, pf_mod.LIK_SIGMA = n_particles, lik_sigma
    sim = Simulator(seed)
    pf, ref = pf_mod.make_stack(sim), ref_mod.make_stack(sim)
    obs = sim.reset()
    rng = np.random.default_rng(1)

    pts = []
    while len(pts) < n_particles:
        p = rng.uniform(0.5, WORLD_SIZE - 0.5, 2)
        if not sim.grid[world_to_cell(p)]:
            pts.append([p[0], p[1], rng.uniform(-np.pi, np.pi)])
    pf.particles = np.array(pts)
    pf.weights = np.full(n_particles, 1.0 / n_particles)

    frames = []
    for _ in range(steps):
        v, w = ref.step(obs)
        pf.last_cmd = (v, w)
        pf._motion_update()
        m = max(1, int(inject * n_particles))
        idx = rng.choice(n_particles, m, replace=False)
        pf.particles[idx, 0] = rng.uniform(0.5, WORLD_SIZE - 0.5, m)
        pf.particles[idx, 1] = rng.uniform(0.5, WORLD_SIZE - 0.5, m)
        pf.particles[idx, 2] = rng.uniform(-np.pi, np.pi, m)
        pf._measurement_update(obs["scan"])
        est = pf._estimate()
        pf._resample_if_needed()
        frames.append({
            "pose": sim.pose.copy(), "scan": obs["scan"].copy(),
            "est": est.copy(), "particles": pf.particles[::4, :2].copy(),
            "path": None, "prob": None, "dyn": [], "dyn_r": [],
            "err": float(np.hypot(*(est[:2] - sim.pose[:2]))),
        })
        obs, done = sim.step(v, w)
        if done:
            break
    return sim, frames


def render(stack_name: str, seed: int, out_name: str, title: str,
           n_dynamic: int = 0, show_map: bool = False, stride: int = 3,
           global_loc: bool = False):
    if global_loc:
        sim, frames = capture_global(seed)
        stride = 1
    else:
        sim, frames = capture(stack_name, seed, n_dynamic)
    frames = frames[::stride]
    if not frames:
        raise RuntimeError(f"{out_name}: captured zero frames")
    print(f"  {out_name}: {len(frames)} frames, goal reached = {sim.at_goal}")

    fig, ax = plt.subplots(figsize=(5.2, 5.2), dpi=100)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    OUT.mkdir(parents=True, exist_ok=True)
    writer = PillowWriter(fps=12)

    with writer.saving(fig, str(OUT / out_name), dpi=100):
        for f in frames:
            ax.clear()
            ax.set_facecolor(BG)
            ax.set_xlim(0, WORLD_SIZE)
            ax.set_ylim(0, WORLD_SIZE)
            ax.set_xticks([])
            ax.set_yticks([])
            for s in ax.spines.values():
                s.set_color("#2a2a3a")

            if show_map and f["prob"] is not None:
                ax.imshow(f["prob"], origin="lower", cmap="bone",
                          extent=(0, WORLD_SIZE, 0, WORLD_SIZE), vmin=0, vmax=1, alpha=0.95)
            else:
                ax.imshow(sim.grid, origin="lower", cmap="Greys_r",
                          extent=(0, WORLD_SIZE, 0, WORLD_SIZE), alpha=0.28)

            if f["path"] is not None and len(f["path"]) > 1:
                ax.plot(f["path"][:, 0], f["path"][:, 1], "-", color=PATH_C, lw=1.4, alpha=0.75)

            if f["particles"] is not None:
                psize = 2.6 if len(f["particles"]) > 500 else 5.0
                ax.scatter(f["particles"][:, 0], f["particles"][:, 1], s=psize,
                           c=PART_C, alpha=0.6, linewidths=0, zorder=4)

            pose = f["pose"]
            bearings = pose[2] + np.arange(N_RAYS) * (2 * np.pi / N_RAYS)
            hit = f["scan"] < MAX_RANGE - 0.25
            ex = pose[0] + f["scan"] * np.cos(bearings)
            ey = pose[1] + f["scan"] * np.sin(bearings)
            for i in np.flatnonzero(hit):
                ax.plot([pose[0], ex[i]], [pose[1], ey[i]], "-", color="#3d5a6c",
                        lw=0.4, alpha=0.5)

            for p, r in zip(f["dyn"], f["dyn_r"], strict=False):
                ax.add_patch(mpatches.Circle(p, r, color=DYN_C, alpha=0.85, zorder=5))

            ax.add_patch(mpatches.Circle(pose[:2], ROBOT_RADIUS, color=ROBOT_C, zorder=6))
            ax.plot([pose[0], pose[0] + 0.55 * np.cos(pose[2])],
                    [pose[1], pose[1] + 0.55 * np.sin(pose[2])],
                    "-", color="white", lw=1.6, zorder=7)
            ax.plot(*sim.goal, "*", color=GOAL_C, markersize=17, zorder=8)
            sub = title
            if "err" in f:
                sub = f"{title}   ·   error {f['err']:.1f} m"
            ax.set_title(sub, color="#d8d8e8", fontsize=10, pad=8)
            writer.grab_frame(facecolor=BG)
    plt.close(fig)


DEMOS = {
    "pf": dict(stack_name="pf_stack", seed=34, out_name="capstone-v1-localization.gif",
               title="v1 · particle-filter lidar localization"),
    "mapping": dict(stack_name="mapping_stack", seed=0, out_name="capstone-v2-mapping.gif",
                    title="v2 · building the map while driving", show_map=True),
    "global": dict(stack_name="pf_stack", seed=34, out_name="capstone-global-localization.gif",
                   title="global localization · 8,000 particles, no prior", global_loc=True),
    "dynamic": dict(stack_name="dynamic_stack", seed=1000, out_name="capstone-v3-dynamic.gif",
                    title="v3 · avoiding obstacles that aren't in the map", n_dynamic=6),
    "slam": dict(stack_name="slam_stack", seed=51, out_name="capstone-v4-slam.gif",
                 title="v4 · SLAM — no map, and no pose sensor", show_map=True),
}


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    seed_override = None
    if "--seed" in sys.argv:
        seed_override = int(sys.argv[sys.argv.index("--seed") + 1])
    targets = DEMOS if which == "all" else {which: DEMOS[which]}
    print(f"rendering into {OUT}")
    for cfg in targets.values():
        cfg = dict(cfg)
        if seed_override is not None:
            cfg["seed"] = seed_override
        render(**cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
