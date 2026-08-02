"""PID controller with output clamping and integral anti-windup.

Conventions:
- ``update(error, dt)`` takes the *error* (setpoint - measurement), not the
  measurement: callers own error computation (and any angle wrapping —
  heading errors must be wrapped BEFORE they reach the controller).
- Derivative is computed on the error signal; the first call after
  ``reset()`` uses zero derivative (no spike from an undefined history).
"""

from __future__ import annotations


class PID:
    """Discrete PID: u = kp*e + ki*∫e dt + kd*de/dt, with anti-windup."""

    def __init__(
        self,
        kp: float,
        ki: float = 0.0,
        kd: float = 0.0,
        output_limits: tuple[float, float] | None = None,
        integral_limit: float | None = None,
    ) -> None:
        if output_limits is not None and output_limits[0] >= output_limits[1]:
            raise ValueError("output_limits must be (low, high) with low < high")
        if integral_limit is not None and integral_limit <= 0:
            raise ValueError("integral_limit must be positive")
        self.kp, self.ki, self.kd = kp, ki, kd
        self.output_limits = output_limits
        self.integral_limit = integral_limit
        self.reset()

    def reset(self) -> None:
        self._integral = 0.0
        self._prev_error: float | None = None

    def update(self, error: float, dt: float) -> float:
        if dt <= 0:
            raise ValueError("dt must be positive")

        self._integral += error * dt
        if self.integral_limit is not None:
            lim = self.integral_limit
            self._integral = max(-lim, min(lim, self._integral))

        derivative = 0.0 if self._prev_error is None else (error - self._prev_error) / dt
        self._prev_error = error

        u = self.kp * error + self.ki * self._integral + self.kd * derivative
        if self.output_limits is not None:
            lo, hi = self.output_limits
            u = max(lo, min(hi, u))
        return u
