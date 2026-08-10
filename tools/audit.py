"""Consistency audit across docs, content and navigation.

`validate_content.py` proves every exercise's *solution* passes its own
tests. That is necessary and not sufficient. This checks the joins nobody
else checks:

  - every <code-exercise>/<quiz-bank> in a lesson resolves to real content
  - every exercise and bank is actually referenced by a lesson
  - every content file's `lesson:` field names a real doc
  - every lesson is reachable from the mkdocs nav
  - a module index that calls a lesson "planned" does not link to it, and
    one that calls it "available" does
  - prereqs exist, and a prereq that comes LATER admits it ("read ahead")
  - every exercise's STARTER fails its own tests

That last one is the important one. An exercise whose starter already
passes is a no-op that looks like work, and nothing else in the toolchain
would ever notice.

    python tools/audit.py [--quick]     # --quick skips the starter runs
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.content_lib import load_all  # noqa: E402

DOCS = ROOT / "docs"
EX_RE = re.compile(r'<code-exercise\s+src="([^"]+)"')
QZ_RE = re.compile(r'<quiz-bank\s+src="([^"]+)"')


def lesson_docs() -> list[Path]:
    """Every page that can host content, not just module lessons — the
    course exams live at the top level and embed banks too."""
    return sorted(p for p in DOCS.rglob("*.md"))


def nav_targets() -> set[str]:
    text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    return set(re.findall(r"([\w\-/]+\.md)", text))


def run_starter(spec: dict) -> str | None:
    """Return None if the starter FAILS its tests (correct), else a message."""
    ns: dict = {}
    try:
        exec(spec["setup_code"], ns)  # noqa: S102
        exec(spec["starter_code"], ns)  # noqa: S102
    except Exception:
        return None  # a starter that cannot even run is a failing starter
    try:
        exec(spec["tests"], ns)  # noqa: S102
    except Exception:
        return None
    return "starter PASSES its own tests — the exercise asks for nothing"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    cs = load_all()
    problems: list[str] = []

    docs = lesson_docs()
    doc_ids = {p.relative_to(DOCS).as_posix()[:-3] for p in docs}
    nav = nav_targets()

    # 1. Every embedded component resolves.
    referenced_ex: set[str] = set()
    referenced_qz: set[str] = set()
    for p in docs:
        text = p.read_text(encoding="utf-8")
        rel = p.relative_to(ROOT).as_posix()
        for eid in EX_RE.findall(text):
            referenced_ex.add(eid)
            if eid not in cs.exercises:
                problems.append(f"{rel}: <code-exercise src={eid!r}> does not exist")
        for qid in QZ_RE.findall(text):
            referenced_qz.add(qid)
            if qid not in cs.quizzes:
                problems.append(f"{rel}: <quiz-bank src={qid!r}> does not exist")

    # 1b. Every local asset a lesson points at actually exists.
    #
    # `mkdocs build --strict` rewrites and validates markdown-syntax paths but
    # passes raw HTML through verbatim, so a broken <img src> in a hand-written
    # <figure> block ships silently as a broken image. That happened.
    asset_re = re.compile(
        r'(?:!\[[^\]]*\]\(([^)\s]+)\)|<img[^>]+src="([^"]+)")')
    for p in docs:
        text = p.read_text(encoding="utf-8")
        rel = p.relative_to(ROOT).as_posix()
        for md_src, html_src in asset_re.findall(text):
            src = md_src or html_src
            if src.startswith(("http://", "https://", "data:", "#", "/")):
                continue
            target = (p.parent / src.split("#")[0].split("?")[0]).resolve()
            if not target.exists():
                problems.append(f"{rel}: asset {src!r} does not exist")

    # 2. Orphans: content nothing links to.
    for eid in sorted(set(cs.exercises) - referenced_ex):
        problems.append(f"exercise {eid}: no lesson embeds it")
    for qid in sorted(set(cs.quizzes) - referenced_qz):
        problems.append(f"quiz bank {qid}: no lesson embeds it")

    # 3. Every content file points at a real lesson.
    for kind, coll in (("exercise", cs.exercises), ("quiz bank", cs.quizzes)):
        for cid, spec in sorted(coll.items()):
            lesson = spec.get("lesson")
            if not lesson:
                problems.append(f"{kind} {cid}: no 'lesson' field")
            elif lesson not in doc_ids:
                problems.append(f"{kind} {cid}: lesson {lesson!r} is not a doc")

    # 4. Every lesson is in the nav.
    for p in docs:
        rel = p.relative_to(DOCS).as_posix()
        if rel not in nav:
            problems.append(f"{rel}: not reachable from the mkdocs nav")

    # 5. Prereqs must exist, and must not silently point forward.
    #    Modules 10 and 11 were written before Module 9 on purpose, so a
    #    forward reference is allowed — it just has to admit it, or a reader
    #    on the numbered path meets a prerequisite they cannot have done.
    numbered: dict[str, tuple[int, int]] = {}
    for p in docs:
        mm = re.match(r"^(\d+)-", p.name)
        if mm and p.parent.name[:2].isdigit():
            numbered[f"{int(p.parent.name[:2])}.{int(mm.group(1))}"] = (
                int(p.parent.name[:2]), int(mm.group(1)))
    for p in docs:
        text = p.read_text(encoding="utf-8")
        m = re.search(r"\*\*Prereqs:\*\*\s*([^\n·]+)", text)
        if not m:
            continue
        line = m.group(1)
        rel = p.relative_to(ROOT).as_posix()
        mm = re.match(r"^(\d+)-", p.name)
        mine = ((int(p.parent.name[:2]), int(mm.group(1)))
                if mm and p.parent.name[:2].isdigit() else None)
        for a, b in re.findall(r"(\d+)\.(\d+)", line):
            key = f"{int(a)}.{int(b)}"
            if key not in numbered:
                problems.append(f"{rel}: prereq {key} does not exist")
            elif mine and (int(a), int(b)) >= mine and "read ahead" not in line:
                problems.append(
                    f"{rel}: prereq {key} comes later and is not marked "
                    f"'(read ahead)'")

    # 6. Module index claims match reality.
    for idx in sorted((DOCS / "modules").glob("*/index.md")):
        text = idx.read_text(encoding="utf-8")
        rel = idx.relative_to(ROOT).as_posix()
        for line in text.splitlines():
            m = re.match(r"\s*\d+\.\s+(.*)", line)
            if not m:
                continue
            body = m.group(1)
            linked = re.search(r"\]\((\d[\w\-.]*\.md)\)", body)
            if "*planned*" in body and linked:
                problems.append(f"{rel}: calls {linked.group(1)} planned and links to it")
            if "**available**" in body and not linked:
                problems.append(f"{rel}: calls a lesson available with no link: {body[:60]}")
            if linked and not (idx.parent / linked.group(1)).exists():
                problems.append(f"{rel}: links to missing {linked.group(1)}")

    # 7. Starters must fail.
    if not args.quick:
        for eid, spec in sorted(cs.exercises.items()):
            msg = run_starter(spec)
            if msg:
                problems.append(f"exercise {eid}: {msg}")

    print(f"docs {len(docs)}  exercises {len(cs.exercises)}  banks {len(cs.quizzes)}")
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("audit OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
