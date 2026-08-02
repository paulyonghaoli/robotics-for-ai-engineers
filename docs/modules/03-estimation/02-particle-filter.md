# 3.2 The particle filter: when Gauss isn't enough

**Status:** Code verified · **Prereqs:** lesson 3.1 · **Time:** ~2.5 h · **Verified:** 2026-08-01, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

The Kalman family assumes the belief is one Gaussian blob. But a robot waking up in a building it has a map of ("global localization") believes it could be in *any* corridor — a multimodal belief no Gaussian can hold. The particle filter represents belief as a swarm of weighted samples and handles arbitrary distributions, nonlinear models, and rude surprises like kidnapping. It powers AMCL — the localization node running on essentially every ROS mobile robot — and it is the estimator our capstone uses.

## B. Mental model

Keep **N candidate robots** (particles). Every step:

1. **Predict:** move every particle through the motion model *with sampled noise* — the swarm spreads.
2. **Weight:** for each particle ask "if I were here, how likely is the measurement I just got?" — particles matching the evidence gain weight.
3. **Resample** (when needed): clone heavy particles, drop light ones — computation concentrates where the probability is.

The swarm *is* the belief: its spread is your uncertainty, its clusters are your hypotheses. Watching a particle cloud collapse from uniform chaos to a tight cluster as the robot senses distinctive features is the most instructive animation in robotics.

## C. Mathematical formulation

Importance weights: \(w_i \propto w_i \cdot p(z \mid x_i)\), normalized. The estimate is the weighted mean (unimodal case) or the dominant cluster. Two health mechanisms:

**Effective sample size** \(N_{eff} = 1 / \sum_i w_i^2\): ranges from \(N\) (uniform weights) to 1 (one particle owns everything). Resample when \(N_{eff} < N/2\) — resampling *too often* throws away diversity (sample impoverishment), too rarely wastes particles on dead hypotheses.

**Systematic resampling:** one random offset, \(N\) evenly-spaced pointers into the cumulative weights — \(O(N)\), low-variance, the standard. (Independent multinomial draws add unnecessary randomness.)

## D. From ML to robotics

- **This is importance sampling + resampling** — sequential Monte Carlo. If you've implemented importance-weighted estimators or SMC samplers, this is that, with a motion model as the proposal.
- **\(N_{eff}\) is your ESS diagnostic** from Bayesian computation, doing the identical job.
- **Particle count is a compute/accuracy dial:** like batch size or ensemble size, more is better with diminishing returns — and the required N grows exponentially with state dimension, which is why particle filters own low-dimensional problems (2D localization) and lose to Kalman variants in high dimensions.
- **The kidnapped-robot fix is exploration:** injecting a few percent random particles every step is an ε-greedy hedge against confident-but-wrong beliefs. Pure exploitation (vanilla SIR) cannot recover from a converged wrong answer.

## E. Minimal implementation

Library: [`robotics_ai/estimation/particle_filter.py`](https://github.com/paulyonghaoli/robotics-for-ai-engineers/blob/main/robotics_ai/estimation/particle_filter.py) — state-agnostic (caller supplies motion and likelihood), systematic resampling, \(N_{eff}\), degenerate-update guard. Tested including the kidnapped-robot recovery.

### Practice — write and run code here

<code-exercise src="est-l2-pf-resample"></code-exercise>

<code-exercise src="est-l2-pf-localize"></code-exercise>

## F. Robotics-framework implementation

Nav2's **AMCL** (adaptive Monte Carlo localization) is this lesson plus two production upgrades: a beam/likelihood-field LiDAR measurement model, and KLD-sampling — adapting N on the fly (thousands of particles while lost, hundreds once converged). Its parameters (`min/max_particles`, `recovery_alpha_*`) map one-to-one onto the concepts above; the `recovery_alpha` machinery *is* random injection.

## G. Experiment

The corridor-with-doors world from the exercise: run with N ∈ {50, 200, 2000} and plot error and \(N_{eff}/N\) over time. Then run the kidnapped-robot scenario (teleport the true robot mid-run) twice: vanilla SIR vs 5% uniform injection. Vanilla stays confidently wrong forever; injection recovers in a few doors' worth of evidence. Finally, resample *every* step regardless of \(N_{eff}\) and watch diversity die (all particles become copies of a few ancestors) — sample impoverishment made visible.

## H. Failure modes

- **Sample impoverishment:** aggressive resampling + low motion noise → the swarm collapses to clones; the belief looks precise and is merely inbred. Symptoms: \(N_{eff}\) fine, particle variety gone.
- **Weight degeneracy:** a too-sharp likelihood (overconfident sensor model) zeroes all but one particle in a single update. Soften the likelihood or gate it.
- **Confident-and-wrong (the kidnapped robot):** without injection, a converged filter cannot represent "somewhere else entirely" — no particles live there to be upweighted.
- **Dimension creep:** adding state dimensions without multiplying N spreads the same particles over exponentially more volume; the filter silently degrades to noise.

## I. Questions

1. *(Concept)* Why can a particle filter represent "the robot is in corridor A *or* corridor B" while a Kalman filter cannot — and what does the KF report in that situation?
2. *(Calculation)* Weights (0.7, 0.1, 0.1, 0.1): compute \(N_{eff}\). Resample at the N/2 rule?
3. *(Debugging)* After adding a high-precision sensor, the filter *diverges more often*. Explain via the weighting step.
4. *(System design)* 2D localization needs ~2,000 particles. Estimate the need for 6-DOF (3D) localization and justify choosing a different estimator.

??? note "Answer sketch for Q2"
    \(N_{eff} = 1/(0.49+0.01+0.01+0.01) = 1/0.52 \approx 1.92\). With N = 4, threshold 2: yes, resample (barely).

### Interactive quiz

<quiz-bank src="estimation-l2-pf"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Thrun et al., *Probabilistic Robotics*, ch. 4 & 8 | book | intermediate | Particle filters and Monte Carlo localization, canonically |
| [Nav2 AMCL docs](https://docs.nav2.org/configuration/packages/configuring-amcl.html) | docs | intermediate | Every parameter maps to a concept in this lesson |
| Doucet & Johansen, *"A tutorial on particle filtering"* (2009) | paper | advanced | The SMC theory under the robotics |

## K. Graded work & portfolio extension

**Graded:** the localization project's second half: particle-filter global localization + kidnapped-robot recovery, scored on convergence time and recovery success rate.

**Portfolio:** an animated particle cloud (uniform → multimodal → converged) on the corridor world, with a kidnap event mid-animation. The single most persuasive "I understand estimation" artifact you can produce; recruiters *watch* this one.
