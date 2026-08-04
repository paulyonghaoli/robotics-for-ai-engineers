# NotebookLM video-overview experiment

Testing whether an AI-generated video overview makes the harder lessons land
faster than the written page does. Not curriculum content — nothing here is
built, linked or CI-gated, and the site does not include it.

## What's here

- `04-pose-graphs-source.md` — a source document for [lesson 4.4](../../docs/modules/04-mapping/04-pose-graphs.md).

## Why 4.4 was chosen first

It is the hardest conceptual jump in Course II and the best-suited to video:

- The core idea is **counterintuitive in a way a single number settles** —
  odometry says 3.0, the loop closure says 2.4, and the answer is 2.55.
- It is **intensely visual**. Springs relaxing, a doubled map snapping into
  single walls, a trajectory floating freely until one node is pinned.
- The written lesson is dense with notation (information matrices, the
  \(\ominus\) operator, gauge freedom) — exactly the material that is quick
  to say aloud and slow to read.

If video helps anywhere, it should help here. If it doesn't help here, it
probably won't help on 13.1 or 12.2 either.

## How the source differs from the lesson

Deliberately, in four ways:

1. **Self-contained.** No "recall from 4.2" — anything needed is restated.
2. **Prose, not reference.** The lesson is written to be scanned and returned
   to; this is written to be read aloud once.
3. **Arithmetic instead of notation.** The least-squares objective is worked
   through as a four-node number line rather than stated as a formula.
4. **Visual beats named explicitly**, with a shot list at the end, since the
   model has to decide what to show as well as what to say.

## Every number in it is measured

| claim | source |
|---|---|
| 0, 0.85, 1.70, 2.55 and the 100× variant | solved directly; reproduce with the snippet below |
| octagon 1.103 m → 0.000 m, worst node 0.017 m | `tests/mapping/test_posegraph.py` |
| zero revisit pairs across six seeds | capstone-log note 14 |
| 39% error reduction on a tour where loops exist | `slam_ablation.py lc+bias+tour` |

```python
import numpy as np
A = np.array([[1,0,0],[-1,1,0],[0,-1,1],[0,0,1]], float)
b = np.array([1.0, 1.0, 1.0, 2.4])
for w_loop in (1.0, 100.0):
    W = np.diag([1.0, 1.0, 1.0, w_loop])
    print(w_loop, np.linalg.solve(A.T @ W @ A, A.T @ W @ b))
```

## Suggested NotebookLM customisation prompt

> Audience: software and machine-learning engineers who are strong at
> optimisation and statistics but have never worked with robots. Assume they
> know what least squares, a loss function, weighted loss and outlier-robust
> losses are; assume they know nothing about odometry, SLAM or coordinate
> frames.
>
> Build the whole explanation around one question: odometry says the robot is
> at 3.0, the loop closure says 2.4, and the correct answer is 2.55 — why?
> Walk the four-node example through slowly and show every node moving, not
> just the last one.
>
> Spend real time on two things: that the correction is spread backwards over
> the entire trajectory rather than applied at the point of recognition, and
> that a confidently wrong loop closure destroys the whole map.
>
> Do not skip the last section. The finding that loop closure did nothing on a
> single-traverse task, because the robot never revisits anywhere, is the most
> useful part and should land as the closing point rather than a footnote.
>
> Tone: direct and concrete. No hype. Do not call anything brilliant,
> stunning, mind-bending, magic or fascinating — state the number and let it
> land. End on the trajectory finding itself; do not add a rhetorical
> closing question about the future of AI.
>
> Two things to get exactly right, because a previous generation got both
> wrong: what measured zero was the number of *revisit opportunities*, not
> the number of loop closures the software attempted; and the there-and-back
> tour result (39% error reduction where a loop exists) must be included,
> because without it the video ends on "the technique does nothing", which is
> the opposite of the finding.

## If it works

The obvious next candidates, in order:

1. **13.1 The performance model** — the accelerator is 3% of the frame and
   doubling its FLOPs changes throughput by exactly zero.
2. **12.2 Replay determinism** — a difference of 1e-12 reaching lane scale in
   519 steps.
3. **3.6 Catching a lying filter** — consistency checking is abstract on the
   page and obvious once animated.

Judge it on one thing: whether someone who has watched the video can then do
the lesson's exercise. Enjoying the video is not the same as being able to
implement the thing, and the exercises already measure the difference.
