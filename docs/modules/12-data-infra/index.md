# Module 12 · Robot Data Infrastructure

**Status:** In progress · **Course IV**

[Module 11](../11-deployment/04-telemetry-forensics.md) decided what a robot should upload. [Module 10](../10-evaluation/04-dataset-lifecycle.md) decided what to keep and how to curate it. This module is about the years afterwards, when there are two hundred thousand episodes and somebody asks a question.

Three questions, specifically, and each is a whole engineering problem:

- **Can you find it?** "Every episode where the robot yielded to a pedestrian approaching from the left" is a reasonable request and an impossible one, unless somebody decided in advance that it would be askable.
- **Can you reproduce it?** A replay that produces different numbers than the original run is not a replay. It is a second, unrelated experiment.
- **Can you still read it?** The log format changed eighteen months ago. Half the archive predates the change, and the new reader parses it without complaining.

None of this is glamorous, and [the frontier research](../../frontier.md) identifies it as the least crowded high-leverage skill in the field — the reason a data-infrastructure role at a humanoid company pays $150–400k and requires no ML modelling at all.

## Lessons

1. [Indexing: you can only find what you decided to record](01-indexing.md) — **available**
2. [Replay determinism: a replay that doesn't reproduce isn't one](02-replay-determinism.md) — **available**
3. Schema evolution and the unreadable archive — *planned*
4. Lab: the dataset that could not be rebuilt — *planned*

## What you'll build

An index over a synthetic fleet archive and the query engine on top of it, a replay harness that proves bit-exact reproduction and then the four ways it stops being bit-exact, and a schema-versioned reader that refuses to silently misinterpret old data.

## What transfers

Almost all of it. This is data engineering, and if that is your background you are already most of the way there. The robotics-specific parts are small and sharp: **time has several meanings** (sensor capture, message receipt, monotonic clock, wall clock, and they disagree), **episodes are the unit rather than rows**, and **the data is causally linked to a physical machine** whose configuration is itself a version you have to record.
