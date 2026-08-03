"""Run every gate CI runs, locally, and fail loudly.

    python tools/verify.py

Exists because of a real incident: local checks were being run as
`python tools/validate_content.py | tail -2` inside an && chain, and a
pipeline's exit status is the *last* command's — so `tail` returned 0 and
masked seven failing exercises across five commits while CI went red.

Never pipe a gate. Run this instead.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

GATES = [
    ("ruff", [PY, "-m", "ruff", "check", "."], ROOT),
    ("pytest", [PY, "-m", "pytest", "-q"], ROOT),
    ("content", [PY, "tools/validate_content.py"], ROOT),
    ("mkdocs", [PY, "-m", "mkdocs", "build", "--strict"], ROOT),
    ("grader:frames", [PY, "-m", "grader", "--reference", "--seed", "1"],
     ROOT / "projects" / "frame_transforms_mini"),
    ("grader:localization", [PY, "-m", "grader", "--reference", "--seed", "1"],
     ROOT / "projects" / "localization"),
    ("grader:control", [PY, "-m", "grader", "--reference", "--seed", "1"],
     ROOT / "projects" / "control_tuning"),
    ("grader:mapping", [PY, "-m", "grader", "--reference", "--seed", "1"],
     ROOT / "projects" / "mapping_mini"),
    ("grader:planning", [PY, "-m", "grader", "--reference", "--seed", "1"],
     ROOT / "projects" / "planning_mini"),
    ("grader:perception", [PY, "-m", "grader", "--reference", "--seed", "1"],
     ROOT / "projects" / "perception_mini"),
    ("capstone:v0", [PY, "-m", "eval", "run", "--episodes", "3", "--seed", "7"],
     ROOT / "projects" / "capstone_nav"),
    ("capstone:v3", [PY, "-m", "eval", "run", "--episodes", "3", "--seed", "1000",
                     "--stack", "dynamic_stack", "--dynamic", "6"],
     ROOT / "projects" / "capstone_nav"),
    ("capstone:v4", [PY, "-m", "eval", "run", "--episodes", "24", "--seed", "0",
                     "--stack", "slam_stack", "--rubric", "slam"],
     ROOT / "projects" / "capstone_nav"),
    ("capstone2:suite", [PY, "solutions/evaluate.py", "--episodes", "20", "--check"],
     ROOT / "projects" / "capstone_ship"),
    ("capstone3:grasp", [PY, "-m", "eval", "run", "--episodes", "12", "--seed", "0"],
     ROOT / "projects" / "capstone_grasp"),
]


def main() -> int:
    failures = []
    for name, cmd, cwd in GATES:
        print(f"--- {name} ", end="", flush=True)
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        if proc.returncode == 0:
            print("ok")
        else:
            print("FAIL")
            failures.append(name)
            tail = (proc.stdout + proc.stderr).strip().splitlines()[-25:]
            for line in tail:
                print(f"    {line}")
    print()
    if failures:
        print(f"FAILED: {', '.join(failures)}")
        return 1
    print(f"all {len(GATES)} gates passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
