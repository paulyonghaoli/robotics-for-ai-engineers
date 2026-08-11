# 3.3 The extended Kalman filter: living with nonlinearity

**Status:** Code verified · **Prereqs:** lessons 3.1, 2.1 (Jacobian intuition) · **Time:** ~2.5 h · **Verified:** 2026-08-01, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

The linear Kalman filter's model, \(x' = Fx\) and \(z = Hx\), describes almost
no real robot. Motion involves \(\cos\theta\) because the robot's heading
determines which way "forward" points, a range sensor measures
\(\sqrt{dx^2 + dy^2}\), and a bearing involves `atan2`. None of those are
linear, and pretending otherwise produces a filter that is confidently wrong
the moment the robot turns.

The extended Kalman filter keeps all of the Kalman machinery and feeds it
*linearisations*: run the genuinely nonlinear functions to propagate the state,
and use their Jacobians wherever the covariance arithmetic needs a matrix. It
is the default estimator of production robotics, underpinning
`robot_localization`, most visual-inertial odometry, and the whole EKF-SLAM
lineage, and its failure modes are among the field's favourite interview
topics.

!!! note "Terms defined here"

    **Linearisation** — replacing a nonlinear function by its tangent plane
    at a particular point, which is a first-order Taylor expansion.

    **Jacobian** — the matrix of partial derivatives that defines that tangent
    plane. Lesson 2.3 is the same object in a kinematic setting.

    **Divergence** — the filter's estimate walking away from the truth while
    its reported covariance stays small, as opposed to merely being noisy.

    **Error-state formulation** — tracking the small error relative to a
    nominal trajectory rather than the state itself, which is how attitude
    filters are really built.

    **UKF** (unscented Kalman filter) — a derivative-free alternative that
    pushes a handful of sample points through the true nonlinearity instead of
    differentiating it.

## B. Mental model

The extended Kalman filter is the ordinary Kalman filter running on a
first-order Taylor expansion that is re-derived at every single step.

Where the linear filter trusts \(F\) and \(H\) globally, the extended version
makes a much weaker claim: *near where I currently believe I am*, the world is
approximately linear, so let me use that tangent plane for this one step and
then re-linearise at wherever I end up. The approximation is excellent when the
uncertainty is small relative to how sharply the models curve, and it degrades,
sometimes catastrophically, when the belief is wide enough that the tangent
plane and the true surface disagree materially across it.

<figure class="rai-fig" markdown>
![Two panels showing the same square-root measurement function and its tangent line at x=4. In the left panel a narrow band of uncertainty is shaded and the tangent tracks the curve closely across it. In the right panel a wide band is shaded and the tangent departs substantially from the curve at both ends.](../../assets/generated/figures/ekf-linearization-light.svg){.fig-light}
![Two panels showing the same square-root measurement function and its tangent line at x=4. In the left panel a narrow band of uncertainty is shaded and the tangent tracks the curve closely across it. In the right panel a wide band is shaded and the tangent departs substantially from the curve at both ends.](../../assets/generated/figures/ekf-linearization-dark.svg){.fig-dark}
<figcaption markdown>The same function, the same linearisation point, and two different beliefs. Nothing about the filter changed between the panels — only how uncertain it is — and that alone decides whether the approximation is sound.</figcaption>
</figure>

That figure is the whole justification for the field's folk rule: **use an EKF
for tracking, where the belief is tight, and a particle filter for global
localisation, where it is wide.** It is exactly how the Module 3 project and
the capstone split the work between them, and section G asks you to earn the
rule rather than accept it.

## C. Mathematical formulation

With nonlinear models \(x_k = f(x_{k-1}, u_k) + w\) and \(z_k = h(x_k) + v\),
the recursion becomes

\[
\begin{aligned}
\textbf{predict:} \quad & x \leftarrow f(x, u), \qquad P \leftarrow F P F^\top + Q, \qquad F = \left.\tfrac{\partial f}{\partial x}\right|_{x} \\
\textbf{update:} \quad & y = z \ominus h(x), \quad S = H P H^\top + R, \quad K = P H^\top S^{-1} \\
& x \leftarrow x + K y, \qquad P \leftarrow (I - KH) P, \qquad H = \left.\tfrac{\partial h}{\partial x}\right|_{x}
\end{aligned}
\]

The \(\ominus\) is deliberate rather than decorative, because **residuals with
angular components must be wrapped**. A bearing residual of \(2\pi - \epsilon\)
is really \(-\epsilon\), and feeding the unwrapped value into the update
injects a correction roughly \(2\pi\) too large. The library takes a
`residual_fn` for precisely this purpose and its test suite demonstrates the
filter degrading when you omit it, which makes this Module 1's oldest bug
wearing an estimation costume.

For a range-and-bearing observation of a landmark \(m\), with
\(\delta = m - x_{1:2}\) and \(q = \|\delta\|^2\), the measurement function and
its Jacobian are the worked example everyone should do by hand once:

\[
h(x) = \begin{bmatrix} \sqrt{q} \\ \operatorname{atan2}(\delta_y, \delta_x) - \theta \end{bmatrix},
\qquad
H = \begin{bmatrix} -\delta_x/\sqrt{q} & -\delta_y/\sqrt{q} & 0 \\ \delta_y/q & -\delta_x/q & -1 \end{bmatrix}
\]

Read the second row before moving on, because the \(1/q\) scaling is what
question 3 is about: as the robot approaches a landmark, those entries grow
without bound.

## D. From ML to robotics

Linearise-and-solve is your oldest friend under another name. Newton's method,
Gauss–Newton and iteratively reweighted least squares are all the same move,
and the extended Kalman filter applies it to Bayesian filtering with exactly
the same pathology: a bad linearisation point poisons the step. The observation
that an EKF diverges when initialised far from the truth *is* the observation
that Newton's method diverges from a bad starting guess.

On Jacobians by hand against automatic differentiation, machine learning
stopped writing derivatives by hand around 2015 while robotics still writes
many of them, for the defensible reasons of speed inside a hard real-time loop
and auditability of code that can hurt someone. Modern stacks increasingly
autodiff them anyway, and checking a hand-derived Jacobian against finite
differences is a robotics unit-test idiom worth stealing, which the exercise
below makes you do.

The unscented alternative, which propagates a small set of sigma points through
the true nonlinearity and refits a Gaussian, is a derivative-free method, and
the trade is the same one as evolutionary strategies against backpropagation:
no gradients required, a few extra function evaluations, and often better
behaviour when the nonlinearity is harsh.

## E. Minimal implementation

The library lives at
[`robotics_ai/estimation/ekf.py`](https://github.com/paulyonghaoli/robotics-for-ai-engineers/blob/main/robotics_ai/estimation/ekf.py),
taking caller-supplied \(f\), \(F\), \(h\) and \(H\), performing a Joseph-form
update and exposing the `residual_fn` hook. The test suite runs a complete
range-and-bearing localisation and includes a `predict_only_diverges` check,
which is the EKF equivalent of confirming that no measurements means no mercy.

### Practice — write and run code here

<code-exercise src="est-l3-jacobian"></code-exercise>

<code-exercise src="est-l3-ekf-localize"></code-exercise>

## F. Robotics-framework implementation

`robot_localization`'s `ekf_node` is a fifteen-state filter covering pose,
velocity and acceleration, and its YAML configuration is mostly a matter of
declaring which rows of which sensors to fuse, so every checkbox in that file
toggles rows of \(H\). Its per-sensor `mahalanobis_threshold` is the NIS
gating from lesson 3.1 under a different name. When you wire up the capstone,
this node is what your filter's role corresponds to.

## G. Experiment — interrogate the folk rule, and find it incomplete

The folk rule says the EKF diverges when initialised far from the truth. Run
the experiment and something more interesting happens: initialise the
range-bearing localiser at 2 m, 5 m, 90° of heading error, even 5 m *plus*
180°, across fifty seeds each — and with three landmarks observed every step,
**it recovers every single time**, to a median final error of 4 cm, even when
\(P_0\) falsely claims centimetre confidence. The measurement geometry here is
simply too strong: three simultaneous range-bearing pairs constrain the pose
from three directions, the innovations are enormous, and the state gets
dragged to the truth before the bad linearisation can do sustained damage.

So bad initialisation alone did not kill it, and overconfidence alone did not
kill it. Now add the one ingredient every production filter has and this clean
experiment lacked: **innovation gating**, at the standard
\(\chi^2_2(0.99) = 9.21\) from lesson 3.5.

| Initialisation, with gating on | Failure rate (50 seeds) | Median error | Measurements rejected |
|---|---|---|---|
| 2 m off, honest \(P_0\) | 0/50 | 0.039 m | 1% |
| 2 m off, confident \(P_0\) | 6/50 | 0.043 m | 43% |
| 90° off, confident \(P_0\) | **50/50** | **5.70 m** | **93%** |
| 2 m + 90°, confident \(P_0\) | **50/50** | 4.60 m | 91% |

There is the divergence — permanent, total, and with a mechanism you can now
name precisely. The confident \(P_0\) makes every honest measurement look like
a 20-sigma outlier, the gate faithfully rejects 93% of them, and the filter
dead-reckons forever inside a bubble of its own certainty. It is lesson 3.5's
death spiral, seeded by initialisation instead of by a bump.

The refined rule is worth stating carefully, because it is more useful than
the folk version: **divergence is a conjunction.** Bad initialisation, an
overconfident covariance, and a rejection mechanism — in this well-observed
regime, any two of the three are survivable, and all three together are fatal
in every seed. (With sparser measurements — one landmark, intermittent
fixes — the linearisation itself can create wrong basins and the conjunction
shrinks; observability buys you slack.) The practical consequences read
straight off the table: initialise \(P\) to reflect what you actually know,
never less; cap consecutive gate rejections; and if you must guess between an
honest-but-wide \(P_0\) and a flattering one, the wide one costs a few
transient updates while the flattering one can cost the mission.

Then hand the 90°-with-gating case to the particle filter from lesson 3.2 and
watch it shrug, since fifty of its four hundred hypotheses are always near
enough to the truth to be upweighted. That pair of results — not "EKF fragile,
PF robust," but *this specific conjunction kills the EKF and cannot kill the
PF* — is the earned version of the folk rule, and the portfolio artifact in
section K.

## H. Failure modes

**Bad initialisation leading to divergence** is the headline, with section
G's refinement: in a well-observed system it takes the conjunction of a bad
state, an overconfident covariance and a gate, and production filters have all
three ingredients on hand at every startup. The structural point stands — once
inside the spiral, the EKF has no mechanism for escaping it — which is why
production systems bootstrap with a global localiser rather than hoping.

**Unwrapped angular residuals** inject a correction of roughly \(2\pi\) from a
single bearing measurement near \(\pm\pi\), and the filter survives it badly
or not at all.

**Jacobian bugs**, particularly sign errors and swapped rows, produce filters
that *almost* work, which is the worst possible outcome because they pass
casual inspection. Innovation monitoring and finite-difference checks are the
defence, and both are cheap.

**Overconfident linearisation** shrinks the covariance according to a tangent
plane that does not fit, and its symptoms are exactly lesson 3.1's NIS
blow-up, so the consistency toolkit transfers across unchanged.

## I. Questions

1. *(Concept)* Why does the EKF use the nonlinear \(f\) and \(h\) for the
   state but the Jacobians only for the covariance?
2. *(Calculation)* Robot at \((0, 0, 0)\) and landmark at \((4, 3)\):
   evaluate both rows of \(H\).
3. *(Debugging)* Your EKF tracks well until the robot drives directly toward a
   landmark, then briefly misbehaves. Which entries of \(H\) become
   ill-conditioned, and why?
4. *(System design)* You must estimate 3D pose, velocity and IMU biases,
   fifteen states in total, at 200 Hz on an embedded CPU. EKF, UKF or particle
   filter, and what did your choice cost you?

??? note "Answer sketches"
    **1.** The mean is a single point, and the best available estimate of where
    that point goes is the true \(f\) and \(h\), so linearising them would
    discard accuracy for no benefit. Covariance transport is different: it has
    a closed form only under a *linear* map, namely
    \(P \leftarrow F P F^\top + Q\), so the Jacobian is needed to supply the
    local tangent plane that the Gaussian machinery requires. The nonlinear
    function moves the point; its derivative moves the spread.

    **2.** With \(\delta = (4, 3)\), \(q = 25\) and \(\sqrt{q} = 5\):
    \(H = \begin{bmatrix} -0.8 & -0.6 & 0 \\ 0.12 & -0.16 & -1 \end{bmatrix}\).

    **3.** As the robot closes on the landmark, \(q = \|\delta\|^2 \to 0\) and
    the bearing row's position entries \(\delta_y/q\) and \(-\delta_x/q\) grow
    like \(1/\|\delta\|\). Physically, at short range a centimetre of lateral
    error swings the bearing through a large angle, so the linearisation is
    valid only over a vanishing neighbourhood and \(S\) becomes
    ill-conditioned. The range row stays bounded but its direction degenerates
    as well. The fix is to gate out landmarks below a minimum range, or to drop
    the bearing row and fuse range only when \(q\) is small.

    **4.** Take the EKF, in error-state form, with IMU-driven propagation and
    hand-checked Jacobians. The particle filter is disqualified outright,
    because fifteen dimensions implies an exponentially infeasible particle
    count. The UKF would require \(2n+1 = 31\) sigma points pushed through
    \(f\) every step at 200 Hz, roughly thirty-one times the propagation work,
    and it buys accuracy only where the nonlinearity bends appreciably across
    the belief, which it does not for a well-initialised tight-belief tracking
    filter on an embedded budget. What the EKF costs you is derivatives you
    must derive and verify against finite differences, plus no recovery from a
    bad initialisation, so budget a separate bootstrap and global-alignment
    path rather than discovering you need one.

### Interactive quiz

<quiz-bank src="estimation-l3-ekf"></quiz-bank>

## J. Annotated references

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Thrun et al., *Probabilistic Robotics*, ch. 3.3 & 7 | book | intermediate | The EKF and EKF localisation, which is this lesson's canonical source |
| Solà (2017), *Quaternion kinematics for the error-state KF* | paper | advanced | The error-state formulation, and how attitude EKFs are really built |
| [`robot_localization` docs](https://docs.ros.org/en/melodic/api/robot_localization/html/index.html) | docs | intermediate | The production fifteen-state EKF's configuration surface, which reads as this lesson's vocabulary |

## K. Graded work and portfolio extension

**Graded:** the localisation project's tracking phase is the EKF's home turf,
and an EKF variant of the project — the same harness with
`ExtendedKalmanFilter` substituted for particles — is the natural stretch goal.

**Portfolio:** the initialisation-robustness study from section G, plotting
failure fraction against initial error for both estimators. Two estimators,
one harness, and a quantified folk theorem is exactly the evidence-over-claims
artifact this curriculum exists to produce.
