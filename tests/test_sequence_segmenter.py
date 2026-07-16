"""PrototypeSegmenter.peek() / reset() — non-mutating introspection used for
live gesture-transparency debug info, and the state-clearing needed when
entering air-draw mode (a stale in-progress primitive must not leak through).
"""

from __future__ import annotations

from backend.gestures.schema import GestureFeatureVector, MotionPrimitive
from backend.gestures.sequence import PrototypeSegmenter


def _fv(ts: float, **kw) -> GestureFeatureVector:
    return GestureFeatureVector(ts=ts, hands_visible=1, **kw)


def test_peek_returns_best_match_first() -> None:
    seg = PrototypeSegmenter()
    candidates = seg.peek(_fv(0.0, expansion_rate=0.5, tempo=0.4, separation=1.2))
    assert candidates[0][0] == MotionPrimitive.EXPAND
    scores = [s for _, s in candidates]
    assert scores == sorted(scores, reverse=True)


def test_peek_does_not_mutate_in_progress_state() -> None:
    seg = PrototypeSegmenter()
    seg.update(_fv(0.0, expansion_rate=0.5, tempo=0.4, separation=1.2))
    before = (seg._current, list(seg._scores))
    for i in range(5):
        seg.peek(_fv(i * 0.01, stillness=0.95, tempo=0.02))
    after = (seg._current, list(seg._scores))
    assert before == after


def test_reset_clears_pending_segment_without_emitting() -> None:
    seg = PrototypeSegmenter(min_duration_s=0.05)
    seg.update(_fv(0.0, expansion_rate=0.5, tempo=0.4, separation=1.2))
    seg.reset()
    # a transition that would normally flush the pending segment now emits nothing
    result = seg.update(GestureFeatureVector(ts=0.2, hands_visible=0))
    assert result is None
