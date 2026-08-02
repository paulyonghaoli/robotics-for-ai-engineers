"""Linear Kalman filter.

Model:
    x_k = F x_{k-1} + B u_k + w,   w ~ N(0, Q)     (process)
    z_k = H x_k + v,               v ~ N(0, R)     (observation)

State ``x`` is a column-free 1D array of shape (n,); covariance ``P`` is
(n, n). ``predict``/``update`` mutate the filter and also return (x, P)
for convenience.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]


class KalmanFilter:
    def __init__(
        self,
        F: FloatArray,
        H: FloatArray,
        Q: FloatArray,
        R: FloatArray,
        x0: FloatArray,
        P0: FloatArray,
        B: FloatArray | None = None,
    ) -> None:
        self.F = np.atleast_2d(np.asarray(F, dtype=np.float64))
        self.H = np.atleast_2d(np.asarray(H, dtype=np.float64))
        self.Q = np.atleast_2d(np.asarray(Q, dtype=np.float64))
        self.R = np.atleast_2d(np.asarray(R, dtype=np.float64))
        self.B = None if B is None else np.atleast_2d(np.asarray(B, dtype=np.float64))
        self.x = np.atleast_1d(np.asarray(x0, dtype=np.float64))
        self.P = np.atleast_2d(np.asarray(P0, dtype=np.float64))

    def predict(self, u: FloatArray | None = None) -> tuple[FloatArray, FloatArray]:
        self.x = self.F @ self.x
        if u is not None:
            if self.B is None:
                raise ValueError("control input given but no B matrix configured")
            self.x = self.x + self.B @ np.atleast_1d(u)
        self.P = self.F @ self.P @ self.F.T + self.Q
        return self.x, self.P

    def update(self, z: FloatArray) -> tuple[FloatArray, FloatArray]:
        z = np.atleast_1d(np.asarray(z, dtype=np.float64))
        y = z - self.H @ self.x                       # innovation
        S = self.H @ self.P @ self.H.T + self.R       # innovation covariance
        K = self.P @ self.H.T @ np.linalg.inv(S)      # Kalman gain
        self.x = self.x + K @ y
        # Joseph form: numerically safer, keeps P symmetric positive-definite.
        ikh = np.eye(self.P.shape[0]) - K @ self.H
        self.P = ikh @ self.P @ ikh.T + K @ self.R @ K.T
        return self.x, self.P

    def nis(self, z: FloatArray) -> float:
        """Normalized innovation squared for consistency monitoring."""
        z = np.atleast_1d(np.asarray(z, dtype=np.float64))
        y = z - self.H @ self.x
        S = self.H @ self.P @ self.H.T + self.R
        return float(y @ np.linalg.solve(S, y))
