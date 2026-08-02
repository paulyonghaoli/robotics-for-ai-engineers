"""Run a single exercise's reference solution against its tests.

    python tools/check_one.py est-l5-gating [--verbose]

Exists because iterating on one exercise through the full validator is slow,
and because a failing exercise's *printed output* is usually the fastest
route to understanding why.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.content_lib import load_all, run_exercise_solution  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    target = sys.argv[1]
    cs = load_all()
    if target not in cs.exercises:
        print(f"no such exercise: {target}")
        print("available:", ", ".join(sorted(cs.exercises)))
        return 2
    err = run_exercise_solution(cs.exercises[target])
    if err:
        print(f"FAIL {target}\n  {err}")
        return 1
    print(f"ok   {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
