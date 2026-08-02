# Module 10 · Evaluation & Data Systems

**Status:** In progress (being written early, out of order) · **Course III**

The [frontier research](../../frontier.md) ranks this module's content as the **highest-leverage area** for an ML or data engineer entering robotics — and documents a field-wide evaluation crisis in which only about 20% of state-of-the-art claims on the dominant benchmarks are statistically significant.

It's also the module whose lab you already have: the [capstone harness](../capstone/index.md) is a scenario-evaluation system, and everything here generalizes it.

## Lessons

1. [Statistical rigor: how many episodes justify a claim?](01-statistical-rigor.md) — **available**
2. Scenario-suite design: coverage, difficulty, and what to randomize *(planned)*
3. Regression testing from logs and bags *(planned)*
4. Dataset lifecycle: curation, provenance, versioning *(planned)*
5. Drift monitoring in deployment *(planned)*
6. Neural real-to-sim evaluation *(planned)*
7. Lab: the benchmark that lied *(planned)*

## Why this is a separate module

The original plan had one "production robotics" module covering evaluation, data, deployment, fleet, and safety. Two things forced the split: the 2026 research showing evaluation as the field's binding constraint, and job postings like Figure's *Helix AI Engineer, Data Infrastructure* — **$150–400k, no ML modeling required**, asking instead for Linux, Python, Postgres, SLURM/Kubernetes, and dataset tooling. Deployment, fleet operations, and safety moved to Module 11.
