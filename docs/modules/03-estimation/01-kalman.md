# 3.1 The Kalman filter: Bayes at 50 Hz

**Status:** Code verified · **Prereqs:** Module 1, lesson 1.4, probability basics · **Time:** ~3 h · **Verified:** 2026-08-01, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

The robot never knows its state; it maintains a **belief** — a probability distribution over states — and updates it two ways: *predict* (push the belief through the motion model; uncertainty grows) and *update* (fold in a measurement; uncertainty shrinks). When belief, motion, and noise are all Gaussian and linear, this Bayes recursion has a closed form: the Kalman filter, arguably the most-deployed algorithm in robotics. Your GPS+IMU fusion, wheel-odometry smoothing, object trackers — all Kalman variants.

## B. Mental model

The KF is a **precision-weighted average, run recursively**. You have two opinions about the state: your prediction (with covariance \(P\)) and your measurement (with covariance \(R\)). The posterior sits between them, closer to whichever is more confident. The Kalman gain \(K\) *is* that mixing weight — near 0 when the model is trusted, near 1 when the sensor is. Everything else is bookkeeping for correlated, multidimensional beliefs.

The rhythm to internalize:

```
predict:  x ← F x        P ← F P Fᵀ + Q      (uncertainty GROWS by Q)
update:   x ← x + K(z − H x)   P ← (I − KH) P   (uncertainty SHRINKS)
```

The term \(z - Hx\) — the **innovation** — is the measurement's surprise. Healthy filters have small, zero-mean, white innovations; watching them is how you *debug* a filter (section H).

## C. Mathematical formulation

Model: \(x_k = F x_{k-1} + B u_k + w\), \(w \sim \mathcal{N}(0, Q)\); \(z_k = H x_k + v\), \(v \sim \mathcal{N}(0, R)\).

Update in full:

\[
\begin{aligned}
y &= z - H x \quad &\text{(innovation)} \\
S &= H P H^\top + R \quad &\text{(innovation covariance)} \\
K &= P H^\top S^{-1} \quad &\text{(gain)} \\
x &\leftarrow x + K y, \qquad P \leftarrow (I - KH)\, P
\end{aligned}
\]

The library uses the **Joseph form** \(P \leftarrow (I-KH) P (I-KH)^\top + K R K^\top\) — algebraically identical, numerically self-symmetrizing (the naive form slowly loses symmetry and positive-definiteness in float arithmetic).

Consistency: the **NIS** statistic \(y^\top S^{-1} y\) should average ≈ the measurement dimension (it's \(\chi^2\)-distributed). A filter with low RMSE but NIS ≫ dim is *overconfident* — accurate today, dangerously certain tomorrow.

## D. From ML to robotics

- **The KF is exact Bayesian inference in a linear-Gaussian state-space model** — the same model family as a Gaussian HMM with continuous states. Predict/update = the forward algorithm's transition/emission steps in closed form.
- **Q and R are hyperparameters with meaning.** \(R\) you can measure (log a stationary sensor; take the variance). \(Q\) is your admission of model imperfection — tuning it is bias-variance: small Q = smooth-but-laggy (high bias), big Q = jittery-but-responsive (high variance).
- **Innovation monitoring ≈ drift detection.** Whitened residuals leaving their expected distribution is precisely a data-drift alarm on your sensor stream — the NIS is the robotics version of your monitoring dashboard.

## E. Minimal implementation

Library: [`robotics_ai/estimation/kalman.py`](https://github.com/paulyonghaoli/robotics-for-ai-engineers/blob/main/robotics_ai/estimation/kalman.py) — Joseph-form update, optional control input, NIS. Tested on constant-velocity tracking with consistency checks.

### Practice — write and run code here

<code-exercise src="est-l1-kf-1d"></code-exercise>

<code-exercise src="est-l1-kf-cv"></code-exercise>

## F. Robotics-framework implementation

ROS 2's `robot_localization` package runs a 15-state EKF fusing wheel odometry, IMU, and GPS — its config file is essentially "declare H and R per sensor." The capstone will feed our filter's output into the `map → odom` correction edge from lesson 1.3. The **E**xtended KF (linearize F, H around the current estimate) and **U**nscented KF (propagate sigma points) arrive in lesson 3.3; the particle filter for the genuinely non-Gaussian cases is next lesson.

## G. Experiment

On the constant-velocity tracker: multiply your assumed \(R\) by 10 (pessimistic sensor) and by 0.1 (overconfident sensor) while the *actual* noise stays fixed. Watch RMSE degrade mildly when pessimistic and the **NIS explode when overconfident** — the filter that trusts a bad sensor spec doesn't just get worse, it stops *knowing* it's worse. Then repeat for Q. This four-quadrant exercise (Q, R × over, under) is the entire craft of filter tuning.

## H. Failure modes

- **Overconfidence (Q or R too small):** covariance collapses, gain → 0, filter ignores real measurements — it "diverges politely," reporting tiny uncertainty around a wrong state.
- **Innovation bias:** a consistent nonzero-mean innovation means a *modeling* error (sensor bias, miscalibrated H, wrong frame — see Module 1), not noise. No amount of Q/R tuning fixes a bias.
- **Covariance asymmetry from the naive update:** after 10⁵ steps P stops being positive-definite and the filter NaNs. Joseph form or explicit re-symmetrization.
- **Outliers:** one corrupted measurement yanks the linear-Gaussian filter hard. Production filters gate on NIS (reject measurements with NIS > χ² threshold) — three lines that save robots.

## I. Questions

1. *(Concept)* Why does uncertainty grow in predict and shrink in update — and what would it mean if a filter's P never shrank?
2. *(Calculation)* Scalar filter: prediction \(x=5, P=4\); measurement \(z=6, R=1\). Compute K and the posterior.
3. *(Debugging)* RMSE is low but NIS averages 8 on a 1-D measurement. What is wrong and why is it dangerous?
4. *(System design)* GPS (1 Hz, meters of noise, absolute) + IMU (200 Hz, drifting, relative). Sketch the fusion: what does each sensor's update contribute, and why does the combination beat either alone?

??? note "Answer sketches"
    **1.** Predict adds \(Q\) because time passes with no new information and the motion model is imperfect — the belief is pushed forward and smeared. Update is a precision-weighted average of two independent opinions, and combining precisions can only add, so \(P\) strictly shrinks (that's the \((I-KH)\) factor). A \(P\) that never shrinks means \(K \approx 0\): the filter is ignoring its measurements — \(R\) absurdly large, \(H\) wrong or zero in the relevant rows — and is running pure dead reckoning.

    **2.** \(K = 4/(4+1) = 0.8\); \(x = 5 + 0.8(6-5) = 5.8\); \(P = (1-0.8)\cdot4 = 0.8\). The posterior sits 80% of the way to the more-confident measurement.

    **3.** Expected NIS on a 1-D measurement is 1, so an average of 8 says \(S = HPH^\top + R\) is about 8× too small — the filter is overconfident, with \(Q\) and/or \(R\) understated. It's dangerous because the low RMSE is on loan: the gain has collapsed toward 0, so the first real model error or unmodeled maneuver will be met with a filter that ignores exactly the measurements that would correct it, diverging while reporting tiny covariance. Inflate \(Q\) (or fix \(R\) if it was mismeasured) until NIS averages ≈ 1.

    **4.** The IMU at 200 Hz drives predict — smooth, low-latency, and cheap between fixes — but its bias makes position error grow like \(t^2\), so \(P\) inflates fast; the 1 Hz GPS contributes an absolute-position update with a large \(R\) (meters) that resets that accumulated drift every second and, with bias states in \(x\), makes the IMU biases observable. Neither works alone: IMU-only drifts without bound, GPS-only is too slow and too noisy for control and says nothing about attitude. The combination wins because the error structures are complementary — fast-relative and slow-absolute — which is precisely the pair a precision-weighted average exploits best.

### Interactive quiz

<quiz-bank src="estimation-l1-kalman"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Thrun et al., *Probabilistic Robotics*, ch. 3 | book | intermediate | The canonical treatment; read alongside this lesson |
| Labbe, *Kalman and Bayesian Filters in Python* | book/notebooks | introductory | Free, runnable, wonderfully intuitive |
| Sola (2017), §3–6 | paper | advanced | Error-state formulation — read before doing IMU fusion for real |
| Bar-Shalom et al., *Estimation with Applications to Tracking* | book | advanced | NIS/NEES consistency testing, gating — the professional's reference |

## K. Graded work & portfolio extension

**Graded:** the Module 3 **localization project** (in development): fuse odometry + landmarks on the 2D robot, scored on RMSE *and* NIS consistency — accuracy without honesty fails the rubric.

**Portfolio:** the four-quadrant tuning study from section G, plotted (RMSE and NIS vs Q/R scaling). It demonstrates the rarest interview skill: knowing when a filter is *lying to you*.
