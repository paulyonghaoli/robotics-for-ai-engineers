# 2.6 Model predictive control: a first look

**Status:** Code verified · **Prereqs:** lessons 1.4, 2.2 · **Time:** ~2 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

PID reacts; **MPC deliberates**. At every control step it asks: *given my model, which input sequence over the next N steps minimizes cost without violating constraints?* — applies only the first input, then re-asks with fresh state. This "receding horizon" loop is how quadrupeds place feet, how autonomous cars keep lane changes comfortable *and* legal, and how any controller handles the thing PID fundamentally cannot: **constraints** (actuator limits, obstacles, "never exceed 2 m/s²") as first-class citizens rather than clamps bolted on after.

## B. Mental model

MPC = **planning and control collapsed into one loop**. Where the capstone plans a path (slow) and tracks it with pure pursuit (fast), MPC re-plans a short trajectory *every step* — planning at control rate over a short horizon. The three dials:

- **Horizon N**: how far ahead to think. Too short: greedy, brakes late. Too long: expensive, and your model is fiction that far out anyway.
- **Cost**: state error vs control effort (\(Q\) vs \(R\) weights — same letters as Kalman, same "how much do I care" role, opposite direction).
- **Constraints**: the reason to bother. \(|u| \le u_{max}\), \(|v| \le v_{max}\) are *promises the optimizer keeps*, not saturations discovered after the fact.

Why replan every step instead of executing the whole optimal sequence? Because the model is wrong and the world is noisy — feedback re-enters through re-optimization. MPC is feedforward optimization wearing feedback's loop.

## C. Mathematical formulation

\[
\min_{u_0 \dots u_{N-1}} \sum_{k=0}^{N-1} \Big( \|x_k - x_{ref}\|_Q^2 + \|u_k\|_R^2 \Big) + \|x_N - x_{ref}\|_{Q_f}^2
\quad \text{s.t.} \quad x_{k+1} = f(x_k, u_k), \;\; u_k \in \mathcal{U}, \;\; x_k \in \mathcal{X}
\]

Linear model + quadratic cost + box constraints = a QP, solved in microseconds by OSQP/acados in production. This lesson's exercise uses the honest-but-simple alternative — **sampling-based MPC**: roll out a bank of candidate input sequences through the model, score them, take the best sequence's first input. Crude, derivative-free, embarrassingly parallel — and the direct ancestor of MPPI, which real legged robots run today.

## D. From ML to robotics

- **Receding horizon = beam search with re-rooting**: search, commit one step, re-search from reality — the same anytime-planning pattern as game-tree search or LLM decoding with lookahead.
- **Q/R weights are loss-function engineering**, and terminal-cost design is reward shaping; the failure modes (myopia, cost hacking) transfer intact.
- **Sampling MPC is the bridge to Module 9**: replace "roll out through the physics model" with "roll out through a *learned* model" and you have model-based RL's control loop (MPPI, world models). One lesson, half the modern robot-learning stack demystified.

## E. Minimal implementation & practice

<code-exercise src="ctl-l6-mpc"></code-exercise>

## F. Robotics-framework implementation

Nav2's **MPPI controller** is sampling MPC as the local planner — rollouts of twist sequences through the motion model, scored against path-following, obstacle, and smoothness costs. For arms and legged robots, OCS2/acados/Crocoddyl solve the QP/DDP versions at kHz. The concepts you just built are the configuration surface of all of them.

## G. Experiment

On the exercise's constrained cart: sweep horizon N ∈ {3, 10, 30} and watch short horizons brake too late (constraint says stop; myopia says not yet) while long horizons waste compute for identical behavior. Then break the model (simulate 20% more mass than the model assumes) and watch replanning quietly absorb the error — feedback through re-optimization, demonstrated.

## H. Failure modes

- **Horizon myopia**: N too short to see an approaching constraint → infeasible or violent late corrections.
- **Model-plant mismatch beyond what replanning absorbs**: persistent bias in a *direction* the cost doesn't penalize accumulates (the Kalman-Q lesson, control edition).
- **Infeasibility handling**: constraints can become unsatisfiable (obstacle appeared inside the braking distance). Production MPC has explicit fallbacks — soften constraints, or hand off to a safety stop. An optimizer that "has no solution" at 2 m/s needs a plan B *designed*, not discovered.
- **Compute jitter**: an optimizer that usually takes 5 ms and occasionally 80 ms breaks the real-time contract worse than one that always takes 20 (Module 10's p95 obsession, already visible).

## I. Questions

1. *(Concept)* Why apply only the first input of the optimal sequence instead of executing all N?
2. *(Calculation)* Cart at x = 0, v = 2 m/s, u ∈ [−1, 1] m/s². What's the minimum stopping distance — and the shortest horizon (dt = 0.5 s) that can *see* a wall at x = 2.5 m in time?
3. *(Debugging)* Your MPC tracks well but chatters between +u_max and −u_max every step. Which weight is wrong?
4. *(System design)* Split the capstone's navigation between A* and an MPC local controller: who owns obstacles, who owns dynamics, and at what rates?

??? note "Answer sketches"
    **1.** The tail of the sequence is optimal for the *predicted* state trajectory, and the model is wrong, so executing it open-loop compounds model error and disturbances for N steps with no correction. Applying only \(u_0\) and re-solving from the freshly measured state is exactly where feedback re-enters — the receding horizon is what turns an open-loop optimization into a closed-loop controller.

    **2.** Stopping distance \(v^2/2u_{max} = 2\) m; the wall at 2.5 m leaves 0.5 m of margin, but braking takes 2 s = 4 steps — a horizon shorter than ~4 steps literally cannot represent stopping in time.

    **3.** \(R\) is too small relative to \(Q\): with no meaningful price on control effort, bang-bang is (marginally) the cheapest way to hold the state target, and nothing in the cost penalizes reversing sign every single step. Raise \(R\), or better, add an input-rate term \(\|u_k - u_{k-1}\|^2_{R_\Delta}\), which attacks the chatter directly without making the controller sluggish overall.

    **4.** A* owns the static map and the global route, replanned at ~1 Hz or on map change; MPC owns dynamics, actuator and velocity/acceleration constraints, and near-field dynamic obstacles at control rate (10–50 Hz) over a 1–2 s horizon, tracking the A* path as its reference. The split follows the blind spots: A* has no dynamics model and cannot run at control rate, while MPC's horizon is far too short to reason its way out of a dead end.

### Interactive quiz

<quiz-bank src="control-l6-mpc"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Borrelli, Bemporad & Morari, *Predictive Control*, ch. 1 | book | intermediate | The clean formulation, freely available draft |
| Williams et al., *"MPPI"* (2016) | paper | intermediate | Sampling MPC done seriously — the exercise's grown-up sibling |
| [Nav2 MPPI controller docs](https://docs.nav2.org/configuration/packages/configuring-mppic.html) | docs | intermediate | Production sampling-MPC knobs |

## K. Graded work & portfolio extension

**Graded:** MPC returns as an alternative capstone local controller (stretch goal, scored by the same harness).

**Portfolio:** swap the exercise's MPC in as the capstone's tracker and publish the rubric comparison vs pure pursuit — same harness, two controllers, honest numbers. Exactly the "evaluated, not vibed" evidence this whole project is for.
