import numpy as np

from robotics_ai.estimation import ExtendedKalmanFilter
from robotics_ai.geometry import wrap_angle

LANDMARKS = np.array([[0.0, 10.0], [10.0, 0.0], [10.0, 10.0]])
DT = 0.1


def motion(x, v=1.0, w=0.3):
    px, py, th = x
    return np.array([px + v * np.cos(th) * DT, py + v * np.sin(th) * DT, wrap_angle(th + w * DT)])


def motion_jac(x, v=1.0):
    _, _, th = x
    return np.array([
        [1.0, 0.0, -v * np.sin(th) * DT],
        [0.0, 1.0, v * np.cos(th) * DT],
        [0.0, 0.0, 1.0],
    ])


def obs(x, lm):
    d = lm - x[:2]
    return np.array([np.hypot(*d), wrap_angle(np.arctan2(d[1], d[0]) - x[2])])


def obs_jac(x, lm):
    dx, dy = lm - x[:2]
    q = dx * dx + dy * dy
    r = np.sqrt(q)
    return np.array([[-dx / r, -dy / r, 0.0], [dy / q, -dx / q, -1.0]])


def residual(z, pred):
    y = z - pred
    y[1] = wrap_angle(y[1])
    return y


Q = np.diag([1e-3, 1e-3, 1e-3])
R = np.diag([0.1**2, 0.05**2])


def run_ekf(steps=300, seed=0, use_residual=True):
    rng = np.random.default_rng(seed)
    true_x = np.array([2.0, 2.0, 0.0])
    ekf = ExtendedKalmanFilter(true_x + [0.5, -0.5, 0.1], np.eye(3) * 1.0)
    errors = []
    for _ in range(steps):
        true_x = motion(true_x) + rng.normal(0, [0.01, 0.01, 0.005])
        true_x[2] = wrap_angle(true_x[2])
        ekf.predict(motion, motion_jac, Q)
        for lm in LANDMARKS:
            z = obs(true_x, lm) + rng.normal(0, [0.1, 0.05])
            z[1] = wrap_angle(z[1])
            ekf.update(
                z,
                lambda x, lm=lm: obs(x, lm),
                lambda x, lm=lm: obs_jac(x, lm),
                R,
                residual_fn=residual if use_residual else None,
            )
        errors.append(np.hypot(*(ekf.x[:2] - true_x[:2])))
    return np.array(errors), ekf


class TestEKF:
    def test_converges_on_range_bearing(self):
        errors, _ = run_ekf()
        assert errors[50:].mean() < 0.1, f"mean error {errors[50:].mean():.3f}"

    def test_covariance_bounded_and_spd(self):
        _, ekf = run_ekf()
        np.testing.assert_allclose(ekf.P, ekf.P.T, atol=1e-10)
        assert np.all(np.linalg.eigvalsh(ekf.P) > 0)
        assert ekf.P[0, 0] < 0.5

    def test_wrapped_residual_matters(self):
        # Without wrapping, bearing residuals near +/-pi inject huge
        # corrections; the filter should do visibly worse across seeds.
        wrapped = np.mean([run_ekf(seed=s)[0][50:].mean() for s in range(4)])
        raw = np.mean([run_ekf(seed=s, use_residual=False)[0][50:].mean() for s in range(4)])
        assert wrapped <= raw, f"wrapped {wrapped:.4f} should not be worse than raw {raw:.4f}"

    def test_predict_only_diverges(self):
        rng = np.random.default_rng(1)
        true_x = np.array([2.0, 2.0, 0.0])
        ekf = ExtendedKalmanFilter(true_x + [0.5, -0.5, 0.1], np.eye(3))
        for _ in range(300):
            true_x = motion(true_x) + rng.normal(0, [0.01, 0.01, 0.005])
            ekf.predict(motion, motion_jac, Q)
        assert ekf.P[0, 0] > 0.2, "without updates, uncertainty must keep growing"
