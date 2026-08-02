"""A minimal static transform tree (the concept behind ROS 2's TF2).

Frames form a tree: every frame has at most one parent, connected by the
rigid transform T_parent_child. ``lookup(target, source)`` composes along
the unique path between any two frames, inverting edges walked "upstream".

This implementation is static (no timestamps); the time-varying version
with interpolation arrives with TF2 in Module 6.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from robotics_ai.geometry.transforms2d import se2_inverse

FloatArray = npt.NDArray[np.float64]


class TransformTree:
    """Static tree of SE(2) transforms between named frames."""

    def __init__(self) -> None:
        # child -> (parent, T_parent_child)
        self._parent: dict[str, tuple[str, FloatArray]] = {}

    def add(self, parent: str, child: str, T_parent_child: FloatArray) -> None:
        """Register frame ``child`` with pose ``T_parent_child`` in ``parent``."""
        if child in self._parent:
            raise ValueError(f"frame {child!r} already has a parent; frames form a tree")
        # Cycle check BEFORE inserting: if child already sits on parent's path
        # to the root, the new edge would close a loop (and _path_to_root
        # would never terminate afterwards).
        if child in self._path_to_root(parent):
            raise ValueError(f"adding {parent!r}->{child!r} would create a cycle")
        self._parent[child] = (parent, np.asarray(T_parent_child, dtype=np.float64))

    def _path_to_root(self, frame: str) -> list[str]:
        path = [frame]
        while path[-1] in self._parent:
            path.append(self._parent[path[-1]][0])
        return path

    def lookup(self, target: str, source: str) -> FloatArray:
        """Return T_target_source: maps points in ``source`` into ``target``."""
        up_t, up_s = self._path_to_root(target), self._path_to_root(source)
        common = next((f for f in up_s if f in up_t), None)
        if common is None:
            raise KeyError(f"frames {target!r} and {source!r} are not connected")
        # T_common_source: compose parent-edges from source up to the ancestor.
        T_cs = np.eye(3)
        for f in up_s[: up_s.index(common)]:
            T_cs = self._parent[f][1] @ T_cs
        # T_common_target likewise, then invert.
        T_ct = np.eye(3)
        for f in up_t[: up_t.index(common)]:
            T_ct = self._parent[f][1] @ T_ct
        return se2_inverse(T_ct) @ T_cs
