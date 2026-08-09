"""Shared loader/validator for interactive content (quiz banks, code exercises).

Authoring format: YAML under curriculum/<module>/questions/*.yaml and
curriculum/<module>/exercises/*.yaml. At mkdocs build time these are converted
to JSON under docs/assets/generated/ for the front-end components; in CI every
exercise's reference solution is executed against its own tests.
"""

from __future__ import annotations

import ast
import inspect
import json
import types
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CURRICULUM = REPO_ROOT / "curriculum"
GENERATED = REPO_ROOT / "docs" / "assets" / "generated"

QUESTION_TYPES = {"single", "multi", "numeric"}


@dataclass
class ContentError:
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


@dataclass
class ContentSet:
    quizzes: dict[str, dict] = field(default_factory=dict)   # id -> bank
    exercises: dict[str, dict] = field(default_factory=dict)  # id -> spec
    errors: list[ContentError] = field(default_factory=list)


def _validate_quiz(bank: dict, path: str, errors: list[ContentError]) -> None:
    if not bank.get("id"):
        errors.append(ContentError(path, "quiz bank missing 'id'"))
        return
    questions = bank.get("questions")
    if not isinstance(questions, list) or not questions:
        errors.append(ContentError(path, "quiz bank needs a non-empty 'questions' list"))
        return
    seen: set[str] = set()
    for q in questions:
        qid = q.get("id", "?")
        loc = f"{path}#{qid}"
        if qid in seen:
            errors.append(ContentError(loc, "duplicate question id"))
        seen.add(qid)
        qtype = q.get("type", "single")
        if qtype not in QUESTION_TYPES:
            errors.append(ContentError(loc, f"unknown type {qtype!r}"))
        if not q.get("prompt"):
            errors.append(ContentError(loc, "missing prompt"))
        if qtype == "numeric":
            if not isinstance(q.get("answer"), (int, float)):
                errors.append(ContentError(loc, "numeric question needs a numeric 'answer'"))
        else:
            opts = q.get("options")
            if not isinstance(opts, list) or len(opts) < 2:
                errors.append(ContentError(loc, "needs >= 2 options"))
                continue
            n_correct = sum(1 for o in opts if o.get("correct"))
            if qtype == "single" and n_correct != 1:
                msg = f"single-choice needs exactly 1 correct, has {n_correct}"
                errors.append(ContentError(loc, msg))
            if qtype == "multi" and n_correct < 1:
                errors.append(ContentError(loc, "multi-choice needs >= 1 correct option"))
            for i, o in enumerate(opts):
                if not o.get("text"):
                    errors.append(ContentError(loc, f"option {i} missing text"))


def _validate_exercise(spec: dict, path: str, errors: list[ContentError]) -> None:
    for key in ("id", "title", "starter_code", "tests", "solution"):
        if not spec.get(key):
            errors.append(ContentError(path, f"exercise missing '{key}'"))


def _exec(src: str, ns: dict) -> None:
    """Run exercise code the way the browser does.

    `exec` inherits __future__ flags from the calling frame, and this module
    uses `from __future__ import annotations`. Left alone, that silently runs
    every exercise under a different language mode than Pyodide uses — most
    visibly turning annotations into strings. dont_inherit=True removes the
    difference.
    """
    exec(compile(src or "", "<exercise>", "exec", dont_inherit=True), ns)  # noqa: S102


def run_exercise_solution(spec: dict) -> str | None:
    """Execute setup + reference solution + tests. Returns error text or None.

    This is the guarantee that in-browser exercises can't silently rot: the
    same namespace-exec model the Pyodide worker uses, run in local CPython.
    """
    ns: dict = {}
    try:
        _exec(spec.get("setup_code", ""), ns)
        _exec(spec["solution"], ns)
        _exec(spec["tests"], ns)
    except AssertionError as e:
        return f"reference solution FAILS its own tests: {e}"
    except Exception as e:  # noqa: BLE001
        return f"error running solution: {type(e).__name__}: {e}"
    return None


def _summarize_value(v: object, compact: bool = False) -> str:
    """One-line description of a value the learner is handed.

    `compact` is for computed example output, where seventeen significant
    digits are noise. Declared constants keep their exact repr — a lane width
    of `1.0` should not print as `1`.
    """
    if isinstance(v, bool | int | str | type(None)):
        return repr(v)
    if isinstance(v, float):
        if not compact:
            return repr(v)
        # Keep it a float on the page: a pixel width of 54.0 shown as "54"
        # reads as an integer count.
        s = f"{v:.6g}"
        return s if any(c in s for c in ".en") else s + ".0"
    if np.isscalar(v) and hasattr(v, "item"):   # np.float64(…) is noise
        return f"{float(v):.6g}"
    shape = getattr(v, "shape", None)
    if shape is not None:                       # numpy array
        head = ""
        try:
            if v.size <= 6:  # type: ignore[attr-defined]
                # suppress_small, or a rounding residue prints as -1.959e-16
                # and reads like a real measurement.
                head = " = " + np.array2string(  # type: ignore[arg-type]
                    v, precision=3, separator=", ", suppress_small=True)
        except Exception:  # noqa: BLE001, S110
            pass
        return f"ndarray shape={tuple(shape)} dtype={getattr(v, 'dtype', '?')}{head}"
    if isinstance(v, list | tuple) and len(v) <= 6 and all(
            isinstance(x, bool | int | float) for x in v):
        # A short tuple of numbers is a value, not a container: "tuple of 3"
        # hides exactly the thing the learner needs (e.g. a sensor mount pose).
        inner = ", ".join(_summarize_value(x, compact=True) for x in v)
        return f"({inner})" if isinstance(v, tuple) else f"[{inner}]"
    if isinstance(v, slice):
        # Bare "slice" hides the bounds, which are the whole content.
        stop = "" if v.stop is None else str(v.stop)
        step = "" if v.step is None else f", {v.step}"
        return f"slice({'' if v.start is None else v.start}, {stop}{step})"
    if isinstance(v, list | tuple | set | dict):
        return f"{type(v).__name__} of {len(v)}"
    return type(v).__name__


def _type_name(t: object) -> str:
    """Short, readable name for an annotation.

    inspect's default repr gives `numpy.random._generator.Generator`, which
    puts a private module path in front of a learner.
    """
    if t is inspect.Parameter.empty:
        return ""
    return getattr(t, "__name__", str(t)).replace("numpy.", "np.")


def _render_signature(name: str, value: object) -> str:
    try:
        sig = inspect.signature(value)
    except (TypeError, ValueError):
        return f"{name}(...)"
    parts = []
    for p in sig.parameters.values():
        s = p.name
        ann = _type_name(p.annotation)
        if ann:
            s += f": {ann}"
        if p.default is not inspect.Parameter.empty:
            s += f" = {p.default!r}" if ann else f"={p.default!r}"
        parts.append(s)
    out = f"{name}({', '.join(parts)})"
    ret = _type_name(sig.return_annotation)
    return f"{out} -> {ret}" if ret else out


def _used_names(spec: dict) -> set[str]:
    """Names the learner's starter and the reference solution actually read."""
    used: set[str] = set()
    for src in (spec.get("starter_code", ""), spec.get("solution", "")):
        try:
            tree = ast.parse(src or "")
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used.add(node.id)
    return used


def build_provided(spec: dict, errors: list[str] | None = None) -> list[dict]:
    """Describe the hidden objects `setup_code` hands the learner.

    The learner never sees `setup_code`, so a bare `# Provided: a, b, c`
    comment leaves them guessing at signatures — which argument is the step
    index, whether an rng is consumed, what units come back. Everything that
    can be derived is derived here (exact signature, constant values) so it
    can never drift from the code; the author adds only what introspection
    cannot know, via an optional `provided:` block in the YAML:

        provided:
          plant:
            summary: Advance one timestep and return the new lateral offset.
            notes:
              - "`k` is the step index; a gust hits at k == 40."
              - Consumes one draw from `rng`.
            example: plant(0.6, -0.72, 0, np.random.default_rng(0))

    `example` is executed at build time and its real output is baked in, so a
    worked call cannot go stale either. Set `hide: true` to withhold an object
    whose docstring would give away a diagnosis.
    """
    setup = spec.get("setup_code", "")
    if not (setup or "").strip():
        return []
    ns: dict = {}
    try:
        _exec(setup, ns)
    except Exception as e:  # noqa: BLE001
        if errors is not None:
            errors.append(f"setup_code failed: {type(e).__name__}: {e}")
        return []

    authored = spec.get("provided") or {}
    if not isinstance(authored, dict):
        if errors is not None:
            errors.append("'provided' must be a mapping of name -> {summary, notes, example}")
        authored = {}
    for name in authored:
        if name not in ns and errors is not None:
            errors.append(f"'provided' documents {name!r}, which setup_code never defines")

    used = _used_names(spec)
    out: list[dict] = []
    for name, value in ns.items():          # insertion order == definition order
        if name.startswith("__") or isinstance(value, types.ModuleType):
            continue
        extra = authored.get(name) or {}
        # Author-documented names are always shown; otherwise only what the
        # learner's own code touches, so the panel stays a reference and not
        # a dump of the exercise's internals.
        if name not in used and name not in authored:
            continue
        if extra.get("hide"):
            continue
        entry: dict = {"name": name}
        if callable(value):
            entry["kind"] = "class" if isinstance(value, type) else "function"
            entry["signature"] = _render_signature(name, value)
        else:
            entry["kind"] = "constant"
            entry["value"] = _summarize_value(value)
        # An authored summary wins over the docstring, which is written for
        # someone reading the source and may name the bug outright. Constants
        # get no docstring fallback at all: inspect.getdoc(1.0) returns
        # float's own docstring, which is nonsense in this context.
        summary = extra.get("summary") or ""
        if not summary and entry["kind"] != "constant":
            summary = inspect.getdoc(value) or ""
        if summary:
            entry["summary"] = " ".join(summary.split())
        if extra.get("notes"):
            entry["notes"] = list(extra["notes"])
        # A signature gives parameter NAMES. It does not say that `k` is an
        # integer step index or that the return is metres, and the learner
        # cannot open the source to find out. Types come from annotations
        # where the author added them; meaning and units are authored here.
        if extra.get("params") or extra.get("returns"):
            ann = getattr(value, "__annotations__", {}) or {}

            def _type_of(name: str, ann: dict = ann) -> str:
                t = ann.get(name)
                if t is None:
                    return ""
                return getattr(t, "__name__", str(t))

            try:
                real = set(inspect.signature(value).parameters)
            except (TypeError, ValueError):
                real = set()
            for k in extra.get("params") or {}:
                if real and k not in real and errors is not None:
                    errors.append(
                        f"provided.{name}.params documents {k!r}, which is not "
                        f"a parameter of {entry.get('signature', name)}")
            for k in sorted(real):
                if k not in (extra.get("params") or {}) and errors is not None:
                    errors.append(
                        f"provided.{name}.params omits {k!r}; document every "
                        f"parameter or none")
            entry["params"] = [
                {"name": k, "type": _type_of(k), "doc": v}
                for k, v in (extra.get("params") or {}).items()
            ]
            if extra.get("returns"):
                entry["returns"] = {"type": _type_of("return"),
                                    "doc": extra["returns"]}
        if extra.get("example"):
            entry["example"] = extra["example"]
            try:
                result = eval(extra["example"], dict(ns))  # noqa: S307
                entry["example_out"] = _summarize_value(result, compact=True)
            except Exception as e:  # noqa: BLE001
                if errors is not None:
                    errors.append(
                        f"provided example for {name!r} raised {type(e).__name__}: {e}")
        out.append(entry)
    return out


def load_all() -> ContentSet:
    cs = ContentSet()
    for path in sorted(CURRICULUM.glob("*/questions/*.yaml")):
        rel = str(path.relative_to(REPO_ROOT))
        try:
            bank = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            cs.errors.append(ContentError(rel, f"YAML parse error: {e}"))
            continue
        _validate_quiz(bank, rel, cs.errors)
        if bank.get("id"):
            if bank["id"] in cs.quizzes:
                cs.errors.append(ContentError(rel, f"duplicate quiz bank id {bank['id']!r}"))
            cs.quizzes[bank["id"]] = bank
    for path in sorted(CURRICULUM.glob("*/exercises/*.yaml")):
        rel = str(path.relative_to(REPO_ROOT))
        try:
            spec = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            cs.errors.append(ContentError(rel, f"YAML parse error: {e}"))
            continue
        _validate_exercise(spec, rel, cs.errors)
        if spec.get("id"):
            if spec["id"] in cs.exercises:
                cs.errors.append(ContentError(rel, f"duplicate exercise id {spec['id']!r}"))
            cs.exercises[spec["id"]] = spec
    return cs


def _write_if_changed(path: Path, content: str) -> bool:
    """Avoid touching unchanged files: mkdocs serve watches docs/ and would
    otherwise loop forever on rebuild."""
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def export_json(cs: ContentSet) -> int:
    """Convert loaded content to docs/assets/generated/*.json. Returns count written."""
    written = 0
    for bank_id, bank in cs.quizzes.items():
        out = json.dumps(bank, indent=1)
        if _write_if_changed(GENERATED / "quizzes" / f"{bank_id}.json", out):
            written += 1
    for ex_id, spec in cs.exercises.items():
        public = {k: spec.get(k) for k in
                  ("id", "title", "description", "starter_code", "setup_code",
                   "tests", "hints", "solution")}
        public["provided"] = build_provided(spec)
        out = json.dumps(public, indent=1)
        if _write_if_changed(GENERATED / "exercises" / f"{ex_id}.json", out):
            written += 1
    return written
