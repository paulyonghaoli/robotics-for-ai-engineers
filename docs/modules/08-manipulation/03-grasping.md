# 8.3 Grasp synthesis: where to put the fingers

**Status:** Code verified · **Prereqs:** lesson 8.1, lesson 7.3 · **Time:** ~2 h · **Verified:** 2026-08-03, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Perception tells you an object is there. Kinematics tells you the arm can reach it. Neither says where to *hold* it, and that question has a mechanical answer that most learned grasping systems are, underneath, approximating.

The value of understanding the mechanics is not that you will hand-code grasps in production — you probably will not. It is that grasp failures are legible once you know what a good grasp is. A network that keeps choosing the smooth curved side of a mug is not undertrained; it is optimising something that does not include friction cones, and no amount of extra data fixes a missing constraint.

## B. Mental model

**A grasp is a claim about resisting forces.** Not "the fingers touch the object" but "for any disturbance the task might apply, the contacts can generate an opposing wrench." That is *force closure*, and it is the property that separates holding something from merely touching it.

**Antipodal is the two-finger version.** Two contacts, on opposite sides, with the line between them lying inside both friction cones. Concretely: the line joining the contacts must be nearly anti-parallel to both surface normals. If the grip line is 60° off the normal at one contact and friction only supports 20°, the object squirts out — and the failure looks like the gripper closed on nothing.

**The friction cone is the whole constraint.** A contact with friction coefficient `μ` can only push within `atan(μ)` of the surface normal. With `μ = 0.5` that is 26.6°, which is a much tighter budget than intuition suggests and is why smooth curved surfaces are genuinely hard rather than merely inconvenient.

## C. Formulation

For contacts $\mathbf{p}_1, \mathbf{p}_2$ with outward normals $\mathbf{n}_1, \mathbf{n}_2$, let $\mathbf{g}$ be the unit vector from the first to the second. The grasp is **antipodal** when both contact directions lie inside their friction cones:

$$
\angle(\;\;\mathbf{g}, -\mathbf{n}_1) \le \arctan\mu
\qquad\text{and}\qquad
\angle(-\mathbf{g}, -\mathbf{n}_2) \le \arctan\mu
$$

A useful scalar quality, once a candidate passes that test, combines three things a grasp planner actually cares about:

$$
Q = \underbrace{\min_i \cos\theta_i}_{\text{margin in the cone}}
\;\cdot\;
\underbrace{\exp\!\left(-\frac{d_{\text{com}}}{\ell}\right)}_{\text{near the centre of mass}}
\;\cdot\;
\underbrace{\mathbb{1}\!\left[w_{\min} \le \|\mathbf{p}_2-\mathbf{p}_1\| \le w_{\max}\right]}_{\text{the gripper actually opens that far}}
$$

The third term is not a refinement. A grasp planner that ignores the gripper's stroke produces beautiful, physically sound, entirely unexecutable answers — and it is the single most common way a grasp pipeline wastes a week.

### Geometry first, friction second — counted

Enumerating antipodal pairs on this lesson's two objects, with the gripper's
stroke window (2–9 cm) enforced and the friction cone checked at both
contacts:

| Friction μ | Box (6×14 cm) | Disc (11 cm diameter) |
|---|---|---|
| 0.2 (smooth) | 5% of width-feasible pairs hold | **0%** |
| 0.5 (rubber pads) | 9% | **0%** |
| 1.0 (implausibly grippy) | 17% | 22% |

The box always has grasps, because parallel flat faces provide truly
antipodal normals that satisfy any friction cone — at μ = 0.2 the survivors
are exactly the face-to-face pinches. The disc has **none at all** until
μ reaches 1.0, and the reason is pure geometry: its diameter (11 cm) exceeds
the gripper's 9 cm stroke, so every reachable chord is non-diametric, the
contact normals on a non-diametric chord are not anti-aligned, and holding
one is asking friction to supply what alignment didn't. At μ = 1.0 — a 45°
friction cone, beyond most real material pairs — friction finally rescues
22% of the chords, which is the quantified version of a rule every grasp
planner encodes: **force closure is bought with geometry and only rented
with friction.** An object one centimetre wider than the stroke is not
"harder to grasp"; within physical friction, it is ungraspable, and the fix
is a different approach direction or a different gripper, not a better
planner.

## D. From ML to robotics

**What transfers:** ranking candidates by a learned score is exactly the right architecture, and it is what Dex-Net and its successors do.

**What is new:** the score has to encode a *physical* constraint, and physical constraints are not soft. In ML you usually optimise a smooth objective and accept the best point found. Here, a grasp either lies inside the friction cone or the object slips — there is no partial credit, and a model trained on a smooth proxy loss will happily propose grasps just outside it.

**The practical consequence:** generate candidates however you like, including with a network, but **filter them through the mechanics before executing.** The filter is cheap, verifiable, and catches the failure mode the learned scorer cannot see. This is the same runtime-assurance argument as [11.5](../11-deployment/05-safety-cases.md), one level down.

## E. Practice

<code-exercise src="man-l3-antipodal"></code-exercise>

## F. In production

Dex-Net and GraspNet-family models generate and rank grasps from depth data and are the standard starting point. GPD and its descendants sample geometrically and score with a network, which is the hybrid most teams end up with.

What the papers under-emphasise:

- **The approach path matters as much as the grasp.** A perfect antipodal pair that requires passing the gripper through the table is not a grasp. Candidate scoring should include reachability, which couples this stage to [8.2](02-inverse-kinematics.md).
- **μ is a guess.** Published coefficients are for clean, dry, specific material pairs. Assume less friction than you measured, and treat the margin as the safety factor it is.
- **Objects move when you touch them.** The grasp you planned is on the object's pre-contact pose. Compliant fingers and a bit of closing travel absorb the difference; a rigid gripper aimed at a millimetre-perfect plan does not.

## G. Experiment

Take a rectangular object and sweep the friction coefficient from 0.1 to 0.8, counting how many of the sampled contact pairs qualify as antipodal. The count rises sharply — and then plot the same thing for a circular object, where it barely moves. The shape of those two curves is the whole argument for why round objects need either high friction, an enveloping grasp, or a different strategy entirely.

## H. Failure modes

- **Ignoring the gripper's stroke.** Physically sound grasps the hardware cannot open wide enough to attempt, or narrow enough to close on.
- **Optimistic friction.** Using a handbook μ for a dusty warehouse floor's worth of contamination.
- **Grasping far from the centre of mass.** The grasp holds and the object rotates in the fingers under its own weight, which reads as slipping.
- **Ignoring the approach.** Scoring contacts without checking that the gripper can get there without hitting the object, the table, or itself.
- **Treating a learned score as a guarantee.** It ranks; it does not certify. Filter through the mechanics.

## I. Questions

<quiz-bank src="man-l3-quiz"></quiz-bank>

## J. References

- Bicchi & Kumar, *Robotic Grasping and Contact: A Review* (2000) — the force-closure formalism, and still the clearest statement of what a grasp is.
- Mahler et al., *Dex-Net 2.0* (2017) — learned grasp quality from depth, and the paper that made synthetic grasp datasets standard.
- ten Pas et al., *Grasp Pose Detection in Point Clouds* (2017) — geometric sampling plus learned scoring, the hybrid most production systems resemble.
- Fang et al., *GraspNet-1Billion* (2020) — the benchmark, and a good illustration of how much the evaluation protocol shapes the reported numbers.

## K. Graded work & portfolio extension

**Graded:** the exercise above, plus the grasp-scoring stage of [Capstone III](../capstone-3/index.md).

**Portfolio:** produce the two-curve figure from section G — qualifying grasps against friction coefficient, for a box and for a cylinder — and annotate the μ your gripper actually achieves on the materials you care about. It turns "round things are hard to grasp" from folklore into a number, and it is the kind of analysis that justifies a hardware decision.
