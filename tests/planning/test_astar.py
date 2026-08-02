import numpy as np
import pytest

from robotics_ai.planning import astar_grid, inflate_grid, path_length


def empty(n=10):
    return np.zeros((n, n), dtype=bool)


class TestAstar:
    def test_straight_line(self):
        path = astar_grid(empty(), (0, 0), (0, 9))
        assert path is not None and path[0] == (0, 0) and path[-1] == (0, 9)
        assert path_length(path) == pytest.approx(9.0)

    def test_diagonal_shortcut(self):
        path = astar_grid(empty(), (0, 0), (9, 9))
        assert path_length(path) == pytest.approx(9 * np.sqrt(2))

    def test_routes_around_wall(self):
        g = empty()
        g[0:9, 5] = True  # wall with a gap at the bottom
        path = astar_grid(g, (4, 0), (4, 9))
        assert path is not None
        assert all(not g[c] for c in path), "path must avoid occupied cells"
        assert path_length(path) > 9.0  # detour is longer than the crow flies

    def test_no_path_returns_none(self):
        g = empty()
        g[:, 5] = True  # full wall
        assert astar_grid(g, (4, 0), (4, 9)) is None

    def test_occupied_endpoint_returns_none(self):
        g = empty()
        g[0, 0] = True
        assert astar_grid(g, (0, 0), (5, 5)) is None

    def test_out_of_bounds_raises(self):
        with pytest.raises(ValueError):
            astar_grid(empty(), (0, 0), (20, 20))

    def test_diagonal_wall_is_watertight(self):
        # With no corner cutting, a diagonal line of blocked cells seals the
        # start completely — None is the correct answer.
        g = empty(3)
        g[0, 1] = g[1, 0] = True
        assert astar_grid(g, (0, 0), (2, 2)) is None

    def test_no_corner_cutting_takes_detour(self):
        # A short diagonal wall: the squeeze between (1,2) and (2,1) is
        # forbidden, but a legal detour around the wall's end exists.
        g = empty(4)
        g[1, 2] = g[2, 1] = True
        path = astar_grid(g, (0, 0), (3, 3))
        assert path is not None
        for a, b in zip(path, path[1:], strict=False):
            dy, dx = b[0] - a[0], b[1] - a[1]
            if dy and dx:
                assert not (g[a[0] + dy, a[1]] or g[a[0], a[1] + dx]), (
                    "diagonal move squeezed between blocked orthogonals"
                )
        assert path_length(path) > 3 * np.sqrt(2) + 1e-9  # longer than the illegal shortcut

    def test_optimality_vs_bruteforce(self):
        # Small random grids: A* path length must match Dijkstra (no heuristic).
        rng = np.random.default_rng(0)
        for _ in range(10):
            g = rng.random((8, 8)) < 0.25
            g[0, 0] = g[7, 7] = False
            a = astar_grid(g, (0, 0), (7, 7))
            d = astar_grid(np.where(g, True, False), (0, 0), (7, 7))
            if a is None:
                assert d is None
            else:
                assert path_length(a) == pytest.approx(path_length(d))


class TestInflate:
    def test_single_cell_grows(self):
        g = empty()
        g[5, 5] = True
        out = inflate_grid(g, 1)
        assert out[4:7, 4:7].all()
        assert out.sum() == 9

    def test_blocks_narrow_gap(self):
        g = empty()
        g[0:4, 5] = True
        g[6:10, 5] = True  # 2-cell gap at rows 4-5
        assert astar_grid(g, (5, 0), (5, 9)) is not None
        assert astar_grid(inflate_grid(g, 2), (5, 0), (5, 9)) is None

    def test_zero_radius_is_copy(self):
        g = empty()
        g[3, 3] = True
        out = inflate_grid(g, 0)
        assert (out == g).all() and out is not g
