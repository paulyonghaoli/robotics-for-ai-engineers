# Project: Particle-Filter Localization (autograded, 100 pts)

**Status:** Code verified · **Prereqs:** lessons 3.1–3.2, Module 1 · **Time:** ~4–6 h

The Course I flagship. A differential-drive robot wanders a 20 × 20 m field of landmarks, receiving noisy odometry and range-bearing observations. You build the particle filter that tracks it from a known start, localizes it from *total ignorance*, and — the finale — recovers after the robot is kidnapped mid-run.

## Setup

The project lives at `projects/localization/`:

```bash
cd robotics-for-ai-engineers/projects/localization
python -m grader          # randomized worlds, fresh each run
```

You implement four functions in `student.py`; the harness (`world.py`) runs the loop and the physics. Sample grader output:

```
Localization project — seed 483920

  motion_update              20/20   ok
  measurement_likelihood      0/25   FAIL: bearing residual must be WRAPPED: two headings
                                     0.02 rad apart got likelihood ratio 3.1e-171 ...
  systematic_resample        15/15   ok
  inject_random              10/10   ok
  closed-loop tracking        0/15   FAIL: ...
  global + kidnap recovery    0/15   FAIL: ...

  TOTAL: 45/100
```

## Rubric

| Task | Points | What's actually graded |
|---|---|---|
| `motion_update` | 20 | Arc propagation with per-particle noise at the *correct scale* — the spread is checked statistically |
| `measurement_likelihood` | 25 | Range-bearing Gaussian model, including the **wrapped bearing residual** — the ±π trap returns with money on the line |
| `systematic_resample` | 15 | Selection frequency must track the weights |
| `inject_random` | 10 | Uniform injection, shape-safe, in-world |
| Closed-loop tracking | 15 | Mean error < 0.8 m after burn-in, three random worlds |
| Global + kidnap recovery | 15 | Uniform-prior convergence, then re-convergence after a mid-run teleport |

Everything here is a concept you've already built in the lessons — the project's work is making them survive contact with a harness you don't control, statistical grading, and each other. Which is, of course, the actual job.
