# 0.5 Lab: from the notebook to the robot

**Status:** Code verified · **Prereqs:** lesson 0.1 · **Time:** ~1.5 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this lab exists

[Lesson 0.1](01-what-changes.md) lists four assumptions that stop holding when
a model starts driving something. Reading them is easy, and reading them
produces a comfortable feeling of understanding that does not survive contact
with a real symptom.

The skill this lab builds is different: recognising one of those four
assumptions **from a symptom**, at eleven at night, when three plausible
explanations are on the table and one of them is "buy a better sensor". That
is genuinely hard, because in every case here the wrong explanation is
reasonable, well-supported by the evidence you have, and expensive.

So the lab gives you three systems that fail on a robot, each with an offline
story that looks entirely convincing. In all three, **the code is wrong about
the world, not the model weak about the data.** And in all three the obvious
remedy — more data, a better camera, a re-tuned gain — makes no difference
whatsoever, which is exactly why teams spend months on them.

!!! note "How to work through this lab"

    Each exercise gives you a *probe*: a few lines of output from the running
    system. Read the probe before reading the code. The diagnosis is
    available from the numbers alone in every case, and the habit of reading
    instrumentation before reading source is most of what makes debugging
    fast.

    Then fix the code so the tests pass. The tests do not check that you
    produced a particular number; they check that your evaluation is now
    asking the right question.

## B. The diagnostic table

Keep this open while you work. It is the compressed version of what the lab
teaches, and it is worth returning to whenever a real system surprises you.

| Symptom | The tempting explanation | The assumption that actually broke |
|---|---|---|
| Great held-out metric, fails immediately on the robot | overfitting; collect more data | **your outputs change your inputs** — it was scored on someone else's states |
| Fails at speed, fine when slowed down | perception isn't accurate enough at speed | **latency is correctness** — the measurement describes the past |
| Selection script picked a controller that broke something | bad luck; tighten the threshold | **mistakes are physical** — a constraint was averaged into an objective |
| Estimate looks perfect in replay, drifts live | model mismatch | **the state is hidden** — replay had ground truth available |

The fourth row has no exercise here; it arrives properly in Module 3. The
first three follow.

## C. Bug 1 — the metric that said 100%

!!! note "Terms defined here"

    **Behavioural cloning** — training a policy by supervised learning on
    (state, action) pairs recorded from an expert. The simplest way to learn
    a controller, and the one whose failure mode this exercise is about.

    **Covariate shift** — the input distribution at deployment differs from
    the input distribution in training. Here it is not an accident of data
    collection: the policy *causes* the shift by acting.

    **Action agreement** — the fraction of states where the policy's action
    is within some tolerance of the expert's. A standard offline metric for
    a cloned policy.

<code-exercise src="tr-l5-offline-metric"></code-exercise>

The policy scores **100% action agreement** on a genuinely held-out set — a
perfect score, not a good one — and the car ends up about **52 m outside a
1 m lane**.

It is worth being clear about why this is not overfitting, because that is
where everyone's mind goes first. The policy is not memorising. On its
training range it reproduces the expert *exactly* — the two functions are
literally equal for \(|y| \le 0.7\), so there is no approximation error to
blame at all. Every conventional diagnostic for overfitting comes back clean,
because there is no overfitting.

What breaks is the test set's provenance. It contains the states the
**expert** drove through, and the policy will never occupy those states once
it is the one steering. Its own small deviations take it somewhere slightly
different, the next state is generated from *there*, and the process
compounds. The gust in this world is one the expert recovers from without
difficulty; the policy cannot, because recovery states never appear in data
collected by someone who never needed to recover.

That last sentence is the entire problem in one line, and it generalises:
**an expert's demonstrations systematically omit the situations that only
non-experts get into.**

The gap between "accurate on the data" and "competent in the loop" is the
whole of [Module 9](../09-robot-learning/01-behavior-cloning.md), met here on
day one.

## D. Bug 2 — the perfect detector that was too late

<code-exercise src="tr-l5-stale-estimate"></code-exercise>

The detector is **exact**. Zero error, every frame, no noise. The robot still
hits things at 2 m/s and stops safely at 1 m/s.

Read that symptom the way a team actually would: perception degrades at speed.
Motion blur, maybe; shorter reaction window; the model was probably trained on
slower footage. Every one of those is a sensible hypothesis and every one
sends somebody shopping for a better camera.

It is arithmetic. The pipeline is 0.30 s from photon to detection on the bus —
six ticks at 50 Hz — and the reported gap is therefore the gap as it was
0.30 s ago:

| Speed | Distance covered in 0.30 s | Error in the reported gap |
|---|---|---|
| 1.0 m/s | 0.30 m | 0.30 m |
| 1.5 m/s | 0.45 m | 0.45 m |
| 2.0 m/s | 0.60 m | 0.60 m |

A perfect measurement of where the obstacle *was* is a 0.60 m error about
where it *is*, and the error scales linearly with speed while the available
braking distance scales with the square of it. That is why the failure has a
threshold: below some speed the margin absorbs the staleness, above it the
margin does not.

The fix is not a better sensor and it is not a bigger safety margin. It is to
**propagate the measurement forward** by the known latency before using it —
you know how old the reading is and you know how fast you are going, so you
can predict where the obstacle is now. Latency you can measure is latency you
can compensate. Latency you have not measured is the one that kills you, which
is why Module 13 spends a whole lesson on measuring it.

## E. Bug 3 — the average that shipped the wrong controller

!!! note "Terms defined here"

    **Envelope** — a certified physical limit: maximum speed, force, reach,
    or joint angle. Leaving it is not a quality problem, it is a safety
    event.

    **Violation** — a moment the system left that envelope. Counted, not
    averaged, in any correct treatment.

<code-exercise src="tr-l5-mean-hides-it"></code-exercise>

The selection script has worked for a year. It ranks candidates on
`mean_error + 0.01 * mean_violations` and picks the smallest. Here is what
it actually computes:

| Candidate | Mean tracking error | Total violations (40 episodes) | Penalty term | Score |
|---|---|---|---|---|
| reckless | 0.0801 | **7** | 0.0017 | **0.0818** ← selected |
| aggressive | 0.1101 | 1 | 0.0003 | 0.1103 |
| conservative | 0.1492 | 0 | 0.0000 | 0.1492 |

Look at the magnitudes rather than the ranking. The reckless candidate's
accuracy advantage over the next one is \(0.1101 - 0.0801 = 0.030\). Its
entire safety penalty — for **seven** envelope violations — is 0.0017. The
accuracy advantage is roughly **twenty times larger than the total cost of
seven safety violations.**

The tempting fix is a bigger weight. It does not work, and the reason is
structural rather than numerical: *any* finite weight can be bought back by
enough accuracy. Whatever coefficient you choose, a candidate that is
sufficiently precise will out-score a candidate that is safe, because you have
declared safety and accuracy to be commensurable and they are not. Averaging a
hard constraint over forty episodes is how a physical limit becomes a rounding
error.

The correct response is to change the shape of the computation, not its
coefficients: **filter, then rank.** Discard every candidate with a violation.
Rank whatever survives on accuracy. And if nothing survives, the correct
output is *"none of these are shippable"* — which is a valid answer that a
weighted sum is structurally incapable of producing.

## F. Diagnosis drills

<quiz-bank src="tr-l5-drills"></quiz-bank>

## G. Debrief: three questions worth carrying

The three bugs are instances of three general questions. The questions are the
transferable part.

**1. Ask where the data came from before asking what the model did with it.**

Bug 1 is invisible until you notice who generated the evaluation states. The
question — *whose actions produced these states?* — is the dividing line
between an offline metric and a closed-loop one, and it is the question behind
all of [Module 10](../10-evaluation/01-statistical-rigor.md). It applies well
beyond robotics: any time a model is evaluated on data produced by a different
policy than the one being deployed, this bug is available.

**2. When a failure scales with speed, suspect time, not accuracy.**

Bug 2's signature is that slowing down fixes it. Anything that improves when
you go slower is about *how long something takes*, not how correct it is.
This is a strong diagnostic because it is cheap: you can test it in five
minutes, and it separates a whole class of causes from another whole class.

It has a corollary worth knowing: slowing the robot down is a real fix, it
does work, and nobody wants to ship it. A great deal of robotics engineering
is the effort to avoid this particular concession.

**3. Constraints and objectives are different kinds of thing.**

Bug 3 puts a safety limit inside a weighted sum, where it can always be traded
away. This is not a tuning error and no amount of tuning addresses it. A
constraint partitions the candidates into acceptable and unacceptable; an
objective orders the acceptable ones. Collapsing the two is a category error
that happens constantly because a single scalar score is so convenient.

[Lesson 11.5](../11-deployment/05-safety-cases.md) builds the whole
safety-case argument on this distinction.

## H. Graded work and portfolio extension

**Graded.** The three fixes are Module 0's diagnostic assessment. Note that
none of them require robotics knowledge you do not already have — no
kinematics, no filtering, no control theory. They require noticing which
assumption stopped holding. That is deliberate: the barrier at this stage is
not technical background, it is a habit of thought.

**Portfolio.** Take bug 1 further and plot the divergence curve: worst \(|y|\)
against rollout length, for several per-step error magnitudes. The family of
curves shows the \(O(\varepsilon T^2)\) shape that
[lesson 9.1](../09-robot-learning/01-behavior-cloning.md) derives — measured
rather than asserted. It makes a good first portfolio figure because it
explains a real and slightly counter-intuitive phenomenon with about twenty
lines of code, and because the quadratic shape is visible by eye once plotted.

## I. Annotated references

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Ross & Bagnell, *Efficient Reductions for Imitation Learning* (2010) | paper | intermediate | The formal version of bug 1, including where the \(O(\varepsilon T^2)\) bound comes from |
| Ross, Gordon & Bagnell, *A Reduction of Imitation Learning to No-Regret Online Learning* (2011) | paper | intermediate | DAgger — the standard fix for bug 1, covered in Module 9 |
| Leveson, *Engineering a Safer World*, ch. 2 | book | introductory | Why bug 3 is a category error rather than a tuning problem, argued far more thoroughly than here |
