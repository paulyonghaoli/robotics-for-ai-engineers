# 8.1 Manipulator kinematics: from joints to a pose

**Status:** Code verified · **Prereqs:** lessons 1.3, 2.1, 2.3 · **Time:** ~2 h · **Verified:** 2026-08-03, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

You command joints. You care about the tool. Everything in manipulation lives in the gap between those two sentences.

Forward kinematics — joints to tool pose — is a chain of transforms and is never the hard part. What matters is what the chain *tells* you: which poses are reachable at all, which are reachable in more than one way, and where the relationship between joint motion and tool motion breaks down. That last question is the one that decides whether your controller is stable, and it is answered by the Jacobian you already met in [2.3](../02-control/03-jacobians.md).

## B. Mental model

**Two spaces, and you must always know which one you are in.**

| | Configuration space | Task space |
|---|---|---|
| A point is | a vector of joint angles `q` | a tool pose |
| Dimension | number of joints `n` | 3 (planar) or 6 (spatial) |
| What's easy | checking joint limits, interpolating | expressing what the task wants |
| What's hard | saying what a configuration *means* | knowing whether a pose is achievable |

Forward kinematics maps the first to the second and is always well defined. The inverse is the problem, and [8.2](02-inverse-kinematics.md) is about it.

**Redundancy is a resource, not a nuisance.** When `n` exceeds the task dimension, the map has a *null space*: joint velocities that produce no tool motion at all. A 3-link planar arm reaching for an (x, y) target has one such direction, and you can move along it freely to dodge an obstacle or back away from a joint limit while the gripper stays put.

**The workspace boundary is where the mathematics changes character.** At full extension every joint's lever arm to the tool points the same way, so every column of the Jacobian is perpendicular to the arm: the tool can still *swing* freely, and cannot **extend** at all. Radial motion at the boundary would require infinite joint velocity. That is a singularity, and it is a property of the geometry rather than a numerical accident — the direction you lose is the one pointing along the arm.

## C. Formulation

For a planar arm with link lengths $l_i$ and joint angles $q_i$, the tool position is a sum of links, each rotated by the accumulated angle:

$$
\mathbf{p}(\mathbf{q}) = \sum_{i=1}^{n} l_i
\begin{bmatrix} \cos\left(\sum_{k\le i} q_k\right) \\ \sin\left(\sum_{k\le i} q_k\right) \end{bmatrix}
$$

The **Jacobian** is its derivative, $J_{ij} = \partial p_i / \partial q_j$. For the planar case it has a clean form — column $j$ is the perpendicular from joint $j$ to the tool:

$$
J_{:,j} = \begin{bmatrix} -(p_y - p_{y,j}) \\ \;\;\,(p_x - p_{x,j}) \end{bmatrix}
$$

which is worth internalising, because it makes the singularities *visible*: when all those perpendiculars become parallel, the columns are linearly dependent and the arm has lost a direction.

**Manipulability** condenses that into one number ([Yoshikawa, 1985](#j-references)):

$$
w = \sqrt{\det\left(J J^\top\right)}
$$

`w = 0` exactly at a singularity. It is a scalar field over configuration space, and looking at where it collapses tells you which parts of the workspace to stay out of.

### What redundancy looks like in the singular values

The third joint changes the Jacobian's shape — 2×3 now, wider than tall —
and the consequences read directly off its singular values at three postures:

| Posture | \(\sigma_1, \sigma_2\) | Null-space dimension |
|---|---|---|
| Comfortably bent | 2.58, 0.49 | 1 |
| Nearly stretched | 2.84, **0.047** | 1 |
| Fully stretched | 2.84, 0.000 | **2** |

A wide Jacobian has a null space *everywhere* — at least one combination of
joint velocities that leaves the tip exactly still, which is the redundancy
lesson 8.2 will spend. The stretch singularity from lesson 2.3 is still here
too, and nastier in one respect: near full extension \(\sigma_2\) collapses
through 0.047 to zero, and at the singularity itself the null space *grows*
to two dimensions — two independent self-motions, neither of which helps you,
because the direction the task needs is precisely the one that vanished.
Redundancy is extra freedom in the directions you already had, never a
substitute for the one you lost, and this table is the compact proof.

## D. From ML to robotics

The forward map is a differentiable function of a parameter vector — familiar territory. Three things are not:

- **The parameters have hard limits.** Joints stop. Gradient steps that ignore that produce a plan the hardware refuses, and the failure appears as a controller that saturates rather than as an error.
- **The map is many-to-one.** Multiple `q` reach the same pose, so "the" answer does not exist and any loss with a unique minimiser is describing something false.
- **The conditioning varies wildly across the domain.** Near a singularity, a small task-space request demands enormous joint motion. This is not ill-conditioning to be preconditioned away — it is the physical geometry, and the response is to plan around it.

## E. Practice

<code-exercise src="man-l1-fk"></code-exercise>

<code-exercise src="man-l1-manipulability"></code-exercise>

## F. In production

Real arms use Denavit–Hartenberg parameters or URDF to describe the chain, and libraries — KDL, Pinocchio, `robotics_toolbox` — to evaluate it. Pinocchio is the current default for anything performance-sensitive because it gives you analytic derivatives, not just values.

Two practical notes that cost people weeks:

- **The tool frame is not the flange frame.** Every gripper adds a fixed transform, and forgetting it produces an error that is constant in the tool frame and therefore looks like a calibration problem in the base frame.
- **Joint zero is a convention.** The manufacturer's zero, the URDF's zero, and the encoder's zero need not agree. Verify by commanding a known configuration and measuring, rather than by reading a datasheet.

## G. Experiment

Sweep a 3-link arm across its reachable workspace and plot manipulability as a heatmap. The structure is immediately legible: a bright well-conditioned band at mid-extension, a dark ring at full extension, and a dark patch near the base where the arm folds on itself. Then overlay the straight-line path between two ordinary poses and notice how often it passes through the dark ring — which is why joint-space planning ([8.4](../../curriculum.md)) is not merely an implementation convenience.

## H. Failure modes

- **Ignoring joint limits in the model.** Your planner produces beautiful trajectories the hardware will not execute.
- **Treating IK as single-valued.** Multiple solutions exist; picking arbitrarily among them makes the arm flip configuration mid-trajectory, which is violent and occasionally destructive.
- **Working near a singularity.** Small task-space errors demand huge joint velocities. The tell is a controller that is well behaved in the middle of the workspace and screams at the edges.
- **Angle wrapping in joint space.** A joint at +179° and one at −179° are 2° apart, and code that does not wrap will command a 358° rotation.
- **Forgetting the tool transform.** A constant offset in the tool frame that rotates with the wrist, which reads as a calibration error and is not one.

## I. Questions

<quiz-bank src="man-l1-quiz"></quiz-bank>

## J. References

- Lynch & Park, *Modern Robotics*, ch. 4–5 — the current standard text, and the product-of-exponentials formulation is cleaner than DH once you are past the basics.
- Siciliano et al., *Robotics: Modelling, Planning and Control*, ch. 2–3 — the classical treatment, with the most thorough singularity analysis.
- Yoshikawa, *Manipulability of Robotic Mechanisms* (1985) — the original manipulability measure, short and readable.
- Pinocchio documentation — the library, and a good example of why analytic derivatives matter for anything running in a loop.

## K. Graded work & portfolio extension

**Graded:** the two exercises above, plus the forward-kinematics and manipulability components of the manipulation mini-project.

**Portfolio:** produce the manipulability heatmap from section G for a 3-link arm, with a straight-line task-space path drawn over it and the joint velocities required along that path plotted underneath. The two panels together make the case for configuration-space planning in a way that no amount of prose does: the path looks completely reasonable, and the velocity plot has a spike in the middle of it.
