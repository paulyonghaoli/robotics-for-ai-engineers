# Pose Graphs and Loop Closure: How a Lost Robot Fixes Its Own Map

*A source document for a video explainer. Companion to lesson 4.4 of "Robotics for AI Engineers". Every number below is measured, not illustrative.*

---

## The one sentence to remember

**SLAM is a least-squares problem with a graph-shaped loss** — and when a robot recognises a place it has been before, the correction does not get applied at that spot. It gets spread backwards across the entire journey.

That second half is the part people get wrong, and it is the part worth building the whole explanation around.

---

## 1. The problem: every robot is slowly lying to itself

A robot estimates where it is by adding up small movements. Wheel encoders say "you went forward 0.5 metres and turned 3 degrees", and the robot adds that to where it thought it was.

Each of those measurements is slightly wrong. That is fine. The problem is that the errors **accumulate**, because each new position is built on top of the last one. There is no step at which the robot gets told the truth, so a small consistent bias — a wheel slightly worn, a gyroscope reading a fraction of a degree high — compounds into metres.

And here is the cruel part: **the robot cannot detect this by looking harder at its sensors.** If the wheel is under-reporting by 2% every single step, then every measurement is self-consistent. The robot's map and the robot's position are wrong *together*, in perfect agreement. Nothing looks broken from the inside.

The only way out is to recognise a place you have already been, and notice that you have drawn it in two different spots.

**Visual beat:** a robot driving a loop around a building, its estimated path drawn in blue drifting steadily away from the true path in grey. When it returns to the start, the blue path ends metres away from where it began — a loop that visibly fails to close.

---

## 2. The reframe: stop maintaining a belief, start keeping a history

Earlier SLAM systems maintained one big probability distribution over the robot's position and every landmark, updated continuously. That works, and it hits a wall: the bookkeeping grows with the square of the number of landmarks, because everything becomes correlated with everything.

The modern approach throws that out and keeps something simpler: **the history**.

- Every past position the robot occupied is a **node**.
- Every measurement relating two positions is an **edge**.

That is the whole data structure. And once you have it, finding the best trajectory is an optimisation problem: *choose the positions for all the nodes that make all the edges as happy as possible.*

For anyone who has trained a model, this is a familiar object. It is a loss function. It is a sum over terms. Each term is a squared error. You minimise it. The only unusual feature is that the loss has a graph shape — each term touches exactly two nodes — which makes it extremely **sparse**, and sparse least squares scales to millions of terms.

---

## 3. Two kinds of edge

**Odometry edges** connect consecutive positions. "Node 5 is about 0.5 metres ahead of node 4." Short, plentiful, individually reliable, and collectively the source of all the drift, because their errors add up along the chain.

**Loop-closure edges** connect two positions that are far apart *in time* but close together *in space*. The robot looks at what its laser scanner sees now, compares it against what it recorded twenty minutes ago, and concludes: this is the same doorway. That single edge reaches across the entire chain and says "these two nodes are actually almost on top of each other."

**Visual beat:** the trajectory as a chain of beads connected by short springs. Then one long spring is drawn from the last bead back to the first. Everything is about what happens when you let go.

---

## 4. The springs picture

Think of every edge as a spring with a natural length equal to what it measured.

The odometry springs are each slightly the wrong length, so the chain settles into a crooked arc. Then you attach the loop-closure spring between the two ends — and it is badly stretched, because odometry has walked the end of the chain metres away from where the loop closure says it should be.

Now let go of everything at once.

The chain does not snap at one point. **Every spring gives a little**, until the system reaches the arrangement that leaves the total stored energy as low as possible. The final shape is a compromise in which every edge is slightly unhappy and none is catastrophically so.

That is exactly what least squares computes. The springs are a physical picture of the same arithmetic.

---

## 5. The number that explains everything

Here is the smallest possible version, and it is worth walking through slowly because it contains the entire idea.

A robot moves along a straight line. It records four positions: node 0, 1, 2, 3.

- Odometry says each step was exactly **1.0 metres**. So odometry believes node 3 sits at **3.0**.
- Then a loop closure fires and says: node 3 is actually **2.4** metres from node 0.
- Node 0 is pinned at zero — we will come back to why.

Odometry says 3.0. The loop closure says 2.4. **Where does least squares put node 3?**

Almost everyone guesses 2.4 — the loop closure is the new information, so surely it wins. That is wrong.

The answer is **2.55**.

And the other nodes moved too. Solving the least-squares problem gives:

| | position |
|---|---|
| node 0 | 0.00 (pinned) |
| node 1 | **0.85** |
| node 2 | **1.70** |
| node 3 | **2.55** |

Look at the gaps between consecutive nodes: 0.85, 0.85, 0.85. Every odometry step shrank by exactly the same amount.

**Why?** There were four edges in disagreement: three odometry edges and one loop closure, all trusted equally. The total disagreement was 0.6 metres. The optimiser split it into four equal parts of 0.15 — each odometry edge gives up 0.15, and the loop-closure edge *also* accepts being wrong by 0.15 (2.55 instead of the 2.4 it claimed).

Nobody wins. Everybody compromises equally. That is what "least squares" means when you write it out.

**Visual beat:** an animation of the four nodes. First the odometry positions at 0, 1, 2, 3. Then the loop-closure constraint appears as an arrow pulling node 3 leftward. Then all four nodes slide simultaneously to 0, 0.85, 1.70, 2.55 — and crucially, node 1 and node 2 move even though nobody measured anything about them directly.

---

## 6. Why the whole trajectory moves

This is the conceptual centre of the lesson.

The loop closure is a statement about nodes 0 and 3. It says nothing whatsoever about nodes 1 and 2. So why did they move?

Because they are **connected**. Node 1 is tied to node 0 and node 2 by springs. If node 3 moves left and node 1 stays put, the springs between them get stretched, and stretched springs cost energy. The cheapest total arrangement moves everyone a little.

The practical consequence is enormous. The correction is not a patch applied at the moment of recognition — it is a **rewrite of history**. Every position the robot recorded during the entire loop gets adjusted. And because the map is drawn from those positions, redrawing the map from the corrected trajectory is what makes a smeared, doubled, ghostly floor plan snap into clean single walls.

**Visual beat:** a blurry map with every wall drawn twice, slightly offset. The optimisation runs. The doubled walls slide together into single crisp lines. This is the money shot of the entire video.

---

## 7. Stiffness is confidence

Not all measurements deserve equal trust, and the framework has a dial for this: each edge carries a weight — formally an *information matrix*, usually written omega — that says how stiff its spring is.

Take the same four-node example and make the loop-closure edge 100 times more confident than the odometry edges. Now:

| | equal weights | loop edge 100× stiffer |
|---|---|---|
| node 3 lands at | 2.550 | **2.402** |
| each odometry gap | 0.850 | 0.801 |

With a very stiff loop closure, the answer moves almost all the way to 2.4 — the loop closure's claim — and the odometry edges absorb nearly all of the compromise.

So the weights decide who yields. This should feel familiar: it is **weighted loss**, exactly as in any model where some examples are trusted more than others. Robotics arrived at it from measurement uncertainty rather than from class imbalance, but it is the same mathematics.

---

## 8. Why one node must be nailed down

There is a subtlety that trips up everyone building their first pose graph.

Every edge in the graph is a statement about a *relative* relationship: this node is 1.0 metres from that node. Nothing anywhere says where the whole structure sits in the world.

Which means you can pick up the entire optimised trajectory, slide it three metres north, rotate it forty degrees, and **every single constraint is still satisfied exactly as well**. The loss is completely indifferent.

That freedom is called the **gauge**, and if you leave it in, the optimiser is being asked to choose among infinitely many equally good answers. In practice, the equations become singular and the solver fails — the first pose-graph rite of passage is an inscrutable linear algebra error.

The fix is one line: pin the first node. Declare that node 0 is the origin, by definition, and let everything else be measured relative to it. In the worked example above, that is why node 0 stayed at exactly zero while everything else moved.

Note that this is not extra information — it is a *choice of coordinate system*. The robot never learns where it is in any absolute sense, and it does not need to.

---

## 9. The dangerous half: who proposes the edges

The system splits cleanly in two.

The **front end** decides which edges exist. It processes sensor data and proposes: "I believe this scan matches the one from twenty minutes ago." This is a recognition problem.

The **back end** is the optimisation described above. It takes the proposed edges as given and finds the trajectory that best satisfies them.

The back end is well-behaved mathematics. **The front end is where the catastrophes live.**

If the front end proposes a *wrong* loop closure — claiming the robot is back at a doorway when it is really at a different, similar-looking doorway — the back end will faithfully do exactly what it is designed to do: warp the entire trajectory to satisfy that constraint. One confident lie folds the map like bad origami, and it destroys not just the current position but the whole recorded history.

Warehouses are notorious for this. Every aisle looks like every other aisle.

The defences are worth naming, because they map onto things ML engineers already do:
- Be conservative about proposing closures at all.
- Verify geometrically before accepting: does the match actually align, or is it merely plausible?
- Use robust loss functions — Huber and relatives — so a single wildly inconsistent edge gets down-weighted instead of dominating.

That last one is precisely the outlier-robust-loss instinct, applied to maps.

---

## 10. What it looks like when it works

These figures come from a working implementation, checked by unit tests against a case whose correct answer is known by construction.

The setup: a robot walks a closed octagonal circuit, eight positions. A constant rotational bias of 0.05 radians is added to every single step — the kind of systematic error a slightly miscalibrated gyroscope produces.

- **Before closure:** the final position lands **1.103 metres** from where it should be. The loop visibly fails to close.
- **Add one loop-closure edge and optimise.** The final position lands **0.000 metres** from truth.
- And the correction is genuinely distributed: the *worst* error at *any* node anywhere on the trajectory is **0.017 metres** — under two centimetres.

That last figure is the one that proves the point. If the optimiser had simply snapped the last node into place, the final error would be zero and the middle of the trajectory would still be bent. Instead the entire loop is correct to within centimetres.

---

## 11. The catch that almost nobody mentions

Here is a result from actually trying this on a working robot navigation system, and it is the most useful thing in this document.

The loop-closure machinery was built, tested, and verified. Then it was run on a real navigation task — and it did **nothing at all**. Error before: 2.31 metres. Error after: 2.28 metres.

The instinct is to tune the recognition system. The right move was to ask whether there was anything to recognise. So the trajectories were measured directly: how many times does the robot pass within 1.5 metres of somewhere it was more than six seconds ago?

Across six independent test runs, that count was: **zero, zero, zero, zero, zero, zero.**

**Be precise about what was zero, because it is easy to get this backwards.** The detector was not idle — it fired six times across those six runs. What was zero is the number of *genuine revisits available to find*. The robot never went back anywhere, so every one of those six was a spurious match between two nearby-but-different places, and the error did not move. "No opportunities existed" is the finding. "The software never ran" is not, and would be wrong.

The task was to drive from a start point to a goal. A single traverse. **A robot that drives from A to B never returns anywhere it has been**, so there is no loop, and loop closure has nothing to close. No amount of work on the algorithm would have changed that.

### And then the other half, which must not be left out

It would be completely wrong to conclude that loop closure does not work. Give the same robot a there-and-back tour — drive to the goal, then drive home, which is what a proper SLAM benchmark does — and the trajectory revisits everything. Run the identical code:

| | error before | error after |
|---|---|---|
| runs where a loop exists (four of six) | 2.23 m | **1.37 m** — a 39% reduction |
| runs where no loop exists (two of six) | 8.45 m | 8.44 m — unchanged |

**39% of the remaining error, removed by the same software that did nothing on the other task.** Not because the code changed, but because the robot's path changed.

The two runs where it still did nothing failed for two measurable reasons: one environment was too open, so a laser scan returns mostly empty space and there is not enough geometry to identify a place at all; the other ran out of time before completing the return trip.

**The lesson: loop closure is a property of the trajectory and the environment, not a property of the algorithm.** It is a capability that only pays out when the robot's actual behaviour gives it something to work with — and when it does pay out, it pays well. Knowing which situation you are in, in advance, is worth more than any amount of tuning.

---

## 12. What to take away

1. **SLAM is optimisation.** Nodes are positions, edges are measurements, the loss is a sum of squared disagreements, and the graph shape makes it sparse enough to scale.
2. **A loop closure rewrites history.** The correction spreads across every node in the loop, in proportion to how much each edge is trusted. It is not a patch at the closing point.
3. **The compromise is the answer.** With equal trust, odometry saying 3.0 and a loop closure saying 2.4 produce 2.55 — not either claim.
4. **Weights decide who yields**, and they are the same idea as weighted loss.
5. **Pin one node**, or the problem has infinitely many answers and the solver will tell you so rudely.
6. **The optimiser is safe; the recogniser is dangerous.** A confident false loop closure destroys the whole map, which is why robust losses exist.
7. **None of it pays out if the robot never goes back** — and where the robot does go back, it removes 39% of the error. Both halves are the finding; either one alone is misleading.

---

## Suggested visual sequence for the video

1. Blue estimated path drifting from grey truth around a loop; the loop fails to close by metres.
2. The trajectory redrawn as beads on springs.
3. The four-node number line: 0, 1, 2, 3 → 0, 0.85, 1.70, 2.55, with all nodes sliding at once.
4. The same animation with a stiff loop spring: nodes land at 0, 0.80, 1.60, 2.40.
5. A doubled, ghosted floor plan snapping into single clean walls.
6. The gauge: the entire optimised trajectory sliding and rotating freely, with all constraints still satisfied — then a pin dropping onto node 0.
7. A false loop closure between two identical warehouse aisles, and the map folding.
8. The octagon: 1.103 m open, then closed to 0.000 m with worst-node error 0.017 m.
9. A single A-to-B traverse with a large "0 revisits" overlay, next to a there-and-back tour with the loop highlighted.
