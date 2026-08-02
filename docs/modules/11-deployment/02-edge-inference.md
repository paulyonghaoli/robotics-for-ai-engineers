# 11.2 Edge inference: quantization and the accuracy/latency trade

**Status:** Code verified · **Prereqs:** lesson 11.1 · **Time:** ~2 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

The model runs on the robot. Not on an A100 — on a Jetson bolted to a chassis, sharing thermal budget with motors, at batch size one, inside a control loop with a deadline.

That environment inverts an intuition you probably hold. In offline evaluation, a more accurate model is a better model. On a robot, **a more accurate model that misses the deadline is a worse robot**, and the gap can be enormous. This lesson quantifies that inversion.

## B. Mental model

**Quantization trades numerical precision for speed and memory.** FP32 → FP16 typically costs almost nothing in accuracy and roughly halves latency and memory. FP32 → INT8 gives a further 2× or so for a few points of accuracy. INT4 and below usually fall off a cliff.

The mistake is evaluating that trade on the model in isolation. What matters is the *robot's* success rate, which combines model accuracy with whether the answer arrived in time. The exercise measures all four precisions through that lens:

| precision | model accuracy | latency mean (ms) | deadline miss | **end-to-end success** |
|---|---:|---:|---:|---:|
| FP32 | **0.970** | 36.0 | 0.401 | **0.581** |
| FP16 | 0.968 | 19.0 | 0.017 | **0.952** |
| INT8 | 0.941 | 11.2 | 0.001 | 0.940 |
| INT4 | 0.723 | 6.6 | 0.000 | 0.723 |

Read the first and last columns together. **FP32 is the most accurate model and produces the worst robot** — by 37 percentage points — because it blows the deadline 40% of the time. Ranking by accuracy and ranking by end-to-end success give different answers, and only one of them is the thing you care about.

Note also the shape: success rises then falls. Once you are comfortably inside the deadline (FP16 → INT8), further quantization buys latency you have no use for and costs accuracy you do. **Quantize until you clear the deadline with margin, then stop.**

## C. Formulation

Post-training quantization maps FP32 tensors to integers with a scale and zero-point per tensor or per channel:

\[
q = \operatorname{round}(x / s) + z, \qquad \hat{x} = s\,(q - z)
\]

The scale \(s\) comes from a **calibration pass** over representative data. Calibration data that doesn't match deployment is a classic and quiet failure — the scales are set for a distribution you don't encounter, and accuracy degrades in ways that look like a bad model rather than a bad calibration set.

Where robotics differs from typical ML serving:

- **Batch size is 1.** Throughput optimizations that assume batching don't apply, and per-sample latency is all that matters.
- **The tail matters more than the mean** (lesson 11.1), so a quantization that reduces mean latency but not p99 may not help at all.
- **Thermal throttling is real.** A model benchmarked cold on a Jetson gets slower after twenty minutes of driving. Measure under sustained load.
- **Memory bandwidth is often the binding constraint**, not compute — which is why INT8's 4× memory reduction sometimes buys more than its arithmetic speedup suggests.

## D. From ML to robotics

- **This is serving optimization** with a hard deadline instead of a latency SLO, and the deadline changes the objective from "minimize p99" to "maximize the probability of a correct answer arriving in time."
- **Quantization-aware training** is the higher-effort option when post-training quantization loses too much: simulate quantization during training so the weights adapt. Worth it when INT8 costs more than a couple of points.
- **Distillation is the other lever** — a smaller model trained to mimic a larger one — and composes with quantization.

## E. Practice

<code-exercise src="dep-l2-quantization"></code-exercise>

## F. In production

TensorRT is the default path on Jetson (INT8 with calibration, layer fusion, kernel autotuning); ONNX Runtime and TFLite fill the same role elsewhere. NVIDIA's Jetson Thor is the 2026 robotics-specific part. The frontier numbers make the constraint concrete: LingBot-VLA 2.0 at 6B runs ~130 ms on a consumer GPU, while world-action models take 590–800 ms per action chunk — and per lesson 11.1, that difference decides what control rate is available to you at all.

## G. Experiment

Take the capstone's particle filter — the most expensive stage — and quantize its likelihood computation to float16, then to a fixed-point integer representation. Measure localization RMSE and p95 step latency for each. You'll find the RMSE barely moves while latency drops, because the likelihood field is a smooth function being evaluated coarsely. Then push to 8-bit and find where it breaks.

## H. Failure modes

- **Optimizing model accuracy in isolation.** The table in section B is the warning; the ranking flips.
- **Calibrating on the wrong data.** Scales set for a distribution you don't deploy in, producing accuracy loss that looks like a model problem.
- **Benchmarking cold.** Thermal throttling means the sustained number is the real number.
- **Over-quantizing past the deadline.** Once you clear it with margin, further compression is pure accuracy loss.
- **Assuming the mean speedup helps.** If your misses come from a tail, check that quantization moved the p99 and not just the average.

## I. Questions

1. *(Concept)* Why can a less accurate model produce a more reliable robot?
2. *(Calculation)* Model accuracy 0.97 with a 40% deadline-miss rate, versus 0.941 accuracy with a 0.1% miss rate. Compute both end-to-end success rates.
3. *(Debugging)* You quantize to INT8 and offline accuracy is fine, but on-robot performance drops sharply. Name two candidate causes.
4. *(System design)* Your model clears the deadline comfortably at FP16. Should you quantize further to INT8?

??? note "Answer sketches"
    **1.** Because the robot's success requires a correct answer *that arrives in time*, and those are two independent failure paths. A model 3 points more accurate but missing its deadline 40% of the time delivers a correct-and-timely answer far less often than a slightly worse model that always answers. The measured gap in the exercise is 0.581 versus 0.952 — the more accurate model produced a robot 37 points worse.

    **2.** \(0.97 \times 0.60 = 0.582\) versus \(0.941 \times 0.999 = 0.940\). The 2.9-point accuracy sacrifice buys a 36-point improvement in end-to-end reliability, which is the trade in a sentence.

    **3.** First, **calibration mismatch** — the quantization scales were fitted on data unlike what the robot actually sees, so the effective precision is wrong where it matters, and this looks like a model problem rather than a calibration one. Second, **thermal throttling** — the offline benchmark ran cold while the robot runs the model continuously, so the sustained latency is worse than the measured one. Both are checked cheaply: re-calibrate on logged on-robot data, and re-benchmark after twenty minutes of sustained load.

    **4.** Probably not. Latency you don't need has no value, while the accuracy INT8 costs is real and permanent. Quantize until you clear the deadline with margin — enough headroom for thermal throttling and load variation — then stop. The exception is if memory or power is separately binding, since INT8's 4× memory reduction may matter even when its latency gain doesn't.

### Interactive quiz

<quiz-bank src="dep-l2-quant-quiz"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Jacob et al., *Quantization and Training for Efficient Integer-Arithmetic Inference* (2017) | paper | intermediate | The scale/zero-point scheme, from the source |
| [TensorRT developer guide](https://docs.nvidia.com/deeplearning/tensorrt/) | docs | intermediate | The path you'd actually take on a Jetson |
| Dean & Barroso, *The Tail at Scale* (2013) | paper | introductory | Why the p99, not the mean, is what your deadline sees |

## K. Graded work & portfolio extension

**Graded:** the quantization exercise makes the accuracy/deadline inversion concrete and is the module's second core skill.

**Portfolio:** the section G study on your capstone — localization RMSE and p95 latency across precisions, with the point where accuracy finally breaks. It is a complete deployment investigation on a system you built, and the inversion it demonstrates is one many practitioners have never actually measured.
