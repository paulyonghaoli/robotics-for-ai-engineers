# Contributing

## Content status system

Every lesson declares one of: **Draft** → **Technically reviewed** → **Code verified** → **Reproducible** → **Production extension available**, plus: tested OS, Python version, ROS distro (if used), expected runtime, and last-verified date. Robotics tutorials decay fast — pin versions, never imply permanent compatibility.

## Lesson schema

Every lesson uses the same sections, in order: **A** Why this matters · **B** Mental model · **C** Mathematical formulation · **D** From ML to robotics · **E** Minimal implementation · **F** Framework implementation · **G** Experiment · **H** Failure modes · **I** Questions (concept / calculation / debugging / system design) · **J** Annotated references · **K** Portfolio extension.

See [docs/modules/01-geometry/01-coordinate-frames.md](docs/modules/01-geometry/01-coordinate-frames.md) for the reference example.

## Code standards

- Python ≥ 3.11, NumPy-first; type hints everywhere; `ruff` and `mypy --strict` clean.
- Every public function in `robotics_ai/` has a docstring stating **conventions** (frames, units, orderings) and a corresponding test.
- Conventions are law: angles wrap to (-π, π]; transforms are `T_parent_child`; quaternions are scalar-first internally.
- Tests must cover boundary behavior (±π, 180° rotations, near-parallel slerp) — that's where robotics code breaks.

## Workflow

```bash
pip install -e ".[dev,docs]"
python tools/verify.py     # runs every gate CI runs, unpiped
```

`tools/verify.py` is the only local check you should trust. It exists because
of a real incident in this repo: gates were being run as
`python tools/validate_content.py | tail -2` inside an `&&` chain — and a
shell pipeline's exit status is the *last* command's, so `tail` returned 0
and masked seven failing exercises across five commits while CI went red.

**Never pipe a gate into `tail`, `head`, or `grep` when its exit status is
what you're relying on.** To iterate on a single exercise, use
`python tools/check_one.py <exercise-id>`.

## Launch state

The published site is in **soft launch**: reachable but excluded from search
engines by `docs/robots.txt` and a `noindex` meta tag. Toggle both together:

```bash
python tools/launch.py --status     # which state am I in?
python tools/launch.py --go         # allow indexing
python tools/launch.py --unlaunch   # restore the guards
```

Repo visibility on GitHub is deliberately *not* scripted — that stays a
manual decision.
