# Module 9 · Robot Learning & Embodied AI

**Status:** In progress · **Course III**

This is the module people arrive at robotics *for*, and it is deliberately placed last. Every learned component here plugs into scaffolding built in Courses I–II: policies emit setpoints that controllers track, their beliefs come from filters, their failures get caught by watchdogs, and their claims get checked by Module 10's evaluation machinery.

The [frontier research](../../frontier.md) is blunt about where the leverage is. The bottleneck in 2026 is **not** architecture — it's data composition, evaluation rigour, and reliability. This module is weighted accordingly: imitation learning at a scale you can actually run, a full lesson on the data engine, and vision-language-action models treated as something to *evaluate* rather than train.

## Lessons

1. [Behavior cloning and the compounding-error problem](01-behavior-cloning.md) — **available**
2. Multimodality: why regression averages your demonstrations *(planned)*
3. The data engine: interventions and human-in-the-loop *(planned)*
4. Sim-to-real and domain randomization *(planned)*
5. World models: learn the dynamics, plan through it *(planned)*
6. Vision-language-action models: inference and honest evaluation *(planned)*
7. Lab: the policy that memorized *(planned)*

## What you'll build

A behavior-cloned policy on an unstable plant, where you can watch a 12% gain error produce a 0.009 validation MAE and total failure by horizon 50 — and a DAgger loop that takes the same task from 0% to 100% success in one round of relabelling.

## What this module deliberately does not do

Train a foundation model. That is a lab-scale endeavour, and the 2026 evidence is that the field's binding constraint lies elsewhere. Evaluating a generalist policy honestly is both more tractable and, per the hiring data, more in demand.
