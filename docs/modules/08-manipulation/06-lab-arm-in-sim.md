# 8.6 Lab: the arm that worked in simulation

**Status:** Code verified · **Prereqs:** lessons 8.1–8.5 · **Time:** ~2 h · **Verified:** 2026-08-03, Python 3.13, NumPy ≥ 1.26

---

## A. Why this lab exists

Three systems that pass every test their author wrote, produce trajectories that look correct when plotted, and do something violent on hardware.

That combination is specific to manipulation. A mobile robot's failures are usually visible in the plot — it goes the wrong way, it hits a wall, it oscillates. An arm's failures live in the gap between task space and configuration space: the tool follows a smooth path while the joints do something no one asked for, and the plot everybody looks at is the tool.

All three bugs below are invisible in task space and obvious in joint space. That is the lesson, and it is why the probes plot what they plot.

## B. The diagnostic table

| Symptom | The tempting explanation | The assumption that actually broke |
|---|---|---|
| Wrist occasionally makes a full revolution | a motor or encoder fault | **joint angles are periodic** — interpolating the raw difference |
| Arm folds into itself; obstacles fine | the planner is broken | **the arm is an obstacle too** |
| Smooth tool path, joints jump mid-traverse | IK solver instability | **IK is a relation** — the seed selects a branch |
| Controller screams at the workspace edge | gains need retuning | **singularity** ([8.1](01-kinematics.md)) |
| "Free" null-space motion drags the tool | the projector is wrong | **linearisation drift** ([8.2](02-inverse-kinematics.md)) |

## C. The gauntlet

<code-exercise src="man-l6-bug-wrap"></code-exercise>

Two degrees apart, 358 degrees travelled. Nothing is wrong with linear interpolation — the problem is what is being interpolated. `b - a` on periodic quantities is not the angular difference, and the simulator's plot of the *tool* shows a perfectly smooth arc throughout, because the tool genuinely does move smoothly while the wrist goes the long way round.

<code-exercise src="man-l6-bug-selfcollide"></code-exercise>

Every world obstacle is respected. The folded configuration is 0.007 m from passing the third link through the first, and the checker reports it valid because it was only ever asked about the world. Note which lesson makes this worse: the null-space posture term from [8.2](02-inverse-kinematics.md) moves the elbow freely through exactly the configurations nobody is checking, so the better your redundancy resolution, the more reliably you find this bug.

<code-exercise src="man-l6-bug-coldstart"></code-exercise>

The tool moves 3 cm between waypoints; the joints jump 1125°. Seeding every IK solve from the same fixed configuration lets the solver land in whichever basin that seed falls into, and which basin that is changes as the target moves. Warm-starting from the previous solution takes the same trajectory from 1125° to 2°.

## D. Diagnosis drills

<quiz-bank src="man-l6-drills"></quiz-bank>

## E. Debrief: the method

**Plot joint space, not just task space.** All three bugs are invisible in the plot everyone looks at. The tool position is smooth in every one of them, because the tool position is what the solver was optimising — of course it is smooth. Whatever you optimise will look fine; look at what you did not optimise.

**Ask what your validity check is actually checking.** Bug 2's checker is entirely correct about the question it was asked. The bug is the question. This is the same shape as [7.6's](../07-perception/06-lab-perception-lied.md) safe default and [11.6's](../11-deployment/06-lab-the-incident.md) insufficient telemetry: the system is answering precisely, and it is answering the wrong thing.

**Periodicity and multiplicity are the two structural facts about joint space.** Angles wrap; poses have several configurations. Nearly every manipulation-specific bug is one of those two arriving somewhere it was not expected — bug 1 is periodicity, bug 3 is multiplicity, and the branch flip in bug 3 is what happens when you let multiplicity resolve itself independently at every timestep.

And carry the module's measured numbers out as calibration: a null-space
descent at a practical step size drifts the tip **33 mm** until a one-line
task correction zeroes it; a disc one centimetre wider than the gripper's
stroke has **zero** force-closure grasps below μ = 1.0; a 0.6 rad edge check
waves through **22%** of true tunnel edges; and IBVS forgives a 4× depth
error while diverging at 10×. Each is the price tag on an assumption this
lab's bugs quietly violate.

## F. Graded work & portfolio extension

**Graded:** the three fixes are Module 8's diagnostic assessment, and each corresponds to a stage of [Capstone III](../capstone-3/index.md) — interpolation, validity checking, and trajectory continuity.

**Portfolio:** take any trajectory your arm code produces and build a two-panel plot: tool position against time, and all joint angles against time, with the maximum per-step joint delta annotated. Run it on a path that crosses a branch boundary. The top panel is smooth and the bottom has a cliff, and having that figure in your debugging toolkit turns a class of intermittent hardware event into something you can see before you ever run it.
