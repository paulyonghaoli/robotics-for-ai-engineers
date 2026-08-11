# 5.1 Graph search and A*: planning as principled impatience

**Status:** Code verified · **Prereqs:** lesson 1.5 · **Time:** ~2.5 h · **Verified:** 2026-08-01, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Once the map is a grid and the robot is a point (lesson 1.5's inflation trick), "get from A to B" becomes graph search — and A* has been the backbone answer since 1968. It plans our capstone's every route, it's inside Nav2's default global planner, and its core idea (*expand in order of optimistic total cost*) recurs everywhere from RRT* rewiring to LLM beam search. You likely know A* already; this lesson is about knowing it the way planners are debugged in production.

## B. Mental model

Dijkstra is a flood: expand outward by cost-so-far \(g\), guaranteed optimal, blind to where the goal is. A* adds a compass: order expansion by \(f = g + h\), where \(h\) optimistically estimates cost-to-go. If \(h\) never overestimates (**admissible**), the first time the goal is expanded is provably optimal — you get Dijkstra's guarantee while exploring a fraction of the map. The heuristic is *principled impatience*: exactly as much greed as correctness allows.

The dial to internalize: \(h = 0\) is Dijkstra (slow, optimal); \(h\) = octile distance is exact-optimistic for 8-connected grids (fast, optimal); \(h\) inflated by \(\varepsilon > 1\) is *weighted A\** (faster, bounded suboptimality \(\varepsilon\)) — a knob production planners actually expose.

## C. Mathematical formulation

Priority queue on \(f(n) = g(n) + h(n)\). For 8-connected grids with unit/\(\sqrt{2}\) step costs, the octile heuristic

\[
h = (\Delta x + \Delta y) + (\sqrt{2} - 2)\min(\Delta x, \Delta y)
\]

is admissible *and* consistent (\(h(n) \le c(n, n') + h(n')\)), which lets each node be finalized on first expansion — no reopening. Euclidean distance is also admissible here but weaker (explores more); Manhattan distance **overestimates** diagonal-capable motion and silently breaks optimality — the classic copy-paste bug from 4-connected code.

One correctness subtlety our implementation enforces: **no corner cutting** — a diagonal step requires both orthogonal neighbors free, else the robot's body would clip the corner between two blocked cells (and a diagonal wall of obstacles becomes, correctly, watertight).

### The heuristic sweep, measured

Every claim about heuristics deserves a number, so here they all are at once,
on ten random 100×100 obstacle grids, 8-connected, planning corner to corner:

| Heuristic | Mean expansions | Mean path cost | vs optimal |
|---|---|---|---|
| Zero (Dijkstra) | 9,502 | 144.87 | exact |
| Euclidean | 1,968 | 144.87 | exact |
| Octile (tight) | 1,099 | 144.87 | exact |
| Octile, weight 1.5 | **137** | 145.34 | +0.32% |
| Octile, weight 3.0 | 112 | 145.30 | +0.30% |
| Manhattan (inadmissible on 8-connected) | 114 | 145.22 | +0.24% |

Read it in three passes. First, the free lunch: every admissible heuristic
returns the *identical* optimal cost, and tightening the heuristic from
nothing to Euclidean to octile cuts expansions 4.8× and then 8.6× — the
heuristic is pure search-pruning with zero cost in solution quality, which is
the theorem, observed. Second, the deliberate trade: **weighted A\*** at
\(w = 1.5\) gives up admissibility and 0.32% of path quality to buy a
**69× reduction** over Dijkstra and 8× over honest A\*. A third of a per cent
of extra driving for an order of magnitude less compute is a trade almost
every real-time system takes, which is why `w` is a first-class parameter in
production planners rather than a bug.

Third, the classic "bug": Manhattan distance on an 8-connected grid
overestimates diagonal moves and is therefore inadmissible — and here it
costs all of 0.24%, behaving almost exactly like weighted A\*. That is worth
stating honestly rather than theatrically: on *random* clutter, mild
inadmissibility is mild suboptimality. The theorem's teeth show elsewhere —
adversarial mazes where the overestimate points the search down a long wrong
corridor — so the correct posture is to know which regime you are in, not to
treat admissibility as a superstition.

## D. From ML to robotics

- **The heuristic is a value-function prior.** \(h\) is a hand-built lower bound on cost-to-go — a pessimist's value function. Learning \(h\) from experience is an active research thread, and the admissibility trade you feel here is exactly the optimism/soundness tension in RL exploration bonuses.
- **Weighted A\* is a compute/quality dial** like beam width or sampling temperature: \(\varepsilon\)-bounded suboptimality bought with wall-clock. Planners publish this trade; your serving stack does too.
- **Grid search doesn't scale in dimension** — 100×100 cells is fine for a floor plan, hopeless for a 7-DOF arm (lesson 1.5's curse). That cliff is *why* sampling-based planners (RRT/PRM, lesson 5.3) exist: same reason ML abandoned grid search for hyperparameters.

## E. Minimal implementation

Library: [`robotics_ai/planning/astar.py`](https://github.com/paulyonghaoli/robotics-for-ai-engineers/blob/main/robotics_ai/planning/astar.py) — heap-based, octile heuristic, corner-cutting guard, plus `inflate_grid` (lesson 1.5 shipped as code). The test suite includes an optimality check against brute-force Dijkstra on random grids — steal that idiom for any search code you ever write.

### Practice — write and run code here

<code-exercise src="plan-l1-astar"></code-exercise>

<code-exercise src="plan-l1-heuristic"></code-exercise>

## F. Robotics-framework implementation

Nav2's global planner family (`NavFn`, `SmacPlanner2D`) is this lesson on a *costmap* — cells carry graded costs (inflation skirts, not just binary walls), so paths prefer clearance, and the Hybrid-A* variant plans in \((x, y, \theta)\) with motion primitives for car-like robots. Our capstone uses the library A* on the inflated grid directly — you can read its entire planning path in one sitting.

## G. Experiment

On a 100×100 world with rooms: run Dijkstra (\(h=0\)), A* (octile), and weighted A* (\(\varepsilon \in \{1.5, 3\}\)), counting expanded nodes and path length. Typical result: A* expands 5–10× fewer nodes than Dijkstra for identical paths; \(\varepsilon = 3\) expands 30× fewer for a path a few percent longer. Then hand weighted A* a *maze* and watch the advantage evaporate — heuristics only help when geometry cooperates. Plot all four frontiers; the pictures are the intuition.

## H. Failure modes

- **Inadmissible heuristic** (Manhattan on 8-connected motion): silently suboptimal paths that look fine in demos and cost money at fleet scale.
- **Forgetting inflation**: paths hug walls perfectly legally in cell-space and scrape paint in the real world. Plan on the inflated grid, always (the capstone's rubric would catch it as collisions).
- **Corner cutting allowed**: intermittent clipped corners at diagonal squeezes — looks like a controller bug, is a planner bug.
- **Replanning thrash**: replanning every cycle from noisy poses makes the path flicker between homotopy classes and the robot dither at decision points. Production: replan on triggers (blocked path, large deviation), not on timers alone.

## I. Questions

1. *(Concept)* Why does consistency (not just admissibility) let A* finalize nodes on first expansion?
2. *(Calculation)* From (0,0) to (5,3) with 8-connectivity: compute the octile heuristic and an optimal path length.
3. *(Debugging)* Your A* returns paths 2–5% longer than a colleague's on the same maps, only when routes have long diagonal stretches. Find the bug.
4. *(System design)* A warehouse robot replans at 2 Hz on a 400×400 costmap with a 20 ms budget. Choose: plain A*, weighted A*, or D*-Lite incremental replanning — and defend it.

??? note "Answer sketches"
    **1.** Consistency, \(h(n) \le c(n,n') + h(n')\), makes \(f\) non-decreasing along every path, so the priority queue pops nodes in non-decreasing \(f\) order. Any path discovered later must therefore have \(f\) at least as large as the one already used to expand a node, and cannot improve its \(g\) — the node is final on first pop, no reopening. Admissibility alone gives you optimality *at the goal* but permits a node to be expanded with an inflated \(g\) and improved later, which is exactly what the reopening bookkeeping exists to catch.

    **2.** \(h = (5+3) + (\sqrt{2}-2)\cdot 3 = 8 - 1.757 = 6.24\); optimal = 3 diagonal + 2 straight = \(3\sqrt{2} + 2 \approx 6.24\). Octile is exact on open ground — the tightest admissible grid heuristic.

    **3.** An inadmissible heuristic — almost certainly Manhattan (\(\Delta x + \Delta y\)) copy-pasted from 4-connected code onto 8-connected motion. Manhattan charges 2 for a diagonal step that costs \(\sqrt{2}\), so it *overestimates* cost-to-go by up to \((2-\sqrt{2})\min(\Delta x,\Delta y)\), which is zero on axis-aligned routes and grows exactly with diagonal content — hence the symptom's selectivity. Fix: use the octile heuristic, and add the brute-force-Dijkstra optimality test on random grids so it can't regress.

    **4.** **D\*-Lite.** 400×400 = 160k cells, and a from-scratch A\* only fits 20 ms in the easy case — the moment the route is blocked and the heuristic stops helping, expansion counts spike precisely in the cycle where replanning matters most, which is the wrong place to have a variable-cost planner. Between 2 Hz cycles the costmap changes in a small neighbourhood of the robot, so D\*-Lite repairs only the affected region and its cost tracks the change, not the map. If incremental replanning is too much machinery to own, ship weighted A\* (\(\varepsilon \approx 1.5\)–2) with an anytime deadline and take best-so-far; plain A\* is the option to rule out, since bounded-suboptimal-on-time beats optimal-sometimes for a controller waiting on a path.

### Interactive quiz

<quiz-bank src="planning-l1-astar"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Hart, Nilsson & Raphael (1968) | paper | introductory | The original A* paper — short, and the optimality proof is readable |
| LaValle, *Planning Algorithms*, ch. 2 | book | intermediate | Discrete planning done properly — free online |
| [Nav2 SmacPlanner docs](https://docs.nav2.org/configuration/packages/configuring-smac-planner.html) | docs | intermediate | Costmaps, Hybrid-A*, and the knobs production exposes |
| Koenig & Likhachev, *D\* Lite* (2002) | paper | advanced | Incremental replanning — read before answering Q4 for real |

## K. Graded work & portfolio extension

**Graded:** A* is the capstone's global planner; the path-ratio metric in `python -m eval` scores its output every episode.

**Portfolio:** the section G frontier study as an animated comparison (four expansion frontiers racing across the same map) — the single best visual explanation of heuristics there is.
