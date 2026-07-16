"""Geometric shape classification for finished air-draw strokes.

Fixtures are hand-constructed point paths (circle/line/zigzag/freeform),
mirroring the synthetic-fixture style used for gesture feature math in
test_gestures.py.
"""

from __future__ import annotations

import math

from backend.gestures.schema import StrokePoint
from backend.gestures.shape import _position_label, classify_shape


def _circle_points(
    n: int = 24, cx: float = 0.5, cy: float = 0.5, r: float = 0.15
) -> list[StrokePoint]:
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        pts.append(StrokePoint(ts=i * 0.05, x=cx + r * math.cos(t), y=cy + r * math.sin(t)))
    return pts


def _line_points(n: int = 20) -> list[StrokePoint]:
    return [StrokePoint(ts=i * 0.05, x=0.2 + i * (0.6 / n), y=0.2) for i in range(n)]


def _zigzag_points() -> list[StrokePoint]:
    # A sharp "W" — large lateral swings per step force high direction-reversal
    # count and a path length well beyond the bounding-box diagonal.
    xs = [0.1 * i for i in range(8)]
    ys = [0.3, 0.0, 0.3, 0.0, 0.3, 0.0, 0.3, 0.0]
    return [StrokePoint(ts=i * 0.05, x=x, y=y) for i, (x, y) in enumerate(zip(xs, ys, strict=True))]


def _freeform_points() -> list[StrokePoint]:
    # An L-shaped path: not circular, not a single straight line, no zigzag reversals.
    xs = [0.2, 0.25, 0.3, 0.35, 0.4, 0.4, 0.4, 0.4, 0.4]
    ys = [0.2, 0.2, 0.2, 0.2, 0.2, 0.3, 0.4, 0.5, 0.6]
    return [StrokePoint(ts=i * 0.05, x=x, y=y) for i, (x, y) in enumerate(zip(xs, ys, strict=True))]


def test_too_few_points_returns_none() -> None:
    assert classify_shape(_circle_points(n=3), shoulder_w=0.35) is None


def test_circle_is_classified_as_circle() -> None:
    shape = classify_shape(_circle_points(), shoulder_w=0.35)
    assert shape is not None
    assert shape.shape == "circle"
    assert shape.confidence > 0.5


def test_straight_line_is_classified_as_line() -> None:
    shape = classify_shape(_line_points(), shoulder_w=0.35)
    assert shape is not None
    assert shape.shape == "line"


def test_zigzag_is_classified_as_zigzag() -> None:
    shape = classify_shape(_zigzag_points(), shoulder_w=0.35)
    assert shape is not None
    assert shape.shape == "zigzag"


def test_ambiguous_path_falls_back_to_freeform() -> None:
    shape = classify_shape(_freeform_points(), shoulder_w=0.35)
    assert shape is not None
    assert shape.shape == "freeform"
    assert shape.confidence == 0.4


def test_bbox_size_scales_inversely_with_shoulder_width() -> None:
    narrow = classify_shape(_circle_points(), shoulder_w=0.2)
    wide = classify_shape(_circle_points(), shoulder_w=0.7)
    assert narrow is not None and wide is not None
    assert narrow.bbox_size > wide.bbox_size


def test_falsy_shoulder_width_falls_back_to_default() -> None:
    shape = classify_shape(_circle_points(), shoulder_w=0.0)
    reference = classify_shape(_circle_points(), shoulder_w=0.35)
    assert shape is not None and reference is not None
    assert shape.bbox_size == reference.bbox_size


def test_duration_reflects_first_and_last_point_timestamps() -> None:
    shape = classify_shape(_line_points(), shoulder_w=0.35)
    assert shape is not None
    assert shape.duration_s > 0


def test_position_label_grid() -> None:
    assert _position_label(0.05, 0.05) == "upper-left"
    assert _position_label(0.5, 0.5) == "center"
    assert _position_label(0.95, 0.95) == "lower-right"
