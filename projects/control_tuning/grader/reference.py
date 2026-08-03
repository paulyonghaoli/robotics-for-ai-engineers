"""Reference solution. `python -m grader --reference` scores this, which is
how CI proves the grader is passable and its thresholds are honest."""

from __future__ import annotations

import numpy as np
from plant import U_MAX, W_MAX, arm_jacobian, forward_kinematics


def wrap(theta):
    wrapped = np.mod(-np.asarray(theta, dtype=float) + np.pi, 2.0 * np.pi)
    result = -(wrapped - np.pi)
    return float(result) if np.ndim(theta) == 0 else result


class PID:
    def __init__(self, kp: float, ki: float, kd: float,
                 output_limits: tuple[float, float] = (-U_MAX, U_MAX)) -> None:
        self.kp, self.ki, self.kd = kp, ki, kd
        self.lo, self.hi = output_limits
        self.integral = 0.0
        self.prev_measurement: float | None = None

    def reset(self) -> None:
        self.integral = 0.0
        self.prev_measurement = None

    def step(self, measurement: float, setpoint: float, dt: float) -> float:
        error = setpoint - measurement

        # Derivative of the MEASUREMENT, negated: identical to d(error)/dt
        # for a constant setpoint, but immune to setpoint steps.
        if self.prev_measurement is None:
            derivative = 0.0
        else:
            derivative = -(measurement - self.prev_measurement) / dt
        self.prev_measurement = measurement

        candidate_integral = self.integral + error * dt
        unclamped = (self.kp * error
                     + self.ki * candidate_integral
                     + self.kd * derivative)
        output = float(np.clip(unclamped, self.lo, self.hi))

        # Anti-windup: only keep the integration if it wasn't thrown away by
        # the clamp. Integral accumulated while saturated buys no authority
        # now and must be unwound later as overshoot.
        if output == unclamped:
            self.integral = candidate_integral
        return output


def diff_drive_step(pose: np.ndarray, v: float, w: float, dt: float) -> np.ndarray:
    x, y, th = float(pose[0]), float(pose[1]), float(pose[2])
    if abs(w) < 1e-9:
        return np.array([x + v * np.cos(th) * dt, y + v * np.sin(th) * dt,
                         float(wrap(th))])
    r = v / w
    return np.array([
        x + r * (np.sin(th + w * dt) - np.sin(th)),
        y - r * (np.cos(th + w * dt) - np.cos(th)),
        float(wrap(th + w * dt)),
    ])


def ik_step(q: np.ndarray, target: np.ndarray, step: float = 0.5,
            damping: float = 0.05) -> np.ndarray:
    e = np.asarray(target, dtype=float) - forward_kinematics(q)
    J = arm_jacobian(q)
    A = J @ J.T + (damping ** 2) * np.eye(2)
    return step * (J.T @ np.linalg.solve(A, e))


def pure_pursuit(pose: np.ndarray, path: np.ndarray, lookahead: float,
                 v: float) -> float:
    path = np.asarray(path, dtype=float)
    d = np.linalg.norm(path - pose[:2], axis=1)
    nearest = int(np.argmin(d))
    ahead = np.nonzero(d[nearest:] >= lookahead)[0]
    idx = nearest + int(ahead[0]) if len(ahead) else len(path) - 1
    target = path[idx]

    dx, dy = target - pose[:2]
    c, s = np.cos(-pose[2]), np.sin(-pose[2])
    y_body = s * dx + c * dy
    L = float(np.hypot(dx, dy))
    if L < 1e-6:
        return 0.0
    return float(v * (2.0 * y_body / (L * L)))


def track(path: np.ndarray, pose0: np.ndarray, steps: int, dt: float,
          lookahead: float = 0.9, v: float = 1.0, goal_tol: float = 0.3
          ) -> np.ndarray:
    pose = np.asarray(pose0, dtype=float).copy()
    out = [pose.copy()]
    end = np.asarray(path)[-1]
    for _ in range(steps):
        if np.linalg.norm(pose[:2] - end) < goal_tol:
            break
        w = float(np.clip(pure_pursuit(pose, path, lookahead, v), -W_MAX, W_MAX))
        pose = diff_drive_step(pose, v, w, dt)
        out.append(pose.copy())
    return np.array(out)
