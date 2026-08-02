import numpy as np
import pytest

from robotics_ai.control import cross_track_error, lookahead_point, pure_pursuit
from robotics_ai.geometry import wrap_angle


def drive(pose, path, lookahead=0.8, v=1.0, steps=300, dt=0.05):
    """Closed-loop pure-pursuit rollout; returns pose history."""
    poses = []
    for _ in range(steps):
        w = np.clip(pure_pursuit(np.asarray(pose), path, lookahead, v), -2.5, 2.5)
        x, y, th = pose
        if abs(w) < 1e-9:
            pose = (x + v * np.cos(th) * dt, y + v * np.sin(th) * dt, th)
        else:
            r = v / w
            pose = (
                x + r * (np.sin(th + w * dt) - np.sin(th)),
                y - r * (np.cos(th + w * dt) - np.cos(th)),
                wrap_angle(th + w * dt),
            )
        poses.append(pose)
    return np.array(poses)


STRAIGHT = np.column_stack([np.linspace(0, 30, 301), np.zeros(301)])


class TestGeometry:
    def test_cross_track_sign(self):
        # Path along +x; robot below the path (y = -1) -> path is to its LEFT.
        assert cross_track_error(np.array([5.0, -1.0, 0.0]), STRAIGHT) == pytest.approx(1.0)
        assert cross_track_error(np.array([5.0, 2.0, 0.0]), STRAIGHT) == pytest.approx(-2.0)

    def test_lookahead_point_ahead(self):
        g = lookahead_point(np.array([5.0, 0.0, 0.0]), STRAIGHT, 2.0)
        assert g[0] >= 7.0 - 0.2

    def test_lookahead_end_of_path(self):
        g = lookahead_point(np.array([29.9, 0.0, 0.0]), STRAIGHT, 5.0)
        np.testing.assert_allclose(g, STRAIGHT[-1])

    def test_bad_lookahead_raises(self):
        with pytest.raises(ValueError):
            pure_pursuit(np.array([0.0, 0.0, 0.0]), STRAIGHT, 0.0, 1.0)

    def test_steers_toward_path(self):
        # Robot left of the path, facing along it: must steer right (w < 0).
        assert pure_pursuit(np.array([5.0, 1.0, 0.0]), STRAIGHT, 1.5, 1.0) < 0
        assert pure_pursuit(np.array([5.0, -1.0, 0.0]), STRAIGHT, 1.5, 1.0) > 0


class TestClosedLoop:
    def test_converges_from_lateral_offset(self):
        poses = drive((0.0, 2.0, 0.0), STRAIGHT)
        assert np.all(np.abs(poses[150:, 1]) < 0.1), (
            f"late lateral error {np.abs(poses[150:, 1]).max():.3f}"
        )

    def test_tracks_circle(self):
        t = np.linspace(0, 2 * np.pi, 400)
        circle = np.column_stack([5 * np.cos(t), 5 * np.sin(t)])
        poses = drive((5.0, 0.0, np.pi / 2), circle, lookahead=1.0, steps=500)
        radii = np.hypot(poses[:, 0], poses[:, 1])
        assert np.all(np.abs(radii[100:] - 5.0) < 0.35), (
            f"worst radial error {np.abs(radii[100:] - 5.0).max():.3f}"
        )

    def test_shorter_lookahead_tracks_tighter(self):
        t = np.linspace(0, 2 * np.pi, 400)
        circle = np.column_stack([5 * np.cos(t), 5 * np.sin(t)])
        err = {}
        for L in (0.5, 2.5):
            poses = drive((5.0, 0.0, np.pi / 2), circle, lookahead=L, steps=400)
            radii = np.hypot(poses[100:, 0], poses[100:, 1])
            err[L] = np.abs(radii - 5.0).mean()
        assert err[0.5] < err[2.5], (
            f"short lookahead should cut the corner less (0.5: {err[0.5]:.3f}, 2.5: {err[2.5]:.3f})"
        )
