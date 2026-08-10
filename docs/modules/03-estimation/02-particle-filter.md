# 3.2 The particle filter: when Gauss isn't enough

**Status:** Code verified · **Prereqs:** lesson 3.1 · **Time:** ~2.5 h · **Verified:** 2026-08-01, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

The Kalman family assumes the belief is a single Gaussian blob, and for
tracking a robot that already roughly knows where it is, that assumption is
excellent. It fails completely for the situation a robot faces when it is
switched on inside a building it has a map of, because at that moment it
believes it could be in *any* corridor, and no single Gaussian can hold a
belief with several separated peaks.

The particle filter represents the belief as a swarm of weighted samples
instead, which lets it carry arbitrary distributions, nonlinear motion and
measurement models, and rude surprises such as somebody picking the robot up
and putting it somewhere else. It powers AMCL, the localisation node running
on essentially every ROS mobile robot, and it is the estimator the capstone
uses.

!!! note "Terms defined here"

    **Particle** — one hypothesis about the complete state, carrying a weight
    that says how plausible it currently is.

    **Global localisation** — working out where you are with no prior idea,
    as opposed to tracking a pose you already know approximately.

    **The kidnapped-robot problem** — recovering after the robot is moved
    without being told, which is the hardest case because the filter's belief
    is confident and wrong.

    **Importance weight** — how much a sample counts, proportional to how
    well it explains the measurement.

    **Effective sample size**, \(N_{eff}\) — how many particles are actually
    contributing, as opposed to how many exist.

    **Sample impoverishment** — the swarm collapsing into copies of a few
    ancestors, so that it looks precise while carrying almost no information.

## B. Mental model

Keep \(N\) candidate robots, and at every step do three things.

**Predict** by moving every particle through the motion model *with sampled
noise*, which spreads the swarm out in proportion to how uncertain the motion
is. **Weight** each particle by asking, if I were standing here, how likely is
the measurement I just received, so that particles consistent with the
evidence gain weight. **Resample** when the swarm has become lopsided, cloning
heavy particles and dropping light ones, which concentrates computation where
the probability actually is.

The swarm *is* the belief. Its spread is your uncertainty and its clusters are
your competing hypotheses, and watching a particle cloud collapse from uniform
chaos into a tight cluster as the robot senses distinctive features is
probably the most instructive animation in robotics.

<figure class="rai-fig" markdown>
![Three stacked histograms of particle position at steps 1, 4 and 12 along a corridor with three doors. At step 1 the particles are spread across the whole corridor, by step 4 they have concentrated into a few clusters near the doors, and by step 12 a single tight cluster sits on the true position.](../../assets/generated/figures/particle-cloud-light.svg){.fig-light}
![Three stacked histograms of particle position at steps 1, 4 and 12 along a corridor with three doors. At step 1 the particles are spread across the whole corridor, by step 4 they have concentrated into a few clusters near the doors, and by step 12 a single tight cluster sits on the true position.](../../assets/generated/figures/particle-cloud-dark.svg){.fig-dark}
<figcaption markdown>A corridor with three doors, four hundred particles, and a sensor that reports distance to the nearest door. Early on the belief is genuinely multimodal, because several positions explain the reading equally well; accumulated motion between sightings is what eventually breaks the tie.</figcaption>
</figure>

The middle panel is the point of the whole lesson. That belief has several
separated peaks, it is a correct representation of what the robot actually
knows, and a Kalman filter asked to describe it would report a mean somewhere
between the peaks, which is a location the robot is certainly *not* in.

## C. Mathematical formulation

The importance weights update multiplicatively as
\(w_i \propto w_i \cdot p(z \mid x_i)\), followed by normalisation, and the
reported estimate is the weighted mean in the unimodal case or the dominant
cluster otherwise.

Two health mechanisms keep this from falling apart.

The **effective sample size**, \(N_{eff} = 1 / \sum_i w_i^2\), ranges from
\(N\) when all weights are equal down to 1 when a single particle owns
everything, and it measures how many particles are really doing work. The
standard rule is to resample when \(N_{eff} < N/2\), and both directions of
error hurt: resampling too often discards diversity and causes sample
impoverishment, while resampling too rarely wastes most of the swarm on
hypotheses that have already been ruled out.

**Systematic resampling** uses one random offset and \(N\) evenly spaced
pointers into the cumulative weight distribution, which is \(O(N)\) and
lower-variance than drawing \(N\) independent multinomial samples. The
independent draws add randomness that buys nothing, so systematic resampling
is the default in every serious implementation.

## D. From ML to robotics

This is importance sampling followed by resampling, which is to say sequential
Monte Carlo. If you have implemented importance-weighted estimators or SMC
samplers, this is that machinery with the motion model serving as the
proposal distribution, and \(N_{eff}\) is the same effective-sample-size
diagnostic you would already compute.

The particle count behaves like batch size or ensemble size, in that more is
better with diminishing returns, but with one crucial difference: the required
\(N\) grows *exponentially* with state dimension. That single fact explains
the division of labour in the field, since particle filters own low-dimensional
problems such as 2D localisation and lose decisively to Kalman variants in
higher dimensions, which question 4 quantifies.

The fix for the kidnapped robot is exploration. Injecting a few per cent of
uniformly random particles at every step is an ε-greedy hedge against a
confident but wrong belief, and pure exploitation cannot recover from a
converged wrong answer for exactly the reason ε-greedy exists: there are no
samples in the right place to be upweighted.

## E. Minimal implementation

The library lives at
[`robotics_ai/estimation/particle_filter.py`](https://github.com/paulyonghaoli/robotics-for-ai-engineers/blob/main/robotics_ai/estimation/particle_filter.py).
It is state-agnostic, with the caller supplying the motion model and the
likelihood, and it implements systematic resampling, \(N_{eff}\) tracking and
a guard against degenerate updates. The tests include kidnapped-robot
recovery.

### Practice — write and run code here

<code-exercise src="est-l2-pf-resample"></code-exercise>

<code-exercise src="est-l2-pf-localize"></code-exercise>

## F. Robotics-framework implementation

Nav2's **AMCL**, for adaptive Monte Carlo localisation, is this lesson plus
two production upgrades. The first is a proper LiDAR measurement model, either
beam-based or likelihood-field. The second is KLD sampling, which adapts \(N\)
on the fly so the filter runs thousands of particles while lost and only
hundreds once converged, which is where most of its efficiency comes from.

Its parameters map one-to-one onto the concepts above, with `min_particles`
and `max_particles` bounding the adaptive count, and the `recovery_alpha_slow`
and `recovery_alpha_fast` machinery being precisely the random injection that
section D describes.

## G. Experiment — three studies on one world

Using the corridor-with-doors world from the exercise, run three separate
studies.

First run with \(N \in \{50, 200, 2000\}\) and plot both error and
\(N_{eff}/N\) over time, which shows you where the diminishing returns set in
for this particular problem.

Then run the kidnapped-robot scenario, teleporting the true robot mid-run,
twice: once with vanilla resampling and once with five per cent uniform
injection. The vanilla filter stays confidently wrong indefinitely, because
it has no particles anywhere near the new position and therefore nothing to
upweight, while the injected filter recovers after a few doors' worth of
evidence.

Finally, resample at *every* step regardless of \(N_{eff}\) and watch
diversity die as all particles become copies of a handful of ancestors. That
is sample impoverishment made visible, and it is worth seeing because the
symptom is so misleading: the belief looks tight and confident precisely when
it has stopped carrying information.

## H. Failure modes

**Sample impoverishment** follows from aggressive resampling combined with low
motion noise, and the swarm collapses into clones so that the belief appears
precise while being merely inbred. The confusing part is that \(N_{eff}\) can
look perfectly healthy, because the weights are uniform — across particles
that are all the same particle.

**Weight degeneracy** is the opposite failure, in which a too-sharp
likelihood, meaning an overconfident sensor model, zeroes every weight but one
in a single update. Soften the likelihood or gate it.

**Confident and wrong**, the kidnapped-robot case, cannot be recovered from
without injection, because a converged filter has no way to represent
"somewhere else entirely" when no particles live there.

**Dimension creep** happens when state dimensions are added without
multiplying \(N\), spreading the same number of particles over exponentially
more volume, and the filter degrades silently into noise rather than failing
loudly.

## I. Questions

1. *(Concept)* Why can a particle filter represent "the robot is in corridor A
   *or* corridor B" while a Kalman filter cannot, and what does the Kalman
   filter report in that situation?
2. *(Calculation)* Given weights \((0.7, 0.1, 0.1, 0.1)\), compute
   \(N_{eff}\). Does the \(N/2\) rule say to resample?
3. *(Debugging)* After fitting a higher-precision sensor, the filter diverges
   *more* often. Explain this through the weighting step.
4. *(System design)* 2D localisation needs roughly 2,000 particles. Estimate
   the requirement for 6-DOF localisation and justify choosing a different
   estimator.

??? note "Answer sketches"
    **1.** The particle filter's belief is a set of weighted samples, so
    nothing prevents half the swarm from sitting in corridor A and half in
    corridor B; the representation carries both hypotheses literally and their
    weights carry the odds between them. A Kalman filter's belief is a single
    Gaussian parameterised by a mean and a covariance, so asked to cover both
    corridors it reports the mean *between* them, which is a location the
    robot is certainly not in, with a covariance wide enough to span both.
    That reads to any consumer as a single confident answer at an impossible
    place, which is worse than an honest refusal.

    **2.** \(N_{eff} = 1/(0.49 + 0.01 + 0.01 + 0.01) = 1/0.52 \approx 1.92\).
    With \(N = 4\) the threshold is 2, so yes, resample, though only barely.

    **3.** Weight degeneracy caused by a too-sharp likelihood. A
    high-precision sensor makes \(p(z \mid x_i)\) fall off very steeply with
    error, so unless a particle happens to sit almost exactly on the truth its
    weight underflows to approximately zero. One particle then takes
    everything, \(N_{eff}\) collapses to about 1, and resampling clones that
    single and possibly wrong hypothesis. Fix it by softening the measurement
    model, using a \(\sigma\) noticeably larger than the sensor's true
    \(\sigma\) or adding a flat mixture component, and by raising motion noise
    or \(N\) so that some particle lands close enough to be credited.

    **4.** The required \(N\) grows exponentially with state dimension, so
    moving from 3-DOF \((x, y, \theta)\) to 6-DOF at the same per-axis
    resolution squares the count, giving \(2000^2 = 4 \times 10^6\) particles,
    each requiring a full likelihood evaluation every step, which is hopeless
    at sensor rate. Use an EKF or UKF instead — in practice an error-state EKF
    — because its cost is cubic in dimension rather than exponential, and the
    Gaussian assumption is affordable since 6-DOF pose *tracking* is a
    tight-belief problem. Buy back the one capability you lose, global
    initialisation, with a place-recognition system or a low-dimensional
    global localiser to bootstrap the filter, rather than by attempting a
    six-dimensional particle filter.

### Interactive quiz

<quiz-bank src="estimation-l2-pf"></quiz-bank>

## J. Annotated references

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Thrun et al., *Probabilistic Robotics*, ch. 4 & 8 | book | intermediate | Particle filters and Monte Carlo localisation, canonically |
| [Nav2 AMCL docs](https://docs.nav2.org/configuration/packages/configuring-amcl.html) | docs | intermediate | Every parameter maps onto a concept in this lesson, which makes it unusually readable documentation |
| Doucet & Johansen, *"A tutorial on particle filtering"* (2009) | paper | advanced | The sequential Monte Carlo theory underneath the robotics |

## K. Graded work and portfolio extension

**Graded:** the localisation project's second half is particle-filter global
localisation with kidnapped-robot recovery, scored on convergence time and on
recovery success rate.

**Portfolio:** an animated particle cloud moving from uniform through
multimodal to converged on the corridor world, with a kidnap event partway
through. It is probably the single most persuasive demonstration of estimation
understanding you can produce, largely because it is one of the few robotics
artifacts that a non-specialist will actually watch to the end.
