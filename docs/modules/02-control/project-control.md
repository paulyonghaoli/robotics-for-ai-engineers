# Mini-project: Control (autograded, 100 pts)

**Status:** Code verified · **Prereqs:** lessons 2.1–2.4 · **Time:** ~3–4 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

You implement the control layer of a mobile robot: a PID controller that survives contact with a real actuator, exact differential-drive integration, damped inverse kinematics, and a closed pursuit loop. A grader scores them against **randomized** scenarios — the seed changes every run, so fitting one case scores once and fails the next.

## Setup

```bash
cd robotics-for-ai-engineers/projects/control_tuning
python -m grader
```

Implement the stubs in `student.py`. `plant.py` is given: a saturating speed plant, a two-link arm with analytic kinematics, and a reference path.

## The marks

| Check | Points |
|---|---:|
| PID basics | 10 |
| PID output limits | 5 |
| PID derivative kick | 15 |
| PID anti-windup | 20 |
| Differential-drive arc | 15 |
| Damped Jacobian IK | 15 |
| Pure pursuit | 10 |
| Closed-loop tracking | 10 |

## Why half the marks are on PID

Because the two properties under test are precisely the ones a textbook implementation leaves out, and both fail in disguise.

**Anti-windup** ([2.2](02-pid.md)). The plant saturates at 3.75 m/s and the test asks for 11.25. An unclamped integrator spends ten seconds accumulating authority the actuator does not have; when the setpoint drops to something reachable, that debt is repaid as a controller pinned in the wrong direction while it unwinds. On a plot it looks like a badly tuned gain, and tuning the gain does not fix it.

**Derivative kick** ([2.2](02-pid.md)). d(error)/dt contains d(setpoint)/dt, and a setpoint step is instantaneous — so every operator input fires an impulse into the actuator. The check holds the *measurement* constant and steps the setpoint: a correct implementation outputs nothing at all, because nothing has moved. It looks like a noisy sensor, and filtering the sensor does not fix it.

## The one that catches most people

`track` is run with a 45 m driving budget on a 16 m path. A tracker with no terminal condition reaches the end and then orbits the final waypoint indefinitely — which looks entirely healthy if you plot only the first half, and which is why the budget is nearly three times the path length. Stop when you arrive.

The IK check includes a near-singular pose: the arm almost straight, reaching past its own span. A raw pseudo-inverse demands enormous joint velocities there. Damped least squares trades a little accuracy for not doing that, and [2.3](03-jacobians.md) explains why the trade is nearly always worth it.

## Portfolio extension

Sweep the PID gains and plot the step response surface — rise time against overshoot — with and without anti-windup. The pair of surfaces is a more convincing artifact than either alone, because it shows a whole region of gain space that only becomes usable once the integrator is clamped.
