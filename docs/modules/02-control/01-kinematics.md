# 2.1 Forward and inverse kinematics: the 2-link arm

**Status:** Code verified · **Prereqs:** Module 1 · **Time:** ~2 h · **Verified:** 2026-08-01, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Kinematics is the dictionary between two languages the robot speaks simultaneously: **joint space** (what the motors control: angles \(\theta_1, \theta_2, \dots\)) and **task space** (what you care about: where the hand is). Forward kinematics (FK) translates joints → pose and is trivial; inverse kinematics (IK) translates desired pose → joints and is where the trouble — multiple solutions, unreachable targets, singularities — lives. Every pick-and-place, every reach, every footstep starts with an IK solve.

## B. Mental model

FK is *composition of transforms* — lesson 1.1 applied down a chain: frame at each joint, rotate by the joint angle, translate along the link, repeat. You have already done this.

IK is *root-finding*: find \(\theta\) such that \(FK(\theta) = p_{target}\). For a 2-link arm a closed-form solution exists (law of cosines); for general arms you iterate. The workhorse iteration is beautifully familiar: **gradient-descent-shaped**. The Jacobian \(J = \partial FK / \partial \theta\) says how the hand moves per unit joint motion; step joints by \(J^{+} \, e\) (pseudoinverse times task-space error) until the error vanishes. If you have implemented backprop-and-step, you have implemented damped-least-squares IK without knowing it.

Two solutions generally exist for the 2-link arm — elbow-up and elbow-down — a first taste of the C-space branches from lesson 1.5.

## C. Mathematical formulation

FK for link lengths \(l_1, l_2\):

\[
p = \begin{bmatrix} l_1 \cos\theta_1 + l_2 \cos(\theta_1 + \theta_2) \\ l_1 \sin\theta_1 + l_2 \sin(\theta_1 + \theta_2) \end{bmatrix}
\]

Closed-form IK: with \(D = \frac{\|p\|^2 - l_1^2 - l_2^2}{2 l_1 l_2}\) (reachable iff \(|D| \le 1\)):

\[
\theta_2 = \pm\arccos D, \qquad
\theta_1 = \operatorname{atan2}(y, x) - \operatorname{atan2}\!\big(l_2 \sin\theta_2,\; l_1 + l_2 \cos\theta_2\big)
\]

Numerical IK (damped least squares, the production default):

\[
\Delta\theta = J^\top (J J^\top + \lambda^2 I)^{-1} \, e
\]

The damping \(\lambda\) is Tikhonov regularization — it trades a little accuracy for boundedness near singularities, where \(J\) loses rank and the pure pseudoinverse commands infinite joint speed.

## D. From ML to robotics

- **Numerical IK is literally optimization**: minimize \(\|FK(\theta) - p\|^2\) by following the Jacobian. Damped least squares ≈ ridge regression on the update step; step-size intuition, convergence stalls, local minima — all your optimizer instincts apply.
- **Singularities ≈ ill-conditioning.** A stretched-out arm can't move its hand radially no matter the joint velocity — \(J\) is rank-deficient exactly like a nearly-singular design matrix, and the fix (damping) is the same fix.
- **Elbow-up/down ≈ multimodality.** Gradient methods find *a* solution; which one depends on initialization. Task-space regression models in robot learning (Module 9) inherit this multimodality problem — it's why naive behavior cloning averages between modes and breaks.

## E. Minimal implementation

FK you can write from section C directly. Numerical IK:

```python
import numpy as np

def jacobian(theta, l1=1.0, l2=0.8):
    t1, t12 = theta[0], theta[0] + theta[1]
    return np.array([
        [-l1*np.sin(t1) - l2*np.sin(t12), -l2*np.sin(t12)],
        [ l1*np.cos(t1) + l2*np.cos(t12),  l2*np.cos(t12)],
    ])

def ik_step(theta, target, lam=0.1):
    e = target - fk(theta)
    J = jacobian(theta)
    return theta + J.T @ np.linalg.solve(J @ J.T + lam**2 * np.eye(2), e)
```

### Practice — write and run code here

<code-exercise src="ctl-l1-fk"></code-exercise>

<code-exercise src="ctl-l1-ik"></code-exercise>

## F. Robotics-framework implementation

Real arms describe their chain in **URDF** (Module 6); generic FK/IK runs through KDL or MoveIt 2's kinematics plugins, and production IK solvers (TRAC-IK, or the analytic IKFast) handle 6–7 DOF with joint limits and collision constraints layered on top (Module 8). The 2-link core you built is the honest miniature of all of it.

## G. Experiment

Run numerical IK to targets sweeping from well-inside the workspace to just past its boundary (\(\|p\| \to l_1 + l_2\)). Log iterations-to-converge and final joint speeds as the target approaches the singularity, with \(\lambda \in \{0, 0.01, 0.1\}\). Watch undamped IK explode at the boundary and damped IK degrade gracefully — then check which solution branch (elbow-up/down) you converged to from different initializations.

## H. Failure modes

- **Unreachable targets** (\(|D| > 1\)): closed form fails loudly; numerical IK stalls at the workspace boundary, silently returning its best effort — check the residual, always.
- **Singularity commands:** near full extension, un-damped IK requests enormous joint velocities; on hardware this is a safety stop or a broken gearbox.
- **Branch flips mid-trajectory:** solving IK per-waypoint without warm-starting from the previous solution can alternate elbow-up/down between adjacent points — the arm thrashes. Warm-start and stay on one branch.
- **Degrees vs radians.** Still undefeated as a source of absurd arm poses.

## I. Questions

1. *(Concept)* Why does damping make IK robust at singularities, and what does it cost away from them?
2. *(Calculation)* \(l_1 = l_2 = 1\), target \((1.2, 0)\): compute \(D\) and both \(\theta_2\) solutions.
3. *(Debugging)* Your IK converges but the elbow oscillates between two configurations on alternate calls. Why, and what's the fix?
4. *(System design)* A 6-DOF arm has infinite IK solutions for most poses (redundancy). Name two useful secondary objectives to spend the redundancy on.

??? note "Answer sketch for Q2"
    \(D = (1.44 - 2)/2 = -0.28\); \(\theta_2 = \pm 1.855\) rad (±106.3°) — elbow-up and elbow-down, symmetric about the reach line.

### Interactive quiz

<quiz-bank src="control-l1-kinematics"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Lynch & Park, *Modern Robotics*, ch. 4 & 6 | book | intermediate | FK via products of exponentials; numerical IK done rigorously |
| Buss, *"Introduction to IK with Jacobian transpose, pseudoinverse and DLS"* | tutorial | introductory | The classic practical IK note — short, readable |
| [MoveIt 2 kinematics docs](https://moveit.picknik.ai/main/doc/examples/kinematics/kinematics_tutorial.html) | docs | intermediate | Where these solvers live in production |

## K. Graded work & portfolio extension

**Graded:** IK joins the Module 2 project (planned): a reaching task scored on convergence rate, residual, and singularity behavior.

**Portfolio:** an animated 2-link reacher tracing targets with a live Jacobian-conditioning readout (color the arm by \(\sigma_{min}(J)\)) — singularities become *visible* as the arm blushes red at full extension.
