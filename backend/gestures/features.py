"""Continuous semantic feature extraction from landmark streams.

Stateless per-frame geometry + stateful temporal derivatives over a sliding
window. Pure math, no ML, fully unit-testable with synthetic landmarks.
"""

from __future__ import annotations

import math
from collections import deque

import numpy as np

from backend.gestures.filters import EMAVec3Filter
from backend.gestures.schema import GestureFeatureVector
from backend.vision.schema import HandLandmarks, LandmarkFrame

WRIST, INDEX_TIP, INDEX_PIP, MIDDLE_TIP, THUMB_TIP, PINKY_TIP = 0, 8, 6, 12, 4, 20
FINGERTIPS = (4, 8, 12, 16, 20)
L_SHOULDER, R_SHOULDER, L_HIP, R_HIP, NOSE = 11, 12, 23, 24, 0


def _hand_openness(hand: HandLandmarks) -> float:
    pts = np.asarray(hand.points)
    palm = pts[WRIST]
    size = np.linalg.norm(pts[MIDDLE_TIP] - palm) or 1e-6
    spread = float(np.mean([np.linalg.norm(pts[t] - palm) for t in FINGERTIPS]))
    return float(np.clip(spread / (size * 1.1), 0.0, 1.0))


def _pinch_distance(hand: HandLandmarks) -> float:
    """0 = fingertips touching (pinched), larger = fingers apart. Scale-invariant."""
    pts = np.asarray(hand.points)
    palm = pts[WRIST]
    size = np.linalg.norm(pts[MIDDLE_TIP] - palm) or 1e-6
    return float(np.linalg.norm(pts[THUMB_TIP] - pts[INDEX_TIP]) / size)


def _pointing_scores(hand: HandLandmarks) -> tuple[float, float]:
    pts = np.asarray(hand.points)
    index_ext = np.linalg.norm(pts[INDEX_TIP] - pts[WRIST])
    others = np.mean([np.linalg.norm(pts[t] - pts[WRIST]) for t in (12, 16, 20)])
    isolated = float(np.clip((index_ext / (others + 1e-6)) - 1.0, 0.0, 1.0) * 2)
    v = pts[INDEX_TIP] - pts[INDEX_PIP]
    n = np.linalg.norm(v) or 1e-6
    up = max(0.0, float(-v[1] / n))  # image y is downward
    fwd = max(0.0, float(-v[2] / n))  # z toward camera is negative in MediaPipe
    return isolated * up, isolated * fwd


def _circle_fit_score(xy: np.ndarray) -> float:
    """1.0 = perfect circle of meaningful radius, 0 = not circular."""
    if len(xy) < 8:
        return 0.0
    c = xy.mean(axis=0)
    r = np.linalg.norm(xy - c, axis=1)
    mean_r = float(r.mean())
    if mean_r < 0.04:  # too small to be deliberate
        return 0.0
    residual = float(r.std()) / (mean_r + 1e-6)
    angles = np.unwrap(np.arctan2(*(xy - c).T[::-1]))
    coverage = min(1.0, abs(angles[-1] - angles[0]) / (2 * math.pi))
    return float(np.clip((1.0 - residual * 2.5), 0, 1) * coverage)


def _spectral_smoothness(speeds: np.ndarray) -> float:
    if len(speeds) < 4:
        return 1.0
    jerk = np.diff(speeds)
    return float(np.clip(1.0 - np.abs(jerk).mean() * 20, 0.0, 1.0))


class FeatureExtractor:
    """Consumes LandmarkFrames, emits GestureFeatureVectors (~ input rate)."""

    def __init__(self, window_s: float = 2.0, smoothing_alpha: float = 0.35) -> None:
        self._window_s = window_s
        self._hist: deque[tuple[float, dict[str, float]]] = deque()
        self._wrist_hist: deque[tuple[float, float, float, float]] = (
            deque()
        )  # ts,x,y,z (primary hand)
        self._wrist_filter = EMAVec3Filter(smoothing_alpha)
        self.last_shoulder_w = 0.35

    def update(self, frame: LandmarkFrame) -> GestureFeatureVector:
        f = GestureFeatureVector(ts=frame.ts, hands_visible=len(frame.hands))
        shoulder_w, shoulder_y = 0.35, 0.5
        if frame.pose and len(frame.pose.points) > R_HIP:
            pp = np.asarray(frame.pose.points)
            shoulder_w = float(np.linalg.norm(pp[L_SHOULDER][:2] - pp[R_SHOULDER][:2])) or 0.35
            shoulder_y = float((pp[L_SHOULDER][1] + pp[R_SHOULDER][1]) / 2)
            hip_z = (pp[L_HIP][2] + pp[R_HIP][2]) / 2
            sho_z = (pp[L_SHOULDER][2] + pp[R_SHOULDER][2]) / 2
            f.posture_lean = float(np.clip((hip_z - sho_z) * 5, -1, 1))
        self.last_shoulder_w = shoulder_w

        if frame.hands:
            f.openness = float(np.mean([_hand_openness(h) for h in frame.hands]))
            f.pinch = min(_pinch_distance(h) for h in frame.hands)
            scores = [_pointing_scores(h) for h in frame.hands]
            f.pointing_up = max(s[0] for s in scores)
            f.pointing_forward = max(s[1] for s in scores)
            wrists = np.asarray([h.points[WRIST] for h in frame.hands])
            f.verticality = float(np.clip((shoulder_y - wrists[:, 1].mean()) / 0.4, -1, 1))
            if len(frame.hands) == 2:
                f.separation = float(np.linalg.norm(wrists[0][:2] - wrists[1][:2]) / shoulder_w)
            w = wrists[0]
            fx, fy, fz = self._wrist_filter.update(float(w[0]), float(w[1]), float(w[2]))
            self._wrist_hist.append((frame.ts, fx, fy, fz))

        if frame.face:
            f.valence, f.arousal = frame.face.valence, frame.face.arousal
            f.head_yaw, f.head_pitch = frame.face.yaw, frame.face.pitch

        self._prune(frame.ts)
        self._temporal(f)
        self._hist.append((frame.ts, {"sep": f.separation, "vert": f.verticality}))
        return f

    def _prune(self, now: float) -> None:
        for dq in (self._hist, self._wrist_hist):
            while dq and now - dq[0][0] > self._window_s:
                dq.popleft()

    def _temporal(self, f: GestureFeatureVector) -> None:
        if len(self._hist) >= 2:
            t0, first = self._hist[0]
            dt = f.ts - t0 or 1e-6
            f.expansion_rate = (f.separation - first["sep"]) / dt
            f.vertical_velocity = (f.verticality - first["vert"]) / dt

        if len(self._wrist_hist) >= 4:
            arr = np.asarray(self._wrist_hist)
            ts, xy, z = arr[:, 0], arr[:, 1:3], arr[:, 3]
            d = np.linalg.norm(np.diff(xy, axis=0), axis=1)
            dts = np.diff(ts) + 1e-6
            speeds = d / dts
            f.tempo = float(np.clip(speeds.mean() * 2.5, 0, 1))
            f.stillness = float(np.clip(1.0 - speeds.mean() * 8, 0, 1))
            f.smoothness = _spectral_smoothness(speeds)
            f.circularity = _circle_fit_score(xy)
            f.circle_overhead = f.circularity * max(0.0, f.verticality)
            f.horizontal_travel = float(np.clip(np.ptp(xy[:, 0]) * 2, 0, 1))
            f.depth_velocity = float(np.clip(-(z[-1] - z[0]) / (ts[-1] - ts[0] + 1e-6) * 5, -1, 1))

        if len(self._hist) >= 4:  # bimanual symmetry via separation stability under motion
            seps = np.asarray([h["sep"] for _, h in self._hist])
            if seps.max() > 0:
                f.symmetry = float(np.clip(1.0 - seps.std() / (seps.mean() + 1e-6), 0, 1) * f.tempo)
