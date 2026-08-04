# Module 11 mini-project — The deployment gate

Four questions that have to be answered before a policy leaves the lab.

```bash
cd projects/deployment_mini
python -m grader
```

100 points across four checks, random seed each run unless you pass `--seed N`.

## What you implement

All in [`student.py`](student.py):

| | Points | |
|---|---:|---|
| `pipeline_samples`, `sum_of_stage_p99`, `tail_driver`, `mean_driver` | 25 | The pipeline's tail is not the sum of the stages' tails |
| `quant_params`, `fake_quant`, `per_tensor_error`, `per_channel_error` | 25 | What INT8 costs, and why per-channel is the default |
| `detect` | 25 | What a staged rollout buys, and what it does not |
| `frame_ms`, `mean_fps`, `sustained_fps`, `deadline_breach_time` | 25 | The datasheet number and the true one |

## The four results

**Adding per-stage p99s overstates the pipeline's p99 by about 45%**, because
the stages do not spike on the same frames. The pipeline's p99 is also *larger*
than any individual stage's, so the per-stage dashboard understates it too.
Neither direction is a bound; only the pipeline's own distribution answers the
question. And the stage that owns the mean (`undistort`) and the stage that
owns the tail (`track`) are different stages, which is why a profile sorted by
mean aims the work at the wrong one.

**One badly-scaled channel ruins per-tensor quantization for all sixty-four.**
Channel 17 has a hundred times the dynamic range of the rest, sets the scale,
and the other sixty-three lose most of their bits to a range they never use —
an 8× RMS error difference. Per-channel quantization is not an optimization,
it is the thing that makes INT8 usable at all.

**A staged rollout does not reduce how much bad service you deliver.** Both
plans expose exactly `k / rate` robot-hours to the bad version before the
monitor fires — 250 robot-hours, identically, because failures accrue with
exposure and the alarm is a failure count. What the staged plan buys is the
*blast radius*: 10% of the fleet is on the bad version when the alarm fires
instead of 100%. What it costs is time — 26.6 hours to detection instead of
0.5. Both of those are worth saying out loud before choosing a plan.

**The benchmark number is 2× the number that is still true after five
minutes.** A 30-second run never leaves the boost window and reports 91 fps;
the sustained rate is 45. The 50 Hz deadline first breaks at about 280 seconds
of continuous operation, so every benchmark anyone would think to run is clean
and the robot cannot hold its loop rate for a five-minute mission. A 40 Hz loop
survives the throttle entirely — the deadline you chose is what decides whether
this hardware works.

## `deploykit.py`

Given, not modified: the per-stage latency traces, the weight tensor, the two
rollout plans, the fleet size, and the thermal clock model.
