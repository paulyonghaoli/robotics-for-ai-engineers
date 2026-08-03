# 2.7 Lab: control pathologies

**Status:** Code verified · **Prereqs:** lessons 2.1–2.4 · **Time:** ~2 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this lab exists

Every controller in this lab is *correct*. Each one implements the equation from the lesson faithfully, passes a step-response test on the bench, and fails in the field.

That is the actual shape of control work. A PID that diverges obviously gets fixed in an afternoon. The ones that cost weeks are the ones that work — until an actuator saturates, until an operator types a new number, until someone raises the speed limit. Each bug below presents as something else entirely, and the thing it resembles is not the thing that's wrong.

## B. The diagnostic table

| Symptom | Looks like | Actually is | Lesson |
|---|---|---|---|
| Overshoots badly after a large setpoint change | badly tuned gains | **integral windup** — authority accumulated while saturated | [2.2](02-pid.md) |
| Actuator spikes when the operator types a target | noisy encoder | **derivative kick** — differentiating the setpoint | [2.2](02-pid.md) |
| Stable in testing, weaves when deployed faster | a speed-dependent plant | **fixed lookahead** against a fixed *delay* | [2.4](04-trajectory-tracking.md) |
| Position drifts on long curved runs | odometry noise | **Euler integration** instead of the exact arc | [2.1](01-kinematics.md) |
| Joint velocities explode near full extension | numerical instability | **singular Jacobian**, undamped inverse | [2.3](03-jacobians.md) |
| Robot turns the long way round | planner error | **unwrapped heading error** | [1.1](../01-geometry/01-coordinate-frames.md) |

## C. The gauntlet

Three controllers. Each has one wrong line, a probe that exposes it, and a test that will not accept a fix that breaks the ordinary case.

<code-exercise src="ctl-l7-bug-windup"></code-exercise>

The cart tops out at 3.75 m/s and is asked for 12. For two hundred ticks the integrator accumulates error it has no authority to act on — the actuator is already at its limit and doing nothing more. When the setpoint drops to something reachable, that stored debt keeps the command pinned in the wrong direction until it unwinds. The controller isn't mis-tuned; it's paying off a loan.

<code-exercise src="ctl-l7-bug-kick"></code-exercise>

The measurement in the probe is a perfectly smooth ramp. There is no discontinuity anywhere in the physical signal, and yet the command jumps 8.4 units in a single tick. Whatever produced that spike was differentiating something that *did* jump — and the only thing that jumped was the operator's intent.

<code-exercise src="ctl-l7-bug-lookahead"></code-exercise>

The third is the one worth sitting with, because nothing in the controller is wrong at all. A 0.5 m lookahead is stable at 0.5 and 1.0 m/s, weaves 0.82 m at 2.0, and diverges to 2.9 m at 3.0. The code never changed. What changed is the ratio between a lookahead measured in *metres* and a control delay measured in *seconds*: at 0.5 m/s the robot travels 0.10 m while a command is in flight, against a 0.5 m preview; at 2.0 m/s it travels 0.40 m, and is steering toward where it has already been.

## D. Diagnosis drills

<quiz-bank src="ctl-l7-drills"></quiz-bank>

## E. Debrief: the method

**Probe the boundary, not the middle.** All three controllers behave perfectly in the regime they were tested in. Windup needs saturation, kick needs a setpoint change, the lookahead bug needs speed. A test suite that exercises only the nominal operating point will pass all three, which is why bench-tested controllers still fail on delivery.

**When the same code behaves differently, look outside the code.** Bug 3 has no wrong line. The instability lives in the relationship between the controller, the vehicle speed, and the actuation delay — and no amount of reading the function will show it to you. Change one thing at a time and watch the boundary move.

**Ask what the term is differentiating, and what the integral is buying.** Both PID bugs come from the same failure of attention: treating `error` as a single quantity rather than as `setpoint - measurement`, two signals with completely different dynamics. The derivative should see only one of them. The integral should stop when it can no longer buy anything.

## F. Graded work & portfolio extension

**Graded:** the three fixes are Module 2's diagnostic assessment, and they compose directly into the [control mini-project](project-control.md), where the same anti-windup and derivative-on-measurement requirements are worth 35 of 100 points.

**Portfolio:** take the third bug further. Sweep lookahead against speed and actuation delay, and plot the stability boundary — the surface separating "converges" from "limit cycle." Then overlay the `max(0.4, 0.9v)` rule and show where it sits relative to that boundary. A tuning rule presented alongside the region it is valid in is a substantially stronger artifact than the rule alone, and it is the kind of figure that makes a reviewer trust the rest of your work.
