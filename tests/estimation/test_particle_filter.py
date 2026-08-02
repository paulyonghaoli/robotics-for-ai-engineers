import numpy as np
import pytest

from robotics_ai.estimation import ParticleFilter


def make_1d_pf(n=2000, seed=0, low=0.0, high=10.0):
    rng = np.random.default_rng(seed)
    particles = rng.uniform(low, high, size=(n, 1))
    return ParticleFilter(particles, rng=rng)


class TestParticleFilter:
    def test_localizes_from_uniform_prior(self):
        pf = make_1d_pf()
        true_x = 7.3
        for _ in range(10):
            pf.predict(lambda p, rng: p + rng.normal(0, 0.05, p.shape))
            pf.update(lambda p: np.exp(-0.5 * ((p[:, 0] - true_x) / 0.5) ** 2))
            if pf.neff() < pf.n / 2:
                pf.resample()
        assert pf.estimate()[0] == pytest.approx(true_x, abs=0.3)

    def test_weights_normalized_after_update(self):
        pf = make_1d_pf()
        pf.update(lambda p: np.ones(len(p)) * 5.0)
        assert pf.weights.sum() == pytest.approx(1.0)

    def test_degenerate_update_recovers_uniform(self):
        pf = make_1d_pf(n=100)
        pf.update(lambda p: np.zeros(len(p)))  # impossible measurement
        assert pf.weights.sum() == pytest.approx(1.0)
        assert pf.neff() == pytest.approx(100.0)

    def test_neff_drops_with_peaked_weights(self):
        pf = make_1d_pf(n=100)
        assert pf.neff() == pytest.approx(100.0)
        pf.update(lambda p: np.exp(-0.5 * ((p[:, 0] - 5.0) / 0.1) ** 2) + 1e-12)
        assert pf.neff() < 50.0

    def test_systematic_resample_follows_weights(self):
        pf = make_1d_pf(n=1000, seed=3)
        # Peak the weights hard around x = 2.
        pf.update(lambda p: np.exp(-0.5 * ((p[:, 0] - 2.0) / 0.2) ** 2) + 1e-12)
        pf.resample()
        assert pf.weights.max() == pytest.approx(1.0 / 1000)
        assert np.mean(pf.particles[:, 0]) == pytest.approx(2.0, abs=0.3)

    def test_kidnapped_robot_recovers_with_random_injection(self):
        # The classic: converged in the wrong place, then strong evidence
        # elsewhere. Pure SIR fails; 10% uniform injection recovers.
        rng = np.random.default_rng(4)
        pf = ParticleFilter(rng.normal(2.0, 0.1, size=(1000, 1)), rng=rng)  # wrong belief
        true_x = 8.0
        for _ in range(25):
            def inject_and_drift(p, rng):
                p = p + rng.normal(0, 0.05, p.shape)
                k = len(p) // 10
                p[rng.choice(len(p), k, replace=False), 0] = rng.uniform(0, 10, k)
                return p
            pf.predict(inject_and_drift)
            pf.update(lambda p: np.exp(-0.5 * ((p[:, 0] - true_x) / 0.5) ** 2) + 1e-12)
            if pf.neff() < pf.n / 2:
                pf.resample()
        assert pf.estimate()[0] == pytest.approx(true_x, abs=0.5)
