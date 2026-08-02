# 3.3 The extended Kalman filter: living with nonlinearity

**Status:** Code verified · **Prereqs:** lessons 3.1, 2.1 (Jacobian intuition) · **Time:** ~2.5 h · **Verified:** 2026-08-01, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

The linear Kalman filter's model — \(x' = Fx\), \(z = Hx\) — describes almost no real robot. Motion involves \(\cos\theta\); a range sensor measures \(\sqrt{dx^2 + dy^2}\); a bearing involves \(\operatorname{atan2}\). The **EKF** keeps the KF's machinery and feeds it *linearizations*: run the nonlinear functions for the actual numbers, use their Jacobians for the covariances. It is the default estimator of production robotics — `robot_localization`, visual-inertial odometry, most EKF-SLAM lineage — and its failure modes are the field's favorite interview territory.

## B. Mental model

**The EKF is the KF running on a first-order Taylor expansion, re-derived at every step.** Where the KF trusts \(F\) and \(H\) globally, the EKF says: *near where I currently believe I am*, the world is approximately linear — use that tangent plane for this one step, then re-linearize. The approximation is excellent when uncertainty is small relative to the curvature of your models, and degrades — sometimes catastrophically — when the belief is wide enough that the tangent plane and the true surface disagree across it. Hence the folk rule: **EKF for tracking (tight belief), particle filter for global localization (wide belief)** — which is exactly how our project and the capstone split the work.

## C. Mathematical formulation

Nonlinear models \(x_k = f(x_{k-1}, u_k) + w\), \(z_k = h(x_k) + v\). The recursion:

\[
\begin{aligned}
\textbf{predict:} \quad & x \leftarrow f(x, u), \qquad P \leftarrow F P F^\top + Q, \qquad F = \left.\tfrac{\partial f}{\partial x}\right|_{x} \\
\textbf{update:} \quad & y = z \ominus h(x), \quad S = H P H^\top + R, \quad K = P H^\top S^{-1} \\
& x \leftarrow x + K y, \qquad P \leftarrow (I - KH) P, \qquad H = \left.\tfrac{\partial h}{\partial x}\right|_{x}
\end{aligned}
\]

That \(\ominus\) is deliberate: **residuals with angular components must be wrapped** (a bearing residual of \(2\pi - \epsilon\) is really \(-\epsilon\)). The library takes a `residual_fn` for exactly this; the test suite demonstrates the filter degrading when you skip it — Module 1's oldest bug, now wearing an estimation costume.

For the range-bearing observation of landmark \(m\) the Jacobian rows are the worked example everybody should do once by hand:

\[
h(x) = \begin{bmatrix} \sqrt{q} \\ \operatorname{atan2}(\delta_y, \delta_x) - \theta \end{bmatrix},
\qquad
H = \begin{bmatrix} -\delta_x/\sqrt{q} & -\delta_y/\sqrt{q} & 0 \\ \delta_y/q & -\delta_x/q & -1 \end{bmatrix}
\]

with \(\delta = m - x_{1:2}\), \(q = \|\delta\|^2\).

## D. From ML to robotics

- **Linearize-and-solve is your oldest friend:** Newton's method, Gauss–Newton, IRLS — the EKF is that same move applied to Bayesian filtering, with the same pathology: a bad linearization point poisons the step. "EKF diverges when initialized far from truth" *is* "Newton diverges from a bad start."
- **Jacobians by hand vs autodiff:** in ML you stopped writing derivatives in 2015; robotics still writes many by hand for speed and auditability — but modern stacks increasingly autodiff them (JAX/Sophus-style), and checking a hand Jacobian against finite differences is a robotics unit-test idiom worth stealing (our exercise does it to you).
- **The UKF alternative** (propagate a handful of sigma points through the true nonlinearity, refit a Gaussian) is a *derivative-free* method — the same trade as evolutionary strategies vs backprop: no gradients needed, a few extra function evaluations, often better with harsh nonlinearity. Lesson 3.4 material, but the mapping is worth planting now.

## E. Minimal implementation

Library: [`robotics_ai/estimation/ekf.py`](https://github.com/paulyonghaoli/robotics-for-ai-engineers/blob/main/robotics_ai/estimation/ekf.py) — caller-supplied \(f, F, h, H\), Joseph-form update, `residual_fn` hook. The test suite runs a full range-bearing localization and includes a `predict_only_diverges` check — the EKF equivalent of "no measurements, no mercy."

### Practice — write and run code here

<code-exercise src="est-l3-jacobian"></code-exercise>

<code-exercise src="est-l3-ekf-localize"></code-exercise>

## F. Robotics-framework implementation

`robot_localization`'s `ekf_node` is a 15-state (pose, velocity, acceleration) EKF whose YAML config is mostly *which rows of which sensors to fuse* — every checkbox toggles rows of \(H\). Its `mahalanobis_threshold` per sensor is NIS gating from lesson 3.1. When you wire the capstone, this is the node our filter's role maps onto.

## G. Experiment

Initialize the EKF progressively farther from the truth (0.5 m, 2 m, 5 m, plus 90° of heading error) and record convergence rate and failure fraction over 50 seeds. Small offsets: graceful. Large heading error: the linearization points the corrections the wrong way and the filter confidently walks off — *divergence, not noise*. Then hand the identical worst cases to your particle filter from the project and watch it shrug. That pair of plots is the EKF-vs-PF folk rule, earned rather than memorized.

## H. Failure modes

- **Bad initialization → divergence** (see the experiment). The EKF has no mechanism to recover from a wrong basin; production systems bootstrap it with a global localizer.
- **Unwrapped angular residuals** — a single bearing residual near ±π injects a \(\sim 2\pi\) correction; the filter survives it badly or not at all.
- **Jacobian bugs**: sign errors and swapped rows produce filters that *almost* work — innovation monitoring and finite-difference checks are the defense.
- **Overconfident linearization**: covariance shrinks based on the tangent-plane model even where it's a poor fit; symptoms are exactly lesson 3.1's NIS blow-up. The consistency toolkit transfers unchanged.

## I. Questions

1. *(Concept)* Why does the EKF use the nonlinear \(f, h\) for the state but the Jacobians only for the covariance?
2. *(Calculation)* Robot at \((0, 0, 0)\), landmark at \((4, 3)\): evaluate both rows of \(H\).
3. *(Debugging)* Your EKF tracks well until the robot drives directly toward a landmark, then briefly misbehaves. Which entries of \(H\) become ill-conditioned and why?
4. *(System design)* You must estimate 3D pose + velocity + IMU biases (15 states) at 200 Hz on an embedded CPU. EKF, UKF, or PF — and what did each cost you?

??? note "Answer sketches"
    **1.** The mean is a single point, and the best estimate of where that point goes is the true \(f\) and \(h\) — linearizing them would throw away accuracy for nothing. Covariance transport, by contrast, has a closed form only under a *linear* map (\(P \leftarrow F P F^\top + Q\)), so the Jacobian supplies the local tangent plane the Gaussian machinery needs. Nonlinear function for the point, its derivative for the spread.

    **2.** \(\delta = (4, 3)\), \(q = 25\), \(\sqrt{q} = 5\): \(H = \begin{bmatrix} -0.8 & -0.6 & 0 \\ 0.12 & -0.16 & -1 \end{bmatrix}\).

    **3.** As the robot closes on the landmark \(q = \|\delta\|^2 \to 0\), and the bearing row's position entries \(\delta_y/q,\, -\delta_x/q\) blow up like \(1/\|\delta\|\) — at short range a centimetre of lateral error swings the bearing by a large angle, so the linearization is valid over a vanishing neighbourhood and \(S\) becomes ill-conditioned. The range row stays bounded but its direction degenerates too. Fix: gate out landmarks below a minimum range, or drop the bearing row and fuse range-only when \(q\) is small.

    **4.** Take the EKF — in error-state form, IMU-driven propagation, hand-checked Jacobians. The PF is disqualified outright: 15 dimensions means an exponentially infeasible particle count. The UKF would cost \(2n+1 = 31\) sigma points pushed through \(f\) every step at 200 Hz, roughly 31× the propagation work, and it buys accuracy only where the nonlinearity bends appreciably across the belief — which it does not for a well-initialized tight-belief tracking filter on an embedded budget. What the EKF costs you: derivatives you must derive and verify against finite differences, and no recovery from a bad initialization, so budget a separate bootstrap/global-alignment path.

### Interactive quiz

<quiz-bank src="estimation-l3-ekf"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Thrun et al., *Probabilistic Robotics*, ch. 3.3 & 7 | book | intermediate | EKF and EKF localization — this lesson's canonical source |
| Sola (2017), *Quaternion kinematics for the error-state KF* | paper | advanced | The error-state formulation — how attitude EKFs are really built |
| [`robot_localization` docs](https://docs.ros.org/en/melodic/api/robot_localization/html/index.html) | docs | intermediate | The production 15-state EKF's configuration surface |

## K. Graded work & portfolio extension

**Graded:** the localization project's tracking phase is the EKF's home turf — an EKF variant of the project (same harness, `ExtendedKalmanFilter` instead of particles) is the natural stretch goal and planned as extra credit.

**Portfolio:** the initialization-robustness study from section G (EKF vs PF, failure fraction vs initial error) — two estimators, one harness, a quantified folk theorem. Exactly the kind of evidence-over-claims artifact this curriculum exists to produce.
