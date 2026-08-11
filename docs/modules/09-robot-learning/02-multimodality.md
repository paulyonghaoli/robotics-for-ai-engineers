# 9.2 Multimodality: why regression averages your demonstrations

**Status:** Code verified · **Prereqs:** lessons 2.1, 9.1 · **Time:** ~2 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Lesson 9.1's failure was about *where* the data comes from. This one is about what happens when the data is perfectly collected and the loss function is still wrong.

Ask ten people to drive around a parked car. Roughly half go left, half go right, and every one of them is correct. Fit a policy to those demonstrations with mean-squared error and it will confidently predict the average of left and right, which is **straight into the car**. The loss is minimized, the validation number looks fine, and the behaviour is a collision that appears in none of the training data.

This is the single clearest reason diffusion policies exist, and it explains a design choice that otherwise looks like fashion: why a generative model — machinery built for images — turned out to be the right tool for predicting robot actions.

## B. Mental model

**MSE regression learns the conditional mean, and the mean of a multimodal distribution usually isn't in it.**

Whenever a task admits several equally valid solutions, its action distribution has multiple modes:

- around an obstacle: left or right
- reaching a target: elbow-up or elbow-down (lesson 2.1's two IK branches, now a data problem)
- grasping a symmetric object: any of several approach angles
- a doorway: pause and let the person pass, or proceed now

Averaging any of these produces an action that is not merely suboptimal but *invalid*. And note what the training loss reports: predicting the mean is exactly what minimizes MSE against a symmetric bimodal target. **The model is doing its job perfectly.** The specification is wrong.

Three families of fix, in increasing sophistication:

1. **Discretize the action space** and classify. A softmax over bins can represent multiple modes, and you sample or take the argmax — you never average. Crude, effective, and what the RT-family VLAs do with action tokens.
2. **Explicit mixtures** — predict a mixture density (means, variances, weights) and sample a component.
3. **Generative models over actions** — diffusion policies, flow matching. These represent arbitrary action distributions and are what the 2026 frontier converged on.

The unifying idea: **model the distribution, don't summarize it.**

## C. Formulation

Given observations \(o\) and expert actions \(a\), MSE training solves

\[
\min_\theta \mathbb{E}\big[\|\pi_\theta(o) - a\|^2\big] \quad\Longrightarrow\quad \pi^*(o) = \mathbb{E}[a \mid o]
\]

The minimizer is the conditional mean — that's the whole problem in one line. For a symmetric bimodal target with modes at \(c \pm d\), the optimal MSE prediction is exactly \(c\): the midpoint, the obstacle, the thing no demonstrator ever did.

Classification over \(K\) discretized bins instead maximizes likelihood over a categorical distribution, whose modes survive. The cost is resolution (bin width) and the loss of natural ordering between adjacent actions — real systems mitigate with fine bins, per-dimension discretization, or a generative model that avoids the trade entirely.

The diffusion-policy formulation learns to reverse a noising process on action sequences, sampling \(a \sim p(a \mid o)\) rather than predicting a point. It costs multiple denoising steps per action, which is why inference latency is a live concern in the frontier research.

### Two perfect strategies, averaged into zero — measured

This lesson's obstacle world makes the mode-averaging failure exact. The
demonstrations are bimodal at ±0.98 — every demonstrator dodged hard left or
hard right, and both choices work:

| Policy | Success |
|---|---|
| Commit to the left mode (−0.98) | 100% |
| Commit to the right mode (+0.98) | 100% |
| Each demo, on its own episode | 100% |
| **The mean of the demos (+0.02)** | **0%** |

The mean of two perfect strategies drives straight into the obstacle every
single time, because the average of "dodge left" and "dodge right" is "don't
dodge", an action *no demonstrator ever took*. The regression loss is
perfectly happy — the mean minimises squared error to the data — and the
minimiser is the one action guaranteed to fail.

One more measurement closes an escape route. Conditioning on the obstacle's
side and averaging within each side still scores **0%** (per-side means of
−0.12 and +0.16), because the left-or-right choice in these demos is *free*,
not determined by the context — demonstrators facing the same obstacle chose
differently. No amount of input conditioning fixes multimodality that lives
in the demonstrators' preferences rather than in the observable state. The
fix has to change the *output* representation: commit to a mode (argmax over
discretised actions), or model the distribution and sample from it, which is
precisely the job diffusion policies and action-chunking transformers exist
to do. When someone asks why modern imitation learning uses generative
policy heads instead of regression, this table is the answer.

## D. From ML to robotics

- **You have met this exact failure.** A regression model on bimodal targets predicting the trough is a standard cautionary tale; robotics just makes the trough a collision instead of a bad forecast.
- **This is why generative modelling arrived in control.** Not because images and actions are alike, but because both need *distributions* rather than point estimates. Diffusion was the mature tool at hand.
- **Mode collapse versus mode averaging** are different diseases with similar symptoms. Averaging (MSE) invents an action nobody took; collapse (a generative model that ignores its conditioning) always picks the same valid mode. The first is dangerous, the second merely inflexible — and telling them apart requires looking at the *distribution* of rollouts, not one trajectory.

## E. Practice

<code-exercise src="rl-l2-averaging"></code-exercise>

## F. In production

RT-1 and RT-2 discretize each action dimension into 256 bins and predict tokens — option 1, at scale. ACT predicts action chunks with an encoder that tolerates multimodality across the chunk. Diffusion Policy (Chi et al., 2023) made option 3 the default for manipulation, and the 2026 world-action models denoise video and actions jointly. The consistent thread across all of them is that **nobody who ships uses plain MSE regression on a multimodal action space.**

## G. Experiment

Take the capstone's global planner in a world with two homotopy classes — a symmetric obstacle with equal-cost routes either side. Log which side A\* picks as you vary the seed; you'll get a bimodal distribution over routes. Now clone it with MSE regression on (state → steering) and watch the cloned policy drive at the obstacle. Then discretize the steering command into 15 bins and re-clone. Same data, same architecture, different loss — and the second one survives.

## H. Failure modes

- **Silent averaging.** Nothing errors. Training loss is at its true minimum. The only signal is behaviour that appears nowhere in the demonstrations, which is why "did the policy do something no demonstrator ever did?" is a genuinely useful diagnostic question.
- **Bins too coarse.** Discretization caps precision at the bin width; a 0.1 rad bin on a task needing 0.02 rad is a different failure.
- **Mode collapse after the fix.** A generative policy that ignores its conditioning always chooses the same mode — safe but rigid, and invisible if you only look at success rate.
- **Averaging *across* demonstrators.** Two operators with different styles create artificial multimodality; sometimes the right fix is conditioning on operator identity rather than a fancier model.
- **Assuming unimodality because the mean looks reasonable.** Plot the action histogram per state before choosing a loss.

## I. Questions

1. *(Concept)* Why is predicting the mean the *correct* solution to the MSE objective, and what does that tell you about where the bug lives?
2. *(Calculation)* Demonstrations go left (+0.8) 60% of the time and right (−0.8) 40%, relative to the obstacle. What does an MSE-trained policy predict, and does it clear an obstacle of half-width 0.5?
3. *(Debugging)* Your policy succeeds on 90% of tasks but on one it consistently does something no demonstrator ever did. What do you plot first?
4. *(System design)* You must pick between 256-bin action discretization and a diffusion policy for a 7-DoF arm at 30 Hz. State the trade and choose.

??? note "Answer sketches"
    **1.** Because the mean minimizes expected squared error by definition — for a symmetric bimodal target the midpoint is the unique minimizer, so the model achieving it is behaving perfectly. The bug therefore lives in the *objective*, not the data, the architecture, or the optimizer. That matters practically: more data, more parameters, and longer training all leave this failure exactly where it was.

    **2.** \(0.6(+0.8) + 0.4(-0.8) = +0.16\) relative to the obstacle centre. With half-width 0.5 the policy needs \(|a| > 0.5\), so it collides — and note that the asymmetry made it *worse* than useless rather than better: the prediction is confidently on the left side yet nowhere near clear of the obstacle. Unequal mode weights shift the average without rescuing it.

    **3.** The histogram of expert actions conditioned on that state. If it's bimodal, you have mode averaging and the loss is the culprit; if it's unimodal, look instead at coverage (lesson 9.1) — the policy may simply be extrapolating there. "Behaviour absent from the demonstrations" is the signature that distinguishes an averaging failure from an ordinary error, because ordinary errors resemble the data.

    **4.** Discretization at 30 Hz. Diffusion needs multiple denoising passes per action, and a 33 ms budget across 7 joints makes that latency the binding constraint — the same trade the 2026 world-action models pay, at 590–800 ms per chunk versus ~190 ms. Take 256 bins per dimension (finer than most tasks need), accept the loss of action ordering, and revisit diffusion if the task turns out to need genuinely correlated multi-joint action sequences rather than per-step mode selection.

### Interactive quiz

<quiz-bank src="rl-l2-multimodal"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Chi et al., *Diffusion Policy* (2023) | paper | intermediate | The paper that made generative action models standard |
| Brohan et al., *RT-1* (2022) | paper | intermediate | Action tokenization — discretization at scale |
| Bishop, *Mixture Density Networks* (1994) | paper | introductory | The original statement of exactly this problem |

## K. Graded work & portfolio extension

**Graded:** the averaging exercise is the module's second core skill, and it recurs whenever an action space admits several valid answers.

**Portfolio:** the section G study on the capstone — same data, same architecture, MSE versus discretized, with the collision rate for each. It's a small, complete experiment demonstrating that you understand loss-function design as a safety property rather than a hyperparameter.
