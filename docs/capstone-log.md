# Capstone engineering log: thirteen bugs and how they were found

Every algorithm in this curriculum was written to make the [capstone](modules/capstone/index.md) work. Along the way it broke — thirteen times, in ways worth studying. Each of these was found by **instrumentation, not guesswork**, and each turned out to be a textbook failure mode wearing a disguise.

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

## Capstone v4 — SLAM: no map *and* no pose

v4 keeps v2's navigation verbatim and replaces exactly one thing: the pose sensor becomes an estimate the stack has to earn. It reads `pose_meas` once, to choose where the map's origin is, and never again.

The first end-to-end run scored **0/4 with 3–13 m of error**. Per the method above, the first move was not to tune anything — it was to cut the feedback loop: let the reference controller drive on the true pose, and run the localizer alongside as a pure observer. That harness is `projects/capstone_nav/slam_ablation.py`, and every number below is reproducible from it.

The first thing it printed was humbling:

| localizer | RMSE | worst seed |
|---|---:|---:|
| dead reckoning, no map lookups at all | **0.52 m** | 0.91 |
| scan matching every step | 6.11 m | 9.98 |
| ...scoring occupied evidence only | 29.09 m | 46.76 |

### Bug 9: matching too often is worse than not matching

**Symptom:** every scan-matching variant was 10–50× worse than using no map at all.

**Cause:** 36 beams on a 0.2 m grid is not enough evidence to correct a pose at 10 Hz. Each match injects its own noise into the pose, the scan is then integrated into the map *at that noisy pose*, and the next match scores against the corrupted map. The error has a path back to its own cause.

**Fix:** match at keyframes — every 0.20 m or 0.12 rad — so each correction has enough baseline to be well-posed. And give map updates a *separate*, slower threshold (0.35 m / 0.25 rad): correcting the pose and rewriting the map are different decisions, and mapping on every correction blurs the geometry the matcher depends on. Splitting the two thresholds alone moved success 0.50 → 0.75.

**The lesson:** sensor fusion has a rate at which it stops helping. "Use every measurement" is not free when the measurement's information is smaller than the noise of using it.

### Bug 10: occupied-only scoring, or how I deleted the restoring force

**Symptom:** scoring only occupied cells — which I was confident was the fix — was the *worst* configuration measured, at 29 m.

**Cause:** with free space penalized, a pose that slides its endpoints into known-empty space pays for it. Score only occupancy and free and unknown are both exactly zero: a flat plateau with nothing pushing back, so the pose slides until endpoints happen to pile onto a wall.

**Fix:** score against a **likelihood field** (the distance transform v1 used, now built from the map so far). Unexplored space is *far* from every mapped surface, so it scores badly rather than scoring zero. There is no plateau to slide along.

**The lesson:** when you remove a term because it seems unprincipled, check what it was holding up. The free-space penalty looked like an implementation detail and was the only thing making the objective well-posed.

### Bug 11: boundary-clip reward — the *same* bug as v1's bug 3

**Symptom:** match confidence held at **0.87–0.99 while true error grew monotonically to 14 m**. The matcher was not lost. It was certain, and wrong.

**Cause:** `np.clip` on the endpoint cell indices. The world's boundary ring is solid wall, so every endpoint projected outside the grid was clamped onto a wall surface at distance 0 — maximum likelihood. Drifting out of the world was being paid for.

**Fix:** carry an `inside` mask and score out-of-bounds endpoints as zero evidence. Never clamp.

**The lesson:** I wrote bug 3's lesson — *any `clip`, `clamp`, or `min/max` on the boundary of a scoring function deserves the question "what does this now make free?"* — and then committed the same bug again, in a different file, three stacks later. Knowing a failure mode is not the same as having a habit that catches it. It is also why the confidence trace was the decisive measurement: **high confidence alongside growing error is a signature, and it always means the model is being scored on something it shouldn't be.**

### Bug 12: the argmax of a flat score is not "stay put"

**Symptom:** an uninformative match displaced the pose diagonally instead of leaving it alone.

**Cause:** when every beam gates out, the score array is all zeros and `np.argmax` returns index 0 — the most-negative corner of the search window. Ties do not resolve to the identity; they resolve to whatever the loop built first.

**Fix:** maximize a **posterior**, not the scan likelihood: add an odometry prior penalizing displacement from the incoming guess. Now a scan with nothing to say leaves the pose where odometry put it, which is the correct answer.

**The lesson:** the same lesson as the Kalman filter, arrived at by stepping on it. An estimator with no prior has no defined behaviour when the measurement is uninformative — and "uninformative" is a case that *will* occur.

### Bug 13: the robot that froze because it had stopped

**Symptom:** two seeds parked and sat motionless for 300 steps, believing they had arrived, ~0.7 m from the true goal.

**Cause:** keyframes triggered on *predicted* motion. On arrival the stack commands zero, so dead reckoning predicts no motion, so no keyframe ever fires, so the pose is never corrected again. The robot could not discover it had stopped in the wrong place, because stopping is what disabled the discovery.

**Fix:** trigger keyframes on elapsed time as well as motion.

**The lesson:** any trigger conditioned on the system's own activity has a fixed point at "inactive." Watchdogs, health checks and drift monitors all share this shape — the state you most need to detect is often the one that stops the detector.

### Where v4 lands, and why it stops there

| | success | collision-free | path ratio | loc RMSE |
|---|---:|---:|---:|---:|
| v2 — given a pose sensor | 1.000 | 1.000 | 0.94 | 0.14 m |
| **v4 — SLAM, 24 episodes** | **0.750** | **0.792** | **0.982** | **0.387 m** |

Giving up the pose sensor costs a quarter of the episodes, and the arithmetic is not subtle: drift is 0.39 m against a **0.5 m goal tolerance**, so a quarter of runs park just outside it believing they arrived. v4 is therefore scored against its own published envelope (`--rubric slam`) rather than the bar written for stacks that were handed a map or a pose. Judging it by that bar is a category error; quietly relaxing the bar for everyone would have been worse.

The remaining gap does **not** close by tuning, and the ablation says so directly. Give the odometry a realistic *systematic* error — a wheel-scale factor and a gyro drift, constant per episode, instead of pure white noise:

| | RMSE | spread across seeds |
|---|---:|---|
| dead reckoning | 3.26 m | 0.37 – **8.56** |
| v4's scan matching | 2.31 m | 0.47 – 6.30 |

Scan matching **bounds** drift; it does not remove it. A constant bias is invisible to incremental matching, because detecting it means recognising a place you mapped *before* you drifted — the map and the pose are wrong together and perfectly self-consistent, which is precisely what bug 11's confidence trace was showing. Removing it needs loop closure and a pose graph ([lesson 4.4](modules/04-mapping/04-pose-graphs.md)).

So I built one. It did not become v5, and the reason is worth more than the code.

## Note 14 — the loop closure that had no loop to close

The back end works. `projects/capstone_nav/posegraph.py` is scan-to-scan matching, a Gauss-Newton pose graph on SE(2) with the first keyframe pinned as the gauge, and a map rebuilt from the optimised poses. Against a graph whose answer is known by construction — an octagon walked with a 0.05 rad per-edge bias, which opens the loop by 1.10 m — one closure brings the final node to **0.000 m** and the worst node anywhere on the trajectory to 0.017 m. Those are unit tests, not a demo.

Then I ran it on the capstone and it changed nothing: 2.31 m → 2.28 m, six closures across six seeds.

The instinct is to tune the detector. The right move was to ask whether there was anything to detect, so I counted revisits directly — pairs of points on the true trajectory more than six seconds apart and closer than 1.5 m:

| seed | 0 | 17 | 34 | 51 | 68 | 85 |
|---|---:|---:|---:|---:|---:|---:|
| revisit pairs | **0** | **0** | **0** | **0** | **0** | **0** |

Zero. Every one. **The capstone task is a single traverse from a start to a goal, and a single traverse never returns to anywhere it has been.** There is no loop, so there is nothing for loop closure to do, and no amount of work on the detector would have changed that. An hour of tuning would have produced a slightly different zero.

Loop closure is a property of the **trajectory**, not of the algorithm.

### What it is worth when there is a loop

Give the robot a there-and-back tour — drive to the goal, then home, which is what a SLAM benchmark actually drives — and the trajectory revisits everything. Same localizer, same bias, `slam_ablation.py lc+bias+tour`:

| | RMSE | final error |
|---|---:|---:|
| dead reckoning | 5.34 m | 9.14 m |
| v4 scan matching | 4.31 m | 7.92 m |
| **+ loop closure and pose graph** | **3.73 m** | **4.83 m** |

And the aggregate hides the actual result. Two of the six seeds cannot close a loop even on a tour, for two different measured reasons — and separating them is the whole story:

| | v4 | + loop closure | |
|---|---:|---:|---|
| seeds 0, 34, 68, 85 | 2.23 m | **1.37 m** | **39% better** |
| seeds 17, 51 | 8.45 m | 8.44 m | unchanged |

Seed 17's world is open, so most beams are max-range misses and a keyframe carries fewer than fourteen usable points — **there is not enough geometry to identify a place**, and the matcher correctly refuses rather than closing confidently on six points. Seed 51's tour ran out of steps before completing the return leg, leaving four revisit pairs in the whole episode.

So the honest summary is: where a loop exists and the environment has structure, closure removes 39% of the error the front end could not touch; where either is missing, it does exactly nothing and says so. Both halves are the result.

### Why there is no v5 stack

Making this a shipped capstone version would mean changing the task from "reach the goal" to "tour and return", which means a new simulator termination contract and a new rubric for every earlier version to be re-scored against. That is a different capstone, not a fifth version of this one — and inventing a task to justify a technique I had already written is the wrong order to do engineering in.

The back end, its unit tests and the ablation evidence stay in the repository, and the capstone stays a four-version stack whose published envelope is honest about what bounds its drift.

---

## What the thirteen bugs have in common

(Note 14 is not one of them — it is a negative result, and the only entry here that cost nothing to fix because there was nothing to fix.)

Eleven of the thirteen were **not** bugs in an algorithm. They were bugs in the *interface between* an algorithm and the world: what a sensor's non-detection means, what a clipped coordinate implies, what a blocked command did, how margins accumulate. The algorithms — particle filter, A*, pure pursuit, occupancy mapping, DWA — were textbook-correct throughout.

One of them I had already found, documented, and written a lesson about — then committed again three stacks later. That ratio matches professional experience and it's why this curriculum weights conventions, failure modes, and diagnostic labs as heavily as derivations. It's also why the [frontier research](frontier.md) finds the field's bottleneck in data and evaluation rather than architecture: at every scale, the hard part is the seam between a correct component and a world that doesn't match its assumptions.

**Practice this:** the [frame-debugging gauntlet](modules/01-geometry/06-lab-frame-debugging.md) and [catching a lying filter](modules/03-estimation/06-consistency-lab.md) hand you working-looking code with these same classes of bug inside, and grade you on finding them.
