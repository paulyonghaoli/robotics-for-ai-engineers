"""YOUR capstone stack. Start here.

    python -m eval run --episodes 8 --stack student_stack

That command is the autograder. It runs your stack across randomized
worlds and scores it against the published rubric:

    success_rate          >= 0.85
    collision_free_rate   >= 0.85
    mean_path_ratio       <= 1.60      (executed length / A*-optimal)
    p95_step_latency_ms   <= 50.0

Nothing here is hidden from you. `sim.py` is the world, `eval/` is the
scorer, and reference implementations live in `solutions/` — five of them,
v0 through v4. Read them when you're stuck or when you're done; they are
notes from someone who already walked into the walls, not an answer key
you're cheating by opening. But attempt it first. The bugs in
`docs/capstone-log.md` are only interesting once you've met one.

--------------------------------------------------------------------------
THE CONTRACT

A stack is any object with:

    make_stack(sim) -> stack          module-level factory
    stack.step(obs) -> (v, w)         called once per 0.1 s tick

`obs` is a dict:

    obs["scan"]       (36,) float, lidar ranges in metres, 0.2 rad apart
                      starting at the robot's heading and going CCW.
                      A beam that hits nothing returns MAX_RANGE (6.0).
    obs["pose_meas"]  (3,) noisy (x, y, theta). sigma 0.10 m / 0.05 rad.
    obs["goal"]       (2,) goal position, world frame
    obs["collided"]   bool — True if the LAST command was refused by a
                      collision. Read this. Ignoring it is v1's bug 4.

You return `(v, w)`: forward speed (m/s) and yaw rate (rad/s). The
simulator clips them to v in [0, 1.2] and w in [-2.0, 2.0], so if you
dead-reckon your own commands, clip them the same way or your prediction
will drift every time you saturate.

Optional attributes the harness will use if present:

    stack.last_estimate   (3,) your pose belief -> scores localization RMSE
    stack.path            (N, 2) your current plan -> drawn by render.py

--------------------------------------------------------------------------
WHAT YOU'RE ALLOWED TO USE

`make_stack(sim)` receives the simulator, so `sim.grid` (the true
occupancy grid) is reachable. Which version you're building decides
whether touching it is legitimate:

    v0   known map + pose sensor        sim.grid OK, obs["pose_meas"] OK
    v1   known map, NO pose sensor      sim.grid OK, pose_meas seeds only
    v2   NO map, pose sensor            sim.grid FORBIDDEN
    v3   v2 + moving obstacles          sim.grid FORBIDDEN, --dynamic 6
    v4   NO map, NO pose sensor         both forbidden after step 0

Nobody enforces this. The rubric cannot tell whether you cheated, which
is exactly the situation you'll be in professionally, and the reason the
version you claim matters more than the number you report.

--------------------------------------------------------------------------
BUILD ORDER

Start at v0 and get 8/8. It is a genuine system — global planner, path
follower, recovery behaviour — and everything later is built on it.

  1. Inflate the occupancy grid by the robot radius, so you can plan for
     a point robot instead of a disc.            robotics_ai.planning
  2. A* from your cell to the goal cell.         robotics_ai.planning
  3. Convert the cell path to world waypoints and follow it with pure
     pursuit.                                    robotics_ai.control
  4. Replan periodically, and whenever the path is blocked.
  5. Handle obs["collided"] — stop, rotate, replan. Without this, one
     episode logged 499 collisions with the robot pinned to a wall.

Then remove an assumption and do it again.
"""

from __future__ import annotations

import numpy as np

# Imported for you — the TODOs below are meant to use these.
from sim import GOAL_TOLERANCE, INFLATE_CELLS, cell_to_world, world_to_cell  # noqa: F401

from robotics_ai.control import pure_pursuit  # noqa: F401
from robotics_ai.planning import astar_grid, inflate_grid  # noqa: F401

LOOKAHEAD = 0.8
CRUISE_V = 0.8
REPLAN_PERIOD = 15


class StudentStack:
    def __init__(self, goal: np.ndarray, grid: np.ndarray) -> None:
        self.goal = np.asarray(goal, dtype=float)
        self.grid = grid
        self.path: np.ndarray | None = None
        self.last_estimate: np.ndarray | None = None
        self.steps_since_plan = 0
        self.recovery_steps = 0

    # ---------------- planning ----------------

    def _planning_grid(self) -> np.ndarray:
        """Return the grid A* should search: obstacles grown by the robot
        radius so the robot can be planned as a point.

        TODO: inflate self.grid by INFLATE_CELLS.
        """
        raise NotImplementedError("student_stack: _planning_grid")

    def _plan(self, from_xy: np.ndarray) -> bool:
        """Plan a path from `from_xy` to self.goal. Store world-frame
        waypoints in self.path and return True, or return False if no path
        exists.

        TODO:
          - convert from_xy and self.goal to cells      (world_to_cell)
          - run astar_grid on self._planning_grid()
          - convert the returned cells back to world points (cell_to_world)
          - set the final waypoint exactly to self.goal, so you aim at the
            goal rather than at the centre of the cell containing it
        """
        raise NotImplementedError("student_stack: _plan")

    def _path_blocked(self) -> bool:
        """True if any waypoint on the current path now sits in an
        occupied cell of the planning grid.

        TODO. (For v0 the map never changes, so this can start as
        `return False` — you'll need it for real in v2.)
        """
        raise NotImplementedError("student_stack: _path_blocked")

    # ---------------- the loop ----------------

    def step(self, obs: dict) -> tuple[float, float]:
        """One control tick. Return (v, w).

        TODO, in order:
          1. pose = obs["pose_meas"];  set self.last_estimate = pose
          2. if obs["collided"]: drop the path and enter recovery
             (rotate in place for a few ticks, then replan)
          3. replan if there is no path, the path is blocked, or
             REPLAN_PERIOD ticks have passed
          4. if you are within GOAL_TOLERANCE of the goal, return (0, 0)
          5. otherwise follow self.path with pure_pursuit, and slow down
             when turning hard:  v = CRUISE_V / (1 + 0.8 * abs(w))
        """
        raise NotImplementedError("student_stack: step")


def make_stack(sim) -> StudentStack:
    # v0 is allowed the true map. From v2 on, delete this argument and earn
    # the map from lidar instead.
    return StudentStack(sim.goal, sim.grid)
