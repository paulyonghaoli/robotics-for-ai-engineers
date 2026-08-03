"""Tests for Capstone II's infrastructure.

These check the *apparatus*, not the policy. The policy is allowed to be
bad — it is supposed to be bad. What must not break is the machinery that
measures how bad, because every downstream decision rests on it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
SHIP = ROOT / "projects" / "capstone_ship"
NAV = ROOT / "projects" / "capstone_nav"
for p in (SHIP, SHIP / "solutions", NAV, NAV / "solutions"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from evaluate import wilson  # noqa: E402  (solutions/evaluate.py)
from policy import ACT_DIM, OBS_DIM, MLPPolicy, featurize  # noqa: E402


class TestWilson:
    def test_zero_successes_has_nonzero_upper_bound(self):
        lo, hi = wilson(0, 20)
        assert lo == 0.0
        assert 0.1 < hi < 0.2, "0/20 does not prove a rate of zero"

    def test_perfect_score_does_not_reach_one(self):
        lo, hi = wilson(8, 8)
        assert hi == 1.0
        assert 0.6 < lo < 0.7, "8/8 bounds you near 0.68, not 1.0"

    def test_interval_narrows_with_n(self):
        narrow = wilson(50, 100)
        wide = wilson(5, 10)
        assert (narrow[1] - narrow[0]) < (wide[1] - wide[0])

    def test_contains_point_estimate(self):
        for k, n in ((3, 14), (20, 48), (46, 48), (1, 3)):
            lo, hi = wilson(k, n)
            assert lo <= k / n <= hi

    def test_empty_sample_is_maximally_uncertain(self):
        assert wilson(0, 0) == (0.0, 1.0)


class TestFeaturize:
    def _scan(self):
        return np.full(36, 3.0)

    def test_shape(self):
        f = featurize(self._scan(), np.array([1.0, 1.0, 0.0]), np.array([5.0, 5.0]))
        assert f.shape == (OBS_DIM,)

    def test_is_translation_invariant_in_the_body_frame(self):
        """Same relative geometry, different world position -> same features."""
        a = featurize(self._scan(), np.array([1.0, 1.0, 0.3]), np.array([4.0, 5.0]))
        b = featurize(self._scan(), np.array([6.0, 3.0, 0.3]), np.array([9.0, 7.0]))
        np.testing.assert_allclose(a, b, atol=1e-12)

    def test_rotating_robot_changes_goal_bearing(self):
        pose = np.array([1.0, 1.0, 0.0])
        a = featurize(self._scan(), pose, np.array([5.0, 1.0]))
        b = featurize(self._scan(), pose + np.array([0, 0, np.pi / 2]),
                      np.array([5.0, 1.0]))
        assert not np.allclose(a, b), "body-frame bearing must track heading"

    def test_scan_is_bounded(self):
        f = featurize(np.full(36, 99.0), np.zeros(3), np.array([1.0, 1.0]))
        assert f[:36].max() <= 1.0


class TestPolicy:
    def test_output_shape_single_and_batch(self):
        p = MLPPolicy(seed=1)
        assert p(np.zeros(OBS_DIM)).shape == (ACT_DIM,)
        assert p(np.zeros((7, OBS_DIM))).shape == (7, ACT_DIM)

    def test_fit_reduces_error_on_a_learnable_map(self):
        rng = np.random.default_rng(0)
        X = rng.normal(size=(600, OBS_DIM))
        Y = np.stack([X[:, 0] * 0.5 + X[:, 1], np.tanh(X[:, 2])], axis=1)
        p = MLPPolicy(hidden=32, seed=0)
        before = float(np.mean((p(X) - Y) ** 2))
        stats = p.fit(X, Y, epochs=40, seed=0)
        assert stats["final_train_mse"] < before * 0.5

    def test_save_load_roundtrip(self, tmp_path):
        p = MLPPolicy(seed=3)
        X = np.random.default_rng(1).normal(size=(64, OBS_DIM))
        p.fit(X, np.zeros((64, ACT_DIM)), epochs=2, seed=0)
        f = tmp_path / "w.npz"
        p.save(str(f))
        np.testing.assert_allclose(MLPPolicy.load(str(f))(X), p(X), atol=1e-12)


class TestCandidateIsScorable:
    """The candidate must be judgeable by the incumbent's own harness."""

    def test_bc_stack_honours_the_stack_contract(self):
        weights = SHIP / "policy.npz"
        if not weights.exists():
            pytest.skip("policy.npz not built; run collect.py")
        import bc_stack
        from sim import Simulator

        sim = Simulator(7)
        obs = sim.reset()
        stack = bc_stack.make_stack(sim)
        v, w = stack.step(obs)
        assert 0.0 <= v <= 1.2 and -2.0 <= w <= 2.0
        assert stack.last_estimate is not None


class TestRegressionGate:
    """Stage 2: the gate, and the ordering of its verdicts."""

    def _gate(self):
        from gate import gate
        return gate

    def test_mde_shrinks_with_sample_size(self):
        from gate import minimum_detectable_effect as mde
        small = mde(30, 0.9, 0.4)
        large = mde(300, 0.9, 0.4)
        assert large < small
        # sqrt(n): ten times the episodes is about a third the effect
        assert abs(small / large - np.sqrt(10.0)) < 0.05

    def test_mde_depends_on_discordance_not_volume(self):
        from gate import minimum_detectable_effect as mde
        # A suite everything agrees on carries no information about the
        # difference, however many episodes it contains.
        assert mde(500, 0.9, 0.0) >= 1.0
        assert mde(100, 0.9, 0.5) > mde(100, 0.9, 0.1)

    def test_paired_bootstrap_preserves_pairing(self):
        from gate import paired_bootstrap
        rng = np.random.default_rng(0)
        shared = rng.random(200) < 0.7
        a = shared.copy()
        b = shared.copy()
        # A regression is ONE-directional: turn successes into failures.
        # Flipping entries with ~ turns some failures into successes too,
        # which is a mixed effect and not what a regression looks like.
        b[np.nonzero(a)[0][:25]] = False
        r = paired_bootstrap(a, b, n_boot=4000, seed=1)
        assert r["lo"] <= r["diff"] <= r["hi"]
        assert r["lo"] > 0.0, "a consistent regression should exclude zero"

    def test_block_beats_underpowered(self):
        """An obvious regression must BLOCK even when the MDE is large."""
        gate = self._gate()
        inc = np.ones(20, dtype=bool)
        cand = np.zeros(20, dtype=bool)
        g = gate(inc, cand, tolerance=0.05)
        assert g["verdict"] == "BLOCK", (
            "a 1.000 regression must block; reporting INCONCLUSIVE because "
            "the design's MDE is large gets the check order backwards")

    def test_underpowered_pass_becomes_inconclusive(self):
        """No difference, but too few episodes to have proven it."""
        gate = self._gate()
        rng = np.random.default_rng(2)
        a = rng.random(12) < 0.7
        b = a.copy()
        b[0] = ~b[0]
        g = gate(a, b, tolerance=0.02)
        assert g["verdict"] == "INCONCLUSIVE", (
            "with 12 episodes the gate cannot resolve a 0.02 bar, so a PASS "
            "would be unearned")

    def test_genuine_pass_when_powered(self):
        gate = self._gate()
        rng = np.random.default_rng(3)
        shared = rng.random(4000) < 0.7
        a = shared.copy()
        b = shared.copy()
        b[np.nonzero(a)[0][:20]] = False     # 0.005 regression, inside 0.05
        g = gate(a, b, tolerance=0.05)
        assert g["verdict"] == "PASS"
        assert g["mde"] < 0.05, "with 4000 episodes the design should resolve 0.05"
