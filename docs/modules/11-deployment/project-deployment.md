# Mini-project: The deployment gate (autograded, 100 pts)

**Status:** Code verified · **Prereqs:** lessons 11.1–11.3 · **Time:** ~3 h · **Verified:** 2026-08-03, Python 3.13, NumPy ≥ 1.26

Four questions that have to be answered before a policy leaves the lab, each with an answer that is not the obvious one.

## Setup

```bash
cd robotics-for-ai-engineers/projects/deployment_mini
python -m grader
```

Implement the stubs in `student.py`. `deploykit.py` is given: per-stage latency traces, a weight tensor, two rollout plans, and a thermal clock model.

## The marks

| Check | Points |
|---|---:|
| Pipeline tail against per-stage tails | 25 |
| INT8 quantization, per-tensor against per-channel | 25 |
| Rollout exposure and blast radius | 25 |
| Thermal throttling and the datasheet number | 25 |

## The four results

**Adding per-stage p99s overstates the pipeline's p99 by about 45%.** The stages do not spike on the same frames, so the summed tail describes a frame that never happens. The pipeline's p99 is also *larger* than any individual stage's, so a per-stage dashboard understates it in the other direction. Neither number is a bound, and only the pipeline's own distribution answers the question — which means you have to measure the pipeline, not assemble it from parts.

The second half of that check is sharper: the stage with the largest **mean** and the stage driving the **tail** are different stages. A profile sorted by mean aims a quarter of optimization work at the wrong one, which is [13.5](../13-systems-perf/05-lab-optimization-didnt-help.md) arriving from a different direction.

**One badly-scaled channel ruins per-tensor quantization for all sixty-four.** Channel 17 has a hundred times the dynamic range of the rest; it sets the scale, and the other sixty-three lose most of their bits to a range they never use. The RMS error is 8× worse than per-channel. This is why per-channel quantization is the default in every serious toolchain, and it is worth having the number rather than the folklore.

**A staged rollout does not reduce how much bad service you deliver.** This is the check most worth doing carefully. Both plans expose *exactly* `k / rate` robot-hours to the bad version before the monitor fires — 250 robot-hours, identically, because failures accrue with exposure and the alarm is a failure count. A staged rollout cannot change that.

What it buys is the **blast radius**: 10% of the fleet is on the bad version when the alarm fires rather than 100%, so the rollback is smaller, faster, and does not require touching every robot you own. What it costs is **time**: 26.6 hours to detection instead of 0.5. Both of those belong in the argument, and the usual argument for staged rollout — that it limits the damage before you notice — is the one thing the arithmetic does not support.

**The benchmark number is 2× the number that is still true after five minutes.** A 30-second run never leaves the boost window and reports 91 fps; sustained is 45. The 50 Hz deadline first breaks at about 280 seconds of continuous operation, so every benchmark anyone would naturally run is clean while the robot cannot hold its loop rate through a five-minute mission. A 40 Hz loop survives the throttle entirely — the deadline you chose is what decides whether this hardware works, which is a design conversation rather than a procurement one.

## Portfolio extension

Instrument your own capstone loop for ten minutes of continuous operation on whatever hardware you have, with clocks unpinned, and plot frame time against elapsed time. Then pin the clocks and do it again. Publish both curves with the deadline drawn across them. Almost nobody has this plot, and it answers the only question that matters about a benchmark: for how long is it true?
