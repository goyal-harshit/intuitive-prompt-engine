"""Runtime models for the gesture layer."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class MotionPrimitive(str, Enum):
    EXPAND = "expand"
    CONTRACT = "contract"
    RAISE = "raise"
    LOWER = "lower"
    POINT_UP = "point_up"
    POINT_FORWARD = "point_forward"
    CIRCLE_OVERHEAD = "circle_overhead"
    CIRCLE_FRONTAL = "circle_frontal"
    SWEEP_HORIZONTAL = "sweep_horizontal"
    PUSH_AWAY = "push_away"
    PULL_IN = "pull_in"
    FRAME_RECT = "frame_rect"
    HOLD_STILL = "hold_still"
    WAVE = "wave"


class GestureFeatureVector(BaseModel):
    ts: float
    hands_visible: int = 0
    openness: float = 0.0
    pinch: float = 1.0  # thumb-index distance, normalized; ~0 = pinched, 1+ = open
    separation: float = 0.0
    expansion_rate: float = 0.0
    verticality: float = 0.0
    vertical_velocity: float = 0.0
    pointing_up: float = 0.0  # 0..1 index-extended-upward score
    pointing_forward: float = 0.0
    circularity: float = 0.0
    circle_overhead: float = 0.0  # circularity gated by hand height
    horizontal_travel: float = 0.0
    depth_velocity: float = 0.0  # + toward camera, − away
    tempo: float = 0.0
    smoothness: float = 0.0
    symmetry: float = 0.0
    posture_lean: float = 0.0
    head_yaw: float = 0.0
    head_pitch: float = 0.0
    valence: float = 0.0
    arousal: float = 0.0
    stillness: float = 0.0


class SequenceSegment(BaseModel):
    id: str
    primitive: MotionPrimitive
    t_start: float
    t_end: float
    confidence: float
    params: dict[str, float | str] = {}


class StrokePoint(BaseModel):
    ts: float
    x: float  # normalized 0..1 image space
    y: float


class DrawnShape(BaseModel):
    id: str
    shape: str  # "circle" | "line" | "zigzag" | "freeform"
    points: list[StrokePoint]
    bbox_center: tuple[float, float]
    bbox_size: float  # bbox diagonal, relative to shoulder width
    position_label: str  # e.g. "upper-left" .. "center" .. "lower-right"
    duration_s: float
    confidence: float
