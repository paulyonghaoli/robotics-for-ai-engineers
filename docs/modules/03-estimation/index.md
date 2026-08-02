# Module 3 · State Estimation & Sensor Fusion

**Status:** Complete · **Library:** `robotics_ai.estimation` (code verified, tested)

Your robot never knows where it is — it maintains a *belief*. This module is Bayesian inference applied at 50 Hz.

## Lessons

1. [The Kalman filter: Bayes at 50 Hz](01-kalman.md) — **available**
2. [The particle filter: when Gauss isn't enough](02-particle-filter.md) — **available**
3. [The extended Kalman filter: living with nonlinearity](03-ekf.md) — **available** *(UKF: planned)*
4. [Sensor models: how your sensors lie to you](04-sensor-models.md) — **available**
5. [Multi-sensor fusion architecture](05-fusion.md) — **available**
6. [Lab: catching a lying filter](06-consistency-lab.md) — **available**

## Graded work

**[Particle-filter localization project](project-localization.md)** — **available**, 100 pts: track a wandering robot from noisy odometry + range-bearing landmarks, localize globally from a uniform prior, and recover from a mid-run kidnapping. Statistically graded on randomized worlds.

## What you'll build

Scalar and matrix Kalman filters, a corridor-localizing particle filter with systematic resampling, and the tuning/consistency instincts (Q/R quadrant study, innovation monitoring) that separate filter users from filter engineers.
