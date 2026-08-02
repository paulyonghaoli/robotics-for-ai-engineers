# 0.1 What changes when your model moves a robot

**Status:** Code verified · **Prereqs:** ML practitioner background · **Time:** ~1.5 h · **Verified:** 2026-08-01, Python 3.13

---

## A. Why this matters

You already ship models. Robotics will still feel foreign — not because the math is harder, but because four assumptions your ML instincts rest on quietly stop holding. Naming them up front is the fastest way to transfer your skills instead of fighting them.

## B. The four broken assumptions

**1. Your outputs change your inputs (closed loop).**
An ad-ranking model's predictions don't move the users; a robot's predictions move the robot. Act on a belief, and the next sensor reading comes from the *new* state — errors feed back. A 95%-accurate perception model is not "wrong 5% of the time" in a closed loop; it's wrong 5% of the time *in a correlated way that steers you into situations where it's wrong more often*. This is why robotics obsesses over closed-loop evaluation (drive the course, count collisions) instead of offline metrics (mAP on a test set). Offline metrics remain useful — as unit tests, not verdicts.

**2. Latency is correctness.**
In batch ML, a slow correct answer is correct. On a robot traveling 2 m/s, a perfect obstacle detection delivered 300 ms late describes where the obstacle *was* — you have already covered 60 cm. Every robotics subsystem carries a latency budget the way your services carry SLOs, except breaching it doesn't page you, it hits things. (You'll compute these budgets in Module 10.)

**3. The state is hidden and the sensors lie.**
There is no `SELECT pose FROM robot`. Position, velocity, the world map — all are *beliefs* inferred from noisy, biased, occasionally absent sensor data. The entire discipline of state estimation (Module 3) exists because ground truth is unavailable at runtime. Your instinct for hidden-state models and Bayesian inference is the single most transferable thing you own.

**4. Mistakes are physical.**
A bad recommendation wastes a click; a bad trajectory breaks a wrist or a robot. Safety is not a metric to optimize but a constraint to *prove*: watchdogs, envelope limits, fallback behaviors, e-stops. This changes engineering culture — code review in robotics teams reads like avionics review, and "move fast" acquires a literal, unwelcome meaning.

## C. What transfers directly

Your pipeline discipline (sensor pipelines are data pipelines with deadlines), your evaluation rigor (now applied to scenario suites and replay), your distributed-systems experience (a robot *is* a distributed system — Module 6), your Bayesian inference (Module 3 is applied Bayes at 50 Hz), and your deployment/versioning practices (Module 10). You are not starting over; you are re-basing.

## D. Try it — closed-loop error growth

The exercise below makes assumption #1 tangible: the same disturbance, open-loop vs closed-loop. Watch error grow linearly without feedback and stay bounded with it — then break the controller's assumptions and watch feedback fail too.

<code-exercise src="ml0-open-vs-closed"></code-exercise>

## E. Questions

<quiz-bank src="transition-l1-changes"></quiz-bank>

## F. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Thrun et al., *Probabilistic Robotics*, ch. 1 | book | introductory | The canonical framing of uncertainty as the central problem |
| Karpathy, *"Software 2.0"* + robotics-lens critiques | essay | introductory | Where learned components fit in a safety-constrained stack |
| Any incident postmortem from an AV company's safety report | report | intermediate | How closed-loop failure actually unfolds — read one, annotate the loop |
