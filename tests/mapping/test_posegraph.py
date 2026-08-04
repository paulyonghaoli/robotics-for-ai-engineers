"""Pose-graph back end: tested against graphs whose answer is known.

The optimizer is the one piece of the SLAM stack that can be checked
without a simulator — build a trajectory, corrupt it with a known bias,
add the constraint that says where it should have ended, and the correct
answer is the trajectory you started from.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_CAPSTONE = Path(__file__).resolve().parents[2] / "projects" / "capstone_nav"
if str(_CAPSTONE) not in sys.path:
    sys.path.insert(0, str(_CAPSTONE))

from posegraph import (  # noqa: E402
    PoseGraph,
    compose,
    match_scan_to_scan,
    relative_pose,
)


def _octagon(radius: float = 3.0) -> list[np.ndarray]:
    """Eight poses around a closed circuit, facing along the path."""
    out = []
    for i in range(8):
        th = i * (np.pi / 4)
        out.append(np.array([radius * np.cos(th) - radius,
                             radius * np.sin(th),
                             th + np.pi / 2]))
    return out


def _drifted_graph(bias: float) -> tuple[PoseGraph, list[np.ndarray]]:
    """The circuit walked with a constant rotation bias on every edge."""
    truth = _octagon()
    g = PoseGraph()
    g.poses.append(truth[0].copy())
    g.scans.append(None)
    g.raws.append(None)
    info = np.diag([400.0, 400.0, 278.0])
    for i in range(1, len(truth)):
        rel = relative_pose(truth[i - 1], truth[i]) + np.array([0.0, 0.0, bias])
        g.poses.append(compose(g.poses[-1], rel))
        g.scans.append(None)
        g.raws.append(None)
        g.edges.append((i - 1, i, rel, info))
    return g, truth


def test_relative_and_compose_round_trip():
    a = np.array([1.0, -2.0, 0.7])
    b = np.array([-3.0, 4.0, -2.1])
    back = compose(a, relative_pose(a, b))
    assert np.allclose(back[:2], b[:2], atol=1e-12)
    assert abs(np.sin(back[2] - b[2])) < 1e-12


def test_optimizer_absorbs_a_constant_bias():
    g, truth = _drifted_graph(bias=0.05)
    before = float(np.hypot(*(g.poses[-1][:2] - truth[-1][:2])))
    assert before > 1.0, "a 0.05 rad per-edge bias should open the loop by metres"

    # The closure: keyframe 7 is where keyframe 0 was, measured correctly.
    g.add_loop(0, 7, relative_pose(truth[0], truth[7]))
    g.optimize(20)

    errs = [float(np.hypot(*(g.poses[i][:2] - truth[i][:2]))) for i in range(len(truth))]
    assert errs[-1] < 0.02, f"the loop should close, got {errs[-1]:.3f} m"
    # The correction is distributed over the whole trajectory, not dumped on
    # the last node — that is the difference between a pose graph and a
    # one-off snap.
    assert max(errs) < 0.05, f"worst node error {max(errs):.3f} m"


def test_optimizer_is_a_no_op_without_a_closure():
    """Odometry edges alone are already perfectly satisfied by the
    trajectory that produced them: there is nothing to optimize, and an
    optimizer that moves anything here is wrong."""
    g, _truth = _drifted_graph(bias=0.05)
    before = [p.copy() for p in g.poses]
    g.optimize(20)
    for a, b in zip(before, g.poses, strict=True):
        assert np.allclose(a, b, atol=1e-6)


def test_gauge_is_pinned():
    g, truth = _drifted_graph(bias=0.05)
    g.add_loop(0, 7, relative_pose(truth[0], truth[7]))
    g.optimize(20)
    # Absolute pose is unobservable, so node 0 defines the frame. If it
    # moves, every map built against it moves too.
    assert np.allclose(g.poses[0], truth[0], atol=1e-6)


def test_scan_to_scan_recovers_a_known_transform():
    rng = np.random.default_rng(3)
    ref = rng.uniform(-4.0, 4.0, size=(60, 2))
    true_rel = np.array([0.6, -0.35, 0.18])
    c, s = np.cos(true_rel[2]), np.sin(true_rel[2])
    # Points seen from a pose at `true_rel` relative to the reference.
    cur = np.stack([
        (ref[:, 0] - true_rel[0]) * c + (ref[:, 1] - true_rel[1]) * s,
        -(ref[:, 0] - true_rel[0]) * s + (ref[:, 1] - true_rel[1]) * c,
    ], axis=1)

    z, q = match_scan_to_scan(ref, cur, guess=np.zeros(3))
    assert q > 0.6, f"a clean overlap should match well, got quality {q:.2f}"
    assert np.hypot(*(z[:2] - true_rel[:2])) < 0.25
    assert abs(z[2] - true_rel[2]) < 0.12


def test_scan_to_scan_refuses_too_few_points():
    """An open-space scan is mostly max-range returns, so the cloud is tiny
    and there is not enough geometry to identify a place. Refusing is the
    correct answer; a confident match on six points is not."""
    tiny = np.zeros((4, 2))
    z, q = match_scan_to_scan(tiny, tiny, guess=np.array([1.0, 2.0, 0.3]))
    assert q == 0.0
    assert np.allclose(z, [1.0, 2.0, 0.3]), "and it returns the guess unchanged"


@pytest.mark.parametrize("bias", [0.02, 0.05, 0.09])
def test_closure_helps_at_every_bias(bias):
    g, truth = _drifted_graph(bias=bias)
    before = float(np.hypot(*(g.poses[-1][:2] - truth[-1][:2])))
    g.add_loop(0, 7, relative_pose(truth[0], truth[7]))
    g.optimize(20)
    after = float(np.hypot(*(g.poses[-1][:2] - truth[-1][:2])))
    assert after < 0.05 * before or after < 0.02
