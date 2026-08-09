# 1.6 Lab: the frame-debugging gauntlet

**Status:** Code verified · **Prereqs:** lessons 1.1–1.5 · **Time:** ~2 h · **Verified:** 2026-08-01, Python 3.13, NumPy ≥ 1.26

---

## A. Why this lab exists

Module 1 taught you the machinery. This lab teaches you the **symptoms**, and
they are a different skill entirely.

Frame bugs are almost never found by reading code. The code looks right —
that is the defining property of a frame bug. Every line is individually
defensible, every unit test passes, the matrices are all valid rotations, and
the robot still drives into a wall. What actually finds these bugs is
recognising the failure *signature*: a map that rotates with the robot, a
controller that spins the long way round, a sensor whose world is
mirror-imaged.

So each exercise here hands you **working-looking code containing one classic
bug**, plus a probe showing what the system is doing. Your job is the real
engineering skill, in order: reproduce, localise, name, fix.

!!! tip "Form the hypothesis before you read the code"

    Read the probe output. Say out loud what you think is wrong and why,
    *then* open the code. This is not a study technique — it is the actual
    method. Symptom → candidate cause → discriminating test is what separates
    debugging from flailing, and it is what Module 11's incident-forensics
    work builds on.

    If you read the code first you will find the bug eventually, but you will
    not build the pattern-matching that makes the next one take ninety
    seconds instead of a morning.

## B. The diagnostic table

This is the lab's cheat sheet, and it is the closest thing robotics has to a
stack trace for geometry. It is worth committing to memory.

| Symptom | Prime suspect | Why that symptom |
|---|---|---|
| Map or obstacles **rotate around the robot** as it drives | Inverted transform convention (`T_B_A` used as `T_A_B`) | The inverse rotation is applied, so the world counter-rotates with heading |
| The world appears **mirrored** | Handedness flip — a sign error giving \(\det(R) = -1\), or \(R(-\theta)\) | A reflection is still orthonormal, so every self-consistency check passes |
| The robot occasionally **spins the long way** to a heading | Unwrapped angle subtraction crossing \(\pm\pi\) | A 2° error reads as 358°, and the controller obeys |
| Obstacles **smeared along the direction of travel** | Timestamp mismatch between sensor and pose | Each scan point is placed using a pose from the wrong instant |
| Sensor data offset by a **constant pose** | Composition order swapped, or wrong mount extrinsics | A fixed error composed into every lookup |
| Everything drifts **slowly and smoothly** | **Not a frame bug** — odometry noise | Frame bugs are structural and immediate; noise is gradual |

That last row earns its place. A large part of debugging is knowing when to
stop looking in a given place, and "smooth drift" is the signature that sends
you to Module 3 rather than back into the transform code.

## C. The gauntlet

### Bug 1: the rotating map

The classic, and the one you will meet in real life most often. Watch what
happens to the landmark's estimated position as the robot's heading changes.

<code-exercise src="geo-l6-bug-inverted"></code-exercise>

The tell is that the error is **zero at one particular heading** and grows
with angular distance from it. A constant offset would be a mount error; an
error proportional to heading is a rotation applied in the wrong direction.

### Bug 2: the long way around

<code-exercise src="geo-l6-bug-unwrapped"></code-exercise>

This one is intermittent, which is what makes it nasty. The controller behaves
perfectly for most targets and pathologically for a few. Ask what is special
about the ones that fail — the answer is that the error crosses \(\pm\pi\),
and nothing else about them is unusual.

Note the shape of the evidence: the robot reaches the right *heading*, having
travelled an absurd *distance* to get there. Two numbers that disagree about
whether the run succeeded is itself a diagnostic.

### Bug 3: the misplaced sensor

<code-exercise src="geo-l6-bug-order"></code-exercise>

Composition order. `A @ B` and `B @ A` are both valid transforms, both compose
cleanly, and only one of them is the sensor mounted on the robot rather than
the robot mounted on the sensor. The subscript-cancellation rule from lesson
1.1 catches this **before** you run anything, which is the point.

## D. Diagnosis drills

Symptom-matching under time pressure. No code — just the signature, the way it
arrives in a bug report.

<quiz-bank src="geometry-l6-drills"></quiz-bank>

## E. Debrief: the method

Every bug above yields to the same four-step procedure, and it generalises far
beyond geometry.

**1. Trust the symptom, not the code.**
The code always looks right. You wrote it, or someone competent did, and it
passes its tests. The symptom is the only thing in the room that is not
lying to you.

**2. Test one transform at a time against a physically known configuration.**
Put the robot at the origin facing \(+x\), with a landmark dead ahead at a
known distance. Now every intermediate quantity has a value you can state
without computing it. Machine-checkable ground truth beats staring at
matrices, and constructing it takes two minutes.

**3. Check the invariants.**
These are cheap, and they catch roughly half of all frame bugs at construction
time:

```python
assert np.allclose(T @ se2_inverse(T), np.eye(3))     # round trip
assert np.isclose(np.linalg.det(T[:2, :2]), 1.0)      # rotation, not reflection
assert np.allclose(np.linalg.norm(p_a - q_a),
                   np.linalg.norm(p_b - q_b))          # distances preserved
```

This is exactly why `robotics_ai.geometry` is built from functions with these
properties tested. Note the second assertion in particular: it is the one that
catches bug 1's mirrored cousin, and it is the one nobody writes.

**4. Bisect the chain.**
A wrong `T_map_lidar` is one of exactly three things: a wrong `T_map_base`, a
wrong `T_base_lidar`, or a wrong composition. Verify the middle one first and
you halve the search space in a single test. This is binary search applied to
a transform chain, and on a real robot with a ten-frame chain it is the
difference between four tests and ten.

### The meta-lesson

Every bug in this lab produces **valid** output. Valid rotations, cancelling
units, passing round-trips. That is the recurring lesson of Module 1:

> Self-consistency is not correctness.

A mirrored world is perfectly self-consistent. So is a map rotated by 90°, and
so is a robot that thinks its sensor is its base. The only thing that catches
these is a comparison against a physically known configuration — which is why
step 2 is the one to do first when you are genuinely stuck.

## F. Graded work and portfolio extension

**Graded:** this lab plus the [mini-project](project-frames.md) complete
Module 1's assessment.

**Portfolio:** the frame-debugging visualiser from lesson 1.1's extension, now
with a **bug-injection menu** covering this lab's three bugs. It is a teaching
tool and a demonstration that you can reproduce failure signatures on demand —
which is exactly what a perception-team interviewer wants to hear about,
because reproducing a bug reliably is most of fixing it.

## G. Annotated references

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| [TF2 debugging tools](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Debugging-Tf2-Problems.html) | docs | intermediate | `tf2_echo`, `view_frames` and the standard diagnosis workflow on a real system |
| Zeller, *Why Programs Fail*, ch. 1–3 | book | introductory | The general method behind section E, argued properly. Reproduce, isolate, bisect |
