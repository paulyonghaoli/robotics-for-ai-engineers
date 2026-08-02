"""Content-integrity check, run in CI and pre-publish.

- Schema-validates every quiz bank and exercise spec.
- Executes every exercise's reference solution against its own tests
  (same exec model as the in-browser Pyodide runner).
- Exports the JSON consumed by the front-end components.

Exit code 0 = everything valid.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.content_lib import export_json, load_all, run_exercise_solution  # noqa: E402


def main() -> int:
    cs = load_all()
    failures = list(cs.errors)

    for ex_id, spec in cs.exercises.items():
        err = run_exercise_solution(spec)
        if err:
            from tools.content_lib import ContentError

            failures.append(ContentError(f"exercise {ex_id}", err))

    n = export_json(cs)
    print(f"quiz banks: {len(cs.quizzes)}  exercises: {len(cs.exercises)}  json rewritten: {n}")

    if failures:
        print(f"\n{len(failures)} content error(s):", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print("content OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
