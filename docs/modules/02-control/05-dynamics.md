# 2.5 Dynamics intuition: why gravity compensation exists

**Status:** Code verified · **Prereqs:** lessons 2.1–2.2 · **Time:** ~2 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Kinematics tells you where things can go, and dynamics tells you what it costs
to move them. The whole subject compresses into one equation,

\[
\tau = M(\theta)\,\ddot{\theta} + C(\theta,\dot{\theta})\,\dot{\theta} + g(\theta)
\]

and you do not need to derive Lagrangians to work in robotics. What you do
need is to know the *shape* of that equation, because it explains why arms sag
under their own weight, why a PID controller ends up fighting gravity forever
instead of solving it, and why essentially every industrial arm controller is
built as predictable physics computed in advance plus feedback to clean up
what remains.

!!! note "Terms defined here"

    **Feedforward** — a command computed from a model of what the system will
    need, applied before any error has occurred.

    **Feedback** — a command computed from the error that has already
    occurred. Lesson 2.2 is entirely about feedback.

    **Inertia matrix**, \(M(\theta)\) — how much torque is required to produce
    a given joint acceleration, which depends on the configuration.

    **Stiction** — static friction: the torque needed to start motion from
    rest, which is larger than the torque needed to keep it going.

    **Computed-torque control** — the architecture of model-based feedforward
    plus feedback correction, which is what section C builds in miniature.

## B. Mental model

The equation has three terms and each has a distinct character worth knowing
separately.

The inertia term \(M(\theta)\ddot{\theta}\) is the price of *changing* motion,
and the important word is configuration-dependent: a stretched-out arm is
substantially harder to swing than a folded one, for the same reason a figure
skater spins faster with their arms pulled in. This is why gains tuned in one
pose can misbehave in another, which is failure mode 1.

The velocity-coupling term \(C(\theta,\dot{\theta})\dot{\theta}\) covers
Coriolis and centrifugal effects, and it is noticeable only when the arm is
moving quickly. It is the source of the wobble that appears in aggressive
trajectories and is absent from slow ones.

The gravity term \(g(\theta)\) is relentless and depends on position alone. It
is maximal when a link is horizontal and vanishes when it is vertical, and
because it depends only on where the arm is rather than how it is moving, it
is completely predictable.

That predictability is the whole lesson. **Feedback fights what you did not
predict, and feedforward pays for what you did.** Gravity is perfectly
predictable from \(\theta\), so the right move is to compute \(g(\theta)\) and
add it to the command directly, leaving the feedback controller to handle only
the small unpredictable remainder.

Without that, a PI controller *can* hold position against gravity, but only by
winding its integral up until the accumulated term happens to equal the
gravity torque. It gets there slowly, it sags on the way, and it has to repeat
the process at every new setpoint, because the integral has effectively
memorised one number that physics could have told it in closed form.

## C. Mathematical formulation

For a single-link arm of mass \(m\) and length \(l\), with \(\theta\) measured
from horizontal, a uniform rod has its centre of mass at \(l/2\) and therefore
a gravity torque of

\[
\tau_g = m g \tfrac{l}{2} \cos\theta
\]

and the control law becomes

\[
\tau_{cmd} = \tau_g(\theta) + \text{PD}(\theta_{ref} - \theta) .
\]

That structure — a model-based feedforward term plus a PD correction — is
**computed-torque control** in miniature, and scaled up to the full \(M\),
\(C\) and \(g\) it is precisely what runs inside industrial arm controllers.

The cosine is worth reading physically. At \(\theta = 0\) the arm is
horizontal, the moment arm is at its longest and the gravity torque is
maximal, while at \(\theta = \pi/2\) the arm points straight up, gravity acts
along the link rather than across it, and the torque passes through zero. That
zero crossing turns out to be where a different failure hides, which is
question 3.

Friction, comprising both stiction and a viscous term, is the part nobody
models well. It is why the feedback layer never goes away no matter how good
the model becomes.

## D. From ML to robotics

Feedforward plus feedback is model plus residual learning. The physics model
handles the predictable bulk while feedback handles what is left over, which
is the same decomposition as fitting a learned residual on top of a physical
model, and it is exactly the architecture that Module 9's learned controllers
plug into, since those networks predict residual torques rather than replacing
the physics.

The wound-up integral is a slow learner with a memory of size one. A PI
controller holding an arm against gravity has effectively memorised
\(g(\theta)\) at a single configuration, and it must relearn it from scratch
at every new setpoint. Feedforward is the generalising model and the integral
is a lookup table with one entry, which is a comparison worth keeping because
it predicts exactly when the integral approach will feel adequate — namely
when the arm holds one pose for a long time — and when it will feel terrible.

The configuration-dependent inertia \(M(\theta)\) behaves as a
position-dependent preconditioner, which is why gains that are well tuned at
one pose oscillate at another. The plant genuinely changed underneath the
controller, and this is the concrete version of lesson 2.2's warning that
retuning is not exorcism.

## E. Minimal implementation and practice

<code-exercise src="ctl-l5-gravity"></code-exercise>

## F. Robotics-framework implementation

`ros2_control`'s `effort_controllers` accept feedforward terms directly, and
MoveIt's execution pipeline supplies them. Any torque-controlled arm, such as
a Franka or a Kinova, runs gravity compensation permanently, and that is
precisely why you can push a collaborative robot around by hand: the motors
are continuously cancelling gravity, so the arm feels weightless to your touch
while remaining perfectly capable of holding its own weight the moment you let
go.

## G. Experiment — one plot, whole lesson

Using the exercise's single-link arm, hold \(\theta = 0\), which is horizontal
and therefore the worst case for gravity, under three controllers: PD alone,
PID, and PD with gravity feedforward. Measure steady-state error and
time-to-settle for each.

Then command a sequence of different setpoints and watch what happens. The PID
controller re-winds its integral at every one of them, sagging briefly each
time before recovering, while the feedforward controller lands immediately
because it already knows what each pose costs. That single plot makes the
argument for model-based feedforward more convincingly than any amount of
prose, and it is the portfolio artifact suggested in section K.

## H. Failure modes

**Gains tuned folded and deployed stretched** run into a four-fold change in
\(M\), and the loop oscillates. The remedies are gain scheduling across the
workspace or feeding the inertia forward as well as the gravity.

**Wrong mass parameters inside \(g(\theta)\)** turn feedforward from a fix
into an injected bias, so the arm sags in proportion to the discrepancy
between your CAD model and reality. Calibrate with a payload sweep rather than
trusting the drawing.

**Ignoring stiction near zero velocity** produces limit cycles, where the arm
hunts back and forth around the setpoint with an audible ticking. Add dither
or friction feedforward, or accept a small deadband and stop trying to servo
inside it.

## I. Questions

1. *(Concept)* Why does gravity feedforward eliminate the steady-state sag
   that P-control cannot, without any integral term at all?
2. *(Calculation)* For a uniform rod with \(m = 2\) kg and \(l = 0.5\) m held
   horizontal, compute the gravity torque, taking \(g = 9.81\).
3. *(Debugging)* An arm holds every setpoint perfectly except near vertical,
   where it oscillates slowly. Which term of the dynamics is mismodelled, and
   why does the problem appear *there*?
4. *(System design)* A pick-and-place arm's payload varies between 0 and 5 kg
   depending on the task. Design the compensation strategy, and say where the
   payload estimate comes from.

??? note "Answer sketches"
    **1.** A proportional controller produces torque strictly in proportion to
    error, so holding a load of \(\tau_g\) requires a standing error of
    \(e = \tau_g/k_p\), and that error *is* the sag. Feedforward supplies
    \(\tau_g(\theta)\) open-loop from the model, which makes zero error an
    equilibrium of the closed loop rather than an unreachable ideal, leaving
    the feedback term responsible only for the small unpredictable residual.

    **2.** \(\tau_g = m g (l/2) \cos 0 = 2 \times 9.81 \times 0.25 = 4.9\)
    N·m.

    **3.** Friction, specifically stiction, which is the term the model leaves
    out. Near vertical \(\cos\theta \to 0\), so the gravity torque passes
    through zero. Everywhere else the standing gravity load keeps the
    drivetrain preloaded against one side of its backlash and keeps the
    command comfortably outside the stiction band, but at vertical the command
    sits *inside* the deadband and the joint hunts slowly across it. The
    remedies are friction feedforward, dither, or accepting a small deadband
    around the setpoint.

    **4.** Keep \(g(\theta)\) as feedforward with the payload mass as an
    explicit parameter, and obtain that parameter by measurement rather than
    from the task description, because the task description is what is wrong
    when a part is mis-grasped. Immediately after each grasp, hold a known
    pose and regress the joint-torque residual \(\tau_{meas} - \tau_{model}\)
    onto the payload's moment arm to identify \(m\). Retain a slow integral
    term as a backstop against estimation error, and re-identify on release,
    so that a dropped or mis-grasped part surfaces as an identifiable mismatch
    rather than as a bias you continue injecting.

### Interactive quiz

<quiz-bank src="control-l5-dynamics"></quiz-bank>

## J. Annotated references

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Lynch & Park, *Modern Robotics*, ch. 8 | book | advanced | The full dynamics treatment for when you want the derivations rather than the shape |
| Craig, *Introduction to Robotics*, ch. 6 & 10 | book | intermediate | Dynamics together with the computed-torque architecture, presented gently |

## K. Graded work and portfolio extension

**Graded:** the section G comparison is the natural extension of the Module 2
project.

**Portfolio:** the three-controller comparison plot, with the integral's
relearning visible as a fresh sag at every setpoint change. It is the single
clearest argument for model-based feedforward that you can put in front of a
controls interviewer, precisely because the failure it shows is not a bug but
the expected behaviour of a reasonable-looking design.
