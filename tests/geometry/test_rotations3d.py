import numpy as np
import pytest

from robotics_ai.geometry import (
    matrix_to_quat,
    quat_conjugate,
    quat_from_axis_angle,
    quat_multiply,
    quat_normalize,
    quat_rotate,
    quat_to_matrix,
    slerp,
)

RNG = np.random.default_rng(42)


def random_quat():
    return quat_normalize(RNG.normal(size=4))


class TestQuatBasics:
    def test_normalize_unit(self):
        q = quat_normalize(np.array([2.0, 0.0, 0.0, 0.0]))
        np.testing.assert_allclose(q, [1.0, 0.0, 0.0, 0.0])

    def test_normalize_zero_raises(self):
        with pytest.raises(ValueError):
            quat_normalize(np.zeros(4))

    def test_axis_angle_zero_axis_raises(self):
        with pytest.raises(ValueError):
            quat_from_axis_angle(np.zeros(3), 1.0)

    def test_conjugate_is_inverse(self):
        q = random_quat()
        np.testing.assert_allclose(
            quat_multiply(q, quat_conjugate(q)), [1.0, 0.0, 0.0, 0.0], atol=1e-12
        )


class TestRotation:
    def test_quarter_turn_about_z(self):
        q = quat_from_axis_angle(np.array([0.0, 0.0, 1.0]), np.pi / 2)
        np.testing.assert_allclose(quat_rotate(q, [1.0, 0.0, 0.0]), [0.0, 1.0, 0.0], atol=1e-12)

    def test_matches_matrix_rotation(self):
        q = random_quat()
        v = RNG.normal(size=3)
        np.testing.assert_allclose(quat_rotate(q, v), quat_to_matrix(q) @ v, atol=1e-12)

    def test_composition_order_matches_matrices(self):
        q1, q2 = random_quat(), random_quat()
        np.testing.assert_allclose(
            quat_to_matrix(quat_multiply(q1, q2)),
            quat_to_matrix(q1) @ quat_to_matrix(q2),
            atol=1e-12,
        )

    def test_matrix_is_rotation(self):
        R = quat_to_matrix(random_quat())
        np.testing.assert_allclose(R @ R.T, np.eye(3), atol=1e-12)
        assert np.linalg.det(R) == pytest.approx(1.0)


class TestMatrixToQuat:
    def test_round_trip_random(self):
        for _ in range(50):
            q = random_quat()
            q2 = matrix_to_quat(quat_to_matrix(q))
            # q and -q are the same rotation; compare via |dot| = 1.
            assert abs(np.dot(q, q2)) == pytest.approx(1.0)

    def test_near_180_degree_rotations(self):
        # Trace near -1: the branch where the naive trace formula blows up.
        for axis in np.eye(3):
            q = quat_from_axis_angle(axis, np.pi - 1e-7)
            q2 = matrix_to_quat(quat_to_matrix(q))
            assert abs(np.dot(q, q2)) == pytest.approx(1.0)

    def test_identity(self):
        np.testing.assert_allclose(matrix_to_quat(np.eye(3)), [1.0, 0.0, 0.0, 0.0])


class TestSlerp:
    def test_endpoints(self):
        q0, q1 = random_quat(), random_quat()
        assert abs(np.dot(slerp(q0, q1, 0.0), q0)) == pytest.approx(1.0)
        assert abs(np.dot(slerp(q0, q1, 1.0), q1)) == pytest.approx(1.0)

    def test_midpoint_is_half_rotation(self):
        q0 = quat_from_axis_angle(np.array([0.0, 0.0, 1.0]), 0.0)
        q1 = quat_from_axis_angle(np.array([0.0, 0.0, 1.0]), np.pi / 2)
        expected = quat_from_axis_angle(np.array([0.0, 0.0, 1.0]), np.pi / 4)
        np.testing.assert_allclose(slerp(q0, q1, 0.5), expected, atol=1e-12)

    def test_takes_shortest_arc(self):
        q0 = quat_from_axis_angle(np.array([0.0, 0.0, 1.0]), 0.1)
        q1 = -quat_from_axis_angle(np.array([0.0, 0.0, 1.0]), 0.2)  # negated: same rotation
        mid = slerp(q0, q1, 0.5)
        expected = quat_from_axis_angle(np.array([0.0, 0.0, 1.0]), 0.15)
        assert abs(np.dot(mid, expected)) == pytest.approx(1.0)

    def test_nearly_parallel_falls_back_gracefully(self):
        q0 = random_quat()
        q1 = quat_normalize(q0 + 1e-12 * np.array([0.0, 1.0, 0.0, 0.0]))
        out = slerp(q0, q1, 0.5)
        assert np.linalg.norm(out) == pytest.approx(1.0)

    def test_result_always_unit(self):
        for t in np.linspace(0, 1, 7):
            assert np.linalg.norm(slerp(random_quat(), random_quat(), t)) == pytest.approx(1.0)
