# 0.4 Math prerequisites: a working diagnostic

**Status:** Code verified · **Prereqs:** none · **Time:** ~45 min

---

## A. How to use this

Courses I–II lean on three mathematical pillars: **linear algebra** (Modules 1–2 live on matrices and their geometry), **probability** (Module 3 is applied Bayes), and **enough calculus** (derivatives as sensitivities — Jacobians, gradients). You don't need proofs; you need *working fluency* — the kind that answers the questions below in under a minute each.

Take the diagnostic cold. Score honestly. The point isn't a grade — it's a targeted reading list: each explanation names what to refresh and where it will bite you in the curriculum if you don't.

**Rough calibration:** 10+/12 — proceed, refresh nothing. 7–9 — proceed, refresh the pillars you missed *as they arise*. Below 7 — spend a focused week with the references in section C before Module 1; the curriculum will feel 3× harder without it, and that's a poor trade against ~20 hours of review.

## B. The diagnostic

<quiz-bank src="transition-l4-diagnostic"></quiz-bank>

## C. Targeted refreshers

| Pillar | Refresh with | Skip to |
|---|---|---|
| Linear algebra | 3Blue1Brown's *Essence of Linear Algebra* (visual, fast) + Strang lectures 1–8 for depth | matrix-vector geometry, orthogonality, SVD intuition |
| Probability | Blitzstein & Hwang ch. 1–5, or the first third of *Probabilistic Robotics* ch. 2 | conditioning, Bayes, Gaussians, covariance |
| Calculus | Any source's partial-derivatives and chain-rule chapters | derivatives as sensitivities; gradients of vector functions |

One deliberate omission: no analysis, no measure theory, no proofs of convergence. Working robotics engineers use the pillars above daily and the rest almost never — spend your review time accordingly.
