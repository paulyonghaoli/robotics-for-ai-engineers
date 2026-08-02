import pytest

from robotics_ai.control import PID


def simulate_first_order(pid, setpoint, tau=1.0, dt=0.01, steps=1000, y0=0.0):
    """Plant: dy/dt = (u - y) / tau. Returns trajectory of y."""
    y, ys = y0, []
    for _ in range(steps):
        u = pid.update(setpoint - y, dt)
        y += (u - y) / tau * dt
        ys.append(y)
    return ys


class TestBehavior:
    def test_p_only_has_steady_state_error(self):
        ys = simulate_first_order(PID(kp=2.0), setpoint=1.0)
        final = ys[-1]
        assert 0.5 < final < 0.9  # converges to kp/(kp+1) = 2/3, never 1.0

    def test_pi_removes_steady_state_error(self):
        ys = simulate_first_order(PID(kp=2.0, ki=2.0), setpoint=1.0)
        assert ys[-1] == pytest.approx(1.0, abs=1e-3)

    def test_derivative_damps_overshoot(self):
        # Double integrator (mass under force): P-only oscillates with ~100%
        # overshoot; adding D provides the damping.
        def simulate_double_integrator(pid, steps=4000, dt=0.01):
            x, v, xs = 0.0, 0.0, []
            for _ in range(steps):
                u = pid.update(1.0 - x, dt)
                v += u * dt
                x += v * dt
                xs.append(x)
            return xs

        over_p = max(simulate_double_integrator(PID(kp=4.0)))
        over_pd = max(simulate_double_integrator(PID(kp=4.0, kd=3.0)))
        assert over_p > 1.5  # near-undamped oscillation
        assert over_pd < 1.15  # well damped

    def test_output_limits_respected(self):
        pid = PID(kp=100.0, output_limits=(-1.0, 1.0))
        assert pid.update(10.0, 0.01) == 1.0
        assert pid.update(-10.0, 0.01) == -1.0

    def test_anti_windup_limits_integral(self):
        # Saturated actuator + unreachable setpoint: without the clamp the
        # integral grows unboundedly; with it, recovery is fast.
        pid = PID(kp=1.0, ki=10.0, output_limits=(-1.0, 1.0), integral_limit=0.5)
        for _ in range(1000):
            pid.update(5.0, 0.01)  # huge persistent error
        assert pid._integral == pytest.approx(0.5)

    def test_first_call_has_no_derivative_kick(self):
        pid = PID(kp=0.0, ki=0.0, kd=1.0)
        assert pid.update(5.0, 0.01) == 0.0  # no history -> no derivative
        assert pid.update(5.0, 0.01) == 0.0  # constant error -> zero derivative

    def test_reset_clears_state(self):
        pid = PID(kp=1.0, ki=1.0, kd=1.0)
        pid.update(1.0, 0.1)
        pid.reset()
        assert pid._integral == 0.0
        assert pid._prev_error is None


class TestValidation:
    def test_bad_limits_raise(self):
        with pytest.raises(ValueError):
            PID(1.0, output_limits=(1.0, -1.0))

    def test_bad_dt_raises(self):
        with pytest.raises(ValueError):
            PID(1.0).update(0.0, 0.0)
