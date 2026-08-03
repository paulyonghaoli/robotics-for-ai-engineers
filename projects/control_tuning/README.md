# Module 2 mini-project — Control

Implement the control layer of a mobile robot, graded on behaviour rather than
on matching a reference implementation line for line.

```bash
cd projects/control_tuning
python -m grader
```

100 points across eight checks. The seed is **random each run** unless you pass
`--seed N`, so nothing here can be satisfied by fitting one particular case.

## What you implement

All in [`student.py`](student.py):

| | Points | |
|---|---:|---|
| `PID.step` | 50 | Anti-windup and derivative-on-measurement, not just kp·e + ki·∫e + kd·ė |
| `diff_drive_step` | 15 | Exact arc integration, not single-step Euler |
| `ik_step` | 15 | Damped least squares for a two-link arm |
| `pure_pursuit` | 10 | Lookahead curvature control |
| `track` | 10 | Close the loop and hold the path |

Half the marks are on PID because the two properties being tested are exactly
the ones textbook implementations omit, and both produce failures that look
like something else:

- **Windup** looks like a badly tuned gain. The controller chases a setpoint
  the actuator cannot reach, the integrator keeps accumulating authority it
  does not have, and the debt is repaid as overshoot long after the operator
  changed their mind. The plant here saturates at 3.75 m/s and the test asks
  for 11.25, so an unclamped integrator has ten seconds to dig its hole.
- **Derivative kick** looks like a noisy sensor. Differentiating the *error*
  differentiates the setpoint too, so every operator input fires an impulse
  into the actuator. Differentiate the measurement and negate it.

## What you're given

[`plant.py`](plant.py) — a saturating first-order speed plant, a two-link arm
with analytic forward kinematics and Jacobian, and a reference path. You don't
modify it.

## Notes

`track` runs against a 45 m driving budget on a 16 m path. That is deliberate:
a tracker with no terminal condition reaches the end and then orbits the last
waypoint forever, which looks perfectly healthy if you only plot the first
half. Stop when you arrive.

The IK check includes a near-singular configuration — the arm almost straight,
reaching for a point beyond its span. A raw pseudo-inverse demands enormous
joint velocities there. Damping costs a little accuracy and buys not exploding.
