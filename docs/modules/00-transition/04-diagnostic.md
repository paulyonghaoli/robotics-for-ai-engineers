# 0.4 Math prerequisites: a working diagnostic

**Status:** Technically reviewed · **Prereqs:** none · **Time:** ~45 min

---

## A. How to use this lesson

Courses I and II rest on three mathematical pillars: **linear algebra**,
**probability**, and **enough calculus**. This lesson tells you what "enough"
means for each, shows you the specific form each one takes in robotics — which
is often not the form you met it in — and then gives you a diagnostic so you
can find out where you actually stand rather than guessing.

You do not need proofs. You will not be asked to show that the SVD exists, or
to derive the central limit theorem. What you need is **working fluency**: the
ability to look at \(R^\top R = I\) and immediately think "so \(R^{-1}\) is
just \(R^\top\), that's cheap", rather than having to reconstruct why.

Take the diagnostic cold, before reading section C. Score honestly — nobody
sees it, and a flattering score costs you three modules from now when
everything is quietly harder than it should be.

**Rough calibration:**

| Score | What to do |
|---|---|
| 10+ / 12 | Proceed. Refresh nothing. |
| 7–9 | Proceed, and refresh the specific pillars you missed *as they arise*. The curriculum re-derives most of what it needs. |
| Below 7 | Spend a focused week with the references in section D before Module 1. The curriculum will feel about three times harder without it, which is a poor trade against roughly twenty hours of review. |

## B. What each pillar looks like in robotics

This is the part worth reading even if you score 12/12, because the *form*
these tools take here is often unfamiliar even when the tool is not.

### Linear algebra: matrices as geometry, not as data

In machine learning, a matrix is usually a container — a batch of feature
vectors, a weight tensor. Its rows and columns index things.

In Modules 1 and 2, a matrix is almost always a **transformation with a
geometric meaning**, and the individual entries rarely matter. A rotation
matrix \(R\) is not "nine numbers"; it is an object with structure:

\[
R^\top R = I, \qquad \det(R) = +1
\]

Those two facts do all the work. The first says the columns are orthonormal —
which is why the inverse of a rotation is its transpose, an operation that
costs nothing. The second distinguishes a rotation from a reflection, and when
a numerical routine accidentally produces \(\det(R) = -1\) you get a robot
that mirrors the world, which is a memorable afternoon.

What you need fluently:

- **Matrix–vector products as geometry.** \(Rv\) rotates \(v\). \(Av\) maps
  \(v\) into a new space. Being able to see this without computing.
- **Orthogonality**, and why orthonormal matrices are numerically kind.
- **Rank and null space.** In Module 8, the null space of a Jacobian is the
  set of joint motions that leave the gripper exactly where it is — a
  physical thing you can watch happen.
- **Eigenvectors and SVD, at the level of intuition.** You will not compute
  an SVD by hand, but you will need to know that it finds the directions of
  greatest and least stretch, because that is how you detect a degenerate
  scan match in Module 4.

### Probability: distributions as beliefs

Module 3 is applied Bayesian inference running at 50 Hz. The mathematics is
first-course material; the framing may be new.

The central object is a **belief** — a probability distribution over where the
robot might be — and the central operation is updating it when a measurement
arrives:

\[
p(x \mid z) \;\propto\; p(z \mid x)\, p(x)
\]

posterior ∝ likelihood × prior. That is the whole of Module 3 in one line;
everything else is the question of how to represent \(p(x)\) so the update is
cheap enough to run in 10 ms.

What you need fluently:

- **Conditioning and Bayes' rule**, comfortably, in both directions.
- **Gaussians**, including the multivariate case, and specifically what a
  **covariance matrix** means geometrically: it is an ellipse (or ellipsoid)
  of uncertainty. Large diagonal entries mean uncertain in that axis; large
  off-diagonal entries mean the errors are *correlated*, which is the thing
  people forget and which matters enormously.
- **Independence, and when it fails.** Lesson 0.1's first assumption is
  precisely a failure of independence.

A quick self-test that separates fluency from recall: if a robot's position
covariance is

\[
\Sigma = \begin{bmatrix} 4 & 3.8 \\ 3.8 & 4 \end{bmatrix}
\]

is the robot more uncertain along \(x\), along \(y\), or along some other
direction? (It is highly uncertain along the \(x = y\) diagonal and quite
confident perpendicular to it — the off-diagonal terms are nearly as large as
the diagonal ones, so the ellipse is long and thin at 45°. If that was not
immediately visible, covariance geometry is worth an hour.)

### Calculus: derivatives as sensitivities

You need less calculus than you probably fear, and you need it in one specific
form: **the derivative as a sensitivity**. How much does this output move when
that input moves a little?

The object that carries this in robotics is the **Jacobian** — the matrix of
all first-order partial derivatives of a vector function:

\[
J_{ij} = \frac{\partial f_i}{\partial x_j}
\]

You already meet Jacobians in backpropagation. Here they have a physical
meaning that makes them much easier to reason about. In Module 2, the
manipulator Jacobian maps joint velocities to end-effector velocity: column
\(j\) is literally "how the gripper moves when joint \(j\) rotates". In
Module 3, the EKF Jacobian is "how much does my predicted measurement change
if my position estimate is slightly wrong".

What you need fluently: partial derivatives, the chain rule, and the ability
to read a Jacobian as a stack of sensitivities. That is genuinely all.

## C. The diagnostic

Twelve questions across the three pillars. Untimed, but if a question takes
more than a minute or two, mark it as one you did not know — the target is
fluency, and slow-but-correct is the signal you are looking for.

<quiz-bank src="transition-l4-diagnostic"></quiz-bank>

## D. Targeted refreshers

| Pillar | Refresh with | Focus on |
|---|---|---|
| Linear algebra | 3Blue1Brown, *Essence of Linear Algebra* (visual, about 3 hours, unusually well suited to exactly the intuition needed here). Strang's lectures 1–8 for more depth | matrix–vector products as geometry, orthogonality, rank and null space, SVD intuition |
| Probability | Blitzstein & Hwang, *Introduction to Probability*, ch. 1–5. Or the first third of Thrun et al., *Probabilistic Robotics*, ch. 2, which is shorter and already in robotics framing | conditioning, Bayes' rule, Gaussians, covariance as an ellipse |
| Calculus | Any standard source's chapters on partial derivatives and the chain rule | derivatives as sensitivities, gradients of vector-valued functions, reading a Jacobian |

If you are short on time and have to choose one: **linear algebra**. It is
load-bearing from lesson 1.1 onward and the hardest to pick up incidentally,
whereas the probability arrives gradually and is re-derived where it is used.

## E. What you deliberately do not need

Worth stating explicitly, because mathematical anxiety usually attaches to the
wrong things. This curriculum requires **no** real analysis, **no** measure
theory, **no** proofs of convergence, **no** differential geometry beyond what
is built up in Module 1 from scratch, and **no** Lie-group theory — the parts
of it that matter are introduced concretely where needed and never as
abstraction for its own sake.

Working robotics engineers use the three pillars above constantly and the rest
almost never. Spend your review time accordingly.

## F. If you scored badly

This is not a filter and it is worth saying plainly. A low score means the
refresher week is a good investment, not that the material is out of reach.
The three pillars are all first- and second-year undergraduate topics, they
are extraordinarily well taught by freely available resources, and twenty
focused hours genuinely does move most people from "below 7" to "comfortable".

The mistake is proceeding anyway and attributing the resulting difficulty to
robotics being hard. It usually isn't; it is usually the linear algebra.

## G. Annotated references

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| 3Blue1Brown, *Essence of Linear Algebra* | video series | introductory | The single highest-return three hours available for this curriculum. Builds exactly the geometric intuition Modules 1–2 assume |
| Thrun, Burgard & Fox, *Probabilistic Robotics*, ch. 2 | book | introductory | Probability already framed as robot belief, so it doubles as a Module 3 preview |
| Petersen & Pedersen, *The Matrix Cookbook* | reference | reference | Not for reading. For the day you need the derivative of a quadratic form and do not want to derive it |
