"""Control mini-project — implement the five pieces below.

    python -m grader

Conventions (same as the curriculum):
- Angles in radians, wrapped to (-pi, pi].
- A pose is (x, y, theta); the robot's body x-axis points along theta.
- Differential drive: you command (v, w) — forward speed and yaw rate.

NumPy only. Do not import robotics_ai.
"""

from __future__ import annotations

import numpy as np
from plant import U_MAX, arm_jacobian, forward_kinematics  # noqa: F401


def wrap(theta):
    """Wrap angle(s) to (-pi, pi]. Given to you."""
    wrapped = np.mod(-np.asarray(theta, dtype=float) + np.pi, 2.0 * np.pi)
    result = -(wrapped - np.pi)
    return float(result) if np.ndim(theta) == 0 else result


class PID:
    """A PID controller with two properties that separate a working
    implementation from a textbook one.

    1. ANTI-WINDUP. `output_limits` is not advice — it is the actuator's
       physical range. When your unclamped output is outside it, the extra
       integral you accumulate buys nothing, because the actuator is
       already doing all it can. It just has to be paid back later, as
       overshoot. Stop integrating when saturated (or clamp the integral).

    2. DERIVATIVE ON MEASUREMENT. The derivative of the *error* contains
       the derivative of the setpoint, and a setpoint step is instant, so
       d(error)/dt is a spike — an impulse into your actuator every time an
       operator types a new target. Differentiate the measurement instead
       and negate it. Identical for a constant setpoint, kick-free for a
       changing one.
    """

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
        """Return the (clamped) control output for one tick.

        TODO:
          - error = setpoint - measurement
          - proportional term
          - derivative term from the MEASUREMENT, not the error, and
            negated. On the very first call there is no previous
            measurement, so the derivative term is 0.
          - tentatively integrate, form the unclamped output, and clamp it
          - if clamping changed the output, undo that integration step
            (this is the anti-windup condition)
          - remember the measurement for next time
        """
        raise NotImplementedError("student: PID.step")


def diff_drive_step(pose: np.ndarray, v: float, w: float, dt: float) -> np.ndarray:
    """Integrate a differential-drive pose forward by one tick.

    Use the EXACT arc, not the Euler approximation. For w != 0 the robot
    travels an arc of radius r = v / w, and straight-line integration
    accumulates real error at the yaw rates a robot actually turns at.

    Handle w ~= 0 separately — the arc formula divides by w.

    Returns a new (3,) pose; theta wrapped.

    TODO.
    """
    raise NotImplementedError("student: diff_drive_step")


def ik_step(q: np.ndarray, target: np.ndarray, step: float = 0.5,
            damping: float = 0.05) -> np.ndarray:
    """One damped-least-squares step of Jacobian inverse kinematics.

    Return the joint update dq that moves the end effector toward `target`.

    The plain pseudo-inverse blows up near singularities — when the arm is
    straight, the Jacobian loses rank and J^+ demands enormous joint
    velocities for a small Cartesian motion. Damped least squares trades a
    little accuracy for not doing that:

        dq = J^T (J J^T + lambda^2 I)^-1  e        with e = target - fk(q)

    Scale by `step` before returning. Use `forward_kinematics` and
    `arm_jacobian`, both imported for you.

    TODO.
    """
    raise NotImplementedError("student: ik_step")


def pure_pursuit(pose: np.ndarray, path: np.ndarray, lookahead: float,
                 v: float) -> float:
    """Return the yaw rate w that steers toward a lookahead point.

    Find the point on `path` roughly `lookahead` metres ahead of the robot,
    express it in the robot's frame, and apply the pure-pursuit curvature

        kappa = 2 * y_body / L^2        w = v * kappa

    where y_body is the lookahead point's lateral offset in the body frame
    and L is the distance to it. Positive y_body must steer left.

    Near the end of the path there may be no point a full `lookahead`
    away — aim at the last point rather than returning 0, or the robot
    will stop steering just when it needs to finish.

    TODO.
    """
    raise NotImplementedError("student: pure_pursuit")


def track(path: np.ndarray, pose0: np.ndarray, steps: int, dt: float,
          lookahead: float = 0.9, v: float = 1.0, goal_tol: float = 0.3
          ) -> np.ndarray:
    """Closed-loop: follow `path` and return the executed (N, 3) trajectory.

    Put your own pure_pursuit and diff_drive_step together. Include the
    starting pose as the first row. Clip w to +-W_MAX (from plant) — a
    controller that commands more yaw rate than the robot has is not
    tracking, it is dreaming.

    STOP EARLY, returning what you have, once you are within `goal_tol` of
    the final waypoint. `steps` is a budget, not a target. A tracker with no
    terminal condition drives to the end of its path and then keeps going,
    orbiting the last waypoint forever — which looks fine on a plot of the
    first half and is why the grader runs a budget far longer than the path.

    Graded on cross-track RMSE, so the loop has to converge onto the path
    and stay there, not merely aim at it.

    TODO.
    """
    raise NotImplementedError("student: track")
