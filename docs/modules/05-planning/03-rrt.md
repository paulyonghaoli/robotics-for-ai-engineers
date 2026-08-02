# 5.3 Sampling-based planning: RRT and friends

**Status:** Code verified · **Prereqs:** lessons 1.5, 5.1 · **Time:** ~2.5 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Lesson 1.5 ended on a cliff: explicit C-space construction is hopeless beyond a few dimensions, and 5.1's grids fall off the same cliff (360⁷ cells for a 7-DOF arm). **Sampling-based planners** walk around the cliff entirely: never *represent* free space — just *sample* configurations, ask the collision-checker oracle, and connect what's free. RRT and PRM plan for arms, drones, and parking maneuvers in spaces where grids cannot exist. This is the second half of planning's toolbox, and the half that arm robotics (Module 8, MoveIt) runs on.

## B. Mental model

**RRT grows a tree like frost spreading on glass.** Repeat: (1) sample a random configuration; (2) find the *nearest* tree node; (3) **steer** — extend from that node a bounded step toward the sample; (4) keep the new node if the segment is collision-free. The magic is *Voronoi bias*: the node nearest to a random sample is disproportionately likely to border large unexplored regions, so the tree is automatically pulled toward open space — exploration for free, no grid, no heuristic. A small **goal bias** (sample the goal 5–10% of the time) points the frost at the target.

The family portrait: **PRM** (sample many nodes up front, connect neighbors, then query the roadmap — for *many* queries in a static world) vs **RRT** (grow per query — for single shots) vs **RRT\*** (rewire the tree as it grows so path quality *improves* with samples — asymptotically optimal, at real extra cost).

## C. Mathematical formulation

Probabilistic completeness: if a solution path exists with clearance, RRT finds one with probability → 1 as samples → ∞ — but with **no optimality claim** (raw RRT paths are jagged; everyone post-processes with shortcut smoothing). RRT\* adds two steps per sample — choose-parent (connect through the cheapest nearby node) and rewire (let the new node become a cheaper parent for its neighbors) — buying asymptotic optimality for an \(O(\log n)\)-neighbor cost per iteration.

The steer step-size δ is the resolution/effort dial; segment collision checking at spacing finer than your thinnest obstacle is correctness, not style (lesson 1.5's sparse-sampling warning, now load-bearing).

## D. From ML to robotics

- **The collision checker is a labeling oracle and RRT is active exploration** — the planner "queries where it's uncertain," and Voronoi bias is an exploration bonus you get from geometry instead of engineering it.
- **Grid search vs random search, literally:** the same reason random search beats grid search for hyperparameters (Bergstra & Bengio) is why sampling beats grids in high-dimensional C-spaces — grids waste resolution uniformly; samples concentrate where volume is.
- **Anytime behavior:** RRT\*'s solution quality improves monotonically with compute — a *stop-whenever* planner, the same contract as anytime beam search or diffusion sampling steps. Production plans under a deadline and takes the best-so-far.

## E. Minimal implementation & practice

<code-exercise src="plan-l3-rrt"></code-exercise>

## F. Robotics-framework implementation

MoveIt 2 delegates arm planning to **OMPL**, whose default is RRTConnect — two trees, one from start and one from goal, greedily connected; brutally effective in practice. Every OMPL planner consumes exactly one interface: a state validity checker — the oracle pattern, productized. Nav2's Smac lattice planners stay grid-side because mobile bases live in low dimensions; the split you now understand is *dimension*, not fashion.

## G. Experiment

Plan through a narrow gap at several gap widths; plot success rate vs samples for RRT with and without goal bias, then against gap width. The **narrow-passage problem** emerges — sampling volume ∝ passage volume — and motivates the bridge-test and Gaussian samplers the literature spends so much ink on. Then run RRT 50× on one map and histogram path lengths: the variance *is* the "no optimality" clause, visualized.

## H. Failure modes

- **Coarse segment checking** tunnels through thin walls — the classic. Check at sub-obstacle resolution.
- **Narrow passages** starve uniform sampling; success rate falls off a cliff with passage width.
- **No goal bias** → the tree explores beautifully and arrives eventually-ish; too much (>20%) → greedy stabbing at the goal that gets trapped behind obstacles the way plain gradient descent does.
- **Trusting one run**: RRT output is a random variable. Benchmarks report distributions over seeds — so should you (the library's test suite runs multiple seeds for exactly this reason).

## I. Questions

1. *(Concept)* Explain Voronoi bias: why does nearest-neighbor extension from *uniform* samples explore rather than clump?
2. *(Calculation)* A narrow passage occupies 0.1% of C-space volume. Roughly how many uniform samples before one lands inside, and what does that imply for a 10-second planning budget at 10⁴ samples/s?
3. *(Debugging)* Your RRT solves an easy scene but the paths oscillate wildly between runs, occasionally 3× longer. Which two mitigations, in what order?
4. *(System design)* Pick planners for: (a) a warehouse AMR replanning at 2 Hz on a 2-D costmap; (b) a 7-DOF arm doing one-off reaches; (c) the same arm doing thousands of picks in a *fixed* cell. Justify each.

??? note "Answer sketch for Q4"
    (a) grid/lattice A* — low-dim, needs consistency; (b) RRTConnect — high-dim single query; (c) PRM — amortize the roadmap over queries in the static cell.

### Interactive quiz

<quiz-bank src="planning-l3-rrt"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| LaValle & Kuffner, *"Randomized kinodynamic planning"* (2001) | paper | intermediate | RRT from the source; short and geometric |
| Karaman & Frazzoli (2011) | paper | advanced | RRT\*/PRM\* and the optimality theory |
| LaValle, *Planning Algorithms*, ch. 5 | book | intermediate | Sampling-based planning, comprehensively, free online |

## K. Graded work & portfolio extension

**Graded:** an RRT arm-planner over the Module 1 C-space checker is the planned Module 5 project.

**Portfolio:** animate the tree growing through the narrow-passage scene at three gap widths — sampling-based planning's whole character (and its famous weakness) in one GIF.
