# 1.6 Lab: the frame-debugging gauntlet

**Status:** Code verified · **Prereqs:** lessons 1.1–1.5 · **Time:** ~2 h · **Verified:** 2026-08-01, Python 3.13, NumPy ≥ 1.26

---

## A. Why this lab exists

Module 1 taught you the machinery; this lab teaches you the *symptoms*. Frame bugs are rarely found by reading code — they're found by recognizing the failure signature: a map that rotates with the robot, a controller that spins the long way, a sensor that's mirror-imaged. Each exercise below hands you **working-looking code containing one classic bug**. Your job is the real engineering skill: reproduce, localize, name, fix.

Before touching code, form a hypothesis from the symptom. That habit — symptom → candidate cause → discriminating test — is what separates debugging from flailing, and it's what Module 10's incident-forensics work builds on.

## B. The diagnostic table

Commit this to memory; it's the lab's cheat sheet and the closest thing robotics has to a stack trace for geometry:

| Symptom | Prime suspect |
|---|---|
| Map/obstacles **rotate around the robot** as it drives | Inverted transform convention (`T_B_A` used as `T_A_B`) |
| World appears **mirrored** | Handedness flip — a sign error making det(R) = −1 |
| Robot occasionally **spins the long way** to a heading | Unwrapped angle subtraction crossing ±π |
| Obstacles **smeared along direction of travel** | Timestamp mismatch between sensor and pose |
| Sensor data offset by a **constant pose** | Composition order swapped, or wrong mount extrinsics |
| Everything drifts **slowly and smoothly** | Not a frame bug — that's odometry noise (Module 3's job) |

## C. The gauntlet

### Bug 1: the rotating map

<code-exercise src="geo-l6-bug-inverted"></code-exercise>

### Bug 2: the long way around

<code-exercise src="geo-l6-bug-unwrapped"></code-exercise>

### Bug 3: the misplaced sensor

<code-exercise src="geo-l6-bug-order"></code-exercise>

## D. Diagnosis drills

Symptom-matching under time pressure — no code, just the signature:

<quiz-bank src="geometry-l6-drills"></quiz-bank>

## E. Debrief: the method

Every bug above yields to the same procedure:

1. **Trust the symptom, not the code.** The code always looks right — you wrote it.
2. **Test one transform at a time** against a physically known configuration (robot at origin facing +x; a landmark dead ahead). Machine-checkable ground truth beats staring.
3. **Check the invariants:** `T @ inverse(T) == I`, `det(R) == +1`, distances preserved, subscripts cancel. Cheap assertions catch half of all frame bugs at construction time — which is why `robotics_ai.geometry` is built from functions with exactly these properties tested.
4. **Bisect the chain.** A wrong `T_map_lidar` is one of: wrong `T_map_base`, wrong `T_base_lidar`, or wrong composition. Verify the middle.

## F. Graded work & portfolio extension

**Graded:** this lab plus the [mini-project](project-frames.md) complete Module 1's assessment. The Module 1 exam bank (course-level) lands with the Course I beta.

**Portfolio:** the frame-debugging visualizer from lesson 1.1's extension, now with a "bug injection" menu covering this lab's three bugs — a teaching tool *and* a demonstration that you can reproduce failure signatures on demand, which is exactly what a perception-team interviewer wants to hear about.
