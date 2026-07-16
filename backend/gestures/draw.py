"""Air-draw mode: pinch-triggered fingertip stroke capture.

A thumb-index pinch (already computed as `GestureFeatureVector.pinch`) gates a
separate "drawing" mode, distinct from the 14-primitive gesture vocabulary in
`sequence.py` (no existing prototype uses finger-distance, so this cannot
collide). Hysteresis between enter/exit thresholds plus a short enter-hold
prevents flicker right at the boundary.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

from backend.gestures.features import INDEX_TIP
from backend.gestures.filters import EMAVec3Filter
from backend.gestures.schema import GestureFeatureVector, StrokePoint
from backend.vision.schema import LandmarkFrame


@dataclass
class DrawGateState:
    drawing: bool
    just_entered: bool = False
    just_exited: bool = False


class DrawModeGate:
    """Pinch-distance hysteresis state machine — enter requires a sustained dip,
    exit is immediate once the release threshold is crossed (the enter/exit gap
    itself prevents chatter, so no exit hold is needed)."""

    def __init__(self, enter_threshold: float, exit_threshold: float, enter_hold_s: float) -> None:
        self._enter = enter_threshold
        self._exit = exit_threshold
        self._hold_s = enter_hold_s
        self._drawing = False
        self._candidate_since: float | None = None

    def update(self, fv: GestureFeatureVector) -> DrawGateState:
        if fv.hands_visible == 0:
            return self._exit_if_drawing()

        if self._drawing:
            if fv.pinch > self._exit:
                return self._exit_if_drawing()
            return DrawGateState(drawing=True)

        if fv.pinch < self._enter:
            if self._candidate_since is None:
                self._candidate_since = fv.ts
            elif fv.ts - self._candidate_since >= self._hold_s:
                self._drawing = True
                self._candidate_since = None
                return DrawGateState(drawing=True, just_entered=True)
        else:
            self._candidate_since = None
        return DrawGateState(drawing=False)

    def _exit_if_drawing(self) -> DrawGateState:
        was_drawing = self._drawing
        self._drawing = False
        self._candidate_since = None
        return DrawGateState(drawing=False, just_exited=was_drawing)

    def reset(self) -> None:
        self._drawing = False
        self._candidate_since = None


class StrokeBuffer:
    """Smoothed, downsampled, capped buffer of the pinching hand's index-fingertip."""

    def __init__(self, smoothing_alpha: float, min_point_dist: float, max_points: int) -> None:
        self._filter = EMAVec3Filter(smoothing_alpha)
        self._points: deque[StrokePoint] = deque(maxlen=max_points)
        self._min_dist = min_point_dist

    def add_from_frame(self, lm: LandmarkFrame) -> StrokePoint | None:
        if not lm.hands:
            return None
        # Single-hand drawing: use the first detected hand's index tip.
        x, y, z = lm.hands[0].points[INDEX_TIP]
        fx, fy, _ = self._filter.update(x, y, z)
        if self._points:
            last = self._points[-1]
            if math.hypot(fx - last.x, fy - last.y) < self._min_dist:
                return None
        pt = StrokePoint(ts=lm.ts, x=fx, y=fy)
        self._points.append(pt)
        return pt

    @property
    def points(self) -> list[StrokePoint]:
        return list(self._points)

    def reset(self) -> None:
        self._points.clear()
        self._filter.reset()
