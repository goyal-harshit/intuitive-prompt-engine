"""Pinch-hysteresis draw-mode gate and fingertip stroke buffer."""

from __future__ import annotations

from backend.gestures.draw import DrawModeGate, StrokeBuffer
from backend.gestures.schema import GestureFeatureVector
from backend.vision.schema import HandLandmarks, LandmarkFrame


def _fv(ts: float, pinch: float, hands_visible: int = 1) -> GestureFeatureVector:
    return GestureFeatureVector(ts=ts, hands_visible=hands_visible, pinch=pinch)


def _hand_with_index_tip(x: float, y: float, z: float = 0.0) -> HandLandmarks:
    points = [(0.0, 0.0, 0.0)] * 21
    points[8] = (x, y, z)
    return HandLandmarks(handedness="Right", points=points, score=0.9)


# ---------- DrawModeGate ----------


def test_stays_out_of_draw_mode_while_pinch_is_open() -> None:
    gate = DrawModeGate(enter_threshold=0.35, exit_threshold=0.55, enter_hold_s=0.12)
    for i in range(10):
        state = gate.update(_fv(ts=i * 0.05, pinch=0.9))
    assert state.drawing is False


def test_enters_draw_mode_only_after_sustained_pinch() -> None:
    gate = DrawModeGate(enter_threshold=0.35, exit_threshold=0.55, enter_hold_s=0.12)
    # not yet held long enough
    early = gate.update(_fv(ts=0.0, pinch=0.1))
    assert early.drawing is False and early.just_entered is False
    mid = gate.update(_fv(ts=0.05, pinch=0.1))
    assert mid.drawing is False
    late = gate.update(_fv(ts=0.13, pinch=0.1))
    assert late.drawing is True
    assert late.just_entered is True


def test_brief_pinch_that_releases_before_hold_never_enters() -> None:
    gate = DrawModeGate(enter_threshold=0.35, exit_threshold=0.55, enter_hold_s=0.12)
    gate.update(_fv(ts=0.0, pinch=0.1))
    gate.update(_fv(ts=0.05, pinch=0.9))  # released early — candidate reset
    state = gate.update(_fv(ts=0.13, pinch=0.1))
    assert state.drawing is False  # hold clock restarted, not enough time elapsed yet


def test_hysteresis_keeps_drawing_between_enter_and_exit_thresholds() -> None:
    gate = DrawModeGate(enter_threshold=0.35, exit_threshold=0.55, enter_hold_s=0.1)
    gate.update(_fv(ts=0.0, pinch=0.1))
    gate.update(_fv(ts=0.11, pinch=0.1))
    # now drawing=True; a mid-range pinch (above enter, below exit) should not exit
    state = gate.update(_fv(ts=0.2, pinch=0.45))
    assert state.drawing is True


def test_exits_once_pinch_crosses_exit_threshold() -> None:
    gate = DrawModeGate(enter_threshold=0.35, exit_threshold=0.55, enter_hold_s=0.1)
    gate.update(_fv(ts=0.0, pinch=0.1))
    gate.update(_fv(ts=0.11, pinch=0.1))
    state = gate.update(_fv(ts=0.2, pinch=0.6))
    assert state.drawing is False
    assert state.just_exited is True


def test_losing_hand_visibility_exits_drawing() -> None:
    gate = DrawModeGate(enter_threshold=0.35, exit_threshold=0.55, enter_hold_s=0.1)
    gate.update(_fv(ts=0.0, pinch=0.1))
    gate.update(_fv(ts=0.11, pinch=0.1))
    state = gate.update(_fv(ts=0.2, pinch=0.1, hands_visible=0))
    assert state.drawing is False
    assert state.just_exited is True


def test_reset_clears_pending_and_active_state() -> None:
    gate = DrawModeGate(enter_threshold=0.35, exit_threshold=0.55, enter_hold_s=0.1)
    gate.update(_fv(ts=0.0, pinch=0.1))
    gate.update(_fv(ts=0.11, pinch=0.1))
    gate.reset()
    state = gate.update(_fv(ts=0.12, pinch=0.1))
    assert state.drawing is False and state.just_entered is False


# ---------- StrokeBuffer ----------


def test_no_hands_yields_no_point() -> None:
    buf = StrokeBuffer(smoothing_alpha=0.5, min_point_dist=0.01, max_points=100)
    assert buf.add_from_frame(LandmarkFrame(ts=0.0, hands=[])) is None


def test_far_enough_movement_is_recorded() -> None:
    buf = StrokeBuffer(smoothing_alpha=1.0, min_point_dist=0.01, max_points=100)
    buf.add_from_frame(LandmarkFrame(ts=0.0, hands=[_hand_with_index_tip(0.0, 0.0)]))
    pt = buf.add_from_frame(LandmarkFrame(ts=0.1, hands=[_hand_with_index_tip(0.5, 0.5)]))
    assert pt is not None
    assert len(buf.points) == 2


def test_tiny_movement_is_downsampled_away() -> None:
    buf = StrokeBuffer(smoothing_alpha=1.0, min_point_dist=0.05, max_points=100)
    buf.add_from_frame(LandmarkFrame(ts=0.0, hands=[_hand_with_index_tip(0.0, 0.0)]))
    pt = buf.add_from_frame(LandmarkFrame(ts=0.1, hands=[_hand_with_index_tip(0.001, 0.001)]))
    assert pt is None
    assert len(buf.points) == 1


def test_max_points_caps_the_buffer() -> None:
    buf = StrokeBuffer(smoothing_alpha=1.0, min_point_dist=0.0, max_points=5)
    for i in range(10):
        buf.add_from_frame(LandmarkFrame(ts=i * 0.1, hands=[_hand_with_index_tip(i * 0.1, 0.0)]))
    assert len(buf.points) == 5


def test_reset_clears_points_and_filter_memory() -> None:
    buf = StrokeBuffer(smoothing_alpha=0.5, min_point_dist=0.0, max_points=100)
    buf.add_from_frame(LandmarkFrame(ts=0.0, hands=[_hand_with_index_tip(0.5, 0.5)]))
    buf.reset()
    assert buf.points == []
    pt = buf.add_from_frame(LandmarkFrame(ts=0.1, hands=[_hand_with_index_tip(0.1, 0.1)]))
    assert pt is not None
    assert pt.x == 0.1 and pt.y == 0.1  # filter forgot prior state after reset
