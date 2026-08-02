"""MkDocs build hook: convert curriculum YAML -> docs/assets/generated JSON.

Registered via `hooks:` in mkdocs.yml. Fails the build on invalid content so
broken quizzes/exercises can never ship.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.content_lib import export_json, load_all  # noqa: E402


def on_pre_build(config, **kwargs):  # noqa: ANN001, ARG001
    cs = load_all()
    if cs.errors:
        details = "\n".join(f"  - {e}" for e in cs.errors)
        raise SystemExit(f"interactive content invalid:\n{details}")
    export_json(cs)
