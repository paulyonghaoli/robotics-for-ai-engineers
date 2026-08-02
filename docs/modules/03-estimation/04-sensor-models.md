# 3.4 Sensor models: how your sensors lie to you

**Status:** Code verified · **Prereqs:** lessons 3.1–3.3 · **Time:** ~2 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

A filter is only as honest as its sensor models — the \(h(x)\) and \(R\) you feed it are *claims about how each sensor lies*. Every sensor lies differently: the IMU lies a little more every second (drift), GPS lies meters at a time but never *accumulates*, wheel odometry lies in proportion to distance, lidar lies about glass. Fusion architecture (next lesson) is choreography; this lesson is knowing the dancers.

## B. The cast, by error structure

The organizing question is never "how accurate?" — it's **"how does the error behave over time?"**

| Sensor | Measures | Error structure | The killer lie |
|---|---|---|---|
| **Gyro** | angular rate | white noise + slowly-wandering **bias** | integrating rate → heading drifts *linearly* from bias, √t from noise |
| **Accelerometer** | specific force (incl. gravity!) | noise + bias; double-integrated for position | position drift grows ∝ t² — meters within a minute |
| **Wheel odometry** | incremental motion | error ∝ distance traveled; systematic (wheel radius) + stochastic (slip) | perfect in the log, wrong at the destination; total fiction during slip |
| **GPS** | absolute position | meters of noise, multipath jumps, but **bounded** | urban canyons: confidently wrong by tens of meters — not just noisy |
| **Lidar** | ranges | cm noise, but material-dependent | glass (transparent), mirrors (teleporting returns), rain, max-range ambiguity (capstone field note #1!) |
| **Magnetometer** | heading reference | bounded, but wildly disturbed | every motor, beam, and rebar bends "north" |

The deep pattern: **relative sensors** (gyro, odometry) are smooth, fast, and drift without bound; **absolute sensors** (GPS, landmarks, magnetometer) are noisy or slow but bounded. Fusion exists because these error structures are *complementary* — lesson 3.1's GPS+IMU question, now generalized.

## C. Mathematical formulation

The workhorse IMU error model, per axis:

\[
\tilde{\omega}(t) = \omega(t) + b(t) + n(t), \qquad \dot{b} = n_b
\]

white noise \(n \sim \mathcal{N}(0, \sigma_n^2)\) plus a bias \(b\) that random-walks. Integrated heading error grows as \(\sigma_n \sqrt{t}\) from noise but \(b \cdot t\) from bias — after a minute, bias dominates by an order of magnitude, which is why serious filters **estimate the bias as a state** (the "15-state EKF" = pose + velocity + 6 IMU biases). Characterizing \(\sigma_n\) and the bias stability from a stationary log is the *Allan variance* procedure; the exercise does its two-point essence.

Wheel odometry's standard model: per-distance noise, \(\sigma_{trans} = k_d \sqrt{d}\), plus per-rotation heading noise — Probabilistic Robotics' \(\alpha_1..\alpha_4\) parameters, which you already met as the localization project's motion noise.

## D. From ML to robotics

- **Bias vs variance, literally.** White noise is variance (filters average it away); bias is bias (no amount of averaging helps — it must be *modeled as state* and estimated). The ML instinct "is this error reducible by more data?" maps exactly.
- **Characterizing a sensor = profiling a data source.** Log it stationary, fit the noise, check drift — the same discipline as profiling a new upstream feed before trusting it in a pipeline. Sensor datasheets are like vendor SLAs: a starting point, not the truth about *your* unit.
- **Failure modes are distribution shift:** GPS multipath, magnetometer near steel, lidar on glass — each is a regime where the training-time error model silently stops applying. Detection (via innovation gates, lesson 3.5) beats hope.

## E. Minimal implementation & practice

<code-exercise src="est-l4-gyro"></code-exercise>

## F. Robotics-framework implementation

`robot_localization`'s config is this lesson as YAML: per-sensor which-components-to-fuse plus covariance entries you must fill honestly. REP 145 standardizes IMU message conventions; real IMU drivers report their own noise densities — verify them with your own stationary log anyway (the exercise's procedure, on hardware).

## G. Experiment

Extend the exercise: simulate the same gyro with bias estimated as a filter state (a 2-state KF: heading + bias) fed by occasional absolute heading fixes (a compass every 10 s). Watch the bias estimate converge and heading error flatten from linear growth to bounded — the entire justification for bias-as-state, in one plot.

## H. Failure modes

- **Trusting the datasheet σ**: your unit, your temperature, your vibration. Log-and-fit or the filter's R is fiction.
- **Forgetting gravity in the accelerometer**: it measures specific force — 9.81 m/s² of "acceleration" while sitting still. Orientation error leaks gravity into horizontal acceleration: tilt 1° = 17 cm/s² of phantom acceleration.
- **Odometry during slip**: the model says σ ∝ distance; a wheel spinning on ice generates distance without motion. Detect via fusion disagreement, not odometry itself.
- **Treating multipath GPS as Gaussian**: it's a *mode switch*, not a fat tail. Gate it (lesson 3.5) or model the mixture.

## I. Questions

1. *(Concept)* Why does gyro bias dominate white noise in integrated heading after ~a minute?
2. *(Calculation)* Gyro bias 0.01 rad/s ignored for 60 s: how many degrees of heading error?
3. *(Debugging)* Your robot's fused pose is perfect indoors but veers consistently near the loading dock's steel door. Which sensor, which failure?
4. *(System design)* You get one absolute sensor for a warehouse robot: GPS (useless indoors), UWB beacons, or ceiling-marker camera. Choose and defend via error structure.

??? note "Answer sketches"
    **1.** Integration treats the two error terms completely differently: zero-mean white noise integrates into a random walk whose heading error grows as \(\sigma_n\sqrt{t}\), while a bias is a persistent offset that integrates to \(b\cdot t\). Linear beats \(\sqrt{t}\) quickly — with \(\sigma_n = 0.01\ \text{rad}/\sqrt{\text{s}}\) and \(b = 0.01\ \text{rad/s}\), at 60 s the noise contributes ≈ 0.077 rad but the bias 0.6 rad, nearly an order of magnitude more. That gap is the whole argument for estimating bias as a state rather than burying it in \(Q\).

    **2.** \(0.01 \times 60 = 0.6\) rad ≈ 34° — from a bias that looks like a flat line in any 5-second log.

    **3.** The magnetometer: the steel door, its rebar, and its motor bend the local field, so "north" is displaced by a large, *repeatable* amount in that one location. This is a bias, not noise — the filter fuses it as an honest absolute heading fix and the fused pose veers the same way every pass. Fix: pre-gate the magnetometer on field magnitude and inclination against the surveyed local field, gate its innovation on χ², and let gyro + another absolute source carry heading through the anomaly zone.

    **4.** UWB beacons. Ceiling markers give beautifully bounded pose but only while a marker is in view, so their error structure is really "bounded when visible, unbounded odometry drift otherwise" — and warehouses supply occlusion, dust, and racking that moves. UWB gives continuous absolute ranges at tens of Hz with decimetre noise that does not accumulate with driving time, and it degrades gracefully: losing anchors widens the covariance instead of cutting the absolute fix off at a cliff. The cost you accept is anchor survey/installation and NLOS multipath near metal racking, which is a mode switch — gate it, don't model it as Gaussian.

### Interactive quiz

<quiz-bank src="estimation-l4-sensors"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Thrun et al., *Probabilistic Robotics*, ch. 5–6 | book | intermediate | Motion and measurement models, canonically |
| Woodman, *"An introduction to inertial navigation"* (2007) | report | introductory | The IMU error model, wonderfully clear |
| [REP 145 — IMU conventions](https://www.ros.org/reps/rep-0145.html) | docs | introductory | What the wire format promises |

## K. Graded work & portfolio extension

**Graded:** the localization project's noise parameters are this lesson's vocabulary; the capstone's field note #1 (max-range ambiguity) is a lidar model failure you've already debugged.

**Portfolio:** buy a $30 IMU, log it overnight, produce the Allan-variance plot, and compare against its datasheet — a tiny hardware project that says "I profile sensors before trusting them" louder than any coursework.
