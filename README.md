# Robotics for AI Engineers

I'm a data and ML engineer teaching myself robotics. What I couldn't find was material pitched at someone who already writes Python and is comfortable with Bayesian inference, but has genuinely never had to think about coordinate frames — the tutorials assumed either much less or much more. So I started writing the thing I wanted to read, and kept going until it became this.

**These are my study notes, made rigorous enough to trust and public in case you're on the same path.** If you're an ML, data, or backend engineer who keeps almost-learning robotics, this was written for you.

**📍 [Read it here](https://robotics-for-ai-engineers.paullimale.workers.dev)** — free, no signup, code runs in the browser.

---

## The thing I built to prove I'd understood it

A differential-drive robot navigating randomized worlds. Four versions, each one removing an assumption the last one leaned on. These GIFs come from real evaluation runs — the same code path that scores it.

| Localizing with no idea where it is | Building the map while driving | Avoiding things that aren't on the map |
|---|---|---|
| ![global localization](docs/assets/demo/capstone-global-localization.gif) | ![online mapping](docs/assets/demo/capstone-v2-mapping.gif) | ![dynamic obstacles](docs/assets/demo/capstone-v3-dynamic.gif) |
| 8,000 particles from a uniform prior → 0.2 m | unknown world, carved out by lidar | 6 movers that never yield |

| Version | What it's allowed to assume | How it scored |
|---|---|---|
| v0 | Known map, noisy pose sensor | 20/20 episodes |
| v1 | Known map; localizes from lidar alone | 20/20, 6–11 cm error |
| v2 | Only the goal — builds its own map | 20/20 |
| v3 | Six moving obstacles, not on the map | 18/18, 17/18 collision-free |

The [engineering log](docs/capstone-log.md) is the part I'd actually recommend reading: eight ways this broke, what each one looked like from the outside, and how it was found. Most were not algorithm bugs — they were bad assumptions about what a sensor reading *meant*.

## Why it's built the way it is

Self-teaching has one big failure mode: you read something, nod, and walk away believing you understood it. Everything structural here is a defense against that.

- **The code runs in the browser** (real CPython via Pyodide), so you write it instead of reading it.
- **The autograders randomize their scenarios**, so a solution tuned to one case fails the next — I built these because I kept catching myself pattern-matching instead of understanding.
- **The robot is scored against a published rubric** across many randomized worlds. "It worked when I ran it" is not a result, and holding myself to that changed what I learned.
- **Where things stop working is published too.** The v3 stack handles six moving obstacles; at ten it still reaches every goal but only stays collision-free half the time. That boundary is in the docs rather than tuned away.
- **Failures are written down.** The debugging log exists because those were the moments I actually learned something, and they're the part every tutorial leaves out.

## What's here

- **33 lessons** — geometry, kinematics and control, state estimation, mapping and SLAM, planning. Each bridges to something you likely already know: Kalman filters as recursive Bayesian inference, costmaps as reward shaping, RRT as the same reason random search beats grid search in high dimensions.
- **49 coding exercises** you complete in the browser. Every reference solution is executed against its own tests in CI, so a lab that doesn't work can't ship.
- **Diagnostic labs** where you get working-looking code with a real bug in it and have to find it from the symptom alone: [frames](docs/modules/01-geometry/06-lab-frame-debugging.md), [filters](docs/modules/03-estimation/06-consistency-lab.md), [SLAM](docs/modules/04-mapping/05-lab-slam-failures.md), [planners](docs/modules/05-planning/06-lab-planner-pathologies.md).
- **[Where the field is going](docs/frontier.md)** — a researched snapshot of the 2026 robotics frontier, with every claim marked as verified, company-claimed, or single-source, because a lot of what's written about this space doesn't survive checking.

## Honest status

- **Courses I and II are complete** (geometry through planning). Course III — perception, manipulation, robot learning — is not written yet.
- **Simulation only.** Nothing here has touched real hardware, and the gap between the two is real.
- **I'm a learner, not an authority.** The code is tested; the *pedagogy* is one person's opinion about what makes these ideas click, and the framing of the field is my current understanding rather than an expert consensus. Where I've had to guess, I've tried to say so.
- **Written with AI assistance**, with every code path executed and tested in CI and every failure documented from actual debugging. I'd rather say that plainly than have you wonder.
- **The [frontier page](docs/frontier.md) is a dated snapshot** of a fast-moving area. Check the date before trusting it.

## Running it yourself

```bash
python -m venv .venv && .venv/Scripts/activate   # source .venv/bin/activate on Unix
pip install -e ".[dev,docs]"
python tools/verify.py        # runs every check CI runs
mkdocs serve                  # read the curriculum locally
```

Drive the robot:

```bash
cd projects/capstone_nav
python -m eval run --episodes 8 --stack dynamic_stack --dynamic 6
python render.py all          # regenerate the animations above
```

```
docs/            the curriculum
robotics_ai/     tested library — geometry, control, estimation, mapping, planning
curriculum/      quiz banks and exercise specs (YAML, validated in CI)
projects/        autograded projects, the capstone, and its evaluation harness
tools/           validation and verification scripts
```

## If you're on the same path

I'd genuinely like to hear from you — especially if:

- something is **wrong**. Open an issue. Robotics has a lot of conventions that are easy to state confidently and get backwards, and I would much rather be corrected than be a confident source of someone else's bug.
- a lesson **didn't land**, or the difficulty jumped. That's useful signal and hard to see from the inside.
- you're making the same transition and want to compare notes.

Corrections and clarifications are very welcome. I'm not looking to grow this into a product — it's a study project that turned out well enough to share.

## License

Code is MIT — use it however you like. Curriculum text is [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): copy, adapt, and build on it, just credit the source.
