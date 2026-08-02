# 5.6 Lab: planner pathologies

**Status:** Code verified · **Prereqs:** lessons 5.1–5.5 · **Time:** ~2 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this lab exists

Planners rarely crash. They dither, they freeze, they cut corners, they take the scenic route — and every one of those behaviours looks, from the outside, like "the robot is being weird." This lab gives you the three canonical pathologies with working code, so you learn to name them from the motion rather than from the source.

Both cases here were encountered *for real* while building the capstone ([field notes 5 and 8](../../capstone-log.md)) — which is the strongest argument for the lab existing.

## B. The diagnostic table

| What you see | Pathology | Where it was taught |
|---|---|---|
| Robot advances, retreats, re-advances; never arrives | **Replanning thrash** — successive plans disagree, each locally rational | [5.1](01-astar.md) |
| Robot stops short of a gap, creeps, sometimes never enters | **Freezing** — clearance dominates progress in the local scorer | [5.4](04-local-planning.md) |
| Path is legal in cell-space; robot scrapes walls | **Missing inflation** — planned for a point, drove a body | [1.5](../01-geometry/05-configuration-space.md), [5.2](02-costmaps.md) |
| Robot clips inside corners on turns | **Corner cutting** — long lookahead, or diagonal moves through blocked pairs | [2.4](../02-control/04-trajectory-tracking.md), [5.1](01-astar.md) |
| Paths hug walls exactly at the inflation boundary | **Binary costmap** — no decay skirt, so clearance is free | [5.2](02-costmaps.md) |
| Planner reports failure in a passable corridor | **Over-inflation** — margins composed across layers exceed the gap | [5.2](02-costmaps.md), capstone field note 6 |

## C. The gallery

### Case 1: the robot that changes its mind

A robot exploring toward a goal replans on a timer. Each plan is optimal for what it knows; together they oscillate, and it never arrives. Diagnose from the trajectory, then fix it without making the planner blind to genuine blockages.

<code-exercise src="plan-l6-thrash"></code-exercise>

### Case 2: the robot that won't go through the door

A DWA local planner refuses a gap it fits through comfortably. The parameters look sensible in isolation. Find the one that isn't, and fix it without turning off collision safety.

<code-exercise src="plan-l6-freezing"></code-exercise>

## D. Diagnosis drills

<quiz-bank src="planning-l6-drills"></quiz-bank>

## E. Debrief

The two pathologies here are opposite failures of the same balance:

- **Thrash** is too little commitment — the planner treats every cycle as a fresh decision, so noise and newly-mapped geometry keep flipping the answer.
- **Freezing** is too much caution — the local scorer's safety terms outvote progress, and standing still becomes the optimum.

Both are *tuning* pathologies with no exception and no error log, which is exactly why they're worth practising. And both have the same diagnostic entry point: **plot the decision, not just the trajectory.** Log the chosen plan's identity each cycle (thrash shows as an alternating sequence) or the scores of the top candidate arcs (freezing shows as the zero-velocity arc winning). A planner that can explain its choice is one you can debug; one that only emits `cmd_vel` is not.

The third lesson is architectural, from [lesson 0.2](../00-transition/02-anatomy.md): pathologies live at the *boundary* between planning layers. Thrash is the global planner running too eagerly; freezing is the local planner refusing what the global planner promised. When behaviour is strange, ask which layer owns the decision before tuning either one.

## F. Graded work & portfolio extension

**Graded:** the capstone rubric catches both pathologies quantitatively — thrash inflates path ratio and blows the time limit; freezing shows as goal-failure with zero collisions. That signature pair (no collisions, no arrival) is worth memorizing.

**Portfolio:** instrument your capstone stack to log the chosen local-planner arc and its score components each cycle, then produce a plot of a near-freeze in a doorway. Being able to *show* the decision surface at the moment a robot hesitates is a genuinely rare debugging artifact.
