# Module 1 · Geometry & Robot Motion

**Status:** Complete (first pass) · **Library:** `robotics_ai.geometry` (code verified, 40 tests)

Everything on a robot lives in a coordinate frame; this module builds the transform machinery the entire stack depends on. Every lesson includes an interactive quiz and in-browser coding labs.

## Lessons

1. [Coordinate frames and rigid transformations](01-coordinate-frames.md)
2. [3D rotations and quaternions](02-quaternions.md)
3. [Composing frames: the transform tree](03-transform-trees.md)
4. [Twists: how robots describe velocity](04-twists.md)
5. [Configuration space](05-configuration-space.md)
6. [Lab: the frame-debugging gauntlet](06-lab-frame-debugging.md)
7. [Mini-project: frame transforms](project-frames.md) — autograded, 100 pts

## What you'll build

A tested 2D/3D transform library (`se2`, quaternions, `TransformTree`), differential-drive twist integration, a 2-link-arm C-space mapper, and the debugging instincts to recognize frame-bug signatures on sight — everything the rest of the autonomy stack composes on.
