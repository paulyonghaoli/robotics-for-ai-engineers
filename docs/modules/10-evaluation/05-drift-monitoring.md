# 10.5 Drift monitoring: noticing before the robot does

**Status:** Code verified · **Prereqs:** lessons 3.5, 10.1 · **Time:** ~2 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Every offline evaluation in this module answers a question about the past. Drift monitoring answers the one that matters at 3am: **is the thing running right now still operating in the world it was validated for?**

Robots drift in ways web services don't. Sensors degrade physically — a lens films over, a lidar's returns weaken, a wheel wears and changes its effective radius. Environments change seasonally and by shift. And the robot's own actions change its inputs (lesson 0.1's closed loop), so a slowly-worsening controller produces slowly-shifting sensor statistics, which is a feedback path with no equivalent in batch prediction.

The good news is that you already have the instrument. Module 3 built innovation monitoring — NIS, the normalized measurement surprise — and that same statistic is a production drift detector. You're not learning a new tool here; you're deploying one you have.

## B. Mental model

Three layers, cheapest and earliest first:

1. **Input drift** — are the sensor statistics still what they were? Range histograms, return rates, image brightness. Detects a dirty lens before it affects anything downstream.
2. **Belief drift** — is the estimator still consistent? NIS above its χ² band means the filter's measurements no longer match its model. This is the layer with real theory behind it (lesson 3.6) and it fires before behavior visibly degrades.
3. **Outcome drift** — success rate, intervention rate, collisions. The layer everyone builds first and the *last* to move. By the time success rate drops, the fleet has been degrading for days.

**Detect early, alert on outcomes.** Input drift alone is noisy — lighting changes daily and means nothing. Outcome drift alone is too late. The useful signal is usually a *conjunction*: input statistics shifted **and** NIS rose, so investigate before the success rate follows.

The other half is knowing what your alarm can't see. Lesson 3.6's fourth diagnostic pattern — high NEES with a perfectly healthy NIS — is exactly an error that runtime monitoring is blind to by construction. Monitoring bounds your ignorance; it doesn't eliminate it.

## C. Formulation

**Distribution shift.** For a monitored scalar, compare a recent window against a reference. The Kolmogorov–Smirnov statistic \(D = \sup_x |F_{ref}(x) - F_{win}(x)|\) is the standard nonparametric choice — no distributional assumption, one number, easy to threshold. Population Stability Index is its binned cousin and is what most production dashboards actually plot.

**Sequential detection.** Windowed tests are re-run constantly, so the multiple-comparisons problem is severe: check hourly at α = 0.05 and you false-alarm roughly once a day per metric, forever. Two fixes: require **persistence** (k consecutive windows) and use a **CUSUM**, which accumulates small deviations and signals only when the running sum exceeds a threshold — sensitive to sustained small shifts, resistant to single-window noise.

CUSUM for detecting an upward shift:

\[
S_t = \max(0,\; S_{t-1} + (x_t - \mu_0) - k), \qquad \text{alarm when } S_t > h
\]

with \(k\) a slack term (typically half the shift you care about) and \(h\) the alarm threshold. The slack is what stops noise from accumulating.

## D. From ML to robotics

- **This is model monitoring**, and your instincts transfer wholesale: reference windows, PSI, alert fatigue, the whole discipline. The robotics differences are that inputs degrade *physically* and the feedback loop is closed.
- **NIS is a better drift signal than anything in a typical ML stack** — it's a calibrated statistic with a known distribution under the null, rather than a heuristic threshold on a feature histogram. Robotics has a genuine advantage here and teams routinely fail to use it.
- **Alert fatigue is the actual failure mode**, exactly as in on-call. A monitor everyone mutes is worse than none, because it's mistaken for coverage.

## E. Practice

<code-exercise src="eval-l5-drift"></code-exercise>

## F. In production

`robot_localization` exposes innovation data; `diagnostic_aggregator` is ROS's standard health-reporting path. Fleet operators chart intervention rate per robot per week as the headline outcome metric — the humanoid industry's undisclosed version of this is the number lesson 10.1's frontier research couldn't obtain from anyone. Waymo's published disengagement-adjacent metrics are the same layer, and its remote-assistance ratio (~1 agent per 43 vehicles) is essentially an intervention-rate budget made visible.

## G. Experiment

Run the capstone with a slowly-degrading lidar — multiply `RANGE_SIGMA` by 1.02 each episode. Chart three series: mean measured range (input), mean NIS from the particle filter (belief), and success rate (outcome). You'll see them move in that order, with a real lag between them. That lag is your entire warning budget, and measuring it on your own system is more convincing than any prose about why layered monitoring matters.

## H. Failure modes

- **Alerting only on outcomes** — technically correct, operationally too late.
- **Ignoring multiple comparisons** — hourly tests at α = 0.05 across 20 metrics is ~24 false alarms a day. Persistence requirements and CUSUM exist for this.
- **A stale reference window** — comparing against a window that itself drifted means you detect nothing, having normalized the problem away.
- **Monitoring without ownership** — an alert with no named owner and no runbook is decoration.
- **Trusting NIS alone** — it cannot see unobservable errors (lesson 3.6). Simulation-time NEES auditing is the complement, not a duplicate.

## I. Questions

1. *(Concept)* Why does input drift usually precede outcome drift, and why is the gap the useful part?
2. *(Calculation)* Hourly drift test at α = 0.05 across 20 metrics. Expected false alarms per day?
3. *(Debugging)* NIS rose two weeks ago and stayed high; success rate is unchanged. Ignore it or investigate?
4. *(System design)* Design monitoring for a 50-robot fleet: what's measured at each layer, what pages someone, what only appears on a dashboard, and how the reference window is maintained.

??? note "Answer sketch for Q2"
    \(24 \times 20 \times 0.05 = 24\) false alarms per day — roughly one per hour, from a system where nothing is wrong. This is why persistence requirements and CUSUM are not optional refinements.

### Interactive quiz

<quiz-bank src="eval-l5-drift-quiz"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Page (1954), *Continuous Inspection Schemes* | paper | intermediate | CUSUM from the source |
| Bar-Shalom et al., *Estimation with Applications to Tracking* | book | advanced | Innovation-based consistency monitoring, rigorously |
| [Waymo safety impact](https://waymo.com/safety/impact/) | docs | introductory | Outcome-layer metrics published at fleet scale |

## K. Graded work & portfolio extension

**Graded:** the consistency lab (3.6) is this lesson's offline half; together they're the estimation-monitoring skill set.

**Portfolio:** the section G three-layer lag chart, run on your own capstone. Being able to say "input drift gave us 40 episodes of warning before success rate moved" is a concrete, quantified argument for layered monitoring — and it's your own measurement, not a citation.
