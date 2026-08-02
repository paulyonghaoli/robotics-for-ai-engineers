import numpy as np
import pytest

from robotics_ai.geometry import (
    relative_pose,
    rot2,
    se2,
    se2_compose,
    se2_inverse,
    se2_to_pose,
    transform_points,
    wrap_angle,
)


class TestWrapAngle:
    def test_identity_in_range(self):
        assert wrap_angle(0.5) == pytest.approx(0.5)
        assert wrap_angle(-3.0) == pytest.approx(-3.0)

    def test_boundary_pi_maps_to_pi(self):
        # Interval is (-pi, pi]: +pi stays +pi, -pi wraps to +pi.
        assert wrap_angle(np.pi) == pytest.approx(np.pi)
        assert wrap_angle(-np.pi) == pytest.approx(np.pi)

    def test_full_turns_removed(self):
        assert wrap_angle(3 * np.pi) == pytest.approx(np.pi)
        assert wrap_angle(2 * np.pi) == pytest.approx(0.0)
        assert wrap_angle(-5 * np.pi / 2) == pytest.approx(-np.pi / 2)

    def test_heading_error_near_pi_is_small(self):
        # The bug this function exists to prevent: headings straddling +/-pi.
        error = wrap_angle((np.pi - 0.05) - (-np.pi + 0.05))
        assert error == pytest.approx(-0.1)

    def test_array_input(self):
        out = wrap_angle(np.array([0.0, 3 * np.pi, -np.pi]))
        np.testing.assert_allclose(out, [0.0, np.pi, np.pi], atol=1e-12)


class TestRot2:
    def test_quarter_turn(self):
        np.testing.assert_allclose(rot2(np.pi / 2) @ [1.0, 0.0], [0.0, 1.0], atol=1e-12)

    def test_orthonormal(self):
        R = rot2(1.234)
        np.testing.assert_allclose(R @ R.T, np.eye(2), atol=1e-12)
        assert np.linalg.det(R) == pytest.approx(1.0)


class TestSe2:
    def test_pose_round_trip(self):
        x, y, theta = 1.5, -2.0, 2.5
        assert se2_to_pose(se2(x, y, theta)) == pytest.approx((x, y, theta))

    def test_inverse_composes_to_identity(self):
        T = se2(3.0, -1.0, 0.7)
        np.testing.assert_allclose(se2_compose(T, se2_inverse(T)), np.eye(3), atol=1e-12)
        np.testing.assert_allclose(se2_compose(se2_inverse(T), T), np.eye(3), atol=1e-12)

    def test_compose_chain(self):
        # Robot at (1, 0) facing +y; sensor mounted 0.5 m ahead of base.
        T_map_base = se2(1.0, 0.0, np.pi / 2)
        T_base_sensor = se2(0.5, 0.0, 0.0)
        T_map_sensor = se2_compose(T_map_base, T_base_sensor)
        x, y, theta = se2_to_pose(T_map_sensor)
        assert (x, y) == pytest.approx((1.0, 0.5))
        assert theta == pytest.approx(np.pi / 2)

    def test_compose_empty_is_identity(self):
        np.testing.assert_allclose(se2_compose(), np.eye(3))

    def test_relative_pose(self):
        T_map_a = se2(1.0, 1.0, 0.0)
        T_map_b = se2(2.0, 1.0, np.pi)
        x, y, theta = se2_to_pose(relative_pose(T_map_a, T_map_b))
        assert (x, y) == pytest.approx((1.0, 0.0))
        assert abs(wrap_angle(theta)) == pytest.approx(np.pi)


class TestTransformPoints:
    def test_single_point(self):
        p = transform_points(se2(1.0, 0.0, np.pi / 2), np.array([1.0, 0.0]))
        np.testing.assert_allclose(p, [1.0, 1.0], atol=1e-12)

    def test_point_set_shape_preserved(self):
        pts = np.random.default_rng(0).normal(size=(10, 2))
        out = transform_points(se2(0.3, -0.2, 0.1), pts)
        assert out.shape == (10, 2)

    def test_rigid_distances_preserved(self):
        pts = np.array([[0.0, 0.0], [3.0, 4.0]])
        out = transform_points(se2(5.0, -2.0, 1.9), pts)
        assert np.linalg.norm(out[1] - out[0]) == pytest.approx(5.0)

    def test_bad_shape_raises(self):
        with pytest.raises(ValueError):
            transform_points(se2(0, 0, 0), np.zeros((4, 3)))

    def test_round_trip_through_inverse(self):
        T = se2(2.0, 3.0, -1.2)
        pts = np.array([[1.0, 2.0], [-0.5, 0.25]])
        np.testing.assert_allclose(
            transform_points(se2_inverse(T), transform_points(T, pts)), pts, atol=1e-12
        )
