"""The 'Provided in this exercise' panel is derived, so pin its derivation.

The learner never sees `setup_code`. Everything these tests guard is a way
that panel could quietly start lying: a stale example output, a constant
printed as the wrong type, or a bug exercise leaking its own diagnosis
through a docstring written for someone reading the source.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.content_lib import build_provided, load_all  # noqa: E402

SETUP = """
import numpy as np

DT = 0.1
WIDTH = 1.0
COUNT = 3
GRID = np.zeros((4, 5))

def step(y, action, k):
    \"\"\"Advance one tick.\"\"\"
    return y + action * DT + k

def unused(z):
    \"\"\"Never referenced by the learner.\"\"\"
    return z
"""

STARTER = "out = step(0.0, 1.0, 2) + WIDTH + COUNT + GRID.sum()\n"


def _spec(**over: object) -> dict:
    spec = {"id": "t", "title": "t", "setup_code": SETUP,
            "starter_code": STARTER, "solution": STARTER, "tests": ""}
    spec.update(over)
    return spec


def test_only_surfaces_what_the_learner_touches() -> None:
    names = {i["name"] for i in build_provided(_spec())}
    assert "step" in names
    # DT is defined but never referenced by starter or solution: listing it
    # would turn the panel into a dump of the exercise's internals.
    assert "DT" not in names
    assert "unused" not in names
    assert "np" not in names          # imported modules are not "provided"


def test_signature_is_derived_not_authored() -> None:
    step = next(i for i in build_provided(_spec()) if i["name"] == "step")
    assert step["signature"] == "step(y, action, k)"
    assert step["kind"] == "function"


def test_constant_keeps_its_type() -> None:
    got = {i["name"]: i.get("value") for i in build_provided(_spec())}
    # A float must not print as "1" — these carry units in the lessons.
    assert got["WIDTH"] == "1.0"
    assert got["COUNT"] == "3"
    assert got["GRID"] == "ndarray shape=(4, 5) dtype=float64"


def test_constants_get_no_docstring_fallback() -> None:
    """inspect.getdoc(1.0) returns float's docstring, which is nonsense here."""
    width = next(i for i in build_provided(_spec()) if i["name"] == "WIDTH")
    assert "summary" not in width


def test_callable_falls_back_to_its_docstring() -> None:
    step = next(i for i in build_provided(_spec()) if i["name"] == "step")
    assert step["summary"] == "Advance one tick."


def test_authored_summary_beats_the_docstring() -> None:
    spec = _spec(provided={"step": {"summary": "Authored."}})
    step = next(i for i in build_provided(spec) if i["name"] == "step")
    assert step["summary"] == "Authored."


def test_hide_withholds_an_object() -> None:
    spec = _spec(provided={"step": {"hide": True}})
    assert all(i["name"] != "step" for i in build_provided(spec))


def test_example_output_is_computed_not_transcribed() -> None:
    spec = _spec(provided={"step": {"example": "step(0.0, 1.0, 2)"}})
    step = next(i for i in build_provided(spec) if i["name"] == "step")
    assert step["example_out"] == "2.1"


def test_example_output_stays_a_float() -> None:
    """A pixel width of 54.0 shown as "54" reads as an integer count."""
    spec = _spec(provided={"step": {"example": "step(0.0, 2.0, 3.0)"}})
    step = next(i for i in build_provided(spec) if i["name"] == "step")
    assert step["example_out"] == "3.2"
    spec = _spec(provided={"step": {"example": "step(0.0, 10.0, 4.0)"}})
    step = next(i for i in build_provided(spec) if i["name"] == "step")
    assert step["example_out"] == "5.0"


def test_short_numeric_tuple_shows_its_values() -> None:
    """"tuple of 3" hides exactly what a sensor mount pose needs to say."""
    setup = SETUP + "\nMOUNT = (0.4, 0.0, 3.14159)\n"
    spec = _spec(setup_code=setup, provided={"MOUNT": {}})
    mount = next(i for i in build_provided(spec) if i["name"] == "MOUNT")
    assert mount["value"] == "(0.4, 0.0, 3.14159)"


def test_broken_example_is_an_error() -> None:
    errors: list[str] = []
    build_provided(_spec(provided={"step": {"example": "step(0.0)"}}), errors)
    assert errors and "TypeError" in errors[0]


def test_documenting_a_nonexistent_name_is_an_error() -> None:
    errors: list[str] = []
    build_provided(_spec(provided={"ghost": {"summary": "x"}}), errors)
    assert errors and "ghost" in errors[0]


def test_authored_entry_shows_even_if_unused() -> None:
    """An author may want to surface something the starter doesn't call yet."""
    spec = _spec(provided={"DT": {"summary": "Timestep, seconds."}})
    dt = next(i for i in build_provided(spec) if i["name"] == "DT")
    assert dt["value"] == "0.1"


@pytest.mark.parametrize("ex_id", ["tr-l5-offline-metric"])
def test_real_exercise_panel_is_complete(ex_id: str) -> None:
    """0.5's exercise is the reference example; every object carries a contract."""
    spec = load_all().exercises[ex_id]
    errors: list[str] = []
    items = build_provided(spec, errors)
    assert not errors
    assert {i["name"] for i in items} == {
        "LANE_HALF_WIDTH", "expert", "policy", "plant", "expert_states"}
    for item in items:
        assert item.get("summary"), f"{item['name']} has no description"
    # The docstring on expert_states states the diagnosis outright; the
    # authored summary must be what the learner sees.
    states = next(i for i in items if i["name"] == "expert_states")
    assert "training/test set" not in states["summary"]
