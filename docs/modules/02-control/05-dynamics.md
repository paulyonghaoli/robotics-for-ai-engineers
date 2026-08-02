# 2.5 Dynamics intuition: why gravity compensation exists

**Status:** Code verified · **Prereqs:** lessons 2.1–2.2 · **Time:** ~2 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Kinematics says where things *can* go; dynamics says what it *costs* to move them: \(\tau = M(\theta)\ddot{\theta} + C(\theta,\dot{\theta})\dot{\theta} + g(\theta)\). You don't need to derive Lagrangians to work in robotics — but you must know the *shape* of this equation, because it explains why arms sag, why PID alone fights gravity forever, and why every industrial controller is really **feedforward physics + feedback cleanup**.

## B. Mental model

Three costs, three characters. **\(M\ddot{\theta}\)** — inertia, the price of *changing* motion, configuration-dependent (a stretched arm is harder to swing than a folded one — figure skater physics). **\(C\dot{\theta}\)** — velocity coupling (Coriolis/centrifugal), noticeable only when moving fast; the wobble in aggressive trajectories. **\(g(\theta)\)** — gravity, relentless and *position-dependent*: maximal on a horizontal arm, zero on a vertical one.

The controls insight: **feedback fights what you didn't predict; feedforward pays what you can predict.** Gravity is perfectly predictable from \(\theta\), so compute \(g(\theta)\) and add it to the command — the PID then only handles the (small, unpredictable) rest. Without it, a PI controller *can* hold position, but only by winding its integral up to the gravity torque — slowly, with sag, per setpoint (the integral is *learning* what physics could have told it).

## C. Mathematical formulation

For a 1-link arm (mass \(m\), length \(l\), angle \(\theta\) from horizontal):

\[
\tau_g = m g \tfrac{l}{2} \cos\theta \quad \text{(uniform rod)} \qquad
\tau_{cmd} = \tau_g(\theta) + \text{PD}(\theta_{ref} - \theta)
\]

That structure — model-based feedforward + PD — is "computed-torque control" in miniature, and scaled up (full \(M, C, g\)) it is exactly what runs inside industrial arm controllers. Friction (stiction + viscous) is the term nobody models well; it's why the feedback layer never goes away.

## D. From ML to robotics

- **Feedforward + feedback = model + residual learning.** The physics model handles the predictable bulk; feedback handles the residual — the same decomposition as boosting a learned residual on top of a physical model, and the architecture Module 9's learned controllers plug into (networks predict residual torques, not physics).
- **The wound-up integral as a slow learner:** PI holding an arm against gravity has *memorized* \(g(\theta)\) at one point — and must relearn it at every new setpoint. Feedforward is the generalizing model; the integral is a lookup table of size one.
- **\(M(\theta)\) as curvature:** configuration-dependent inertia is a position-dependent preconditioner — why well-tuned gains at one pose oscillate at another (the plant changed under the controller; lesson 2.2's "retuning is not exorcism").

## E. Minimal implementation & practice

<code-exercise src="ctl-l5-gravity"></code-exercise>

## F. Robotics-framework implementation

`ros2_control`'s `effort_controllers` accept feedforward terms; MoveIt's execution pipeline and any torque-controlled arm (Franka, Kinova) run gravity compensation *always on* — it's why you can push a collaborative robot around by hand: the motors are exactly canceling gravity, leaving the arm weightless to your touch.

## G. Experiment

The exercise's 1-link arm: hold \(\theta = 0\) (horizontal, worst case) with (a) PD only, (b) PID, (c) PD + gravity feedforward. Measure steady-state error and time-to-settle; then command a sequence of setpoints and watch (b) re-wind its integral at each one while (c) lands instantly. One plot, whole lesson.

## H. Failure modes

- **Gains tuned folded, deployed stretched:** \(M\) changed 4×; the loop oscillates. Gain-schedule or feedforward the inertia.
- **Wrong mass parameters in \(g(\theta)\):** feedforward now *injects* bias; the arm sags proportionally to your CAD-vs-reality error. Calibrate with a payload sweep.
- **Ignoring stiction near zero velocity:** limit cycles — the arm hunts around the setpoint, tick-tick-tick. Add dither or friction feedforward.

## I. Questions

1. *(Concept)* Why does gravity feedforward eliminate steady-state sag that P-control cannot, without any integral term?
2. *(Calculation)* Rod arm, \(m = 2\) kg, \(l = 0.5\) m, horizontal: compute the gravity torque (g = 9.81).
3. *(Debugging)* An arm holds every setpoint perfectly except near vertical, where it oscillates slowly. Which term of the dynamics is mismodeled, and why does it show *there*?
4. *(System design)* A pick-and-place arm's payload varies 0–5 kg per task. Design the compensation strategy — where does the payload estimate come from?

??? note "Answer sketches"
    **1.** P-control only produces torque in proportion to error, so holding a load of \(\tau_g\) requires a standing error of \(e = \tau_g/k_p\) — that error *is* the sag. Feedforward pays \(\tau_g(\theta)\) open-loop from the model, so zero error becomes an equilibrium and the feedback term is left with only the small unpredictable residual.

    **2.** \(\tau_g = m g (l/2) \cos 0 = 2 \cdot 9.81 \cdot 0.25 = 4.9\) N·m.

    **3.** Friction — stiction, the term the model leaves out. Near vertical \(\cos\theta \to 0\), so the gravity torque passes through zero: everywhere else the standing gravity load keeps the drivetrain preloaded on one side and the command comfortably outside the stiction band, but at vertical the command sits *inside* the deadband and the joint hunts across it in a slow limit cycle. Add friction feedforward or dither, or accept a small deadband around the setpoint.

    **4.** Keep \(g(\theta)\) as feedforward with payload mass as an explicit parameter, and get that parameter from measurement rather than the task description: right after each grasp, hold a known pose and regress the joint-torque residual \(\tau_{meas} - \tau_{model}\) onto the payload's moment arm to identify \(m\). Leave a slow integral term in as backstop for estimate error, and re-identify on release — a dropped or mis-grasped part then shows up as an identifiable mismatch instead of a bias you keep injecting.

### Interactive quiz

<quiz-bank src="control-l5-dynamics"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Lynch & Park, *Modern Robotics*, ch. 8 | book | advanced | The full dynamics treatment when you want it |
| Craig, *Introduction to Robotics*, ch. 6 & 10 | book | intermediate | Dynamics + the computed-torque architecture, gently |

## K. Graded work & portfolio extension

**Graded:** the section G comparison is the natural Module 2 project extension (planned).

**Portfolio:** the three-controller comparison plot with the integral's "relearning" visible at each setpoint change — the single clearest argument for model-based feedforward you can put in front of a controls interviewer.
