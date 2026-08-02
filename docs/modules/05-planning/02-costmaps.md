# 5.2 Costmaps: obstacles are not binary

**Status:** Code verified · **Prereqs:** lessons 1.5, 5.1 · **Time:** ~1.5 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Lesson 5.1 planned on a binary grid: cell blocked or free. Real planners run on **costmaps** — cells carry *graded* cost, so "legal but uncomfortably close to a shelf" is expensive rather than either forbidden or free. This single change is why Nav2 robots glide down the middle of corridors instead of hugging walls at the exact inflation boundary, and it's the mechanism by which every soft preference (stay away from glass, avoid the loading dock at shift change) enters planning.

## B. Mental model

Three cost bands, radiating from each obstacle: **lethal** (the obstacle itself), **inscribed** (cells whose center guarantees collision given the robot's radius — the hard inflation from lesson 1.5), and the **decay skirt** — cost falling off exponentially with distance beyond the inscribed radius. The planner minimizes *path cost* = length + accumulated cell cost, so it trades a slightly longer route for clearance exactly as much as your decay parameters say to. The skirt is a **soft constraint**; the inscribed band stays hard. Softening what should be hard (or vice versa) is the classic costmap bug.

## C. Mathematical formulation

With \(d(c)\) = distance from cell \(c\) to the nearest obstacle and robot radius \(r\):

\[
cost(c) = \begin{cases}
\infty \text{ (lethal)} & d(c) \le r \\
C_{max} \, e^{-\alpha (d(c) - r)} & d(c) > r
\end{cases}
\]

Search minimizes \(\sum (\text{step length} + w \cdot cost(c))\). The decay rate \(\alpha\) and weight \(w\) *are* the personality of your robot's driving: large → wide berths and longer paths; small → efficient and brave. The distance field is the same chamfer transform the capstone's likelihood field used — one primitive, three jobs now.

## D. From ML to robotics

- **Costmaps are reward shaping**: the hard constraint is the task; the skirt is shaped preference. The failure modes transfer — shape too aggressively and the planner "reward-hacks" into weird detours; too little and behavior is technically-legal-but-alarming.
- **Layered costmaps** (static map + live obstacles + inflation, composed by max) are feature pipelines with a defined merge semantics — and debugging one means inspecting *layers*, not the composite, exactly like debugging a stacked model.
- **α and w are hyperparameters with visible behavior** — tuned in simulation against scenario metrics (the capstone rubric's path-ratio vs collision trade is precisely their loss surface).

## E. Minimal implementation & practice

<code-exercise src="plan-l2-costmap"></code-exercise>

## F. Robotics-framework implementation

Nav2's costmap_2d is this lesson as a subsystem: `static_layer`, `obstacle_layer` (lesson 4.1 live), `inflation_layer` (`inflation_radius`, `cost_scaling_factor` = our α), composed by maximum. Its `inscribed_radius`/`circumscribed` distinction is lesson 1.5's footprint discussion; planners read the composite.

## G. Experiment

On one map, plan with \(w \in \{0, 2, 10\}\): measure path length and minimum clearance for each. Plot the Pareto curve — length vs clearance. Then drop a "social" cost blob (no obstacle, pure preference) in a corridor and watch the path politely detour: costs are how *policy* enters geometry.

## H. Failure modes

- **Skirt where a wall should be:** if the inscribed band is encoded as high-but-finite cost, a long-enough detour makes driving *through the robot's own radius* mathematically attractive. Lethal must be lethal.
- **Cost so high paths can't exist:** an over-weighted skirt in a narrow corridor exceeds any finite alternative — planner declares failure in a passable hallway.
- **Layer clobbering:** composing by sum instead of max double-counts overlapping layers (two sources of the same wall = twice the cost — the correlated-evidence bug from 3.5/4.1, in planning clothes).

## I. Questions

1. *(Concept)* Why compose costmap layers by max rather than sum?
2. *(Calculation)* \(C_{max} = 100\), α = 2/m, r = 0.3 m: cost at 0.8 m from an obstacle?
3. *(Debugging)* Your robot suddenly hugs walls after a map update, though no parameters changed. What property of the *distance field* should you check?
4. *(System design)* Encode "avoid the loading dock 2–3 pm" using costmap machinery. What layer, what update path, what failure if you get the max/sum choice wrong?

??? note "Answer sketches"
    **1.** Layers are independent *statements about the same cell*, not independent obstacles: the static layer's wall and the obstacle layer's live reading of that wall are one wall seen twice. Max takes the most pessimistic claim, is idempotent under re-observation, and preserves lethal-as-lethal; sum double-counts correlated evidence, so a cell covered by three moderate skirts accumulates a wall that no layer ever asserted — the 3.5/4.1 correlated-evidence bug wearing planning clothes.

    **2.** \(100 \cdot e^{-2(0.5)} = 100 e^{-1} \approx 36.8\).

    **3.** Check the distance field's **saturation** — the maximum distance it actually computes, and the units it computes it in. The chamfer transform is usually truncated at the inflation radius (and often produced in *cells*, then scaled by resolution); if the new map is more open, or its resolution changed, every cell past the truncation gets the same clamped \(d\), the exponential skirt flattens to a constant, and search sees no clearance gradient at all — so it minimizes length alone and rides the inscribed boundary. Fix: recompute the field in metres over a range wide enough to cover the corridor half-width, and verify cost varies from wall to centreline before blaming the planner.

    **4.** A separate **time-varying policy layer** in the layered costmap, holding a high-but-finite cost polygon over the dock, re-evaluated on the costmap's own update tick from a schedule so it stamps itself at 2 pm and clears at 3 pm without ever touching the static or obstacle layers (which stay debuggable in isolation). Compose by max, and keep the cost finite: sum would stack the policy cost onto the inflation skirt near the dock's walls and manufacture an impassable band the planner can't route around, and a lethal encoding would fail outright on the day the dock is the only connected route — the "cost so high paths can't exist" failure, on a schedule.

### Interactive quiz

<quiz-bank src="planning-l2-costmaps"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| [Nav2 costmap_2d docs](https://docs.nav2.org/configuration/packages/configuring-costmaps.html) | docs | intermediate | The production layer architecture and its knobs |
| Lu, Hershberger & Smart, *"Layered Costmaps"* (2014) | paper | introductory | Short, readable origin of the layer design |

## K. Graded work & portfolio extension

**Graded:** costmap weighting joins the capstone as a stretch goal (clearance-aware planning scored on the same rubric).

**Portfolio:** the section G Pareto plot (length vs clearance across w) — the one-figure version of "I tune planners against metrics, not vibes."
