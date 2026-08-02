# 2.3 Jacobians and differential kinematics

**Status:** Code verified · **Prereqs:** lesson 2.1 · **Time:** ~2 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

The Jacobian \(J(\theta) = \partial FK / \partial \theta\) is the arm's *exchange rate* between joint space and task space: \(\dot{p} = J \dot{\theta}\). Everything that moves an arm smoothly runs through it — velocity control, the IK you built in 2.1, force mapping (\(\tau = J^\top F\)), and singularity analysis. When a robot arm suddenly can't move the way you asked, the answer is almost always "look at the Jacobian's condition number."

## B. Mental model

At any configuration, the Jacobian's columns are *what each joint contributes*: column \(i\) is the hand velocity produced by unit velocity on joint \(i\). The hand's reachable velocity set is the image of the unit ball under \(J\) — an **ellipse** (the manipulability ellipsoid). Fat ellipse: agile everywhere. Pencil-thin ellipse: you're near a **singularity**, where some task direction has become unreachable no matter how hard the motors work. The ellipse's axes are \(J\)'s singular values — your SVD intuition applies verbatim.

## C. Mathematical formulation

For the 2-link arm (lesson 2.1's FK):

\[
J = \begin{bmatrix}
-l_1 s_1 - l_2 s_{12} & -l_2 s_{12} \\
\;\;\, l_1 c_1 + l_2 c_{12} & \;\;\, l_2 c_{12}
\end{bmatrix},
\qquad
\det J = l_1 l_2 \sin\theta_2
\]

\(\det J = 0\) exactly when \(\theta_2 \in \{0, \pi\}\) — arm fully stretched or fully folded: the two singular configurations. Near them, \(\sigma_{min}(J) \to 0\) and inverting \(J\) demands joint speeds \(\propto 1/\sigma_{min}\). The **statics dual**: \(\tau = J^\top F\) — the same matrix maps hand forces back to joint torques, which is why a stretched arm can *resist* huge radial loads with zero torque (and why you carry heavy boxes with straight arms).

## D. From ML to robotics

- **The manipulability ellipsoid is PCA of instantaneous capability** — singular values as explained variance, singularity as rank collapse.
- **Condition number \(\sigma_{max}/\sigma_{min}\) plays its usual role:** ill-conditioning amplifies noise (joint jitter → wild hand motion near singularities) exactly as in badly-scaled regression.
- **Finite-difference checking** a hand-derived Jacobian (as in lesson 3.3's exercise) is gradient-checking from the pre-autodiff era — robotics still lives there for good reasons (speed, auditability).

## E. Minimal implementation & practice

The analytic \(J\) is eight lines (section C). The exercise builds it, validates against finite differences, and traces \(\sigma_{min}\) across the workspace to *watch* singularities emerge:

<code-exercise src="ctl-l3-jacobian"></code-exercise>

## F. Robotics-framework implementation

MoveIt 2 exposes `getJacobian()` per move group; KDL computes it from the URDF chain. Production arms monitor manipulability continuously and either avoid low-\(\sigma_{min}\) regions in planning or damp commands through them (lesson 2.1's DLS, now with vocabulary).

## G. Experiment

Sweep \(\theta_2\) from 0 to \(\pi\) at fixed \(\theta_1\); plot \(\sigma_{min}\), \(\det J\), and the joint speeds requested by undamped IK for a fixed 1 cm/s hand velocity. All three tell the same story in different units — and the \(1/\sigma_{min}\) blow-up at the endpoints is lesson 2.1's exploding IK, now with a diagnosis.

## H. Failure modes

- **Commanding task velocities through a singularity**: joint-speed spikes, actuator saturation, e-stop. Damp or reroute.
- **Wrong frame for J**: a Jacobian in the base frame applied to a tool-frame velocity command — silent geometric nonsense (Module 1's conventions again).
- **Forgetting the statics dual**: load-carrying configurations chosen by hand-velocity criteria alone can demand enormous holding torques.

## I. Questions

1. *(Concept)* Why does \(\tau = J^\top F\) use the transpose, not the inverse?
2. *(Calculation)* For \(l_1 = l_2 = 1\), \(\theta = (0, \pi/2)\): compute \(\det J\).
3. *(Debugging)* Near full extension your arm's hand tracks radial commands with huge error but tangential commands fine. Explain via \(J\)'s column space.
4. *(System design)* You must specify a workspace region where a 2-link arm guarantees 0.5 m/s in *any* direction with joint speeds ≤ 2 rad/s. State the criterion in terms of \(\sigma_{min}\).

??? note "Answer sketch for Q2"
    \(\det J = l_1 l_2 \sin\theta_2 = 1\) — right angle at the elbow is (maximally) far from singular.

### Interactive quiz

<quiz-bank src="control-l3-jacobians"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Lynch & Park, *Modern Robotics*, ch. 5 | book | intermediate | Jacobians, statics duality, manipulability — the canonical chapter |
| Yoshikawa, *"Manipulability of Robotic Mechanisms"* (1985) | paper | intermediate | Where the ellipsoid came from |

## K. Graded work & portfolio extension

**Graded:** Jacobian machinery reappears in the Module 2 project and lesson 3.3's EKF (observation Jacobians).

**Portfolio:** animate the manipulability ellipse riding on the 2-link arm as it sweeps the workspace — the singularity "pinch" at full extension is the most instructive 10 seconds of arm kinematics you can show anyone.
