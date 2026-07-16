"""Motion-primitive segmentation via soft prototype matching.

Each primitive is a prototype point in feature space; a segment is emitted when
the best-matching prototype stays dominant for `min_duration_s`. Cosine-style
soft matching (not hard thresholds) lets imperfect executions still score,
and prototypes are data — replaceable by a learned temporal model (Phase 3)
behind the same `SequenceSegmenter` interface.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

import numpy as np

from backend.gestures.schema import GestureFeatureVector, MotionPrimitive, SequenceSegment

# feature keys used for matching
_KEYS = (
    "openness",
    "expansion_rate",
    "vertical_velocity",
    "pointing_up",
    "pointing_forward",
    "circularity",
    "circle_overhead",
    "horizontal_travel",
    "depth_velocity",
    "tempo",
    "stillness",
    "separation",
)

# prototype: {feature: (target, weight)} — unlisted features are ignored
_PROTOTYPES: dict[MotionPrimitive, dict[str, tuple[float, float]]] = {
    MotionPrimitive.EXPAND: {
        "expansion_rate": (0.5, 3.0),
        "tempo": (0.4, 0.5),
        "separation": (1.2, 0.5),
    },
    MotionPrimitive.CONTRACT: {"expansion_rate": (-0.5, 3.0), "tempo": (0.4, 0.5)},
    MotionPrimitive.RAISE: {"vertical_velocity": (0.6, 3.0), "tempo": (0.4, 0.5)},
    MotionPrimitive.LOWER: {"vertical_velocity": (-0.6, 3.0), "tempo": (0.4, 0.5)},
    MotionPrimitive.POINT_UP: {"pointing_up": (0.8, 3.0), "tempo": (0.15, 0.5)},
    MotionPrimitive.POINT_FORWARD: {"pointing_forward": (0.8, 3.0), "tempo": (0.15, 0.5)},
    MotionPrimitive.CIRCLE_OVERHEAD: {"circle_overhead": (0.55, 3.0), "tempo": (0.45, 0.5)},
    MotionPrimitive.CIRCLE_FRONTAL: {"circularity": (0.6, 2.5), "circle_overhead": (0.1, 1.0)},
    MotionPrimitive.SWEEP_HORIZONTAL: {
        "horizontal_travel": (0.75, 3.0),
        "circularity": (0.1, 1.0),
        "tempo": (0.5, 0.5),
    },
    MotionPrimitive.PUSH_AWAY: {"depth_velocity": (-0.6, 3.0), "openness": (0.8, 1.0)},
    MotionPrimitive.PULL_IN: {"depth_velocity": (0.6, 3.0)},
    MotionPrimitive.FRAME_RECT: {
        "separation": (1.0, 1.5),
        "stillness": (0.7, 2.0),
        "openness": (0.35, 1.5),
    },
    MotionPrimitive.HOLD_STILL: {"stillness": (0.9, 3.0), "tempo": (0.03, 1.0)},
    MotionPrimitive.WAVE: {
        "tempo": (0.8, 2.0),
        "smoothness": (0.3, 1.0),
        "horizontal_travel": (0.5, 1.5),
    },
}

_SCALE = {"expansion_rate": 1.0, "vertical_velocity": 1.0, "depth_velocity": 1.0}


def _match(fv: GestureFeatureVector, proto: dict[str, tuple[float, float]]) -> float:
    num = den = 0.0
    for key, (target, weight) in proto.items():
        val = getattr(fv, key, 0.0)
        scale = _SCALE.get(key, 1.0)
        sim = max(0.0, 1.0 - abs(val - target) / (scale if scale else 1.0))
        if target < 0 or (key in _SCALE and target < 0):
            sim = max(0.0, 1.0 - abs(val - target))
        num += sim * weight
        den += weight
    return num / den if den else 0.0


class SequenceSegmenter(ABC):
    @abstractmethod
    def update(self, fv: GestureFeatureVector) -> SequenceSegment | None: ...


class PrototypeSegmenter(SequenceSegmenter):
    def __init__(
        self,
        min_score: float = 0.62,
        min_duration_s: float = 0.45,
        hold_still_duration_s: float = 2.0,
    ) -> None:
        self._min_score = min_score
        self._min_dur = min_duration_s
        self._hold_dur = hold_still_duration_s
        self._current: MotionPrimitive | None = None
        self._start_ts = 0.0
        self._scores: list[float] = []

    def peek(self, fv: GestureFeatureVector) -> list[tuple[MotionPrimitive, float]]:
        """Non-mutating: score fv against every prototype, best first. Lets the
        UI show live "what's matching right now" without disturbing segmentation."""
        return sorted(
            ((prim, _match(fv, proto)) for prim, proto in _PROTOTYPES.items()),
            key=lambda t: -t[1],
        )

    def reset(self) -> None:
        """Clear in-progress state without emitting a segment — used when
        entering air-draw mode so a stale partial match doesn't leak through."""
        self._current = None
        self._scores = []
        self._start_ts = 0.0

    def update(self, fv: GestureFeatureVector) -> SequenceSegment | None:
        if fv.hands_visible == 0:
            return self._flush(fv.ts)

        best, best_score = None, 0.0
        for prim, s in self.peek(fv):
            best, best_score = prim, s
            break

        if best_score < self._min_score:
            return self._flush(fv.ts)

        if best != self._current:
            seg = self._flush(fv.ts)
            self._current, self._start_ts, self._scores = best, fv.ts, [best_score]
            return seg

        self._scores.append(best_score)
        return None

    def _flush(self, now: float) -> SequenceSegment | None:
        if self._current is None:
            return None
        prim, start, scores = self._current, self._start_ts, self._scores
        self._current, self._scores = None, []
        dur = now - start
        required = self._hold_dur if prim == MotionPrimitive.HOLD_STILL else self._min_dur
        if dur < required:
            return None
        return SequenceSegment(
            id=f"seg_{uuid.uuid4().hex[:8]}",
            primitive=prim,
            t_start=start,
            t_end=now,
            confidence=float(np.clip(np.mean(scores) * min(1.0, dur / required), 0, 1)),
            params={"duration_s": round(dur, 2)},
        )
