# 2.7 Lab: control pathologies

**Status:** Code verified · **Prereqs:** lessons 2.1–2.4 · **Time:** ~2 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this lab exists

Every controller in this lab is *correct*. Each one implements the equation
from its lesson faithfully, passes a step-response test on the bench, and then
fails in the field.

That is the actual shape of control work, and it is worth being explicit about
why. A PID that diverges obviously gets fixed in an afternoon, because the
symptom points straight at the cause and anyone can see that the gains are
wrong. The bugs that cost weeks are the ones in controllers that work — until
an actuator saturates, until an operator types a new number, until somebody
raises the speed limit on a robot that has been reliable for a year. Each bug
below presents as something else entirely, and the thing it resembles is
never the thing that is wrong.

!!! tip "Probe first, read second"

    Each exercise gives you instrumentation before it gives you code. Read the
    probe, form a hypothesis about which regime the controller left, and only
    then open the implementation. Two of these three bugs are invisible in the
    source and visible immediately in the numbers.

## B. The diagnostic table

| Symptom | Looks like | Actually is | Lesson |
|---|---|---|---|
| Overshoots badly after a large setpoint change | badly tuned gains | **integral windup** — authority accumulated while saturated | [2.2](02-pid.md) |
| Actuator spikes when the operator types a target | a noisy encoder | **derivative kick** — differentiating the setpoint | [2.2](02-pid.md) |
| Stable in testing, weaves when deployed faster | a speed-dependent plant | **fixed lookahead** against a fixed *delay* | [2.4](04-trajectory-tracking.md) |
| Position drifts on long curved runs | odometry noise | **Euler integration** instead of the exact arc | [1.4](../01-geometry/04-twists.md) |
| Joint velocities explode near full extension | numerical instability | **singular Jacobian**, inverted without damping | [2.3](03-jacobians.md) |
| Robot turns the long way round | a planner error | **unwrapped heading error** | [1.1](../01-geometry/01-coordinate-frames.md) |

## C. The gauntlet

Three controllers, each with one wrong line, a probe that exposes it, and a
test that will not accept a fix which breaks the ordinary case.

<code-exercise src="ctl-l7-bug-windup"></code-exercise>

The cart physically tops out at 3.75 m/s and is being asked for 12. For two
hundred ticks the integrator accumulates error that it has no authority to act
on, because the actuator is already at its limit and cannot do anything more
in response. When the setpoint finally drops to something reachable, that
stored debt keeps the command pinned in the wrong direction until it unwinds.
The controller is not mis-tuned; it is paying off a loan it took out while
nobody was watching.

<code-exercise src="ctl-l7-bug-kick"></code-exercise>

The measurement in this probe is a perfectly smooth ramp, with no
discontinuity anywhere in the physical signal, and yet the command jumps by
8.4 units in a single tick. Whatever produced that spike must have been
differentiating something that *did* jump, and the only thing that jumped was
the operator's intent. This is the argument for differentiating the
measurement rather than the error, made by a symptom rather than by a
paragraph.

<code-exercise src="ctl-l7-bug-lookahead"></code-exercise>

The third is the one worth sitting with, because nothing in the controller is
wrong at all. A 0.5 m lookahead is stable at 0.5 and 1.0 m/s, weaves with
0.82 m of error at 2.0 m/s, and diverges to 2.9 m at 3.0 m/s, while the code
never changed.

What changed is the ratio between a lookahead measured in **metres** and a
control delay measured in **seconds**. At 0.5 m/s the robot travels 0.10 m
while a steering command is in flight, against a 0.5 m preview, so the command
still applies to roughly where the robot is. At 2.0 m/s it travels 0.40 m in
the same delay, which is most of the preview distance, so by the time the
command takes effect the robot is steering toward somewhere it has already
been. This is lesson 2.4's speed-scaled lookahead argument arriving as a
failure rather than as advice.

Lesson 2.4's measured boundary makes the fix quantitative: stability requires
a preview *time* of at least 2 to 2.5 times the actuation delay, so with this
system's 0.20 s delay the smallest safe lookahead time is about 0.5 s. Check
the recovery rule `max(0.4, 0.9·v)` against that: it holds preview time at
0.9 s, sitting at roughly twice the measured minimum. That factor of two is
the rule's safety margin, and now you know both the rule and the region it is
valid in — halve the delay and the rule is conservative, double the delay and
it fails, which is precisely what the portfolio task below asks you to map.

## D. Diagnosis drills

<quiz-bank src="ctl-l7-drills"></quiz-bank>

## E. Debrief: the method

**Probe the boundary rather than the middle.** All three controllers behave
perfectly in the regime they were tested in, and each bug needs a specific
excursion to appear: windup needs saturation, kick needs a setpoint change,
and the lookahead bug needs speed. A test suite that exercises only the
nominal operating point passes all three, which is precisely why
bench-validated controllers still fail on delivery, and it is an argument for
writing tests at the edges of the envelope rather than at its centre.

**When the same code behaves differently, look outside the code.** The third
bug has no wrong line anywhere, because the instability lives in the
relationship between the controller, the vehicle speed and the actuation
delay. No amount of reading the function will reveal it, and the only
productive approach is to change one variable at a time and watch the
stability boundary move.

**Ask what the derivative is differentiating and what the integral is
buying.** Both PID bugs come from the same lapse of attention, which is
treating `error` as a single quantity rather than as `setpoint - measurement`,
two signals with completely different dynamics. The derivative term should see
only one of them, and the integral should stop accumulating the moment it can
no longer buy anything.

## F. Graded work and portfolio extension

**Graded:** the three fixes constitute Module 2's diagnostic assessment, and
they compose directly into the [control mini-project](project-control.md),
where the same anti-windup and derivative-on-measurement requirements are
worth 35 of the available 100 points.

**Portfolio:** take the third bug further by sweeping lookahead against both
speed and actuation delay, and plotting the stability boundary that separates
convergence from limit cycling. Then overlay the \(\max(0.4,\, 0.9v)\) tuning
rule and show where it sits relative to that boundary. A tuning rule presented
alongside the region in which it is valid is a substantially stronger artifact
than the rule by itself, and it is the kind of figure that makes a reviewer
trust everything else in your write-up.

## G. Annotated references

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Åström & Murray, *Feedback Systems*, ch. 11 | book | intermediate | The anti-windup and derivative-filtering sections address bugs 1 and 2 directly |
| Franklin, Powell & Emami-Naeini, *Feedback Control of Dynamic Systems*, ch. 9 | book | intermediate | Delay and its effect on stability margin, which is the mechanism behind bug 3 |
