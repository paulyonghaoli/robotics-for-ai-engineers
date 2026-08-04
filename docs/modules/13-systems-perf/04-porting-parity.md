# 13.4 Porting with parity: validating a rewrite you cannot trust

**Status:** Code verified · **Prereqs:** lessons 12.2, 13.3 · **Time:** ~2 h · **Verified:** 2026-08-03, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

A port is the one refactor where you already have the answer. The Python reference works, it is verified, and it is sitting right there — so the question is never "is the new code plausible", it is **"does it produce the same numbers"**, and that question has an executable answer.

Almost nobody asks it properly. The exercise below hands you a port that passes its two-hundred-fixture parity suite with zero disagreements and is wrong in three separate ways. Every test anyone would naturally write is green, including the end-to-end one.

## B. The three ways a green suite lies

**1. The tolerance was chosen for comfort.** The port computes in `float32` where the reference used `float64`, a systematic 1.2 × 10⁻⁷ disagreement on every fixture. At the shipped tolerance of 10⁻³ that is invisible. Tighten to 10⁻⁹ and **186 of 200 fixtures disagree**.

The fix is a rule about where the number comes from: **the tolerance is the float-noise floor, not a comfortable round number.** Reassociation and fused multiply-add produce differences at 10⁻¹⁵ or so; anything above that is a real difference and deserves a name.

| disagreement | what it is | what to do |
|---|---|---|
| 0 | exact | ship it |
| ≤ 1e-12 | reassociation, FMA | fine, and say so explicitly |
| ~1e-7 | **a different float width** | decide whether the loop can carry it |
| > 1e-5 | the two functions do different things | a defect |

That third row is the interesting one, because it is not a bug and not noise. It is a design decision somebody made silently, and [12.2](../12-data-infra/02-replay-determinism.md) already told you what a closed loop does with a 10⁻⁷ difference.

**2. The fixtures never covered the operating range.** The suite draws heading errors from [−1, 1] rad. The robot drives over the full circle, including reversing. Run the same harness at the same tolerance over the real range and **60 of 200 fixtures disagree, the worst by 2.68 rad/s** — the port clamps its upper bound and not its lower one. The threshold was never the problem. A fixture set that happened to test only positive heading errors would also be green.

The check that catches this costs one line: compare the range the fixtures exercise against the range the robot operates in.

**3. The comparison silently skips NaN.** One fixture has an empty path. The reference guards it and returns 0.45; the port takes a mean of nothing and returns NaN. And then:

```python
abs(0.45 - float("nan")) > 1e-3      # False
```

`NaN` compares false against everything, so the obvious harness reports *no difference* in precisely the case you most needed it to catch. A `diff` that returns infinity when exactly one side is NaN is three lines and closes the hole.

## C. Per-step parity is not trajectory parity

Even with the harness fixed, agreement on individual calls is the weaker claim. The step feeds back: a difference in the command changes the state, which changes the next input, and the two implementations stop being evaluated on the same inputs at all.

The exercise runs both steering functions in the same closed loop:

| initial heading error | trajectory gap after 200 steps |
|---|---:|
| −0.5 rad (nominal) | < 10⁻⁶ m |
| −2.5 rad (ordinary field condition) | **0.30 m** |

So the end-to-end test passes too, as long as you start it somewhere the fixtures already covered. **Closed-loop parity has to be run from initial conditions drawn from the same distribution as the field**, and it should report the first divergence rather than the final gap — the first divergence points at the cause, everything after it is a different system.

## D. From ML to robotics

- **This is regression testing against a golden model**, which you have done. The difference is that the golden model here is *executable and exact*, so "close enough" is a choice rather than a necessity.
- **Fixtures are a dataset, and they have all the dataset problems**: coverage gaps, distribution shift from the deployment, and a long tail nobody sampled. [10.2](../10-evaluation/02-scenario-suites.md)'s scenario-suite argument applies unchanged — fixtures drawn from logs beat fixtures written by hand, for the same reason.
- **The NaN hole is the classic silent-comparison bug**, and it shows up in metric code as often as in parity harnesses. Any comparison of floats you did not write carefully has it.
- **Property tests transfer well here.** "For all inputs in this range, the two implementations agree to 1e-12" is exactly what Hypothesis or `rapidcheck` express, and a generator beats two hundred hand-picked cases at finding the sign you forgot to clamp.

## E. Practice

<code-exercise src="sys-l4-parity"></code-exercise>

## F. In production

- **Share the fixtures as data, not as code.** A file of inputs and reference outputs that both implementations read means the C++ suite and the Python suite cannot drift apart.
- **Draw fixtures from logs.** Real inputs have the distribution you deploy into, and they include the weird ones you would not have invented.
- **Run the parity suite in CI on both sides**, and make the reference outputs a versioned artifact — which is [12.3](../12-data-infra/03-schema-evolution.md)'s pinned manifest in miniature.
- **Keep the reference forever.** The temptation after a successful port is to delete the Python version. It is the only oracle you have, and its cost is that it sits in a directory.
- **State the parity guarantee in words** in the port's README: which tolerance, over which input range, on which fixture set. A guarantee nobody wrote down gets weakened one commit at a time.
- **Port at a seam and keep it narrow.** A function with array-in, array-out has a parity suite; one that mutates shared state does not.

## G. Experiment

Take the parity suite for any port you have and replace its hand-written fixtures with inputs sampled from a real log. Then plot the fixture distribution against the log distribution on the same axes. The gap between those two curves is your untested region, and in the exercise above it was the entire reason the suite was green.

## H. Failure modes

- **A tolerance chosen so the tests pass.** It always can be, and the number it should be is the float-noise floor.
- **Fixtures from the nominal region only.** The failure lives in the region nobody drives in during a demo.
- **NaN-blind comparison.** `nan > tol` is False, and so the harness agrees with itself.
- **One-sided coverage.** A clamp with one bound missing is invisible to a suite that only tests the other sign.
- **Per-step parity presented as trajectory parity.** They are different claims, and only the second is what the robot does.
- **Deleting the reference.** Now the port is the specification, including its bugs.
- **Parity checked once at merge.** Both implementations keep changing; without CI the guarantee expires quietly.

## I. Questions

<quiz-bank src="sys-l4-quiz"></quiz-bank>

## J. References

- Goldberg (1991), *What Every Computer Scientist Should Know About Floating-Point Arithmetic* — the reference for why the 1e-12 row exists and where the 1e-7 row comes from.
- Hypothesis (Python) and rapidcheck (C++) — property-based testing, which is the natural shape for "these two functions agree".
- The `pytest.approx` and `numpy.testing.assert_allclose` documentation, read specifically for their NaN handling, which is a decision each of them makes differently.
- [Lesson 12.2](../12-data-infra/02-replay-determinism.md) — what a closed loop does with the 1e-7 you decided to accept.

## K. Graded work & portfolio extension

**Graded:** the exercise above.

**Portfolio:** build a parity harness for one ported component of your capstone: shared fixtures drawn from your own logs, a tolerance justified in writing, NaN-aware comparison, and a closed-loop check from field-distributed initial conditions. Then publish the parity guarantee as a sentence in the README. The sentence is the deliverable — it is a claim precise enough to be wrong, which is more than most ports have.
