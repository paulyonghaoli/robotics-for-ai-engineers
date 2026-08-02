# Module 10 · Evaluation & Data Systems

**Status:** Complete (written early, out of numerical order) · **Course III**

The [frontier research](../../frontier.md) ranks this module's content as the **highest-leverage area** for an ML or data engineer entering robotics — and documents a field-wide evaluation crisis in which only about 20% of state-of-the-art claims on the dominant benchmarks are statistically significant.

It's also the module whose lab you already have: the [capstone harness](../capstone/index.md) is a scenario-evaluation system, and everything here generalizes it.

## Lessons

1. [Statistical rigor: how many episodes justify a claim?](01-statistical-rigor.md) — **available**
2. [Scenario-suite design: what to randomize, and what not to](02-scenario-suites.md) — **available**
3. [Regression testing a stochastic system](03-regression-from-logs.md) — **available**
4. [Dataset lifecycle: curation, provenance, versioning](04-dataset-lifecycle.md) — **available**
5. [Drift monitoring: noticing before the robot does](05-drift-monitoring.md) — **available**
6. [Neural real-to-sim evaluation](06-neural-real-to-sim.md) — **available**
7. [Lab: the benchmark that lied](07-lab-benchmark-lied.md) — **available**

## Why this is a separate module

The original plan had one "production robotics" module covering evaluation, data, deployment, fleet, and safety. Two things forced the split: the 2026 research showing evaluation as the field's binding constraint, and job postings like Figure's *Helix AI Engineer, Data Infrastructure* — **$150–400k, no ML modeling required**, asking instead for Linux, Python, Postgres, SLURM/Kubernetes, and dataset tooling. Deployment, fleet operations, and safety moved to Module 11.
