# 13.1 The performance model: why the datacenter number doesn't transfer

**Status:** Code verified · **Prereqs:** lesson 11.1 · **Time:** ~2 h · **Verified:** 2026-08-03, Python 3.13

---

## A. Why this matters

Your policy runs at 220 fps on the workstation. On the robot it runs at 62.

The instinct is that the robot's accelerator is smaller, which is true and almost entirely beside the point. In the model below the GPU accounts for **3% of the workstation's frame time and 7% of the robot's**. Doubling its peak FLOPs changes throughput by zero — not approximately zero, exactly zero, because the compute term was never the binding constraint and would not be even at half the speed.

This lesson is the arithmetic that tells you which term you are actually paying, before you spend a quarter optimizing the wrong one. It is the same discipline as [11.1](../11-deployment/01-latency-budgets.md)'s latency budget, one level down: 11.1 asked whether the loop closes in time, this asks where the time went.

## B. Mental model

**Three terms, and they serialize.**

$$
t_{\text{frame}} = \underbrace{n_{\text{ops}} \cdot t_{\text{launch}}}_{\text{CPU}} \;+\; \underbrace{\max\!\left(\frac{F}{P},\, \frac{B}{W}\right)}_{\text{accelerator}} \;+\; \underbrace{\frac{B_{\text{in}}}{L}}_{\text{link}}
$$

The middle term is the **roofline**: compute and memory traffic overlap, so the slower one sets the pace. Which one that is depends on the model's **arithmetic intensity** $I = F/B$ — FLOPs per byte moved — against the device's **ridge point** $P/W$:

| | intensity | ridge point | verdict |
|---|---:|---:|---|
| the policy | **26.2 FLOP/byte** | | |
| workstation A100 | | 201 FLOP/byte | memory-bound, 7.6× over |
| robot AGX Orin | | 336 FLOP/byte | memory-bound, 12.8× over |

A batch-1 network is memory-bound on everything, and the reason is structural rather than accidental: **at batch 1 the weights are read once per frame and used once.** There is no reuse to amortize them against. Batching is the thing that raises arithmetic intensity, and batching is the thing a robot cannot do — there is one camera, one frame, now.

The ridge point is worth one more look, because it is where "which GPU should we buy" usually goes wrong. Between these two devices, peak FLOPs differ by 4.5× and bandwidth by 7.6×. For a memory-bound model **only the second ratio exists.** The TOPS number on the datasheet is describing a regime your policy never enters.

**And the first term dominates both.** In an eager framework the CPU launches each kernel, waits for it to return, and launches the next. Seventy-two kernels at 60 µs of host dispatch is 4.3 ms on the workstation; the same seventy-two at 210 µs on an embedded CPU is 15.1 ms. Nothing about that is a GPU property. **The robot's frame rate is set by its CPU.**

## C. What the model says

Running the exercise's numbers:

| mode | device | frame | fps | GPU share | bottleneck |
|---|---|---:|---:|---:|---|
| eager | workstation A100 | 4.55 ms | 220 | 3.2% | **cpu-dispatch** |
| eager | robot AGX Orin | 16.24 ms | 62 | 6.9% | **cpu-dispatch** |
| graph | workstation A100 | 0.23 ms | 4310 | 63% | gpu (34% is PCIe) |
| graph | robot AGX Orin | 1.14 ms | 880 | 98% | gpu |

Three readings, in increasing order of how much they change what you do:

1. **Capturing the graph is worth 14–20×** and touches no hardware. That is what TensorRT, `torch.compile`, and CUDA graphs actually buy at batch 1: not better kernels, one launch instead of seventy-two.

2. **The optimized workstation spends a third of its frame on the PCIe copy**, and the robot spends none — unified memory means the camera buffer is already where the accelerator can see it. On this one axis the embedded part is the better machine, and it is the axis nobody puts on a slide.

3. **Optimizing widens the gap, from 3.6× to 4.9×.** This is the counterintuitive one and worth sitting with: the CPU bottleneck was hurting both machines, and it was *relatively* worse on the workstation because its GPU was otherwise idle. Removing it exposes the bandwidth ratio underneath. A team that benchmarks in eager mode concludes the edge deployment is a 3.6× problem and finds out it is a 4.9× problem after the port.

### The whole budget, computed — and where the frame actually goes

Run this lesson's visuomotor policy (2.1 GFLOP, 80 MB of weights and
activations, 72 kernel launches) through the performance model on both
devices:

| | Workstation A100 | Robot Orin |
|---|---|---|
| Arithmetic intensity vs ridge | 26 vs 201 — **memory-bound** | 26 vs 336 — memory-bound |
| Kernel math (compute or memory, whichever binds) | 51 µs | 391 µs |
| **Dispatch: 72 launches × per-launch overhead** | **4,320 µs** | **15,120 µs** |
| Total, launch-per-op | 4.37 ms (229 Hz) | 15.5 ms (64 Hz) |
| Total with CUDA graph (one launch) | 56 µs | 411 µs |
| **Speedup from graphing alone** | **77×** | **38×** |

Read the middle rows and the folklore of this module becomes arithmetic. The
actual mathematics of the policy occupies 51 microseconds of the A100's
frame; the *launching* of that mathematics occupies 4,320. The GPU spends
1% of the wall-clock computing and 99% being told what to compute next, so
**doubling the device's FLOPs changes the frame time by roughly nothing** —
you would be doubling the throughput of the 1%. The same model explains the
A100-to-Orin cliff without any hand-waving about "edge devices being slow":
the Orin's dispatch overhead is 3.5× higher per launch, and 72 launches
multiply that difference into the whole budget.

It also says exactly what *does* work, in order: fuse or graph the launches
(CUDA graphs collapse 72 dispatches into one, worth 77× here — more than any
conceivable hardware upgrade), then shrink the *bytes* (the model is
memory-bound, so quantisation's 4× byte reduction from lesson 13.3 is a real
4× on the kernel time), and only then think about FLOPs at all. The
performance model is not an approximation of profiling; on a system this
dispatch-dominated it *is* the profile, computable before you buy the
hardware.

## D. From ML to robotics

If you come from training, most of your performance intuition was formed at large batch on a machine with 2 TB/s of bandwidth, and almost none of it transfers.

- **Throughput intuitions become latency intuitions.** Nobody cares what the robot's policy does in aggregate; they care what one inference costs, and the terms that amortize away at batch 256 are the entire cost at batch 1.
- **FLOPs stop being the currency.** A model with half the FLOPs and the same parameter count is the same speed. Parameter count and activation size are the numbers that predict a batch-1 latency; FLOPs predict a training cost.
- **The host becomes a first-class part of the system.** In training the CPU feeds the GPU and is generally not the problem. On a robot the CPU is small, shared with perception, control, and the ROS graph, and it is where the frame time went.
- **"It fits in memory" is a different question.** A 7B VLA in FP16 is 14 GB of weights that must be read *per frame*. At 205 GB/s that is 68 ms before any arithmetic — a hard 14 fps ceiling that no engineering removes. Quantizing to INT4 is not a compression trick there, it is a 4× frame-rate change, which is [11.2](../11-deployment/02-edge-inference.md)'s subject arriving as arithmetic.

## E. Practice

<code-exercise src="sys-l1-perfmodel"></code-exercise>

## F. In production

- **Measure before modelling, then model to know what to measure.** Nsight Systems on a desktop, `tegrastats` and Nsight on Jetson. The first thing to look at is the gap between kernels, not the kernels.
- **Batch 1 is a first-class target.** Export with TensorRT or `torch.compile(mode="reduce-overhead")`, which captures a CUDA graph. Verify numerically against the eager reference before believing the speed.
- **Pin the clocks before benchmarking** (`jetson_clocks`, `nvidia-smi -lgc`). Otherwise you measure the governor, and thermal throttling makes the fifth minute slower than the first — see [11.2](../11-deployment/02-edge-inference.md).
- **Watch for the copy.** Unified memory on Jetson removes it if you use it; a naive port that allocates host buffers and copies anyway pays for hardware it already owns.
- **The two numbers to know for any device**: memory bandwidth and single-thread CPU speed. Peak TOPS is the one on the box and the least predictive of the three.

## G. Experiment

Take the model in the exercise and ask what it costs to make it 2× larger in each of two ways: twice the FLOPs at the same parameter count (deeper at lower width), or twice the parameters at the same FLOPs. On a memory-bound device the first is free and the second is a 2× regression, which is the opposite of what a FLOP-counting intuition predicts. Then check where the crossover is — how large the batch would have to be for the compute term to bind — and notice it is a batch a robot never sees.

## H. Failure modes

- **Benchmarking in eager mode and planning around it.** You measured your framework's dispatch loop, and every conclusion about the hardware is contaminated.
- **Sizing the accelerator on peak TOPS.** For a memory-bound model that number does not participate in the answer.
- **Optimizing the largest kernel.** The largest kernel is often 2% of the frame. Profile for the gaps between kernels first.
- **Benchmarking warm and deploying cold.** First-inference latency includes allocation, autotuning and JIT, and it is often 100× the steady-state number. A robot that runs a policy on a 1 Hz trigger is always paying it.
- **Forgetting the CPU is shared.** A dispatch cost measured on an idle Orin is not the cost you get with perception, the ROS graph and a logger competing for the same cores.

## I. Questions

<quiz-bank src="sys-l1-quiz"></quiz-bank>

## J. References

- Williams, Waterman & Patterson (2009), *Roofline: An Insightful Visual Performance Model* — the original, and still the clearest.
- NVIDIA Jetson AGX Orin technical brief — the bandwidth and TOPS figures used above, and worth reading for how the two are presented relative to each other.
- NVIDIA CUDA graphs documentation, and the `torch.compile(mode="reduce-overhead")` notes — the mechanism behind the 14–20×.
- Nsight Systems user guide, particularly the section on gaps in the CUDA stream — the tool for seeing dispatch-bound behaviour directly.

## K. Graded work & portfolio extension

**Graded:** the exercise above.

**Portfolio:** build the same three-term model for your capstone policy on hardware you actually have, then measure it and publish both. The interesting artifact is the disagreement — where the model is wrong tells you which term you have mis-modelled, and that is a more useful thing to have written down than a table of timings.
