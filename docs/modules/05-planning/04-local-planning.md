# 5.4 Local planning: the dynamic window

**Status:** Code verified · **Prereqs:** lessons 1.4, 2.4, 5.1 · **Time:** ~2 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

The global planner (5.1) thinks in maps and seconds; something must think in *meters and milliseconds* — dodge the pallet that wasn't in the map, respect what the motors can actually do this instant, and still make progress along the route. That's the **local planner**, the layer between path and `cmd_vel` (the rate hierarchy from lesson 0.2, made concrete). The classic algorithm is **DWA — the Dynamic Window Approach** — and having built pure pursuit (2.4) and sampling MPC (2.6), you already own its two halves.

## B. Mental model

Every control cycle, DWA asks: *of the velocities I can actually reach in the next instant, which one is best?*

1. **The dynamic window**: the set of \((v, \omega)\) reachable within one step given acceleration limits — a small rectangle around the current velocity. This is the "respect the motors" part pure pursuit ignores.
2. **Rollout**: simulate each candidate velocity forward a short horizon (constant-twist arcs — lesson 1.4's integration, again).
3. **Score**: weighted sum of *progress* (toward goal / along the global path), *clearance* (distance to nearest obstacle along the arc), and *speed* (prefer brisk). Discard candidates whose arc collides.
4. Command the winner; repeat.

It's sampling MPC (2.6) specialized: horizon of one *held* action, candidates constrained to the reachable window, cost terms standardized. The window is what makes it *dynamically feasible* — no commanded velocity the base can't produce — which is DWA's whole point and name.

## C. Mathematical formulation

\[
V_d = \{ (v, \omega) : v \in [v_c - \dot{v}\Delta t,\ v_c + \dot{v}\Delta t],\ \omega \in [\omega_c - \dot{\omega}\Delta t,\ \omega_c + \dot{\omega}\Delta t] \} \cap V_{admissible}
\]

\(V_{admissible}\) removes velocities that can't stop before their arc's nearest obstacle: \(v \le \sqrt{2\, \dot{v}\, dist(v, \omega)}\) — the braking-distance argument from 2.6's Q2, applied per candidate. Score:

\[
G(v, \omega) = \alpha \cdot \text{progress} + \beta \cdot \text{clearance} + \gamma \cdot \text{velocity}
\]

The weights are the robot's temperament, and mistuning them produces the two canonical pathologies: β too high → the robot "freezes" in doorways (clearance dominates progress); α too high → it grazes furniture at speed.

## D. From ML to robotics

- **DWA is a one-step policy with a hand-crafted value function** — G(v, ω) is a value estimate over an action window. Learned local planners (Module 9) replace G with a network and keep the loop; knowing DWA is knowing the baseline they must beat *and* the safety envelope they run inside.
- **The freezing-robot problem is an exploration failure**: all nearby actions score badly, and a myopic (one-step) agent can't see that short-term discomfort buys long-term progress — the same pathology as greedy policies in sparse-reward settings. Fixes rhyme too: longer horizons (→ MPC/MPPI), or better value functions.
- **α/β/γ tuning is multi-objective scalarization** with all its usual sins — tune against scenario metrics (capstone rubric!), not single anecdotes.

## E. Minimal implementation & practice

<code-exercise src="plan-l4-dwa"></code-exercise>

## F. Robotics-framework implementation

Nav2 ships `dwb_controller` (DWA, refactored, with pluggable "critics" — each score term is a critic class) and the MPPI controller as its modern successor (2.6's sampling MPC with horizon > 1). The critics list in a dwb config file reads as this lesson's section C: `PathAlign`, `GoalDist`, `ObstacleFootprint`, `PreferForward`.

## G. Experiment

Set up a doorway 1.2× the robot's width. Sweep the clearance weight β and record: traversal success rate, minimum clearance, and time-to-traverse. Watch the freeze emerge as β grows — success rate *drops* while minimum clearance rises. Then place a person-sized obstacle mid-door and watch every β fail — the one-step horizon can't back out; that's the cue for MPPI or a recovery behavior (the capstone's rotate-and-replan, formalized).

## H. Failure modes

- **Freezing** in clutter (β ≫): safe, stationary, useless — and the robot blocks the corridor it refused to enter.
- **Grazing** (α ≫ or thin clearance term): technically collision-free arcs whose real-world execution (noise! 1.4) clips corners.
- **Window too optimistic**: acceleration limits from the datasheet, not the loaded robot — commanded velocities the base can't reach make every rollout a fiction (2.5's plant-mismatch, locally).
- **Local minima**: U-shaped obstacles trap one-step reasoning; escape needs the global planner's replan or an explicit recovery — know whose job it is (0.2's hierarchy).

## I. Questions

1. *(Concept)* Why must the admissibility check use *braking distance* rather than current clearance?
2. *(Calculation)* \(v_c = 0.8\) m/s, \(\dot{v}_{max} = 1.0\) m/s², Δt = 0.2 s: the window's v-range?
3. *(Debugging)* Your robot traverses open space fine but stops 1.5 m before every doorway, creeps, then darts through. Which weight, which direction, and why the *dart*?
4. *(System design)* Divide responsibilities between global planner, DWA, and the recovery system for the "person steps into the doorway" scenario — who detects, who reacts, who owns backing out?

??? note "Answer sketch for Q2"
    \([0.6, 1.0]\) m/s — the window is *small*; DWA's agility comes from re-choosing 10× a second, not from a big menu.

### Interactive quiz

<quiz-bank src="planning-l4-dwa"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Fox, Burgard & Thrun, *"The Dynamic Window Approach"* (1997) | paper | introductory | The original — still perfectly readable |
| [Nav2 DWB configuration](https://docs.nav2.org/configuration/packages/configuring-dwb-controller.html) | docs | intermediate | The critics architecture: score terms as plugins |
| Trautman & Krause, *"Unfreezing the robot"* (2010) | paper | advanced | The freezing problem, formally — and why crowds need more than DWA |

## K. Graded work & portfolio extension

**Graded:** a DWA variant of the capstone's controller (same harness) is a planned stretch goal alongside the MPC one — three local planners, one rubric.

**Portfolio:** the doorway β-sweep (success/clearance/time vs β) plus a freeze GIF — the freezing-robot problem is beloved interview territory, and you'll have *measured* it.
