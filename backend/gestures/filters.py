"""Exponential-moving-average smoothing for noisy per-frame position signals.

Pure math, stateful, reused for both the wrist-position history that feeds
temporal features (features.py) and the fingertip trace used for air-drawing
(draw.py). Lower alpha = more smoothing, more lag; higher alpha = more
responsive, more jitter passes through.
"""

from __future__ import annotations


class EMAFilter:
    def __init__(self, alpha: float) -> None:
        self._alpha = alpha
        self._value: float | None = None

    def update(self, value: float) -> float:
        if self._value is None:
            self._value = value
        else:
            self._value += self._alpha * (value - self._value)
        return self._value

    def reset(self) -> None:
        self._value = None


class EMAVec3Filter:
    def __init__(self, alpha: float) -> None:
        self._fx = EMAFilter(alpha)
        self._fy = EMAFilter(alpha)
        self._fz = EMAFilter(alpha)

    def update(self, x: float, y: float, z: float) -> tuple[float, float, float]:
        return self._fx.update(x), self._fy.update(y), self._fz.update(z)

    def reset(self) -> None:
        self._fx.reset()
        self._fy.reset()
        self._fz.reset()
