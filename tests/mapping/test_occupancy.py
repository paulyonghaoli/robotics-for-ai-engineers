import numpy as np
import pytest

from robotics_ai.mapping import OccupancyGridMap, bresenham


class TestBresenham:
    def test_horizontal(self):
        assert bresenham(0, 0, 0, 3) == [(0, 0), (0, 1), (0, 2), (0, 3)]

    def test_diagonal(self):
        assert bresenham(0, 0, 3, 3) == [(0, 0), (1, 1), (2, 2), (3, 3)]

    def test_endpoints_included_any_direction(self):
        cells = bresenham(5, 5, 2, 1)
        assert cells[0] == (5, 5) and cells[-1] == (2, 1)

    def test_single_cell(self):
        assert bresenham(2, 2, 2, 2) == [(2, 2)]


class TestOccupancyGrid:
    def make(self):
        return OccupancyGridMap((50, 50), resolution=0.2)

    def test_hit_raises_endpoint_lowers_path(self):
        m = self.make()
        m.update_ray(np.array([1.0, 1.0]), np.array([5.0, 1.0]), hit=True)
        end = m.world_to_cell(np.array([5.0, 1.0]))
        mid = m.world_to_cell(np.array([3.0, 1.0]))
        assert m.log_odds[end] > 0, "hit endpoint must become more occupied"
        assert m.log_odds[mid] < 0, "cells along the beam must become more free"

    def test_miss_lowers_everything(self):
        m = self.make()
        m.update_ray(np.array([1.0, 1.0]), np.array([5.0, 1.0]), hit=False)
        assert (m.log_odds <= 0).all()

    def test_repeated_hits_converge_and_clamp(self):
        m = self.make()
        for _ in range(200):
            m.update_ray(np.array([1.0, 1.0]), np.array([5.0, 1.0]), hit=True)
        end = m.world_to_cell(np.array([5.0, 1.0]))
        assert m.log_odds[end] == pytest.approx(m.l_clamp)
        assert m.probability()[end] > 0.99

    def test_conflicting_evidence_recovers(self):
        # A cell wrongly seen as occupied must be reclaimable — that's what
        # the clamp buys.
        m = self.make()
        for _ in range(50):
            m.update_ray(np.array([1.0, 1.0]), np.array([5.0, 1.0]), hit=True)
        for _ in range(400):
            m.update_ray(np.array([1.0, 1.0]), np.array([8.0, 1.0]), hit=True)
        cell = m.world_to_cell(np.array([5.0, 1.0]))
        assert m.log_odds[cell] < 0, "sustained free evidence must reclaim the cell"

    def test_out_of_bounds_ray_safe(self):
        m = self.make()
        m.update_ray(np.array([1.0, 1.0]), np.array([50.0, 1.0]), hit=True)  # exits grid
        assert np.isfinite(m.log_odds).all()

    def test_probability_maps_log_odds(self):
        m = self.make()
        assert m.probability()[0, 0] == pytest.approx(0.5)
