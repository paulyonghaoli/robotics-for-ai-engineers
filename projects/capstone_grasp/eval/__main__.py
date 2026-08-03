"""Scenario evaluation for Capstone III.

    python -m eval run [--episodes 12] [--seed 0] [--stack reference_stack]

Ground truth is used for scoring only — stacks see the depth scan and
nothing else.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent.parent
for _p in (_HERE, _HERE / "solutions"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from world import (  # noqa: E402
    GRASP_TOL,
    Q_HOME,
    Q_MAX,
    Q_MIN,
    W_MAX,
    W_MIN,
    depth_scan,
    edge_collides,
    fk,
    make_scene,
    manipulability,
)

RUBRIC = {
    "grasp_success_rate": (">=", 0.80),
    "collision_free_rate": (">=", 0.95),
    "joint_limit_violations": ("<=", 0),
    "mean_plan_ms": ("<=", 200.0),
    "min_manipulability": (">=", 0.05),
}


def run_episode(stack_module, seed: int) -> dict:
    scene = make_scene(seed)
    rng = np.random.default_rng(seed + 4242)
    scan = depth_scan(scene, rng)

    # The commanded target, as an upstream detector or operator would give
    # it: the right object, located to within a few centimetres.
    hint = scene["centres"][int(scene["target"])] + rng.normal(0.0, 0.010, 2)

    t0 = time.perf_counter()
    stack = stack_module.make_stack(scene, seed)
    result = stack.run(scan, Q_HOME.copy(), hint)
    plan_ms = (time.perf_counter() - t0) * 1000.0

    traj = [np.asarray(q, dtype=float) for q in result.get("trajectory", [])]
    grasp = result.get("grasp")
    target = int(scene["target"])
    t_centre = scene["centres"][target]
    t_radius = float(scene["radii"][target])

    # Collision: every edge of the executed path, allowing contact with the
    # target only once the tool is inside the approach region.
    collision = False
    for a, b in zip(traj[:-1], traj[1:], strict=True):
        near = np.linalg.norm(fk(b) - t_centre) < t_radius + 0.12
        if edge_collides(a, b, scene, ignore=target if near else None):
            collision = True
            break

    limits = sum(int(np.any(q < Q_MIN - 1e-9) or np.any(q > Q_MAX + 1e-9))
                 for q in traj)
    manip = min((manipulability(q) for q in traj), default=0.0)

    # Success: the tool reached the target's centre within tolerance, the
    # grasp the stack chose is one the gripper can actually make, and the
    # object it grasped is the one it was supposed to grasp.
    reached = bool(traj) and float(np.linalg.norm(fk(traj[-1]) - t_centre)) < GRASP_TOL
    width_ok = grasp is not None and W_MIN <= float(grasp["width"]) <= W_MAX
    right_object = (grasp is not None
                    and float(np.linalg.norm(grasp["centre"] - t_centre)) < 0.03)
    success = bool(reached and width_ok and right_object and not collision)

    return {
        "seed": seed,
        "success": success,
        "reached": reached,
        "width_ok": bool(width_ok),
        "right_object": bool(right_object),
        "collision": bool(collision),
        "limit_violations": int(limits),
        "min_manipulability": round(float(manip), 4),
        "plan_ms": round(plan_ms, 1),
        "waypoints": len(traj),
        "reason": result.get("reason", ""),
    }


def evaluate(stack_name: str, episodes: int, base_seed: int) -> int:
    mod = importlib.import_module(stack_name)
    rows = [run_episode(mod, base_seed + 13 * i) for i in range(episodes)]

    metrics = {
        "grasp_success_rate": sum(r["success"] for r in rows) / len(rows),
        "collision_free_rate": sum(not r["collision"] for r in rows) / len(rows),
        "joint_limit_violations": sum(r["limit_violations"] for r in rows),
        "mean_plan_ms": float(np.mean([r["plan_ms"] for r in rows])),
        "min_manipulability": float(min(r["min_manipulability"] for r in rows)),
    }

    print(f"\n{stack_name} — {episodes} episodes (base seed {base_seed})\n")
    hdr = (f"{'seed':>6} {'ok':>3} {'coll':>5} {'lim':>4} {'minManip':>9} "
           f"{'planMs':>7} {'wpts':>5}  reason")
    print(hdr + "\n" + "-" * len(hdr))
    for r in rows:
        print(f"{r['seed']:>6} {'Y' if r['success'] else 'N':>3} "
              f"{'Y' if r['collision'] else '-':>5} {r['limit_violations']:>4} "
              f"{r['min_manipulability']:>9.3f} {r['plan_ms']:>7.0f} "
              f"{r['waypoints']:>5}  {r['reason']}")

    print("\nrubric:")
    passed = True
    for key, (op, thr) in RUBRIC.items():
        val = metrics[key]
        ok = val >= thr if op == ">=" else val <= thr
        passed = passed and ok
        print(f"  {'PASS' if ok else 'FAIL'}  {key} = {val:.3f}  (need {op} {thr})")

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump({"stack": stack_name, "metrics": metrics, "episodes": rows}, f, indent=1)
    print(f"\n{'RUBRIC PASSED' if passed else 'RUBRIC FAILED'} — details in results.json")
    return 0 if passed else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("--episodes", type=int, default=12)
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--stack", default="reference_stack")
    args = ap.parse_args()
    return evaluate(args.stack, args.episodes, args.seed)


if __name__ == "__main__":
    sys.exit(main())
