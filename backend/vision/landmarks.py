"""Landmark extraction behind `LandmarkExtractor` so MediaPipe can be swapped
(e.g., browser-side landmarks, RTMPose) without touching downstream stages."""
from __future__ import annotations

import math
from abc import ABC, abstractmethod

import numpy as np

from backend.core.config import VisionConfig
from backend.vision.schema import FaceSignals, HandLandmarks, LandmarkFrame, PoseLandmarks


class LandmarkExtractor(ABC):
    @abstractmethod
    def extract(self, ts: float, frame_bgr: np.ndarray) -> LandmarkFrame: ...

    @abstractmethod
    def close(self) -> None: ...


class MediaPipeExtractor(LandmarkExtractor):
    """Uses MediaPipe legacy Solutions API — models ship with the wheel, no downloads."""

    def __init__(self, cfg: VisionConfig) -> None:
        import cv2
        import mediapipe as mp

        self._cv2 = cv2
        self._mp = mp
        self._draw = mp.solutions.drawing_utils
        self._styles = mp.solutions.drawing_styles
        # Raw MediaPipe results from the most recent extract(), kept only so the
        # overlay renderer can draw dots + connection lines onto the live frame.
        self._last_hands = None
        self._last_pose = None
        self._last_face = None
        self._hands = (
            mp.solutions.hands.Hands(max_num_hands=2, model_complexity=0,
                                     min_detection_confidence=0.5, min_tracking_confidence=0.5)
            if cfg.hands else None
        )
        self._pose = (
            mp.solutions.pose.Pose(model_complexity=0, min_detection_confidence=0.5)
            if cfg.pose else None
        )
        self._face = (
            mp.solutions.face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=False,
                                            min_detection_confidence=0.5)
            if cfg.face else None
        )

    def extract(self, ts: float, frame_bgr: np.ndarray) -> LandmarkFrame:
        rgb = self._cv2.cvtColor(frame_bgr, self._cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        out = LandmarkFrame(ts=ts)

        self._last_hands = self._last_pose = self._last_face = None

        if self._hands:
            res = self._hands.process(rgb)
            self._last_hands = res
            if res.multi_hand_landmarks:
                for lm, handed in zip(res.multi_hand_landmarks,
                                      res.multi_handedness, strict=False):
                    out.hands.append(HandLandmarks(
                        handedness=handed.classification[0].label,
                        points=[(p.x, p.y, p.z) for p in lm.landmark],
                        score=handed.classification[0].score,
                    ))
        if self._pose:
            res = self._pose.process(rgb)
            self._last_pose = res
            if res.pose_landmarks:
                out.pose = PoseLandmarks(
                    points=[(p.x, p.y, p.z) for p in res.pose_landmarks.landmark], score=1.0)
        if self._face:
            res = self._face.process(rgb)
            self._last_face = res
            if res.multi_face_landmarks:
                out.face = _face_signals(res.multi_face_landmarks[0])
        return out

    def annotate(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Return a copy of the frame with the latest landmarks drawn as dots + lines."""
        mp = self._mp
        frame = frame_bgr.copy()
        if self._last_face and self._last_face.multi_face_landmarks:
            for mesh in self._last_face.multi_face_landmarks:
                self._draw.draw_landmarks(
                    frame, mesh, mp.solutions.face_mesh.FACEMESH_CONTOURS,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=self._styles.get_default_face_mesh_contours_style())
        if self._last_pose and self._last_pose.pose_landmarks:
            self._draw.draw_landmarks(
                frame, self._last_pose.pose_landmarks, mp.solutions.pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self._styles.get_default_pose_landmarks_style())
        if self._last_hands and self._last_hands.multi_hand_landmarks:
            for hand in self._last_hands.multi_hand_landmarks:
                self._draw.draw_landmarks(
                    frame, hand, mp.solutions.hands.HAND_CONNECTIONS,
                    self._styles.get_default_hand_landmarks_style(),
                    self._styles.get_default_hand_connections_style())
        return frame

    def close(self) -> None:
        for sol in (self._hands, self._pose, self._face):
            if sol:
                sol.close()


def _face_signals(mesh) -> FaceSignals:  # noqa: ANN001 — mediapipe proto type
    """Cheap geometric affect proxies from face-mesh landmarks."""
    p = mesh.landmark

    def d(a: int, b: int) -> float:
        return math.hypot(p[a].x - p[b].x, p[a].y - p[b].y)

    face_h = d(10, 152) or 1e-6
    mouth_w = d(61, 291) / face_h
    mouth_open = d(13, 14) / face_h
    corner_lift = ((p[13].y - p[61].y) + (p[13].y - p[291].y)) / 2 / face_h
    brow_raise = (d(105, 159) + d(334, 386)) / 2 / face_h

    valence = max(-1.0, min(1.0, corner_lift * 40 + (mouth_w - 0.38) * 3))
    arousal = max(0.0, min(1.0, brow_raise * 12 + mouth_open * 4 - 0.35))

    dx = p[454].x - p[234].x
    yaw = math.degrees(math.atan2(p[454].z - p[234].z, dx if abs(dx) > 1e-6 else 1e-6))
    pitch = math.degrees(math.atan2(p[152].z - p[10].z, d(10, 152)))
    return FaceSignals(valence=valence, arousal=arousal, yaw=yaw, pitch=pitch)
