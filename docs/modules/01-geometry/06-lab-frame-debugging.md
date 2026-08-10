# 1.6 Lab: the frame-debugging gauntlet

**Status:** Code verified · **Prereqs:** lessons 1.1–1.5 · **Time:** ~2 h · **Verified:** 2026-08-01, Python 3.13, NumPy ≥ 1.26

---

## A. Why this lab exists

Module 1 taught you the machinery, and this lab teaches you the symptoms,
which turn out to be a substantially different skill.

Frame bugs are almost never found by reading code, and the reason is that the
code looks correct, which is the defining property of this class of bug rather
than an unlucky accident. Every line is individually defensible, every unit
test passes, the matrices are all valid rotations that compose cleanly and
invert exactly, and the robot still drives into a wall. What actually finds
these bugs is recognising the failure signature: a map that rotates with the
robot, a controller that spins the long way round, a sensor whose world is
mirror-imaged.

Each exercise below therefore hands you working-looking code containing one
classic bug, together with a probe showing what the running system is
producing, and your job is the real engineering sequence of reproduce,
localise, name and fix.

!!! tip "Form the hypothesis before you read the code"

    Read the probe output first, say out loud what you think is wrong and
    why, and only then open the code. This is not a study technique but the
    actual method, because the sequence of symptom, then candidate cause, then
    discriminating test is what separates debugging from flailing, and it is
    what Module 11's incident-forensics work builds on.

    Reading the code first will get you to the answer eventually, but it will
    not build the pattern-matching that makes the next occurrence take ninety
    seconds instead of a morning.

## B. The diagnostic table

This is the lab's cheat sheet and the closest thing robotics has to a stack
trace for geometry, so it is worth committing to memory.

| Symptom | Prime suspect | Why that symptom follows |
|---|---|---|
| Map or obstacles **rotate around the robot** as it drives | Inverted transform convention, `T_B_A` used as `T_A_B` | The inverse rotation is applied, so the world counter-rotates as the heading changes |
| The world appears **mirrored** | Handedness flip: a sign error giving \(\det(R) = -1\), or building \(R(-\theta)\) | A reflection is still orthonormal, so every self-consistency check passes |
| The robot occasionally **spins the long way** to a heading | Unwrapped angle subtraction crossing \(\pm\pi\) | A 2° error is reported as 358° and the controller faithfully obeys it |
| Obstacles **smeared along the direction of travel** | Timestamp mismatch between sensor and pose | Each scan point is placed using a pose from the wrong instant |
| Sensor data offset by a **constant pose** | Composition order swapped, or wrong mount extrinsics | A fixed error is composed into every lookup |
| Everything drifts **slowly and smoothly** | **Not a frame bug** — this is odometry noise | Frame bugs are structural and immediate, whereas noise accumulates gradually |

The last row earns its place because a large part of debugging is knowing when
to stop looking somewhere, and smooth drift is the signature that sends you to
Module 3 rather than back into the transform code.

## C. The gauntlet

### Bug 1: the rotating map

This is the classic, and the one you are most likely to meet in real life.
Watch what happens to the landmark's estimated position as the robot's heading
changes.

<code-exercise src="geo-l6-bug-inverted"></code-exercise>

The tell is that the error is zero at one particular heading and grows with
angular distance from it. A constant offset would indicate a mount error,
whereas an error proportional to heading indicates a rotation applied in the
wrong direction, and distinguishing those two shapes of error is most of the
diagnosis.

### Bug 2: the long way around

<code-exercise src="geo-l6-bug-unwrapped"></code-exercise>

This one is intermittent, which is what makes it unpleasant, because the
controller behaves perfectly for most targets and pathologically for a few.
Ask what is special about the ones that fail, and the answer is that the
heading error crosses \(\pm\pi\) while nothing else about them is unusual.

Notice also the shape of the evidence: the robot reaches the correct heading
having travelled an absurd distance to get there, and two numbers disagreeing
about whether a run succeeded is itself a diagnostic signal.

### Bug 3: the misplaced sensor

<code-exercise src="geo-l6-bug-order"></code-exercise>

This is composition order. Both `A @ B` and `B @ A` are valid transforms that
compose cleanly, and only one of them describes a sensor mounted on the robot
rather than a robot mounted on the sensor. The subscript-cancellation rule
from lesson 1.1 catches this before you run anything, which is the entire
point of having the rule.

## D. Diagnosis drills

Symptom-matching under time pressure, with no code and only the signature as
it would arrive in a bug report.

<quiz-bank src="geometry-l6-drills"></quiz-bank>

## E. Debrief: the method

Every bug above yields to the same four-step procedure, which generalises well
beyond geometry.

**Trust the symptom rather than the code.** The code always looks right,
because you wrote it or somebody competent did and it passes its tests, so the
symptom is the only thing in the room that is not lying to you.

**Test one transform at a time against a physically known configuration.** Put
the robot at the origin facing \(+x\), with a landmark dead ahead at a known
distance, and every intermediate quantity then has a value you can state
without computing it. Constructing that situation takes two minutes and beats
any amount of staring at matrices.

**Check the invariants**, which are cheap and catch roughly half of all frame
bugs at construction time:

```python
assert np.allclose(T @ se2_inverse(T), np.eye(3))      # round trip
assert np.isclose(np.linalg.det(T[:2, :2]), 1.0)       # rotation, not reflection
assert np.allclose(np.linalg.norm(p_a - q_a),
                   np.linalg.norm(p_b - q_b))          # distances preserved
```

This is precisely why `robotics_ai.geometry` is built from functions with
these properties tested. The second assertion deserves particular attention,
because it is the one that catches bug 1's mirrored cousin and it is also the
one nobody writes.

**Bisect the chain.** A wrong `T_map_lidar` is one of exactly three things: a
wrong `T_map_base`, a wrong `T_base_lidar`, or a wrong composition. Verifying
the middle one first halves the search space in a single test, which is binary
search applied to a transform chain, and on a real robot with a ten-frame
chain it is the difference between four tests and ten.

### The meta-lesson

Every bug in this lab produces valid output, in the sense that the rotations
are genuine rotations, the units cancel and the round-trips pass, which is the
recurring lesson of Module 1 stated as compactly as it can be: **self-
consistency is not correctness.**

A mirrored world is perfectly self-consistent, and so is a map rotated by 90°,
and so is a robot that has confused its sensor with its base. The only thing
that catches any of them is comparison against a physically known
configuration, which is why the second step above is the one to reach for
first when you are genuinely stuck.

## F. Graded work and portfolio extension

**Graded:** this lab together with the [mini-project](project-frames.md)
completes Module 1's assessment.

**Portfolio:** the frame-debugging visualiser from lesson 1.1's extension, now
with a bug-injection menu covering this lab's three bugs. It works as a
teaching tool and as a demonstration that you can reproduce failure signatures
on demand, which is exactly what a perception-team interviewer wants to hear
about, because reliably reproducing a bug is most of the work of fixing one.

## G. Annotated references

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| [TF2 debugging tools](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Debugging-Tf2-Problems.html) | docs | intermediate | `tf2_echo`, `view_frames` and the standard diagnosis workflow on a running system |
| Zeller, *Why Programs Fail*, ch. 1–3 | book | introductory | The general method behind section E argued properly, covering reproduce, isolate and bisect |
