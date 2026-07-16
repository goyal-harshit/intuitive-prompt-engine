"""Gesture feature math + primitive segmentation, driven by synthetic landmarks.

No camera or MediaPipe involved: fixtures/*.json are hand-constructed 21-point
hand landmark sets whose expected outputs are computed by hand against the
formulas in backend/gestures/features.py (see comments below for the algebra),
so these tests catch regressions in the math itself, not just "did it crash."
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from backend.gestures.features import (
    FeatureExtractor,
    _circle_fit_score,
    _hand_openness,
    _pointing_scores,
    _spectral_smoothness,
)
from backend.gestures.schema import GestureFeatureVector, MotionPrimitive
from backend.gestures.sequence import PrototypeSegmenter
from backend.vision.schema import HandLandmarks, LandmarkFrame

FIXTURES = Path(__file__).parent / "fixtures"


def _load_hand(name: str) -> HandLandmarks:
    data = json.loads((FIXTURES / f"{name}.json").read_text())
    return HandLandmarks(**data)


def _translated_hand(name: str, offset: tuple[float, float, float]) -> HandLandmarks:
    hand = _load_hand(name)
    ox, oy, oz = offset
    points = [(x + ox, y + oy, z + oz) for x, y, z in hand.points]
    return HandLandmarks(handedness=hand.handedness, score=hand.score, points=points)


# ---------- pure math: openness ----------
# hand_open.json: fingertips (4,8,12,16,20) at distances (.25,.25,.15,.25,.25)
# from the wrist -> mean spread .23, size (middle tip) .15 -> .23/(.15*1.1) > 1 -> clipped to 1.0
# hand_fist.json: same middle tip .15, other tips at .05 -> mean spread .07 -> .07/.165 ~= .424


def test_openness_open_hand_is_fully_open() -> None:
    assert _hand_openness(_load_hand("hand_open")) == pytest.approx(1.0)


def test_openness_fist_is_partially_closed() -> None:
    assert _hand_openness(_load_hand("hand_fist")) == pytest.approx(0.4242, abs=1e-3)


def test_openness_fist_scores_lower_than_open_hand() -> None:
    assert _hand_openness(_load_hand("hand_fist")) < _hand_openness(_load_hand("hand_open"))


# ---------- pure math: pointing ----------
# hand_point.json: index tip far from wrist (2x the other fingertips) and
# extended up+forward relative to its own PIP joint -> isolated clips to 2.0,
# up = 0.8, forward = 0.6 -> pointing_up = 1.6, pointing_forward = 1.2


def test_pointing_up_and_forward_scores() -> None:
    up, fwd = _pointing_scores(_load_hand("hand_point"))
    assert up == pytest.approx(1.6, abs=1e-3)
    assert fwd == pytest.approx(1.2, abs=1e-3)


def test_neutral_hand_does_not_register_as_pointing() -> None:
    up, fwd = _pointing_scores(_load_hand("hand_neutral"))
    assert up == pytest.approx(0.0, abs=1e-6)
    assert fwd == pytest.approx(0.0, abs=1e-6)


# ---------- pure math: circle fit ----------


def test_circle_fit_scores_a_true_circle_highly() -> None:
    angles = np.linspace(0, 2 * math.pi, 24, endpoint=False)
    xy = np.stack([0.3 + 0.15 * np.cos(angles), 0.3 + 0.15 * np.sin(angles)], axis=1)
    assert _circle_fit_score(xy) > 0.8


def test_circle_fit_rejects_a_straight_line() -> None:
    xy = np.stack([np.linspace(0, 0.3, 24), np.full(24, 0.2)], axis=1)
    assert _circle_fit_score(xy) < 0.3


def test_circle_fit_rejects_too_few_points() -> None:
    xy = np.array([[0.0, 0.0], [0.1, 0.1]])
    assert _circle_fit_score(xy) == 0.0


def test_circle_fit_rejects_tiny_radius_as_noise() -> None:
    angles = np.linspace(0, 2 * math.pi, 24, endpoint=False)
    xy = np.stack([0.01 * np.cos(angles), 0.01 * np.sin(angles)], axis=1)
    assert _circle_fit_score(xy) == 0.0


# ---------- pure math: spectral smoothness ----------


def test_smoothness_is_max_for_constant_speed() -> None:
    speeds = np.full(10, 0.2)
    assert _spectral_smoothness(speeds) == pytest.approx(1.0)


def test_smoothness_drops_for_jerky_motion() -> None:
    speeds = np.array([0.0, 0.5, 0.0, 0.5, 0.0, 0.5, 0.0, 0.5])
    assert _spectral_smoothness(speeds) < 0.5


# ---------- temporal features via FeatureExtractor ----------


def test_circular_wrist_motion_yields_high_circularity() -> None:
    extractor = FeatureExtractor(window_s=2.0)
    fv = None
    n = 30
    for i in range(n):
        t = 2 * math.pi * i / n
        ts = i * (1.8 / n)
        hand = _translated_hand(
            "hand_neutral", (0.3 + 0.15 * math.cos(t), 0.3 + 0.15 * math.sin(t), 0.0)
        )
        fv = extractor.update(LandmarkFrame(ts=ts, hands=[hand]))
    assert fv is not None
    assert fv.circularity > 0.5


def test_stationary_wrist_yields_high_stillness_and_low_circularity() -> None:
    extractor = FeatureExtractor(window_s=2.0)
    fv = None
    for i in range(20):
        hand = _translated_hand("hand_neutral", (0.3, 0.3, 0.0))
        fv = extractor.update(LandmarkFrame(ts=i * 0.1, hands=[hand]))
    assert fv is not None
    assert fv.stillness > 0.8
    assert fv.circularity < 0.2


def test_separating_hands_yield_positive_expansion_rate() -> None:
    extractor = FeatureExtractor(window_s=2.0)
    fv = None
    for i in range(10):
        sep = 0.1 + i * 0.05
        left = _translated_hand("hand_neutral", (-sep / 2, 0.0, 0.0))
        right = _translated_hand("hand_neutral", (sep / 2, 0.0, 0.0))
        fv = extractor.update(LandmarkFrame(ts=i * 0.1, hands=[left, right]))
    assert fv is not None
    assert fv.expansion_rate > 0


def test_no_hands_visible_still_returns_a_feature_vector() -> None:
    extractor = FeatureExtractor()
    fv = extractor.update(LandmarkFrame(ts=0.0, hands=[]))
    assert fv.hands_visible == 0
    assert fv.openness == 0.0


# ---------- PrototypeSegmenter ----------


def _fv(ts: float, **kw) -> GestureFeatureVector:
    return GestureFeatureVector(ts=ts, hands_visible=1, **kw)


def test_sustained_stillness_emits_hold_still_segment() -> None:
    seg = PrototypeSegmenter()
    result = None
    # HOLD_STILL requires ~2s of dominance (hold_still_duration_s default)
    for i in range(25):
        result = seg.update(_fv(ts=i * 0.1, stillness=0.95, tempo=0.02)) or result
    # a change of feature vector state flushes the held segment
    result = (
        seg.update(_fv(ts=2.6, stillness=0.0, tempo=0.9, expansion_rate=0.5, separation=1.2))
        or result
    )
    assert result is not None
    assert result.primitive == MotionPrimitive.HOLD_STILL


def test_ambiguous_features_never_reach_min_score() -> None:
    seg = PrototypeSegmenter()
    for i in range(10):
        result = seg.update(_fv(ts=i * 0.1, stillness=0.4, tempo=0.4))
        assert result is None


def test_hands_leaving_frame_flushes_pending_segment() -> None:
    seg = PrototypeSegmenter(min_duration_s=0.05)
    seg.update(_fv(ts=0.0, expansion_rate=0.5, tempo=0.4, separation=1.2))
    result = seg.update(GestureFeatureVector(ts=0.2, hands_visible=0))
    assert result is not None
    assert result.primitive == MotionPrimitive.EXPAND
