"""Extended Kalman filter: the KF recursion on linearized nonlinear models.

The caller supplies the nonlinear functions and their Jacobians:

    predict(f, F_jac, Q, u):   x <- f(x, u);        P <- F P F^T + Q
    update(z, h, H_jac, R):    y = residual(z, h(x)); standard KF update

``residual_fn`` exists for one reason robotics cares about deeply: angle
components must be wrapped after subtraction (a bearing residual of 2*pi-eps
is actually -eps). Pass a residual that wraps the angular rows.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]


class ExtendedKalmanFilter:
    def __init__(self, x0: FloatArray, P0: FloatArray) -> None:
        self.x = np.atleast_1d(np.asarray(x0, dtype=np.float64))
        self.P = np.atleast_2d(np.asarray(P0, dtype=np.float64))

    def predict(
        self,
        f: Callable[[FloatArray], FloatArray],
        F_jac: Callable[[FloatArray], FloatArray],
        Q: FloatArray,
    ) -> None:
        F = np.atleast_2d(F_jac(self.x))
        self.x = np.atleast_1d(f(self.x))
        self.P = F @ self.P @ F.T + np.atleast_2d(Q)

    def update(
        self,
        z: FloatArray,
        h: Callable[[FloatArray], FloatArray],
        H_jac: Callable[[FloatArray], FloatArray],
        R: FloatArray,
        residual_fn: Callable[[FloatArray, FloatArray], FloatArray] | None = None,
    ) -> None:
        z = np.atleast_1d(np.asarray(z, dtype=np.float64))
        pred = np.atleast_1d(h(self.x))
        y = (z - pred) if residual_fn is None else residual_fn(z, pred)
        H = np.atleast_2d(H_jac(self.x))
        R = np.atleast_2d(R)
        S = H @ self.P @ H.T + R
        K = self.P @ H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        ikh = np.eye(len(self.x)) - K @ H
        self.P = ikh @ self.P @ ikh.T + K @ R @ K.T
