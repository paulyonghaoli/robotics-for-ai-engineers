# 9.4 Sim-to-real and domain randomization

**Status:** Code verified · **Prereqs:** lessons 9.1, 10.2 *(read ahead)* · **Time:** ~2.5 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Simulation is where robot learning can afford to happen. It is free, parallel, resettable, and safe. It is also *wrong* — in ways you don't know, which is the entire problem. A policy tuned to exploit your simulator's particular friction model will find that model's mistakes with the enthusiasm of any optimizer handed a flawed objective.

Domain randomization is the dominant answer: instead of trying to make one simulator correct, train across a *distribution* of simulators so that reality is just another sample. It works, it is cheap, and — this is the part usually left out — **it costs you performance on any single condition**, including the real one. This lesson is about that trade, measured.

## B. Mental model

Three stances toward the reality gap:

1. **Close it** — system identification: measure your robot's real parameters and put them in the simulator. Precise, laborious, and only covers what you thought to measure.
2. **Span it** — domain randomization: sample masses, frictions, latencies, and sensor noise from wide distributions each episode. The policy must work for all of them, so it works for reality too.
3. **Sidestep it** — co-training on sim plus a smaller real dataset, which is what shipping systems mostly do. NVIDIA's GR00T reported sim-plus-real beating real-only by **+40%**, using 780,000 synthetic trajectories generated in eleven hours.

The mental image for randomization: you are not training a policy for *a* robot, you are training one for a *family* of robots, and betting reality is inside the family. Two consequences follow immediately, and they pull in opposite directions:

- **Randomize too narrowly** and reality falls outside the family — the policy transfers no better than one trained on the nominal simulator.
- **Randomize too widely** and the policy must hedge against robots that don't exist. It becomes conservative and mediocre everywhere, including on the real robot. This is the **randomization tax**, and the exercise measures it.

The tax is real but usually worth paying, because a policy that is 20% worse and *works* beats one that is optimal and doesn't. The exercise measures all three regimes on one system:

| trained on | nominal simulator | reality |
|---|---|---|
| nominal only | 100% (best tracking) | **0%** |
| randomized to reality's range | 100% (28% worse tracking) | **100%** |
| randomized 2.7× too wide | **35%** | 100% |

Note the last row. Over-randomization doesn't merely cost you some performance — pushed far enough it *breaks the nominal condition*, because the policy is now hedging against robots that don't exist.

## C. Formulation

With simulator parameters \(\xi\) drawn from a randomization distribution \(p(\xi)\), you optimize

\[
\max_\pi \; \mathbb{E}_{\xi \sim p(\xi)}\big[ J(\pi, \xi) \big]
\]

rather than \(J(\pi, \xi_{nominal})\). The maximizer of an expectation over a family is generally optimal for no single member — that sentence is the randomization tax in one line, and it is a property of the objective, not a defect of the method.

**What to randomize**, roughly in order of payoff: masses and inertias, friction coefficients, actuator gains and latency, sensor noise and bias, and — for vision — lighting, textures, and camera pose. Latency is the one teams forget and the one that most reliably breaks transfer.

**How wide?** Wide enough that reality is plausibly inside, no wider. In practice you widen until validation on a held-out *different* simulator stops improving, which is domain randomization's version of a validation set.

The complement is worth naming: **system identification narrows \(p(\xi)\)**. Every parameter you measure is one you no longer have to hedge against, which is why the two stances are partners rather than rivals.

## D. From ML to robotics

- **This is data augmentation with physics.** The exact same logic as rotating and cropping images — you augment along the axes you expect to vary — and the same failure if you augment along axes that don't matter while missing the one that does.
- **The tax is the bias–variance trade in disguise.** A policy specialized to the nominal simulator has low bias there and enormous variance across conditions; a randomized policy trades some nominal performance for stability across the family.
- **"Reality is one sample from the training distribution"** is a strong and testable claim. When transfer fails, the first question is not "is my policy bad?" but **"was reality inside my distribution?"** — and that is usually answerable by measuring the real parameter and checking.

## E. Practice

<code-exercise src="rl-l4-randomization"></code-exercise>

## F. In production

Isaac Lab and MuJoCo/MJX are built for this — thousands of parallel environments each with different parameters. The Newton physics engine (Linux Foundation, 2026) reports 252–475× MJX throughput, which changes what randomization budgets are affordable. Disney trained a robot's locomotion entirely in simulation with zero real training data for a Disneyland Paris attraction. The sober counterpoint from the same year: a world-action model transferred with **zero real demonstrations and heavy randomization reached 35% average success** on a fixed arm — real transfer, and nowhere near deployable alone.

## G. Experiment

Run the capstone with its noise parameters randomized per episode — `RANGE_SIGMA`, `POSE_SIGMA_XY`, and the motion sigmas — over progressively wider ranges, and evaluate each resulting configuration on the *un-randomized* nominal simulator plus a deliberately shifted one (say 2× lidar noise). Plot both curves against randomization width. You should see the nominal curve fall slowly while the shifted curve rises sharply, cross, and then both decline. The crossing point is where randomization starts paying for itself; the far-right decline is the tax becoming unaffordable.

## H. Failure modes

- **Randomizing the wrong axes.** Wide friction randomization while latency stays fixed at zero is effort spent on a parameter that wasn't the gap.
- **Forgetting latency.** Real actuation and perception lag; a zero-latency simulator teaches a policy timing that does not exist.
- **Sim-exploiting policies.** If your simulator lets a gripper pass slightly through an object, the policy will discover and rely on it. Randomize contact parameters, and be suspicious of behaviour that looks *too* clean.
- **Randomizing until nothing works** and concluding the task is hard, when the distribution simply became absurd.
- **No held-out simulator.** Tuning randomization width against the same conditions you evaluate on is the leakage of lesson 10.2, wearing a physics costume.

## I. Questions

1. *(Concept)* Why does a policy trained across a distribution of simulators tend to be suboptimal on every individual one, including reality?
2. *(Calculation)* A policy is 100% successful in sim and 0% on the real robot. A randomized policy is 100% in both, with 26% higher tracking error in sim. If tracking error costs $1 per unit and a failure costs $500, which do you deploy?
3. *(Debugging)* Your policy transfers well to a real robot in the lab but fails in a warehouse. Randomization covered mass, friction, and sensor noise. What is the most likely missing axis?
4. *(System design)* You can spend a week either measuring your robot's real parameters (system identification) or building a randomization pipeline. When is each the better investment?

??? note "Answer sketches"
    **1.** Because it maximizes \(\mathbb{E}_{\xi}[J(\pi,\xi)]\) rather than \(J(\pi,\xi_{nominal})\), and the maximizer of an average over a family is generally optimal for no member of it. The policy must hedge — choose gains that stay stable for the heaviest, slowest, noisiest robot in the distribution — and that hedge is dead weight on any particular robot. It is a property of the objective, not a flaw in the method.

    **2.** Deploy the randomized one, and it isn't close. The tracking penalty is 26% of a small number and is paid continuously; the alternative fails *every* episode at $500 each. Even at one episode a day, the sim-optimal policy costs $500/day versus a few dollars of extra tracking error. The general lesson: the tax is denominated in performance and the failure is denominated in outcomes, and outcomes almost always dominate.

    **3.** Latency — the axis teams most reliably forget. A warehouse adds network hops, more sensor traffic, and higher compute contention than a lab bench, all of which lengthen the perception-to-actuation delay. A policy trained at zero latency has learned timing that no longer holds. Lighting is the runner-up if the stack is vision-based. Both are testable in an afternoon by measuring the real delay and re-running the randomization with it included.

    **4.** Identify when the parameter is few, stable, and measurable — link masses, gear ratios, camera intrinsics — because every parameter you measure is one you no longer hedge against, which directly reduces the tax. Randomize when the parameter is many, drifting, or unmeasurable — contact friction across surfaces, payload variation, wear over months. Most real programmes do both: system identification narrows the distribution, randomization spans what remains. If forced to pick for one week and the robot is fixed and repeatable, identify; if it is a fleet in varied environments, randomize.

### Interactive quiz

<quiz-bank src="rl-l4-sim2real"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Tobin et al., *Domain Randomization* (2017) | paper | introductory | The original statement, still the clearest |
| Peng et al., *Sim-to-Real with Dynamics Randomization* (2018) | paper | intermediate | Randomizing dynamics rather than appearance |
| [Isaac Lab](https://isaac-sim.github.io/IsaacLab/) | docs | intermediate | Where you'd run thousands of randomized environments |

## K. Graded work & portfolio extension

**Graded:** the randomization exercise quantifies the tax, which is the part most treatments assert without measuring.

**Portfolio:** the section G study on your own capstone — nominal and shifted performance against randomization width, with the crossing point marked. It's a complete, self-contained experiment about a trade everyone cites and few measure.
