"""Scene Graph data models."""

from __future__ import annotations

import time

from pydantic import BaseModel, Field

GLOBAL_KEYS = (
    "environment",
    "mood",
    "lighting",
    "weather",
    "camera_angle",
    "camera_distance",
    "artistic_style",
    "motion",
    "scale",
    "time_of_day",
    "color_palette",
    "visual_effects",
)


class AttributeValue(BaseModel):
    value: str
    confidence: float
    updated_at: float = Field(default_factory=time.time)
    provenance: list[str] = []


class SceneObject(BaseModel):
    id: str
    category: str
    attributes: dict[str, AttributeValue] = {}
    salience: float = 0.5


class SceneEvent(BaseModel):
    ts: float
    kind: str  # merged | conflict_won | conflict_lost | object_created | decayed
    detail: str


class SceneMeta(BaseModel):
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    revision: int = 0
    completeness: float = 0.0


class SceneGraph(BaseModel):
    objects: dict[str, SceneObject] = {}
    globals: dict[str, AttributeValue] = {}
    history: list[SceneEvent] = []
    meta: SceneMeta = Field(default_factory=SceneMeta)
