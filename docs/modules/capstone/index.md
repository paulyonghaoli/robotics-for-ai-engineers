# Capstone · Autonomous 2D Mobile Robot

**Status:** v0–v3 live and passing the rubric — at `projects/capstone_nav/` (`python -m eval run --stack ...`). v4 (simultaneous SLAM, ROS 2 packaging) is planned.

<div markdown class="grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:0.8rem;margin:1.2rem 0;">
<figure markdown style="margin:0">
![Global localization](../../assets/demo/capstone-global-localization.gif){ width="100%" }
<figcaption markdown>**Global localization** — 8,000 particles from a uniform prior collapsing to 0.2 m</figcaption>
</figure>
<figure markdown style="margin:0">
![Online mapping](../../assets/demo/capstone-v2-mapping.gif){ width="100%" }
<figcaption markdown>**v2** — the world is unknown; the map is carved out by lidar while driving</figcaption>
</figure>
<figure markdown style="margin:0">
![Dynamic obstacles](../../assets/demo/capstone-v3-dynamic.gif){ width="100%" }
<figcaption markdown>**v3** — six movers that aren't in the map, avoided by DWA</figcaption>
</figure>
</div>

These are rendered from **real evaluation episodes** (`python render.py all`) — the same code path `python -m eval run` scores. Whatever the robot does here is what it does when it's being graded.

| Stack | What it assumes | Result |
|---|---|---|
| **v0** `reference_stack` | Known map, noisy pose sensor | 20/20 episodes |
| **v1** `pf_stack` | Known map; **localizes from lidar** (pose sensor only seeds the belief) | 20/20, 6–11 cm RMSE |
| **v2** `mapping_stack` | **Nothing but the goal** — builds the map online from scans | 20/20 |
| **v3** `dynamic_stack` | Six **moving obstacles that are not in the map** — DWA local planning + dynamic-beam rejection | 18/18, 17/18 collision-free |

Each stage keeps the same evaluation contract, so the metrics are comparable across the whole climb:

```bash
python -m eval run --episodes 8 --stack dynamic_stack --dynamic 6
```

**v3's envelope, measured:** at 6 movers it is 18/18; at **10 movers it still reaches every goal but is collision-free only half the time.** That boundary is published rather than tuned away — and it's partly an artifact worth naming: these obstacles are non-cooperative, walking straight through the robot in a way real people don't.

Read the [engineering log](../../capstone-log.md) for the eight debugging campaigns behind those numbers, and [lesson 10.1](../10-evaluation/01-statistical-rigor.md) for what "18/18" does and does not entitle you to claim.

Everything in v0.1 integrates here: a simulated differential-drive robot with noisy wheel odometry and a range sensor, running

- particle-filter **localization** (Module 3)
- occupancy-grid **mapping**
- A* **global planning** and trajectory following with **PID control** (Module 5)
- packaged as **ROS 2 nodes** with TF, launch files, and bag logging (Module 6)

## Evaluation

The capstone is judged the way a real autonomy stack is judged — quantitatively:

| Metric | Definition |
|---|---|
| Goal success rate | fraction of runs reaching the goal within tolerance |
| Collision rate | collisions per run across randomized worlds |
| Localization RMSE | estimated vs ground-truth pose |
| Planning time | per-replan latency |
| Control error | cross-track error along the executed trajectory |
| End-to-end latency | sensor timestamp → actuation command |

Deliverables: architecture diagram, results table, failure analysis, demo video, reproducible Docker environment.
