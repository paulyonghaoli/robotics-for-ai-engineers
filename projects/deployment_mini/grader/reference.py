"""Reference implementation for the deployment mini-project."""

from __future__ import annotations

import numpy as np
from deploykit import BASE_FRAME_MS, clock_scale


def pipeline_samples(stages):
    """Per-frame pipeline latency: the stages run in series, so a frame's
    cost is the sum of that frame's stage costs."""
    names = list(stages)
    return np.sum([np.asarray(stages[n], dtype=float) for n in names], axis=0)


def sum_of_stage_p99(stages):
    """What you get by adding the per-stage p99s from a dashboard."""
    return float(sum(float(np.percentile(np.asarray(v, dtype=float), 99))
                     for v in stages.values()))


def tail_driver(stages):
    """The stage contributing most of the pipeline's tail: largest
    p99 - p50, not largest mean."""
    def spread(v):
        v = np.asarray(v, dtype=float)
        return float(np.percentile(v, 99) - np.percentile(v, 50))
    return max(stages, key=lambda n: spread(stages[n]))


def mean_driver(stages):
    """The stage with the largest mean — the one a flat profile points at."""
    return max(stages, key=lambda n: float(np.mean(np.asarray(stages[n], dtype=float))))


def quant_params(x, n_bits=8):
    """Asymmetric affine quantization parameters for one tensor."""
    x = np.asarray(x, dtype=float)
    qmax = 2 ** n_bits - 1
    lo, hi = float(x.min()), float(x.max())
    if hi == lo:
        return 1.0, 0
    scale = (hi - lo) / qmax
    zero_point = int(round(-lo / scale))
    return scale, zero_point


def fake_quant(x, scale, zero_point, n_bits=8):
    """Quantize and dequantize: what the network actually sees."""
    x = np.asarray(x, dtype=float)
    qmax = 2 ** n_bits - 1
    q = np.clip(np.round(x / scale) + zero_point, 0, qmax)
    return (q - zero_point) * scale


def per_tensor_error(w, n_bits=8):
    """RMS reconstruction error with one scale for the whole tensor."""
    w = np.asarray(w, dtype=float)
    s, z = quant_params(w, n_bits)
    return float(np.sqrt(np.mean((fake_quant(w, s, z, n_bits) - w) ** 2)))


def per_channel_error(w, n_bits=8):
    """RMS reconstruction error with one scale per output channel."""
    w = np.asarray(w, dtype=float)
    out = np.empty_like(w)
    for i in range(w.shape[0]):
        s, z = quant_params(w[i], n_bits)
        out[i] = fake_quant(w[i], s, z, n_bits)
    return float(np.sqrt(np.mean((out - w) ** 2)))


def detect(plan, rate, k, fleet):
    """When the fleet monitor alarms, and what it cost to get there.

    Failures accrue at `rate` per robot-hour on the new version. The
    monitor fires once `k` of them have accumulated.

    Returns {"hours": wall-clock hours since the rollout started,
             "robot_hours": exposure to the bad version at that moment,
             "fraction": fleet fraction on it when the alarm fired}
    or None if the plan finishes without reaching k.
    """
    hours = 0.0
    robot_hours = 0.0
    failures = 0.0
    for fraction, duration in plan:
        robots = fraction * fleet
        per_hour = robots * rate
        if per_hour > 0 and failures + per_hour * duration >= k:
            need = (k - failures) / per_hour
            return {"hours": hours + need,
                    "robot_hours": robot_hours + robots * need,
                    "fraction": fraction}
        failures += per_hour * duration
        robot_hours += robots * duration
        hours += duration
    return None


def frame_ms(t_s):
    """Frame time `t_s` seconds into a sustained run."""
    return BASE_FRAME_MS / clock_scale(t_s)


def mean_fps(duration_s, dt_s=1.0):
    """Average frame rate measured over a benchmark of `duration_s`."""
    t = np.arange(0.0, duration_s, dt_s)
    return float(np.mean(1000.0 / frame_ms(t)))


def sustained_fps():
    """The number that is true after the heat soak — i.e. the one to
    publish."""
    return float(1000.0 / frame_ms(1e9))


def deadline_breach_time(deadline_ms, horizon_s=3600.0, dt_s=1.0):
    """First second at which the frame time exceeds the deadline, or None."""
    t = np.arange(0.0, horizon_s, dt_s)
    over = np.nonzero(frame_ms(t) > deadline_ms)[0]
    return float(t[over[0]]) if len(over) else None
