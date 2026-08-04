# 12.2 Replay determinism: a replay that doesn't reproduce isn't one

**Status:** Code verified · **Prereqs:** lesson 12.1 · **Time:** ~2 h · **Verified:** 2026-08-03, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

An incident report says the robot braked hard at 14:32:07. You replay the log and it doesn't brake.

At that point you have two runs and no way to tell which one is real, and every hour spent debugging is spent on a system that may not be the one that failed. **Replay is the foundation everything else in this module rests on** — regression suites, root-cause analysis, and any claim that a fix actually fixes something all assume that running the same input twice produces the same output.

In batch ML you can usually live without it: a model that trains to slightly different weights is still a model, and you evaluate it statistically. A robot is a closed loop, and closed loops amplify. A difference of 10⁻¹² in one control cycle is a different action, which is a different state, which is a different observation — and the divergence grows geometrically rather than staying where you put it.

## B. Mental model

**Three grades of reproducibility, and you should know which one you have.**

| Grade | Guarantee | Good for |
|---|---|---|
| **Bit-exact** | identical outputs, byte for byte | regression tests, "did my change do anything" |
| **Statistical** | same distribution over many runs | benchmarking, comparing policies |
| **Vibes** | it usually does roughly the same thing | nothing |

Most systems believe they are the first and are the third. The gap is invisible until you check, and the check is trivially cheap: **run it twice and diff.** That test belongs in CI, not in a runbook.

**The five usual sources**, in roughly the order they bite:

1. **Unseeded randomness.** The obvious one, and rarely the whole story.
2. **Wall-clock dependence.** Timeouts, `now()`, rate limiters, "has 100 ms elapsed". The replay runs faster than real time, so these fire differently.
3. **Message ordering.** Two queues merged by arrival produce a different interleaving each run. Order by *timestamp*, not by arrival.
4. **Carried-over state.** The second run starts with caches, filters, or accumulators the first left behind.
5. **Floating-point accumulation order.** Parallel reductions sum in whatever order threads finish. `a+(b+c) ≠ (a+b)+c` in floating point, and in a closed loop that is enough.

## C. Formulation

**Divergence in a closed loop.** Let two runs differ by `δ₀` at step 0. If the loop's local error amplification is `λ` per step:

$$
\delta_t \approx \delta_0\,\lambda^{t}
$$

With `λ = 1.05` — a very gently unstable loop — a `δ₀ = 10⁻¹²` difference reaches order 1 after about 550 steps, which is under a minute at 10 Hz. Nothing is broken; the arithmetic is simply doing what arithmetic does.

The practical consequence is that **"close enough" is not a stable category**. Two runs that agree to six decimal places at t=0 can disagree about whether the robot stopped, by the end of the episode. So the check has to be exact equality, and the tolerance you are tempted to add is what hides the bug.

**The diff that is worth building** reports the *first* step at which the runs differ, not just that they do. The first divergence points at the cause; the hundredth points at nothing.

## D. From ML to robotics

Your instincts about seeding transfer, and two habits do not.

- **"Set the seed and you're done."** Seeding fixes source 1 of 5. The other four are structural, and three of them (clock, ordering, carried state) survive any amount of seeding.
- **"Tolerances make tests robust."** In a closed loop a tolerance does not make a test robust, it makes it silent. A drifting comparison passes until the drift is large enough to change a discrete decision, at which point it fails catastrophically and with no history of getting worse.

The right shape is: **bit-exact where you can, statistical where you cannot, and explicit about which.** A replay harness that documents "this is statistically reproducible, not bit-exact, because the perception stage runs multithreaded reductions" is a good harness. One that quietly compares with `atol=1e-3` is a liability.

## E. Practice

<code-exercise src="dat-l2-divergence"></code-exercise>

<code-exercise src="dat-l2-determinism"></code-exercise>

## F. In production

- **Record the seed, and record it in the log.** A seed you cannot recover is a seed you did not set.
- **Log the versions of everything**, including the simulator, the libraries, and the calibration. Bit-exactness across library versions is not a thing you get for free.
- **Set the threading environment explicitly.** `OMP_NUM_THREADS=1` for replay is a blunt and extremely effective instrument, and the performance you lose is worth the determinism you gain.
- **Order by timestamp on ingest**, once, rather than hoping every consumer does it.
- **Put "run twice and diff" in CI.** It catches the regression on the day it lands, which is the only day it is cheap.

## G. Experiment

Take your capstone's episode runner and add a `--replay-check` that runs an episode twice and diffs the trajectories step by step. Then deliberately break it four ways — read the clock, shuffle two message streams, keep a module instance between runs, run a reduction in parallel — and confirm the diff catches each and reports a plausible first-divergence step. Which of the four your codebase already has is the interesting part.

## H. Failure modes

- **Seeded but not deterministic.** The most common state, because seeding feels like completion.
- **Deterministic on one machine.** Different CPU, different SIMD width, different reduction order.
- **Tolerant comparison.** Passes until it doesn't, with no warning trend.
- **Replay that reads the clock.** Runs faster than real time, so every timeout fires at a different point in the data.
- **Determinism nobody checks.** It decays silently; without a CI check the first time you find out is during an incident, which is the worst possible time.

## I. Questions

<quiz-bank src="dat-l2-quiz"></quiz-bank>

## J. References

- Kleppmann, *Designing Data-Intensive Applications*, ch. 11 — stream processing and the ordering guarantees you do and do not get.
- Goldberg, *What Every Computer Scientist Should Know About Floating-Point Arithmetic* (1991) — the non-associativity result, which is the whole of section C.
- ROS 2 design docs on deterministic replay — a candid description of why it is hard in a distributed executor.
- Bagnell et al. on reproducibility in robot learning — the statistical-versus-exact distinction, argued from the learning side.

## K. Graded work & portfolio extension

**Graded:** the two exercises above.

**Portfolio:** the section G study — a replay check wired into your capstone's CI, plus a short note on which of the five sources your code was already exposed to and what each fix cost. The note is the artifact. "We had three of the five and did not know" is a more credible statement about engineering maturity than any claim that the code was clean.
