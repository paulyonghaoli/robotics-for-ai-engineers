# 2.2 PID control, properly

**Status:** Code verified · **Prereqs:** lesson 1.4 · **Time:** ~2.5 h · **Verified:** 2026-08-01, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

PID runs the world: your robot's wheel speeds, the drone's attitude, the arm's joints, the oven in your kitchen. It is often dismissed as "the simple controller" and then implemented wrong in five distinct ways (unwrapped angles, derivative kick, integral windup, wrong timestep, noise-amplified D). This lesson is PID as production engineering — the version that survives contact with hardware — because the capstone's trajectory follower and half of Module 10's incidents run through it.

## B. Mental model

Three terms, three time horizons of the error:

- **P — the present.** Push proportionally to the current error. Alone, it's a spring: it undershoots persistent disturbances (steady-state error) and can oscillate.
- **I — the past.** Accumulate error over time and push against the accumulation. This is what cancels steady-state error — the integral *learns the disturbance* — and also what causes windup when the actuator can't deliver.
- **D — the future.** React to the error's rate of change; brake before overshooting. This is damping — and a noise amplifier, since differentiation amplifies high frequencies.

An ML lens that lands well: the integral term is a **bias corrector learned online** (like BatchNorm's running mean, and with the same staleness pathologies), and D is a **momentum-like damping** on the correction.

## C. Mathematical formulation

\[
u(t) = k_p\, e(t) + k_i \int_0^t e(\tau)\, d\tau + k_d\, \dot{e}(t)
\]

Discrete form with the three production guards (exactly what `robotics_ai.control.PID` implements):

1. **Clamp the output** to actuator limits \([u_{min}, u_{max}]\).
2. **Anti-windup:** clamp (or conditionally freeze) the integral, else a saturated actuator lets the integral grow unboundedly and the system massively overshoots when the error finally reverses.
3. **No derivative kick:** the first sample has no history — define its derivative as zero (or differentiate the *measurement* instead of the error so setpoint steps don't spike D).

The **plant** is the system being controlled — the motor, the arm, the car — as opposed to the controller acting on it. The term is inherited from process control, where the plant really was a chemical or power plant, and it is used throughout the control literature for anything you can influence only through actuators.

Why P alone leaves steady-state error, in one line: at equilibrium a first-order plant needs \(u = y\) to hold position; \(u = k_p (r - y)\) gives \(y = \frac{k_p}{1 + k_p} r < r\). The integral supplies the missing constant.

## D. From ML to robotics

- **Tuning gains ≈ tuning learning rates.** Too-high \(k_p\) oscillates like a too-high learning rate; \(k_d\) damps like momentum-correction; the integral is a slow secondary learner. And like LR tuning, there are recipes (Ziegler–Nichols) but the pros tune by looking at the response shape.
- **Windup ≈ optimizer state corruption.** A saturated actuator with a growing integral is stale momentum in an optimizer after gradient clipping — the state no longer reflects reality, and recovery takes as long as the corruption did.
- **PID is a 3-parameter policy.** Model-free, interpretable, provable — which is why it hasn't been replaced by networks in the inner loop. Learned policies (Module 9) typically *output setpoints for PIDs*, not motor currents.

## E. Minimal implementation

The library version: [`robotics_ai/control/pid.py`](https://github.com/paulyonghaoli/robotics-for-ai-engineers/blob/main/robotics_ai/control/pid.py) — clamping, anti-windup, kick-free first step, tested including a saturation-recovery case.

### Practice — write and run code here

<code-exercise src="ctl-l2-pid"></code-exercise>

<code-exercise src="ctl-l2-tune"></code-exercise>

## F. Robotics-framework implementation

In ROS 2, `ros2_control` hosts PIDs in the `joint_trajectory_controller` and `diff_drive_controller`; gains live in YAML parameters and can be retuned live via the parameter interface. The capstone will close the loop as: planner → reference trajectory → PID on cross-track and heading error → `cmd_vel`.

## G. Experiment

On the exercise's mass simulator: raise \(k_p\) until sustained oscillation, note the period, apply Ziegler–Nichols, then improve on it by hand. Then add measurement noise (σ = 1 cm) and watch the D term amplify it into actuator chatter; fix with a low-pass filter on D (α ≈ 0.1) and measure what you paid in damping.

## H. Failure modes

- **Integral windup** — the classic: saturated actuator, unreachable setpoint, integral grows for seconds, then a huge overshoot when conditions change. Guards: integral clamp, conditional integration, back-calculation.
- **Derivative on noisy measurements** — chattering actuators, heated motors. Guard: filtered D, or drop to PI.
- **Unwrapped heading error into a PID** — lesson 1.6's bug 2; the controller is innocent, the error computation is guilty.
- **Retuning masking a plant change** — if gains that worked suddenly don't, suspect the robot (payload, battery sag, worn tire) before the controller. Tuning is not exorcism.

## I. Questions

1. *(Concept)* Why can't P-only control reject a constant disturbance, no matter the gain?
2. *(Calculation)* A P-controller on a first-order plant with \(k_p = 4\): what fraction of the setpoint is reached at steady state?
3. *(Debugging)* A drone's altitude hold works in hover but porpoises violently after aggressive climbs. Which term and which pathology?
4. *(System design)* Cascade control: why do arms run a fast inner velocity PID inside a slower outer position loop instead of one position PID?

??? note "Answer sketches"
    **1.** P output is strictly proportional to error, so the constant effort that cancels a constant disturbance has to be bought with a permanent error \(e = d/k_p\) — at zero error the controller commands zero. Raising \(k_p\) shrinks the offset (\(y = \frac{k_p}{1+k_p} r\)) but never removes it; only a term that sustains nonzero output at zero error — the integral — can.

    **2.** \(y/r = k_p/(1 + k_p) = 4/5 = 0.8\) — 80% of the setpoint, i.e. 20% steady-state error.

    **3.** Integral windup: during the climb the thrust saturates, altitude error integrates, and the accumulated integral overshoots the hover point — porpoising. Clamp or freeze integration while saturated.

    **4.** Cascade, because the inner loop kills torque-level disturbances (friction, gravity load, back-EMF, gearbox stiction) inside its own fast time constant, before they ever surface as position error — and it hands the outer loop a plant that behaves like a clean integrator of commanded velocity, which is trivial to tune. One position PID would have to cover fast actuator dynamics and slow position dynamics with a single gain set, so it gets detuned to the slower one; cascading also gives you velocity and acceleration limiting for free at the interface.

### Interactive quiz

<quiz-bank src="control-l2-pid"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Åström & Murray, *Feedback Systems*, ch. 11 | book | intermediate | PID with actual theory behind the recipes — free online |
| [`ros2_control` PID docs](https://control.ros.org/jazzy/index.html) | docs | intermediate | Where the gains live in production |
| Ziegler & Nichols (1942) | paper | introductory | The original tuning recipe — 80 years old, still the starting point |

## K. Graded work & portfolio extension

**Graded:** the tuning exercise above enforces quantitative step-response specs — settle time, overshoot cap — the same rubric style the capstone's control scoring uses.

**Portfolio:** the section G noise study (D-term chatter, filtered-D fix, damping cost) as a short plotted write-up; controls interviewers ask about exactly this trade-off.
