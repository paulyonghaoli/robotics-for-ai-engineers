# Module 11 · Deployment, Fleet & Safety

**Status:** In progress · **Course III**

Module 10 asked whether your robot works. This one asks whether it keeps working — on hardware you don't own, in conditions you didn't test, across a fleet you can't watch.

This is the module where your platform-engineering instincts transfer most directly, with one twist that changes everything: **a robot missing a deadline is not a slow response, it's a control failure.** Web services degrade under latency; robots crash.

## Lessons

1. [Latency budgets and the real-time contract](01-latency-budgets.md) — **available**
2. [Edge inference: quantization and the accuracy/latency trade](02-edge-inference.md) — **available**
3. [Rollout and rollback across a fleet](03-rollout-rollback.md) — **available**
4. [Fleet telemetry and incident forensics](04-telemetry-forensics.md) — **available**
5. [Safety cases for learned components](05-safety-cases.md) — **available**
6. Lab: the incident *(planned)*

## What you'll build

A latency budget for a real control pipeline — and the discovery that the stage with the largest *mean* is usually not the one causing deadline misses. Then the same lens applied to model precision, where ranking by accuracy and ranking by robot reliability put opposite models first.
