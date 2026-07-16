"""Geometric shape classification for finished air-draw strokes.

No ML — pure geometry, mirroring the circle-fit approach already used for the
`circularity` temporal feature. Scoped to 4 classes (circle/line/zigzag/
freeform); rectangle/arrow are deliberately deferred — they need real corner/
polygon detection, which is meaningfully more fragile for a stroke drawn in
the air with no surface to brace against.
"""

from __future__ import annotations

import math
import uuid

import numpy as np

from backend.gestures.schema import DrawnShape, StrokePoint

_GRID_LABELS = [
    ["upper-left", "upper-center", "upper-right"],
    ["middle-left", "center", "middle-right"],
    ["lower-left", "lower-center", "lower-right"],
]


def _position_label(cx: float, cy: float) -> str:
    col = min(2, max(0, int(cx * 3)))
    row = min(2, max(0, int(cy * 3)))
    return _GRID_LABELS[row][col]


def _circle_score(xy: np.ndarray) -> float:
    if len(xy) < 8:
        return 0.0
    c = xy.mean(axis=0)
    r = np.linalg.norm(xy - c, axis=1)
    mean_r = float(r.mean())
    if mean_r < 1e-4:
        return 0.0
    residual = float(r.std()) / (mean_r + 1e-6)
    angles = np.unwrap(np.arctan2(*(xy - c).T[::-1]))
    coverage = min(1.0, abs(float(angles[-1] - angles[0])) / (2 * math.pi))
    return float(np.clip(1.0 - residual * 2.5, 0, 1) * coverage)


def _eigen_ratio(xy: np.ndarray) -> float:
    if len(xy) < 3:
        return 1.0
    centered = xy - xy.mean(axis=0)
    cov = np.cov(centered.T)
    eigvals = np.clip(np.linalg.eigvalsh(cov), 1e-12, None)
    return float(eigvals.min() / eigvals.max())


def _path_length(xy: np.ndarray) -> float:
    if len(xy) < 2:
        return 0.0
    return float(np.linalg.norm(np.diff(xy, axis=0), axis=1).sum())


def _direction_reversals(xy: np.ndarray) -> int:
    if len(xy) < 4:
        return 0
    diffs = np.diff(xy, axis=0)
    norms = np.linalg.norm(diffs, axis=1)
    mask = norms > 1e-6
    if mask.sum() < 3:
        return 0
    headings = np.arctan2(diffs[mask, 1], diffs[mask, 0])
    dtheta = np.diff(np.unwrap(headings))
    return int(np.sum(np.abs(dtheta) > math.radians(80)))


def classify_shape(points: list[StrokePoint], shoulder_w: float) -> DrawnShape | None:
    """Classify a finished stroke. Returns None only if there aren't enough
    points to say anything meaningful — otherwise always resolves to a shape
    (falling back to "freeform"), matching this v1's approximate-by-design scope.
    """
    if len(points) < 6:
        return None

    xy = np.asarray([(p.x, p.y) for p in points])
    x_min, y_min = xy.min(axis=0)
    x_max, y_max = xy.max(axis=0)
    bbox_diag = math.hypot(x_max - x_min, y_max - y_min)
    center = (float((x_min + x_max) / 2), float((y_min + y_max) / 2))

    circle_score = _circle_score(xy)
    eigen_ratio = _eigen_ratio(xy)
    path_len = _path_length(xy)
    endpoint_dist = float(np.linalg.norm(xy[-1] - xy[0]))
    path_ratio = path_len / (endpoint_dist + 1e-6)
    reversals = _direction_reversals(xy)

    shape, confidence = "freeform", 0.4
    if circle_score > 0.6:
        shape, confidence = "circle", circle_score
    elif eigen_ratio < 0.15 and path_ratio < 1.3:
        shape, confidence = "line", float(np.clip(1.0 - eigen_ratio, 0, 1))
    elif reversals >= 3 and path_len > bbox_diag * 2.0:
        shape, confidence = "zigzag", float(np.clip(reversals / 8.0, 0.4, 1.0))

    return DrawnShape(
        id=f"shp_{uuid.uuid4().hex[:8]}",
        shape=shape,
        points=points,
        bbox_center=center,
        bbox_size=float(bbox_diag / (shoulder_w or 0.35)),
        position_label=_position_label(*center),
        duration_s=float(points[-1].ts - points[0].ts),
        confidence=round(float(confidence), 3),
    )
