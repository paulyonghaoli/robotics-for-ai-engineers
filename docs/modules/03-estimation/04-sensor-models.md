# 3.4 Sensor models: how your sensors lie to you

**Status:** Code verified · **Prereqs:** lessons 3.1–3.3 · **Time:** ~2 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

A filter is only as honest as its sensor models, because the \(h(x)\) and
\(R\) you hand it are literally claims about how each sensor lies. Get those
claims wrong and every consistency statistic in lesson 3.6 will tell you so,
but only after you have shipped.

Every sensor lies differently, and the differences are structural rather than
a matter of degree. The IMU lies a little more every second, GPS lies by
metres at a time but never accumulates, wheel odometry lies in proportion to
distance travelled, and lidar lies about glass. The next lesson is the
choreography of fusing them; this lesson is knowing the dancers.

!!! note "Terms defined here"

    **Bias** — a persistent offset that does not average away, as opposed to
    noise, which does.

    **Drift** — error that accumulates over time or distance without bound.

    **Specific force** — what an accelerometer actually measures, which
    includes gravity and is therefore not acceleration.

    **Multipath** — a signal arriving by a reflected path, so the range is
    honestly measured and refers to the wrong geometry.

    **Allan variance** — a procedure for characterising how a sensor's error
    behaves across time scales, which separates white noise from bias
    instability.

## B. The cast, by error structure

The organising question is never "how accurate is this sensor". It is **how
does the error behave over time**, because that determines what a filter can
and cannot do about it.

| Sensor | Measures | Error structure | The killer lie |
|---|---|---|---|
| **Gyroscope** | angular rate | white noise plus a slowly wandering **bias** | integrating rate makes heading drift *linearly* from bias and as \(\sqrt{t}\) from noise |
| **Accelerometer** | specific force, gravity included | noise plus bias, then double-integrated for position | position drift grows as \(t^2\), reaching metres within a minute |
| **Wheel odometry** | incremental motion | error proportional to distance; systematic from wheel radius, stochastic from slip | perfect in the log and wrong at the destination; total fiction during slip |
| **GPS** | absolute position | metres of noise and multipath jumps, but **bounded** | urban canyons produce confident errors of tens of metres, which is not noise |
| **Lidar** | ranges | centimetre noise, but material-dependent | glass is transparent, mirrors teleport returns, rain scatters, and max-range readings are ambiguous |
| **Magnetometer** | heading reference | bounded, but wildly disturbed | every motor, structural beam and length of rebar bends "north" |

The deep pattern underneath that table is a two-way split. **Relative
sensors**, such as the gyroscope and wheel odometry, are smooth and fast and
drift without bound, while **absolute sensors**, such as GPS, landmarks and
the magnetometer, are noisy or slow but bounded. Fusion exists precisely
because those two error structures are complementary, which is lesson 3.1's
GPS-plus-IMU question generalised into a design principle.

## C. Mathematical formulation

The workhorse IMU error model, per axis, is

\[
\tilde{\omega}(t) = \omega(t) + b(t) + n(t), \qquad \dot{b} = n_b
\]

meaning white noise \(n \sim \mathcal{N}(0, \sigma_n^2)\) on top of a bias
\(b\) that itself performs a random walk.

Those two terms behave completely differently under integration, which is the
central fact of the lesson. Integrated heading error grows as
\(\sigma_n \sqrt{t}\) from the noise but as \(b \cdot t\) from the bias, and
linear growth overtakes square-root growth quickly. After a minute the bias
typically dominates by an order of magnitude, which is why serious filters
**estimate the bias as a state** rather than burying it in \(Q\) — the
familiar "fifteen-state EKF" is pose, velocity and six IMU biases, and those
six states exist entirely because of this asymmetry.

Characterising \(\sigma_n\) and the bias stability from a stationary log is
the Allan variance procedure, and the exercise below implements its two-point
essence.

Wheel odometry's standard model is per-distance noise,
\(\sigma_{trans} = k_d \sqrt{d}\), plus a per-rotation heading noise, which in
*Probabilistic Robotics* appears as the \(\alpha_1 \dots \alpha_4\)
parameters. You have already met these as the motion noise in the localisation
project.

## D. From ML to robotics

Bias against variance is not an analogy here but the same distinction
literally. White noise is variance and a filter averages it away, while bias
is bias and no amount of averaging helps, so it must be modelled as state and
estimated. The instinct you already have — asking whether an error is
reducible by more data — maps exactly onto asking whether an error is
reducible by more measurements.

Characterising a sensor is profiling a data source. You log it stationary, fit
the noise, and check for drift, which is the same discipline as profiling a
new upstream feed before trusting it in a pipeline. Sensor datasheets play the
role of vendor SLAs: a reasonable starting point, and not the truth about
*your* unit at *your* temperature.

The failure modes are all distribution shift. GPS multipath, a magnetometer
near steel and a lidar aimed at glass are each a regime in which the
error model you characterised silently stops applying, and detection through
the innovation gates of lesson 3.5 beats hoping the regime does not occur.

## E. Minimal implementation and practice

<code-exercise src="est-l4-gyro"></code-exercise>

## F. Robotics-framework implementation

`robot_localization`'s configuration is this lesson expressed as YAML,
consisting of per-sensor choices about which components to fuse plus
covariance entries that you are expected to fill in honestly. REP 145
standardises IMU message conventions, and real IMU drivers report their own
noise densities, which you should verify against your own stationary log
anyway — that is the exercise's procedure, run on hardware.

## G. Experiment — the argument for bias-as-state, in one plot

Extend the exercise by simulating the same gyroscope twice. In the first run,
integrate the rate directly. In the second, estimate the bias as a filter
state, using a two-state Kalman filter over heading and bias, fed by an
occasional absolute heading fix such as a compass reading every ten seconds.

Watch the bias estimate converge and the heading error flatten from linear
growth into a bounded band. That single plot is the entire justification for
carrying bias states, and it also shows why the absolute fix is required:
without it the bias is unobservable and the filter has no way to separate a
constant rate offset from genuine slow rotation.

### The experiment's numbers

Running section G's comparison — the same gyroscope (\(\sigma_n = 0.01\
\text{rad}/\sqrt{\text{s}}\), initial bias 0.01 rad/s, slowly wandering) for
five minutes, with a compass fix every ten seconds:

| Strategy | Heading error |
|---|---|
| Integrate the gyro raw | **+191° after 300 s**, growing linearly forever |
| Two-state KF, bias as a state | worst error 7.8°, bounded, indefinitely |
| — its bias estimate at the end | 0.0099 rad/s against a true 0.0109 |

The raw integration is not noisy; it is *wrong in a straight line*, which is
what a bias does under integration, and after five minutes it has lapped half
a revolution. The two-state filter identifies the bias to within ten per cent
— including tracking its slow wander — from nothing but occasional coarse
compass fixes, and holds heading bounded forever after. The section C
arithmetic predicts the crossover: at 60 s the noise random walk has
contributed 4.4° while the bias ramp has contributed 34.4°, so the bias
dominates by 8× within the first minute, and every second after that widens
the gap.

One subtlety the numbers reveal: the bias is **unobservable without the
absolute fix**. Between compass updates the filter cannot distinguish a rate
bias from a genuine slow turn — nothing in the gyro stream separates them —
so the bias estimate only corrects when an absolute reference arrives. That
is why the worst-case error (7.8°) is set by the compass interval, and why
halving that interval roughly halves the bound. Bias states do not remove the
need for absolute sensing; they let sparse absolute sensing go a long way.

## H. Failure modes

**Trusting the datasheet's \(\sigma\)** ignores that the number describes some
unit at some temperature under some vibration, and not necessarily yours. Log
and fit, or the \(R\) in your filter is fiction.

**Forgetting gravity in the accelerometer** matters because the device
measures specific force, reporting 9.81 m/s² while sitting perfectly still.
Orientation error then leaks gravity into the horizontal channels, and the
arithmetic is unforgiving: one degree of tilt produces about 17 cm/s² of
phantom horizontal acceleration, which double-integrates into metres
alarmingly fast.

**Odometry during slip** breaks the model's core assumption, since the model
says error is proportional to distance while a wheel spinning on ice generates
distance without motion. Slip has to be detected through disagreement between
sensors, because odometry cannot detect it in itself.

**Treating multipath GPS as Gaussian** misreads the failure. Multipath is a
mode switch rather than a fat tail, so the fix is to gate it as in lesson 3.5
or to model the mixture explicitly, not to inflate \(R\) until the outliers
fit inside it.

## I. Questions

1. *(Concept)* Why does gyroscope bias dominate white noise in integrated
   heading after roughly a minute?
2. *(Calculation)* A gyroscope bias of 0.01 rad/s is ignored for 60 s. How
   many degrees of heading error does that produce?
3. *(Debugging)* Your robot's fused pose is excellent indoors but veers
   consistently near the loading dock's steel door. Which sensor, and which
   failure?
4. *(System design)* You get exactly one absolute sensor for a warehouse
   robot: GPS, UWB beacons, or a ceiling-marker camera. Choose and defend the
   choice through error structure.

??? note "Answer sketches"
    **1.** Integration treats the two error terms completely differently.
    Zero-mean white noise integrates into a random walk whose heading error
    grows as \(\sigma_n\sqrt{t}\), while a bias is a persistent offset that
    integrates to \(b \cdot t\), and linear growth overtakes square-root growth
    quickly. With \(\sigma_n = 0.01\ \text{rad}/\sqrt{\text{s}}\) and
    \(b = 0.01\ \text{rad/s}\), at 60 s the noise contributes about 0.077 rad
    while the bias contributes 0.6 rad, nearly an order of magnitude more.
    That gap is the entire argument for estimating bias as a state rather than
    absorbing it into \(Q\).

    **2.** \(0.01 \times 60 = 0.6\) rad, which is about 34°, produced by a bias
    that would look like a perfectly flat line in any five-second log.

    **3.** The magnetometer. The steel door, its rebar and its motor bend the
    local magnetic field, so "north" is displaced by a large and *repeatable*
    amount in that one location. This is a bias rather than noise, so the
    filter fuses it as an honest absolute heading fix and the fused pose veers
    the same way on every pass, which is the giveaway. The fix is to pre-gate
    the magnetometer on field magnitude and inclination against the surveyed
    local field, gate its innovation on chi-squared, and let the gyroscope plus
    another absolute source carry heading through the anomaly zone.

    **4.** UWB beacons. Ceiling markers give beautifully bounded pose but only
    while a marker is in view, so their true error structure is "bounded when
    visible, unbounded odometry drift otherwise", and a warehouse reliably
    supplies occlusion, dust and racking that moves. UWB gives continuous
    absolute ranges at tens of hertz with decimetre noise that does not
    accumulate with driving time, and it degrades gracefully, since losing
    anchors widens the covariance rather than cutting the absolute fix off at
    a cliff. The costs you accept are anchor survey and installation, plus
    non-line-of-sight multipath near metal racking, which is a mode switch and
    should be gated rather than modelled as Gaussian.

### Interactive quiz

<quiz-bank src="estimation-l4-sensors"></quiz-bank>

## J. Annotated references

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Thrun et al., *Probabilistic Robotics*, ch. 5–6 | book | intermediate | Motion and measurement models, canonically |
| Woodman, *"An introduction to inertial navigation"* (2007) | report | introductory | The IMU error model, explained with unusual clarity, and the best single source for section C |
| [REP 145 — IMU conventions](https://www.ros.org/reps/rep-0145.html) | docs | introductory | What the wire format promises, which is not always what the driver delivers |

## K. Graded work and portfolio extension

**Graded:** the localisation project's noise parameters are this lesson's
vocabulary, and the capstone's first field note, on max-range ambiguity, is a
lidar model failure you will have already debugged by then.

**Portfolio:** buy a cheap IMU, log it overnight, produce the Allan variance
plot and compare it against the datasheet. It is a tiny hardware project that
says "I profile sensors before trusting them" more convincingly than any
amount of coursework, and the discrepancy you find will be real.
