# 11.5 Safety cases for learned components

**Status:** Code verified · **Prereqs:** lessons 5.4, 9.7, 11.3 · **Time:** ~2.5 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

You can reason about a PID controller. You can bound its response, prove stability margins, and write down what it will do. You can do none of that for a 6-billion-parameter policy, and no amount of testing closes the gap: RAND's standing objection is that demonstrating a fatality rate statistically would require *hundreds of millions to billions* of miles per candidate version, which no development process can afford.

So the question is not "how do I prove the network is safe?" It is: **how do I build a system that is safe even though a component of it cannot be verified?** That reframing is the entire content of this lesson, and it is the single most transferable idea in the module.

## B. Mental model

**Don't make the learned thing safe. Make the system safe despite it.**

The architecture is decades old and goes by several names — runtime assurance, the simplex architecture, a safety shield. A verifiable monitor sits between the untrusted policy and the actuators. It checks each proposed action against a condition simple enough to reason about, and substitutes a trusted fallback when the check fails.

The exercise builds exactly that. A policy that is sensible 97% of the time and occasionally reckless, wrapped in a four-line braking-feasibility check:

| margin | collision rate | task success |
|---|---:|---:|
| no monitor | 0.030 | 0.970 |
| 0.15 m | **0.000** | **1.000** |
| 0.45 m | 0.000 | 1.000 |
| 0.80 m | 0.000 | **0.000** |

The first two rows are the good news: an unverifiable policy became a system with zero collisions, and the thing you had to reason about was arithmetic, not a network.

**The last row is the lesson.** That monitor also reports zero collisions — a perfect score on the safety metric — while the robot never completes its task, because the safety margin exceeded the clearance the task requires. It is perfectly safe and completely useless.

So a safety argument needs two claims, and the second is the one people forget:

- **Safety:** the system does not do the bad thing.
- **Liveness:** the system still does the good thing.

A monitor evaluated only on the first is indistinguishable from a robot that never moves.

## C. What a safety case actually is

A structured argument that a system is acceptably safe in a defined context, with evidence for each claim. Not a document produced at the end — a design artifact that shapes the architecture.

The workable structure for a learned component:

1. **Bound the operating context.** "This is safe" is meaningless; "this is safe below 2 m/s, indoors, on flat floors, with a human-detectable e-stop" is a claim you can defend. The [capstone's published envelope](../../capstone-log.md) — reliable at six movers, not at ten — is a small example of exactly this discipline.
2. **Identify hazards** and, for each, what prevents it.
3. **Assign each hazard to a verifiable mechanism** wherever possible: a monitor, a hardware interlock, a torque limit, a geometric constraint. Learned components should not be load-bearing in a safety argument.
4. **Show the mechanisms are sound** — for a monitor, that its check is conservative with respect to the physics.
5. **Show the system remains useful** under those mechanisms. The liveness claim.
6. **State the residual risk** honestly, including what your evidence could not have detected (lesson 11.3's canary-power argument applies directly).

## D. From ML to robotics

- **This is the guardrail pattern**, and it has the same virtue and the same trap. The virtue: you constrain an unpredictable component with a predictable one. The trap: guardrails tight enough to guarantee safety often make the system useless, and nobody notices because the safety metric looks perfect.
- **Formal verification of networks remains impractical at scale**, which is why the 2026 literature moved toward runtime assurance and safety shields rather than proving properties of the policy. The *Safe Physical AI* workshop and the "from imitation to certification" line of work are this argument institutionalized.
- **VLAs introduced genuinely new attack surfaces** — data poisoning at 0.31% of episodes achieving 98–99% backdoor success, semantic jailbreaks, and "freezing attacks." A monitor that constrains *actions* is agnostic to how the policy was compromised, which is a strong argument for architectural rather than model-level defence.

## E. Practice

<code-exercise src="dep-l5-safety-monitor"></code-exercise>

## F. In production

ISO 10218 and ISO/TS 15066 govern industrial and collaborative robots — speed and separation monitoring, power and force limiting — and are architectural constraints, not model properties. ISO 26262 and SOTIF (ISO 21448) cover the automotive side, with SOTIF specifically addressing hazards from *functional insufficiency* rather than component failure, which is exactly the learned-component problem. Waymo's TÜV SÜD audits of its safety case and its fleet-response programme are the closest thing to a public worked example.

## G. Experiment

Add a monitor to the capstone: before executing each DWA command, check that the arc leaves the robot able to stop within the free space the current scan reports. Run v3 at ten movers — the regime where the published envelope says it becomes unreliable — and measure collisions and success with the monitor at several margins. You should reproduce the table in section B on your own system, including the margin at which safety becomes uselessness.

## H. Failure modes

- **Evaluating a monitor only on the safety metric.** Zero collisions is achievable by never moving.
- **A monitor that isn't conservative.** If the check can be satisfied by an unsafe action — because the physics model behind it is optimistic — the guarantee is void, and the architecture provides false confidence.
- **Load-bearing learned components.** If the safety argument depends on the network behaving, there is no argument.
- **Unbounded operating context.** A claim without a stated envelope cannot be evaluated or defended.
- **Monitors that can be starved.** If the check itself misses the control deadline (lesson 11.1), it isn't a guarantee.
- **Testing your way to a safety claim.** Statistically infeasible for rare events; the argument must be architectural.

## I. Questions

1. *(Concept)* Why can't you test your way to a safety claim for a rare failure?
2. *(Calculation)* A monitor reports zero collisions across 400 episodes. Using lesson 10.1's Wilson interval, what upper bound on the true collision rate does that support?
3. *(Debugging)* Your safety monitor reports zero violations in the field, but the robot has had two collisions. Name two explanations.
4. *(System design)* Write the outline of a safety case for the capstone's v3 stack as deployed in a warehouse.

??? note "Answer sketches"
    **1.** Because the number of trials needed scales inversely with the event rate, and for genuinely rare failures that is hundreds of millions of miles per candidate version — infeasible for any development cycle, and it would have to be repeated for every software change. This is why safety arguments are architectural rather than empirical: you constrain the system so the bad outcome is prevented by a mechanism you can reason about, then use testing to check the mechanism rather than to estimate the rate.

    **2.** 0/400 gives a Wilson upper bound of roughly **0.9%** — so the evidence is consistent with a collision rate approaching one in a hundred. That is a useful bound for a warehouse robot and nowhere near adequate for a safety-critical claim, which is precisely the gap architecture has to close.

    **3.** First, the monitor is **not conservative** — its underlying model is optimistic (braking authority overstated, latency unmodelled, friction assumed), so an action it certifies can still collide. Second, the monitor was **bypassed or starved**: it missed its deadline and was skipped, ran on stale state, or the collision occurred in a mode where it wasn't active. Both are found the same way: log every monitor decision alongside the outcome, and check whether the collisions had a certifying decision or no decision at all.

    **4.** *Context:* indoors, flat floor, ≤ 1.2 m/s, mapped environment, up to six non-cooperative movers, human-accessible e-stop. *Hazards:* collision with a person, collision with infrastructure, entrapment, running while mislocalized. *Mechanisms:* braking-feasibility monitor on every commanded arc (verifiable arithmetic); inflation margin audited end-to-end so layers don't compound (field note 6); localization-consistency gate that halts on sustained NIS elevation; hardware e-stop independent of software. *Soundness:* monitor conservative against measured braking authority including latency. *Liveness:* task success ≥ 0.95 at six movers with monitors active. *Residual risk:* behaviour above six movers is outside the tested envelope and explicitly not claimed — the published operating envelope is part of the safety case, not a footnote to it.

### Interactive quiz

<quiz-bank src="dep-l5-safety-quiz"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| Koopman & Wagner, *Challenges in Autonomous Vehicle Testing and Validation* | paper | intermediate | Why testing alone cannot produce a safety claim |
| Sha, *Using Simplicity to Control Complexity* (2001) | paper | intermediate | The simplex architecture, from the source |
| ISO 21448 (SOTIF) overview | standard | intermediate | Hazards from functional insufficiency — the learned-component case |

## K. Graded work & portfolio extension

**Graded:** the runtime-assurance exercise is the module's capstone skill, and the safety-plus-liveness pairing generalizes to any guardrail you ever build.

**Portfolio:** the section G study, plus a written safety case for your capstone in the section C structure. Very few portfolios contain a safety argument, and the discipline of stating an operating envelope and a residual risk is exactly what distinguishes an engineer from a demo.
