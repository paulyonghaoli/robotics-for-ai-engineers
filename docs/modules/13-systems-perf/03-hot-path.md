# 13.3 The hot path: what C++ buys, and what it does not

**Status:** Code verified · **Prereqs:** lessons 13.1, 13.2 · **Time:** ~2 h · **Verified:** 2026-08-03, Python 3.13

---

## A. Why this matters

Production robotics is overwhelmingly C++, and for an engineer arriving from ML that fact usually gets converted into the wrong plan: learn the language, rewrite the loop, get a speedup.

The rewrite in the exercise below is worth **1.99×**. Two of its five stages get 28× and 58× faster and the loop as a whole roughly doubles, because half the frame was already inside compiled code and no amount of C++ moves it. Meanwhile the two obvious ways to pick what to port — the biggest stage, and the stage with the best speedup — both select something worth less than 0.4% of the frame.

So this lesson is two things at once: the arithmetic that says *whether* to port, and the small subset of C++ that matters *when you do*. The subset is smaller than a language course and the arithmetic is what makes it worth learning.

## B. What a port actually changes

Only three things, and it is worth being able to name them.

1. **Per-call interpreter dispatch** disappears. A Python-level call plus NumPy argument handling is on the order of a microsecond; the same call inlined in C++ is tens of nanoseconds. Irrelevant once, decisive at 240 calls a frame.
2. **Per-element interpreter overhead** disappears. A Python loop body costs ~75 ns per iteration against ~1.5 ns compiled. This is where a 28× lives.
3. **Control over allocation and layout** becomes possible. That is [13.2](02-real-time.md)'s subject, and it is a *variance* win rather than a speed one.

And what does not change: **time already inside a vectorized kernel.** `cv2.undistort`, a BLAS solve, a NumPy reduction over a large array — these are compiled C already, running the same instructions either way. In the exercise, `undistort` is 31% of the frame and porting it is worth 1.0002×.

| stage | Python | ported | speedup | saves | % of frame |
|---|---:|---:|---:|---:|---:|
| cluster | 3.064 ms | 0.110 ms | **27.8×** | **2.954 ms** | 46.8% |
| undistort | 2.001 ms | 2.000 ms | 1.00× | 0.001 ms | 30.6% |
| solve | 1.151 ms | 1.150 ms | 1.00× | 0.001 ms | 17.6% |
| associate | 0.308 ms | 0.025 ms | 12.4× | 0.283 ms | 4.7% |
| control | 0.017 ms | 0.000 ms | **58.0×** | 0.017 ms | 0.3% |

Read the last two columns against each other. **`control` is the fastest port in the table and saves 0.017 ms; `undistort` is the second-largest stage and saves 0.001 ms.** The only ranking that survives contact with a frame budget is absolute milliseconds removed, and by that measure one stage of five is 91% of everything a full rewrite could ever win.

**And then Amdahl sets the ceiling.** 3.15 ms of the 6.54 ms frame is vectorized work that cannot move, so the fully-ported loop is 3.29 ms and the answer to "what if we rewrote all of it in C++" is 1.99×. If the requirement had been 3 ms, no amount of C++ reaches it and the next move is a different algorithm or fewer pixels — which is worth knowing before committing a quarter, rather than after.

## C. The subset that matters

If you do port, this is the part of the language a control loop actually exercises. It is a short list, and none of it is language trivia.

- **RAII and deterministic destruction.** A resource is owned by an object; the destructor runs at a known point. No finalizer, no GC, no `close()` you forgot. This is the feature that makes the rest tractable.
- **Values, references, and who owns what.** `const T&` to borrow, `T` to copy, `std::unique_ptr<T>` to own, `T*` for a non-owning observer that may be null. In Python every name is a borrowed reference and you never had to decide; here it is the central design question of every signature.
- **`const` correctness**, which is documentation the compiler enforces. A function taking `const std::vector<Point>&` cannot quietly modify your buffer.
- **Fixed-capacity containers**: `std::array`, a preallocated `std::vector` with `reserve()`, or a ring buffer. The hot path touches no allocator, which is [13.2](02-real-time.md)'s row B.
- **No allocation, no locks, no I/O, no exceptions in the hot path.** Each of these has an unbounded worst case. The rule is about the maximum, not the mean.
- **Memory layout.** Struct-of-arrays instead of array-of-structs when you sweep one field over many objects. This is often worth more than the language change and is available in NumPy too.

Explicitly *not* on the list for this purpose: template metaprogramming, inheritance hierarchies, the algorithm library's more exotic corners, move-semantics subtleties beyond "know why `std::move` exists". They are real C++ and they are not what a 100 Hz loop needs from you.

## D. From ML to robotics

- **You have already written the fast path**, in NumPy — vectorizing is the same instinct as avoiding per-element interpreter overhead, and it is why so much Python robotics code is fast enough.
- **The new idea is ownership.** Not speed, not syntax: deciding, for every object, who is responsible for its lifetime. It is the thing the language forces you to make explicit and the thing garbage collection let you ignore.
- **The second new idea is that variance is a design target.** An ML engineer optimizes a mean because a mean is what training cost is. A control loop is scored on its maximum, and the techniques differ.
- **The honest reason to learn it** is not usually speed. It is that ROS 2 nodes, driver code, and every real-time component in a production stack are written in it, and being unable to read them is a hard limit on what you can debug.

## E. Practice

<code-exercise src="sys-l3-hotpath"></code-exercise>

## F. In production

- **Profile before porting, and profile the stage rather than the loop.** The exercise's table is what a profiler gives you; the mistake is reading the first column instead of the fourth.
- **Port at a seam.** A stage with a clean array-in, array-out interface can be ported and validated in isolation. One that shares mutable state with the rest of the loop cannot.
- **pybind11 or nanobind before a full rewrite.** Porting one function and calling it from Python keeps the harness, the tests and the plotting, and it is how most real ports actually happen.
- **Check the cheaper options first.** Numba, Cython, or simply vectorizing the loop often capture most of a port's gain for a fraction of the cost. `cluster` is a Python loop over point pairs; a vectorized formulation might get much of the 28× with no new language.
- **Build with sanitizers on in CI** (`-fsanitize=address,undefined`). The class of bug you just took on is the class Python was protecting you from.

## G. Experiment

Take the profile of your own capstone loop and build this table for it: per stage, wall time, estimated ported time, absolute saving. Then answer two questions in writing — what is the ceiling if you port everything, and what is the smallest set of stages that meets your budget. Most of the value of the exercise is discovering that the answer to the second is one or two stages, which is a weekend rather than a quarter.

## H. Failure modes

- **Porting the biggest stage.** It is usually the one already inside a library.
- **Ranking candidates by speedup ratio.** A ratio has no denominator in a frame budget.
- **Rewriting the loop wholesale** when two functions were 91% of the win, and taking on the memory-safety surface of the other three for nothing.
- **Ignoring the ceiling.** If the fully-ported floor is above your requirement, the port is not the project.
- **Porting for speed and then allocating in the hot path**, which throws away the variance win that was the better half of the argument.
- **Losing the test harness.** A ported stage with no parity check against the Python reference is a rewrite you cannot trust — which is the subject of the next lesson.

## I. Questions

<quiz-bank src="sys-l3-quiz"></quiz-bank>

## J. References

- Amdahl (1967) — the one-page argument that sets every ceiling in this lesson.
- The C++ Core Guidelines, particularly the resource-management and `const` sections — the subset above, written by people who argue about it professionally.
- pybind11 and nanobind documentation — the practical route from a Python loop to one ported stage.
- ROS 2's `rclcpp` real-time notes, on allocators and executors — where these constraints meet middleware you would actually ship.

## K. Graded work & portfolio extension

**Graded:** the exercise above.

**Portfolio:** port one stage of your capstone to C++ behind a pybind11 binding, keeping the Python reference in the repository. Publish the profile before and after, and the ceiling calculation that justified choosing that stage. A port with a written justification for its scope reads very differently from a rewrite.
