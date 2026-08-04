"""Given material for the deployment mini-project.

Stage timing traces, a weight tensor with one badly-behaved channel, two
rollout plans, and a thermal model. Nothing here is graded.
"""

from __future__ import annotations

import numpy as np

FRAME_PERIOD_MS = 20.0          # a 50 Hz loop


def stage_traces(rng: np.random.Generator, n: int = 4000) -> dict[str, np.ndarray]:
    """Per-stage latency samples, independent across stages.

    `undistort` has the largest mean and almost no spread. `detect` and
    `track` both allocate, so each occasionally stops for several ms — and
    they do it independently, which is the whole point of the first check.
    """
    return {
        "undistort": rng.normal(3.00, 0.05, size=n),
        "detect": (rng.normal(2.00, 0.10, size=n)
                   + (rng.random(n) < 0.03) * (8.0 + 2.0 * rng.random(n))),
        "track": (rng.normal(0.50, 0.05, size=n)
                  + (rng.random(n) < 0.03) * (12.0 + 3.0 * rng.random(n))),
        "plan": rng.normal(1.50, 0.20, size=n),
    }


def weight_tensor(rng: np.random.Generator, out_ch: int = 64, in_ch: int = 128) -> np.ndarray:
    """A convolution weight tensor, one row per output channel.

    Channel 17 has a hundred times the dynamic range of the rest — one
    badly-scaled channel is enough to ruin a per-tensor quantization, and
    real networks have several.
    """
    w = rng.normal(0.0, 0.05, size=(out_ch, in_ch))
    w[17] = rng.normal(0.0, 5.0, size=in_ch)
    return w


FLEET_SIZE = 500

# Each stage is (fraction of the fleet on the new version, hours held there).
ROLLOUT_PLANS = {
    "ship-it": [(1.00, 48.0)],
    "canary-first": [(0.01, 24.0), (0.10, 24.0), (1.00, 48.0)],
}


# Thermal model: the SoC runs at full clock until the heat soak catches up,
# then the governor drops it toward a sustained floor.
CLOCK_KNEE_S = 90.0             # full clock until here
CLOCK_FLOOR_S = 300.0           # fully throttled from here on
CLOCK_FLOOR = 0.50              # sustained clock as a fraction of boost
BASE_FRAME_MS = 11.0            # frame time at full clock


def clock_scale(t_s):
    """Clock as a fraction of boost, `t_s` seconds into a sustained run."""
    t = np.asarray(t_s, dtype=float)
    ramp = (t - CLOCK_KNEE_S) / (CLOCK_FLOOR_S - CLOCK_KNEE_S)
    return np.clip(1.0 - (1.0 - CLOCK_FLOOR) * np.clip(ramp, 0.0, 1.0), CLOCK_FLOOR, 1.0)
