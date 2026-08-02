# Project: Particle-Filter Localization (Module 3) — 100 points

The Course I flagship. A differential-drive robot wanders a field of landmarks; you implement the particle filter that tracks it — and survives being kidnapped.

## Setup

Implement the four stubs in [`student.py`](student.py). The harness in [`world.py`](world.py) (don't edit) simulates the world and runs your filter.

```bash
python -m grader              # randomized scenarios, fresh each run
python -m grader --seed 7     # reproduce a run
python -m grader --reference  # the grader grading its own reference solution
```

## Rubric

| Task | Points | What's actually being graded |
|---|---|---|
| `motion_update` | 20 | Correct arc propagation *and* correctly-scaled noise: too little and the filter is overconfident, too much and it's mush |
| `measurement_likelihood` | 25 | Range-bearing Gaussian model — including the wrapped bearing residual (the ±π trap from Module 1) |
| `systematic_resample` | 15 | Low-variance resampling statistics |
| `inject_random` | 10 | Uniform injection that preserves array shape and stays in-world |
| Closed-loop tracking | 15 | Mean position error after burn-in, three random worlds |
| Global localization + kidnap recovery | 15 | Uniform-prior convergence, then recovery after the robot is teleported mid-run |

Scenario parameters are randomized per run — make the functions correct, not the outputs memorized. Run from `projects/localization/`.
