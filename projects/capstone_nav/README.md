# Capstone: Autonomous 2D Mobile Robot

The integrated system everything in Courses I–II builds toward. A differential-drive robot must reach randomized goals in randomized obstacle worlds, judged the way real autonomy stacks are judged — by scenario metrics, not vibes.

## Running

```bash
cd projects/capstone_nav
python -m eval run --episodes 8              # evaluate reference_stack
python -m eval run --stack my_stack          # evaluate your own module
```

A stack is any module exposing `make_stack(sim) -> object with .step(obs) -> (v, w)`. Observations: noisy pose, 36-ray lidar scan, goal, collision flag. Ground truth never leaves the simulator — the harness reads it only for scoring.

## Rubric (v0)

| Metric | Threshold |
|---|---|
| Success rate | ≥ 0.85 |
| Collision-free episodes | ≥ 0.85 |
| Mean path ratio (executed / A* optimal) | ≤ 1.6 |
| p95 control-step latency | ≤ 50 ms |

The [reference stack](reference_stack.py) (A* on the inflated known map + pure pursuit on the noisy pose sensor) passes 20/20 episodes — proof the rubric is achievable and the harness honest.

## Roadmap to the full capstone

| Stage | Adds | Uses |
|---|---|---|
| v0 ✅ | Known map, noisy pose sensor, static obstacles ([reference_stack.py](reference_stack.py)) | `astar` + `inflate_grid` + `pure_pursuit` |
| **v1 ✅** | **Particle-filter lidar localization** ([pf_stack.py](pf_stack.py)): pose sensor used only to seed the initial belief; 6–11 cm RMSE, 20/20 episodes | likelihood field, `robotics_ai` estimation/planning/control |
| **v2 ✅** | **Unknown map** ([mapping_stack.py](mapping_stack.py)): blank log-odds grid built online from scans, optimistic planning through unexplored space, replanning with hysteresis; 20/20 episodes, no `sim.grid` access | `robotics_ai.mapping`, Module 4 |
| **v3 ✅** | **Moving obstacles that are not in the map** ([dynamic_stack.py](dynamic_stack.py)): DWA local planner over the global path + dynamic-beam rejection in the localizer. 10/10 and 8/8 episodes at 6 movers | Modules 4–5 |
| v4 | SLAM (unknown map AND pose simultaneously); ROS 2 packaging; bag logging | Modules 4, 6 |

### v3's operating envelope (measured, not assumed)

| Movers | Success | Collision-free |
|---:|---|---|
| 0 | 20/20 | 20/20 |
| 6 | 18/18 | 17/18 |
| **10** | **6/6** | **3/6** |

At 10 movers in a 20 × 20 m world the stack still reaches every goal but stops being collision-free. Worth stating plainly rather than tuning until the number looks good: these obstacles are **non-cooperative** — they walk straight through the robot and never yield, which real people don't. At high density, contact becomes unavoidable for a robot that is the only one avoiding. The honest claim is "6 movers, non-cooperative"; anything beyond that is outside what was tested.

Baseline for comparison — the v1 stack in the same 6-mover worlds: **5/6 success, 5/6 collision-free, and localization RMSE degrading from 0.13 m to as much as 3.96 m.**

Each stage keeps the same evaluation contract, so your metrics are comparable across the whole climb.

## Field notes from building v1 (read these — they're the curriculum)

Four textbook failure modes were found and fixed while making `pf_stack` pass, each traced by instrumentation rather than guesswork:

1. **Max-range miss leakage.** A miss with range noise below a tight cutoff (`MAX_RANGE − 1σ`) masquerades as a hit at ~6 m; its phantom endpoint in open space carries a catastrophic penalty that dominates the whole scan and *actively misleads* the filter (meters of drift). Fix: reject misses with a ≥ 4σ margin. This is lesson 4.1's "phantom ring at max range" bug, wearing a localization costume.
2. **Solid-obstacle likelihood flattening.** A distance field seeded on *all* occupied cells gives depth 0 everywhere inside solid boxes, so mislocalized particles pushing endpoints deep into obstacles score like the truth. Seed the transform on obstacle *surface* cells so depth costs likelihood.
3. **Boundary-clip reward.** Endpoints projected past the map edge, index-clipped onto border-wall cells (distance 0), made drifting toward the map edge free — the belief got sucked into corners. Fix: charge the out-of-bounds overshoot as distance.
4. **Ignoring collision feedback.** Propagating commanded motion that the world blocked decouples belief from reality: the estimate marches on while the robot stays pinned, and the controller pushes into the wall forever. Fix: on `collided`, propagate zero motion, replan, and run a rotate-in-place recovery.

And two more from v2 (online mapping):

5. **Replanning thrash.** As the map grows, every periodic replan offers a "shortcut" through unexplored space that hides the wall just discovered — the robot oscillates between routes, reaching 7 m from the goal and then *retreating*. Fix: hysteresis — keep the committed path unless it's actually blocked or the alternative is ≥ 25% shorter. (Lesson 5.1 called this one in advance.)
6. **The mapped-crust seal.** Ray endpoints land just inside obstacle surfaces, so the online map's walls are ~1 cell fatter than reality; with full inflation, narrow-but-legal passages weld shut — one robot spent an entire episode rotating inside a start pocket its own map had sealed. Fix: inflate the online map one cell less (the crust supplies the missing margin), with a shave-the-skirt fallback when no path exists.
