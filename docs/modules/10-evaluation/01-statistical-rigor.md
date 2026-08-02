# 10.1 Statistical rigor: how many episodes justify a claim?

**Status:** Code verified · **Prereqs:** the capstone harness; basic probability · **Time:** ~2 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

In 2026 a group at TTIC and UChicago audited the robot-manipulation literature and found that **only about 20% of state-of-the-art claims on the two dominant benchmarks are provably statistically significant**. Real-world robot evaluations typically use **25 rollouts or fewer, with no confidence intervals**. On one benchmark, a **0.09-billion-parameter probe with no language encoder and no robotics pretraining** matched the best published result — and reported scores collapsed from 95% to under 30% when the camera viewpoint moved.

This is not a story about sloppy researchers. It's a story about a field that grew fast around a metric — "success rate" — without the statistical hygiene that makes the metric mean anything. Which means: **the ability to design an honest evaluation is currently a differentiator, not a formality.** It is also, conveniently, a data-engineering skill rather than a modeling one.

You already own a scenario-evaluation harness. This lesson is about using it truthfully.

## B. Mental model

A success rate from N episodes is not a number — it is a **sample from a distribution**. Run the same stack on a different set of random worlds and you'd get a different number. The question that matters is never "what did it score?" but **"what range of true performance is consistent with what I observed?"**

The intuition that does most of the work: **a proportion measured from N samples carries an uncertainty of roughly \(1/\sqrt{N}\).** So:

| Episodes | Rough 95% margin on a ~50% success rate |
|---:|---|
| 10 | ±30 points |
| 25 | ±20 points |
| 100 | ±10 points |
| 400 | ±5 points |

Look at that table next to "25 rollouts, no confidence intervals." A paper reporting 72% vs a baseline's 64% on 25 episodes has measured **nothing** — those intervals overlap almost completely. And 8/8 successes, which our capstone reference stack achieved, does *not* mean 100%: its 95% interval reaches down to about 68%.

**The three questions to ask of any robot performance claim:**

1. **How many episodes, and what's the interval?** (Almost never reported.)
2. **How were the episodes generated** — fixed scenarios the system may have been tuned on, or fresh randomization?
3. **Does it survive perturbation** — moved camera, different initial state, changed lighting? (The LIBERO collapse from 95% to 30% was entirely this.)

## C. Mathematical formulation

For a success rate, the **Wilson score interval** is the right default — the textbook "normal approximation" \(\hat{p} \pm 1.96\sqrt{\hat{p}(1-\hat{p})/n}\) is badly wrong exactly where robotics lives (small n, proportions near 0 or 1, where it can produce intervals extending past 100% or of zero width at 8/8):

\[
\frac{\hat{p} + \frac{z^2}{2n} \pm z\sqrt{\frac{\hat{p}(1-\hat{p})}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}
\]

with \(z = 1.96\) for 95%. For **comparing two stacks**, the cleanest tool is a paired comparison on the *same seeds* — running both stacks on identical worlds removes world difficulty as a variance source and can cut the episodes needed by several-fold. Then a bootstrap over episodes gives you a confidence interval on the *difference*, which is the quantity you actually care about.

For continuous metrics (path ratio, localization RMSE, latency), report **percentiles rather than means** — p95 latency is a service-level statement, while a mean latency hides exactly the tail that breaks real-time systems.

## D. From ML to robotics

- **This is A/B testing, and you have probably done it correctly before.** The robotics twist is that episodes are expensive (a real-robot rollout costs minutes and a human resetter), so the discipline of *paired designs and variance reduction* matters far more than in web experimentation where samples are free.
- **The perturbation-collapse story is distribution shift**, measured. A model at 95% in-distribution and 30% under a viewpoint change hasn't "overfit" in the loss-curve sense — it has been evaluated on the training distribution and reported as if it generalizes.
- **Benchmark saturation is leaderboard overfitting** with a community-sized effective sample. When 79 papers report the same benchmark in a single month, the benchmark stops measuring capability and starts measuring how many people tuned against it.

## E. Practice

<code-exercise src="eval-l1-wilson"></code-exercise>

<code-exercise src="eval-l1-compare"></code-exercise>

## F. In production

- **RoboArena** runs distributed double-blind *pairwise* comparisons on real hardware — pairwise because absolute success rates across labs are not comparable, and blind because evaluator expectation is a real effect.
- **AI2's `vla-evaluation-harness`** standardizes 18 benchmarks behind one interface, the way `lm-eval-harness` did for language models.
- **RoboDojo** goes further and standardizes the *physical* protocol — lighting, workspace layout, scene-reset procedure — because those unstated variables were dominating cross-lab differences.

And the cautionary tale from regulation: California's mandated AV disengagement reports measure a safety-driver **test** fleet that represents under 2% of Waymo's actual driving, with a self-defined event and no severity weighting, so a company testing on easy suburban roads posts better numbers than one probing hard cases. The DMV is retiring the metric. **A metric that measures the wrong population, self-defines its event, and rewards easy testing is a design failure — study it before writing your own rubric.**

## G. Experiment

Run the capstone's reference stack at `--episodes 8`, then 32, then 128, recording the success rate and its Wilson interval at each. Watch the point estimate wobble while the interval tightens — and note how many episodes you actually needed before you could distinguish it from a hypothetical 85% competitor. Then re-run 8 episodes with five different `--seed` values and observe the spread of point estimates you could have reported by choosing a seed. That spread is the size of the claim you cannot make.

## H. Failure modes

- **Seed shopping** — running until a good seed appears. The exercise's tests deliberately check a second seed for exactly this reason, and so should your rubrics.
- **Tuning on the evaluation set.** Our graders randomize scenario parameters per run precisely so a stack tuned to one world fails the next.
- **Reporting the mean of a heavy-tailed metric.** Mean latency looks fine while p99 blows the control deadline.
- **Comparing across labs.** Different reset procedures, lighting, and object sets make absolute numbers incomparable; this is why RoboArena went pairwise.
- **Silent truncation.** Dropping timed-out episodes from the average turns a failure mode into a rounding error.

## I. Questions

1. *(Concept)* Why is the normal-approximation interval especially wrong at 8/8 successes, and what does Wilson give instead?
2. *(Calculation)* A stack succeeds in 18 of 25 episodes. Estimate the 95% margin. Can you distinguish it from a 60% baseline?
3. *(Debugging)* A colleague's stack scores 90% on their suite and 55% on yours, same code. List four candidate causes before concluding either suite is wrong.
4. *(System design)* You have a 4-hour nightly CI budget; one episode takes 30 seconds. Design the regression suite: how many scenarios, how many repeats, what gets reported, and what triggers a build failure?

??? note "Answer sketch for Q2"
    \(\hat{p} = 0.72\), \(n = 25\): margin ≈ \(1.96\sqrt{0.72 \cdot 0.28 / 25} \approx 0.176\) — roughly ±18 points, so about 54%–90%. That interval contains 60%, so **no**, you cannot distinguish it from the baseline. This is the arithmetic behind the field's 20%-significance finding.

### Interactive quiz

<quiz-bank src="eval-l1-rigor"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| ["What Are We Actually Benchmarking in Robot Manipulation?" (arXiv:2606.04233)](https://arxiv.org/pdf/2606.04233) | paper | intermediate | The 2026 audit this lesson is built on — read it in full |
| [RoboArena (arXiv:2506.18123)](https://arxiv.org/abs/2506.18123) | paper | intermediate | Why the field went pairwise and double-blind |
| Wilson (1927) | paper | introductory | The interval, from the source — two pages |
| [LIBERO-Plus (arXiv:2510.13626)](https://arxiv.org/abs/2510.13626) | paper | intermediate | The 95%→30% perturbation collapse, systematically |

## K. Graded work & portfolio extension

**Graded:** the capstone rubric is a scenario evaluation; adding confidence intervals to `python -m eval` output is the natural first contribution.

**Portfolio:** publish a proper evaluation of your own capstone stacks — v0 vs v1 vs v2, paired on identical seeds, with bootstrap confidence intervals on the differences and an explicit statement of what the sample size does *not* let you claim. In a field where 80% of published claims can't clear that bar, doing it correctly on your own work is a genuinely differentiating artifact.
