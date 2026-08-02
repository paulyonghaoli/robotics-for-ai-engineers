# Module 11 · Deployment, Fleet & Safety

**Status:** In progress · **Course III**

Module 10 asked whether your robot works. This one asks whether it keeps working — on hardware you don't own, in conditions you didn't test, across a fleet you can't watch.

This is the module where your platform-engineering instincts transfer most directly, with one twist that changes everything: **a robot missing a deadline is not a slow response, it's a control failure.** Web services degrade under latency; robots crash.

## Lessons

1. [Latency budgets and the real-time contract](01-latency-budgets.md) — **available**
2. Edge inference: quantization and the accuracy/latency trade *(planned)*
3. Rollout and rollback across a fleet *(planned)*
4. Fleet telemetry and incident forensics *(planned)*
5. Safety cases for learned components *(planned)*
6. Lab: the incident *(planned)*

## What you'll build

A latency budget for a real control pipeline — and the discovery that the stage with the largest *mean* is usually not the one causing deadline misses.
