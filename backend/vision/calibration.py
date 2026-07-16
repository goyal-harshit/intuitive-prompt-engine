"""Per-session neutral-face baseline for mood signals.

`_face_signals()` in landmarks.py previously computed valence/arousal against
fixed linear coefficients tuned on nobody in particular — resting mouth width,
brow height, etc. vary a lot person to person. This collects a short neutral
baseline at session start and switches valence/arousal to baseline-relative
math once enough samples are in, without any persistent per-user storage
(none exists elsewhere in the app; session-scoped is proportionate).
"""

from __future__ import annotations

import numpy as np

from backend.core.config import FaceCalibrationConfig

# (corner_lift, mouth_w, brow_raise, mouth_open) — reproduces the original
# fixed-coefficient formula (valence's "-0.38", arousal's "-0.35") exactly
# until real per-session samples replace it, so pre-calibration behavior is
# unchanged from the old uncalibrated math.
_DEFAULT_BASELINE = (0.0, 0.38, 0.35 / 12, 0.0)


class FaceCalibrator:
    def __init__(self, cfg: FaceCalibrationConfig) -> None:
        self._enabled = cfg.enabled
        self._duration_s = cfg.calibration_duration_s
        self._start_ts: float | None = None
        self._samples: list[tuple[float, float, float, float]] = []
        self._baseline: tuple[float, float, float, float] | None = None

    @property
    def calibrating(self) -> bool:
        return self._enabled and self._baseline is None

    @property
    def baseline(self) -> tuple[float, float, float, float]:
        return self._baseline or _DEFAULT_BASELINE

    def observe(
        self, ts: float, corner_lift: float, mouth_w: float, brow_raise: float, mouth_open: float
    ) -> None:
        if not self._enabled or self._baseline is not None:
            return
        if self._start_ts is None:
            self._start_ts = ts
        self._samples.append((corner_lift, mouth_w, brow_raise, mouth_open))
        if ts - self._start_ts >= self._duration_s:
            self._baseline = tuple(np.asarray(self._samples).mean(axis=0).tolist())
