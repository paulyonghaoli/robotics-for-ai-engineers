"""MkDocs build hook: convert curriculum YAML -> docs/assets/generated JSON.

Registered via `hooks:` in mkdocs.yml. Fails the build on invalid content so
broken quizzes/exercises can never ship.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.content_lib import export_json, load_all  # noqa: E402


def _write_lesson_manifest() -> int:
    """List every study page, for the progress summary's denominator.

    Derived from disk rather than from the nav so it runs in `on_pre_build`,
    before MkDocs has built one. Titles come from the H1 so the summary
    shows the same name the page does.
    """
    import json
    import re

    docs = Path(__file__).resolve().parent.parent / "docs"

    def h1_of(path: Path) -> str | None:
        if not path.exists():
            return None
        m = re.search(r"^#\s+(.+)$", path.read_text(encoding="utf-8"), re.M)
        return m.group(1).strip() if m else None

    # A module's display name comes from its own overview page, so the
    # summary reads "Module 4 · Mapping & SLAM" rather than "04-mapping".
    module_names = {
        d.name: (h1_of(d / "index.md") or d.name)
        for d in sorted((docs / "modules").iterdir()) if d.is_dir()
    }

    out = []
    for md in sorted((docs / "modules").rglob("*.md")):
        text = md.read_text(encoding="utf-8")
        m = re.search(r"^#\s+(.+)$", text, re.M)
        rel = md.relative_to(docs).as_posix()
        # Relative to the site root, not the domain root: progress.js
        # prefixes whatever base it is actually served from.
        url = (rel[:-len("index.md")] if rel.endswith("index.md")
               else rel[:-len(".md")] + "/")
        out.append({
            "url": url,
            "title": (m.group(1).strip() if m else md.stem),
            "module": module_names.get(md.parent.name, md.parent.name),
            "slug": md.parent.name,
        })
    target = docs / "assets" / "generated" / "lessons.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(out, indent=1)
    if not target.exists() or target.read_text(encoding="utf-8") != payload:
        target.write_text(payload, encoding="utf-8")
    return len(out)


def on_pre_build(config, **kwargs):  # noqa: ANN001, ARG001
    cs = load_all()
    if cs.errors:
        details = "\n".join(f"  - {e}" for e in cs.errors)
        raise SystemExit(f"interactive content invalid:\n{details}")
    export_json(cs)
    _write_lesson_manifest()
