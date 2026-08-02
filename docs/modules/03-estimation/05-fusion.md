# 3.5 Multi-sensor fusion architecture

**Status:** Code verified · **Prereqs:** lessons 3.1–3.4 · **Time:** ~2 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

You know the filters (3.1–3.3) and the sensors (3.4). Fusion architecture is the *system design* between them: which sensor updates which states, at what rate, with what protection against each other's bad days. This is where estimation stops being an algorithm and becomes engineering — and where your distributed-systems instincts (rates, queues, timestamps, defensive boundaries) earn their robotics keep.

## B. Mental model

One filter, many observers. The state vector is the **single source of truth**; each sensor is a *partial, asynchronous witness* contributing only the rows of \(H\) it can actually testify about: wheel odometry speaks to velocity, GPS to absolute position, the gyro to angular rate, landmarks to pose. The filter's predict step runs at the fastest rhythm (usually IMU-driven); each measurement, whenever it arrives, updates only what it knows.

Three architectural defenses do most of the real-world work:

1. **Innovation gating** — before accepting a measurement, check its NIS (lesson 3.1) against a χ² threshold. A GPS multipath jump 8σ from the prediction isn't "unlikely data" — it's a lying sensor; reject it. Three lines of code, the single highest-value robustness mechanism in estimation.
2. **Delay handling** — sensors report the past (camera pipelines: 50–150 ms). Fusing a stale measurement as if current smears the estimate exactly like lesson 1.1's stale-timestamp bug. Production filters keep a short state history and re-apply updates at the right moment.
3. **Health monitoring** — per-sensor innovation statistics over time. A sensor whose innovations grow biased or inflated is failing; the fusion layer should notice before the robot does.

## C. Mathematical formulation

Nothing new — that's the point. Per sensor \(s\): its own \(h_s, H_s, R_s\); the gate is

\[
y_s^\top S_s^{-1} y_s \;\le\; \chi^2_{d_s}(0.99)
\]

(e.g. 9.21 for a 2-D measurement). Sequential updates: process each sensor's measurement through the same filter one after another — for independent sensor noises this equals the batched joint update, which is what makes the one-filter-many-observers architecture legitimate rather than a hack.

## D. From ML to robotics

- **The fusion filter is a streaming feature store with schema enforcement**: heterogeneous producers, one consistent materialized state, per-producer validation at the boundary. Gating is input validation; health monitoring is data-quality dashboards; the χ² threshold is your anomaly-detection cutoff with actual theory behind it.
- **Rates and staleness are your event-time vs processing-time problem.** The measurement-delay fix (buffer, reorder, re-apply) is watermarking, roughly — robotics just has harder deadlines.
- **Graceful degradation is ensemble thinking**: lose GPS and the system doesn't fail, it *widens* — covariance grows honestly along now-unobserved directions. A fusion stack that keeps reporting tight covariance after losing its absolute sensor is lesson 3.1's overconfident filter at system scale.

## E. Minimal implementation & practice

<code-exercise src="est-l5-gating"></code-exercise>

## F. Robotics-framework implementation

`robot_localization` is this lesson shipped: two EKF instances by convention (an `odom`-frame filter fusing only continuous sensors, a `map`-frame filter adding absolute ones — REP 105's two-guarantee split from lesson 1.3, now at the estimation layer), per-sensor `*_config` matrices choosing rows of \(H\), and `*_rejection_threshold` parameters that are exactly our χ² gates.

## G. Experiment

On the exercise's setup: sweep the gate threshold from 2σ to 10σ under (a) clean data and (b) 5% multipath corruption. Plot RMSE vs threshold for both. Clean: looser is (slightly) better — you're throwing away real information at 2σ. Corrupted: a U-curve with the sweet spot near 3σ. Then kill the absolute sensor entirely mid-run and verify covariance *grows* — the honest-widening check.

## H. Failure modes

- **Gating your way to blindness**: a too-tight gate rejects real measurements after any transient, and a filter that rejects everything coasts on dead reckoning while reporting... whatever its covariance says. Gate rejections must be *monitored*, not just counted.
- **The chicken-and-egg gate death spiral**: filter diverges → all measurements gated as outliers → filter diverges harder. Production systems cap consecutive rejections and force-accept or reinitialize.
- **Double-counting correlated sensors**: two "independent" estimates derived from the same wheel encoders fused as independent → overconfidence (the spinning-robot map bug from lesson 4.1, at fusion scale).
- **Frame mixing**: fusing a `map`-frame position into an `odom`-frame filter — Module 1's conventions, final boss form.

## I. Questions

1. *(Concept)* Why does sequential per-sensor updating equal the joint batched update — and what assumption breaks it?
2. *(Calculation)* A 2-D GPS innovation has NIS = 14. Gate at χ²(0.99) = 9.21: accept or reject, and what does 14 *mean* in σ terms?
3. *(Debugging)* After a hard bump, your robot's filter rejects every GPS fix for 30 s, then snaps 2 m sideways. Reconstruct the sequence.
4. *(System design)* Design the fusion for the capstone robot gaining a magnetometer: which states does it update, what gate, and what happens near the loading dock's steel door (lesson 3.4, Q3)?

??? note "Answer sketches"
    **1.** Each update is exact Bayesian conditioning, and conditioning on independent measurements factorizes: \(p(x \mid z_1, z_2) \propto p(z_1 \mid x)\, p(z_2 \mid x)\, p(x)\). So folding in sensor 1 and then using that posterior as the prior for sensor 2 lands on the same Gaussian as one stacked update with block-diagonal \(R\). The assumption that breaks it is exactly that block-diagonality — correlated sensor noise (two estimates derived from the same wheel encoders, or a shared clock/calibration error) gets counted twice and the filter comes out overconfident.

    **2.** Reject: 14 > 9.21. NIS is a squared Mahalanobis distance, so 14 is \(\sqrt{14} \approx 3.7\sigma\) against a gate sitting at \(\sqrt{9.21} \approx 3.0\sigma\). For 2 degrees of freedom the tail is exactly \(e^{-x/2}\), so \(P(\text{NIS} > 14) = e^{-7} \approx 9\times10^{-4}\) — under the assumed model this is a 1-in-1100 event, which is far better explained by a lying sensor (multipath) than by unlucky data.

    **3.** The bump jolted the state; honest GPS now looks like an outlier (gate death spiral); dead reckoning drifts 2 m; eventually an innovation squeaks under the gate — or a rejection cap fires — and the filter lurches to reality. Fix: consecutive-rejection cap + covariance inflation on impact detection.

    **4.** The magnetometer testifies to one thing only — yaw — so it gets a single row of \(H\) touching heading (and the gyro bias states only indirectly, through the filter's own correlations); it must never be allowed to nudge position or velocity. Gate it at 1-D \(\chi^2(0.99) = 6.63\) on a *wrapped* angular residual, behind a hard pre-gate on field magnitude and inclination versus the surveyed local field. Near the steel door the field bends and the innovations go persistently biased rather than noisy, so the gate starts rejecting — which is the correct behaviour: coast on the gyro and let yaw covariance widen honestly. Crucially, the consecutive-rejection cap from failure mode 2 must *not* force-accept here, because the disturbance is a sustained bias, not a transient; disable the sensor by magnetic-anomaly detection or a mapped no-mag zone instead.

### Interactive quiz

<quiz-bank src="estimation-l5-fusion"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Bar-Shalom et al., *Estimation with Applications to Tracking* | book | advanced | Gating, association, and consistency — the professional depth |
| [`robot_localization` wiki](https://docs.ros.org/en/melodic/api/robot_localization/html/index.html) | docs | intermediate | The architecture as configuration surface |
| Moore & Stouch (2016), the `robot_localization` paper | paper | introductory | Short, and explains the two-filter REP 105 convention |

## K. Graded work & portfolio extension

**Graded:** gating joins the localization project as a stretch goal (corrupted-measurement scenario).

**Portfolio:** the section G threshold-sweep U-curve, clean vs corrupted — a one-figure demonstration that you understand robustness as a *tuned trade*, not a checkbox.
