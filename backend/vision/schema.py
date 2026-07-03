"""Runtime models for the vision layer."""
from __future__ import annotations

from pydantic import BaseModel

Point3 = tuple[float, float, float]


class HandLandmarks(BaseModel):
    handedness: str  # "Left" | "Right"
    points: list[Point3]  # 21 normalized landmarks
    score: float


class PoseLandmarks(BaseModel):
    points: list[Point3]  # 33 normalized landmarks
    score: float


class FaceSignals(BaseModel):
    """Compact affect signals derived from face mesh; raw mesh never leaves vision layer."""

    valence: float = 0.0  # −1..1 smile vs frown
    arousal: float = 0.0  # 0..1 brow raise / eye widening
    yaw: float = 0.0  # degrees
    pitch: float = 0.0


class LandmarkFrame(BaseModel):
    ts: float
    hands: list[HandLandmarks] = []
    pose: PoseLandmarks | None = None
    face: FaceSignals | None = None
