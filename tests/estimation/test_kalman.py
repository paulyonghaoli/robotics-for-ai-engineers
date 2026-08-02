import numpy as np
import pytest

from robotics_ai.estimation import KalmanFilter


def make_cv_filter(dt=0.1, q=0.01, r=0.5):
    """Constant-velocity 1D tracker: state [pos, vel], measure pos."""
    return KalmanFilter(
        F=[[1.0, dt], [0.0, 1.0]],
        H=[[1.0, 0.0]],
        Q=np.array([[dt**3 / 3, dt**2 / 2], [dt**2 / 2, dt]]) * q,
        R=[[r**2]],
        x0=[0.0, 0.0],
        P0=np.eye(2) * 10.0,
    )


class TestKalman:
    def test_tracks_constant_velocity(self):
        rng = np.random.default_rng(0)
        kf = make_cv_filter()
        true_pos, true_vel = 0.0, 1.0
        for _ in range(200):
            true_pos += true_vel * 0.1
            kf.predict()
            kf.update([true_pos + rng.normal(0, 0.5)])
        assert kf.x[0] == pytest.approx(true_pos, abs=0.5)
        assert kf.x[1] == pytest.approx(true_vel, abs=0.3)

    def test_update_reduces_uncertainty(self):
        kf = make_cv_filter()
        kf.predict()
        var_before = kf.P[0, 0]
        kf.update([0.0])
        assert kf.P[0, 0] < var_before

    def test_predict_grows_uncertainty(self):
        kf = make_cv_filter()
        kf.update([0.0])
        var_before = kf.P[0, 0]
        kf.predict()
        assert kf.P[0, 0] > var_before

    def test_covariance_stays_symmetric(self):
        rng = np.random.default_rng(1)
        kf = make_cv_filter()
        for _ in range(500):
            kf.predict()
            kf.update([rng.normal()])
        np.testing.assert_allclose(kf.P, kf.P.T, atol=1e-12)
        assert np.all(np.linalg.eigvalsh(kf.P) > 0)

    def test_control_input(self):
        kf = KalmanFilter(
            F=[[1.0]], H=[[1.0]], Q=[[0.0]], R=[[1.0]], x0=[0.0], P0=[[1.0]], B=[[1.0]]
        )
        kf.predict(u=[2.0])
        assert kf.x[0] == pytest.approx(2.0)

    def test_control_without_b_raises(self):
        kf = make_cv_filter()
        with pytest.raises(ValueError):
            kf.predict(u=[1.0])

    def test_nis_reasonable_for_consistent_filter(self):
        rng = np.random.default_rng(2)
        kf = make_cv_filter()
        true_pos, vals = 0.0, []
        for _ in range(300):
            true_pos += 0.1
            kf.predict()
            z = [true_pos + rng.normal(0, 0.5)]
            vals.append(kf.nis(z))
            kf.update(z)
        # NIS for a consistent filter with 1D measurements averages ~1 (chi2 dof=1).
        assert 0.5 < np.mean(vals[50:]) < 2.0
