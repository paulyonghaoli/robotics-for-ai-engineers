# Capstone engineering log: eight bugs and how they were found

Every algorithm in this curriculum was written to make the [capstone](modules/capstone/index.md) work. Along the way it broke — eight times, in ways worth studying. Each of these was found by **instrumentation, not guesswork**, and each turned out to be a textbook failure mode wearing a disguise.

This page exists because the debugging is the education. Anyone can follow a working derivation; the skill that gets you hired is recognizing a symptom and knowing which of five suspects to interrogate first.

---

## The method, before the bugs

Two habits did all the work:

**Isolate the layer under test.** When the particle-filter stack failed (bugs 1–4), the first move was *not* to tune the filter — it was to let the known-good reference stack drive while the filter merely observed. That separates "the estimator is wrong" from "the controller is reacting to a wrong estimate," which are indistinguishable from the outside and have completely different fixes.

**Ask the model what it believes.** The decisive measurement in the localization campaign was evaluating the measurement likelihood *at the true pose* versus *at the filter's estimate*. When the estimate scored **higher** than the truth, the filter was working perfectly — and the model was lying to it. That reframed everything: stop debugging the filter, start debugging the likelihood.

---

## Capstone v1 — particle-filter lidar localization

### Bug 1: max-range miss leakage (the killer)

**Symptom:** localization drifting meters, up to 16 m in the worst episode. 0/8 episodes reached the goal.

**Cause:** the lidar returns `MAX_RANGE` when a beam hits nothing — but with range noise added, a genuine miss can read *just under* the cutoff. The code rejected misses at `MAX_RANGE − 1σ`, so noisy misses slipped through and were treated as **hits at ~6 m**, projecting phantom endpoints into open space. Those phantoms carried enormous likelihood penalties that dominated the entire scan.

**Why it was hard:** the filter wasn't under-informed — it was *actively misled*. More particles, more beams, and better tuning all made it worse, because they amplified a lying signal.

**Fix:** reject misses with a ≥ 4σ margin. One line. Tracking error went from meters to **4–10 cm** across every seed.

**The lesson generalizes:** this is [lesson 4.1's](modules/04-mapping/01-occupancy-grids.md) "phantom ring at max range" mapping bug, in localization clothing. A sensor's *failure to detect* is information with completely different semantics from a detection — conflate them at the noise boundary and you inject fiction.

### Bug 2: solid-obstacle likelihood flattening

**Symptom:** persistent residual error after bug 1, worse in maps with large box obstacles.

**Cause:** the likelihood field (distance-to-nearest-obstacle) was seeded on *all* occupied cells, so every cell **inside** a solid box had distance 0. A badly mislocalized particle whose scan endpoints landed deep inside an obstacle scored exactly as well as the truth.

**Fix:** seed the chamfer transform on obstacle **surface** cells only, so depth inside an obstacle costs likelihood.

**The lesson:** a cost function that assigns equal cost to "correct" and "absurd" isn't a weak signal — it's a *missing* one. Check that your objective actually separates the cases you care about.

### Bug 3: boundary-clip reward

**Symptom:** beliefs drifting toward map edges and corners.

**Cause:** scan endpoints projected outside the map were index-clipped onto border cells — which are wall surfaces, distance 0, i.e. **maximum likelihood**. Drifting toward the edge was being silently rewarded.

**Fix:** charge the out-of-bounds overshoot as distance.

**The lesson:** clipping is the most common way to accidentally create a reward. Any `clip`, `clamp`, or `min/max` on the boundary of a scoring function deserves the question *"what does this now make free?"*

### Bug 4: ignoring collision feedback

**Symptom:** one episode logged **499 collisions** — the robot pinned against a wall, pushing forever.

**Cause:** the stack propagated its *commanded* motion into the particle filter even when the simulator had blocked that motion. The belief marched confidently forward while the robot sat still; the controller, seeing a pose that had "passed" the obstacle, kept pushing.

**Fix:** on `collided`, propagate zero motion, discard the plan, and run a rotate-in-place recovery before replanning.

**The lesson:** an open-loop assumption hiding inside a closed-loop system. [Lesson 0.1's](modules/00-transition/01-what-changes.md) first broken assumption — *your outputs change your inputs* — punishes you specifically at the moment the world refuses your command.

---

## Capstone v2 — online mapping

### Bug 5: replanning thrash

**Symptom:** the robot reached 7 m from the goal, then **retreated**. Six of eight episodes timed out with zero collisions — it simply never arrived.

**Cause:** as the map grew, every periodic replan discovered a "shortcut" through still-unexplored space — space that concealed the very wall just mapped. Each replan looked locally rational; together they oscillated the robot between two routes indefinitely.

**Fix:** hysteresis. Keep the committed path unless it's genuinely blocked or the alternative is ≥25% shorter.

**The lesson:** [lesson 5.1](modules/05-planning/01-astar.md) predicts this verbatim in its failure modes — "replanning thrash… the robot dithers at decision points." Optimism about unknown space is what makes exploration work *and* what makes it oscillate; the fix is commitment, not better optimism.

### Bug 6: the mapped-crust seal

**Symptom:** one robot spent an entire 60-second episode rotating in place at its start position.

**Cause:** lidar endpoints land *just inside* obstacle surfaces, so an online-built map's walls are about one cell fatter than reality. Applying the same inflation radius as the known-map stacks, the robot's own map welded its starting pocket shut. It was, correctly, unable to find a path out of a room that didn't exist.

**Fix:** inflate the online map one cell less — the measurement crust already supplies that margin — plus a shave-the-skirt fallback when no path exists at all.

**The lesson:** safety margins **compose**. Every layer that pads for uncertainty (sensor model, mapping, inflation, controller) adds its own, and the total can quietly exceed the physical clearance. Audit margins end-to-end, not per-layer.

---

## Capstone v3 — moving obstacles

### Bug 7: the movers broke the localizer, not just the path

**Symptom:** switching on six moving obstacles, the v1 stack's localization RMSE jumped from **0.13 m to as much as 3.96 m** — while its planner behaved fine. The robot got lost, then failed.

**Cause:** the likelihood field encodes *the static map*. A beam that stops early on a moving obstacle produces an endpoint in what the map says is open space — which the filter reads as overwhelming evidence that the robot is somewhere else entirely. Six movers generate a steady stream of these, and they systematically drag the particle cloud off the truth.

**Fix:** reject beams whose endpoint lands far from anything the map knows about (> 0.75 m from any mapped surface). Those beams carry no information about the robot's pose.

**The lesson:** this is [lesson 4.2's](modules/04-mapping/02-scan-matching.md) **ICP outlier trimming**, wearing localization clothing. Any algorithm that matches sensor data against a static model needs a story for data that isn't static — and "a person walked through my scan" is the most common such story in the world.

### Bug 8: fixing the planner froze the robot (and how the fix's fix fell out for free)

**Symptom, part one:** the DWA local planner avoided obstacles where they *were*, and got hit anyway. An obstacle at 0.29 m/s walked into the robot 45 steps into an episode — 63 collisions in one run.

**Cause, part one:** DWA scores rollouts against scan points treated as a **static snapshot**. Over a 1-second horizon, a 0.5 m/s mover travels half a metre into the arc the planner just certified as clear.

**Fix, part one:** require a margin that *grows with rollout time* — by step k, an unseen mover could have closed `MAX_DYN_SPEED · k · Δt`. A cheap reachable-set hedge.

**Symptom, part two:** collisions went to zero — and two episodes now timed out with the robot **frozen in place**. I had produced [lesson 5.4's](modules/05-planning/04-local-planning.md) freezing-robot problem, on purpose, by accident.

**Cause, part two:** the growing margin was being applied to *every* scan point, including mapped walls. Walls do not move. In a corridor narrower than the inflated margin, no arc is admissible and the robot correctly concludes it cannot proceed.

**Fix, part two:** apply the time inflation **only to points the static map cannot explain** — and that classification already existed, computed for bug 7's beam rejection. One classification, two consumers with opposite policies:

| Beam type | Localizer | Local planner |
|---|---|---|
| Explained by the map | **Use it** — evidence about pose | Constant margin |
| Not explained by the map | **Ignore it** — not evidence about pose | **Time-inflated** margin |

Result: 18/18 episodes at six movers, 17/18 collision-free, localization RMSE holding at 0.06–0.12 m.

**The lesson:** the two hardest bugs in v3 were the *same question* asked by two subsystems — "is this sensor reading part of the world I modeled?" — and answering it once, well, served both. When a fix in one place induces a pathology in another, the usual cause is that a distinction the system needs hasn't been made explicit yet.

---

## What the eight have in common

Seven of the eight were **not** bugs in an algorithm. They were bugs in the *interface between* an algorithm and the world: what a sensor's non-detection means, what a clipped coordinate implies, what a blocked command did, how margins accumulate. The algorithms — particle filter, A*, pure pursuit, occupancy mapping, DWA — were textbook-correct throughout.

That ratio matches professional experience and it's why this curriculum weights conventions, failure modes, and diagnostic labs as heavily as derivations. It's also why the [frontier research](frontier.md) finds the field's bottleneck in data and evaluation rather than architecture: at every scale, the hard part is the seam between a correct component and a world that doesn't match its assumptions.

**Practice this:** the [frame-debugging gauntlet](modules/01-geometry/06-lab-frame-debugging.md) and [catching a lying filter](modules/03-estimation/06-consistency-lab.md) hand you working-looking code with these same classes of bug inside, and grade you on finding them.
