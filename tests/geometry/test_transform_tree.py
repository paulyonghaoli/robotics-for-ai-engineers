import numpy as np
import pytest

from robotics_ai.geometry import se2, se2_to_pose
from robotics_ai.geometry.transform_tree import TransformTree


@pytest.fixture
def tree():
    t = TransformTree()
    t.add("map", "odom", se2(5.0, 0.0, 0.0))
    t.add("odom", "base", se2(1.0, 2.0, np.pi / 2))
    t.add("base", "lidar", se2(0.5, 0.0, 0.0))
    t.add("base", "camera", se2(0.2, 0.1, 0.0))
    return t


class TestLookup:
    def test_chain_down(self, tree):
        x, y, theta = se2_to_pose(tree.lookup("map", "lidar"))
        assert (x, y) == pytest.approx((6.0, 2.5))
        assert theta == pytest.approx(np.pi / 2)

    def test_inverse_direction(self, tree):
        T_ab = tree.lookup("map", "base")
        T_ba = tree.lookup("base", "map")
        np.testing.assert_allclose(T_ab @ T_ba, np.eye(3), atol=1e-12)

    def test_sibling_via_common_ancestor(self, tree):
        # lidar and camera are siblings under base.
        x, y, theta = se2_to_pose(tree.lookup("lidar", "camera"))
        assert (x, y) == pytest.approx((-0.3, 0.1))
        assert theta == pytest.approx(0.0)

    def test_identity(self, tree):
        np.testing.assert_allclose(tree.lookup("base", "base"), np.eye(3), atol=1e-12)


class TestStructure:
    def test_reparenting_rejected(self, tree):
        with pytest.raises(ValueError, match="already has a parent"):
            tree.add("map", "base", se2(0, 0, 0))

    def test_cycle_rejected(self, tree):
        with pytest.raises(ValueError, match="cycle"):
            tree.add("lidar", "map", se2(0, 0, 0))

    def test_disconnected_raises(self, tree):
        tree.add("mars", "rover", se2(0, 0, 0))
        with pytest.raises(KeyError, match="not connected"):
            tree.lookup("map", "rover")
