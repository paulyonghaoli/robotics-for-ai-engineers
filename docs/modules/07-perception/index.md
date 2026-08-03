# Module 7 · Robotic Perception

**Status:** Complete · **Course III**

You have spent years turning images into tensors. This module is about the part that comes before and after that: the **geometry** that says which ray of the world a pixel came from, and what to do with the resulting 3D structure once you have it.

That geometry is where the transition from ML to robotics actually bites. A detector that is 2% wrong about an object's *class* is a slightly worse detector. A camera model that is 2% wrong about its focal length is a system that mislocates everything at range by an amount that grows with distance — and nothing in the training loss will ever tell you.

## Lessons

1. [Camera models: pixels are rays](01-camera-models.md) — **available**
2. [Stereo and depth: the error grows as Z²](02-stereo-depth.md) — **available**
3. [Point clouds: unordered, metric, and mostly empty](03-point-clouds.md) — **available**
4. [3D detection: pillars, anchors and NMS](04-3d-detection.md) — **available**
5. [BEV and fusion: two sensors, one frame, one clock](05-bev-fusion.md) — **available**
6. [Lab: the perception stack that lied](06-lab-perception-lied.md) — **available**

## What you'll build

A camera model you can project *and* unproject through, a stereo depth estimator with its error bars derived rather than guessed, and the pieces of a 3D detection pipeline — ending in a [mini-project](project-perception.md) graded on geometry, not on a trained network.

Nothing here trains a model. That is deliberate: the parts of a perception stack that break in the field are almost never the weights.

## What transfers, and what doesn't

**Transfers:** your feature-engineering instincts, your comfort with tensor layouts, your evaluation discipline, and — if you have worked on PointPillars or any voxel-based detector — the entire encoder story.

**Doesn't:** the assumption that the input is a fixed-size grid with no physical units. A point cloud is unordered, variable-length, metrically scaled, and sparse in a way that is *informative* — empty space is a measurement, not missing data.
