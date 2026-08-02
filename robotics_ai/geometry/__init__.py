"""Rigid-body geometry: SO(2)/SE(2) transforms and 3D rotations."""

from robotics_ai.geometry.rotations3d import (
    matrix_to_quat,
    quat_conjugate,
    quat_from_axis_angle,
    quat_multiply,
    quat_normalize,
    quat_rotate,
    quat_to_matrix,
    slerp,
)
from robotics_ai.geometry.transform_tree import TransformTree
from robotics_ai.geometry.transforms2d import (
    relative_pose,
    rot2,
    se2,
    se2_compose,
    se2_inverse,
    se2_to_pose,
    transform_points,
    wrap_angle,
)

__all__ = [
    "TransformTree",
    "wrap_angle",
    "rot2",
    "se2",
    "se2_inverse",
    "se2_compose",
    "se2_to_pose",
    "relative_pose",
    "transform_points",
    "quat_normalize",
    "quat_from_axis_angle",
    "quat_multiply",
    "quat_conjugate",
    "quat_rotate",
    "quat_to_matrix",
    "matrix_to_quat",
    "slerp",
]
