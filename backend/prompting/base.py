"""Prompt generation strategy interface."""
from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel

from backend.scene.schema import SceneGraph


class OptimizedPrompt(BaseModel):
    positive: str
    negative: str = "blurry, low quality, distorted, watermark, text, deformed"
    guidance: float = 7.0
    steps: int = 30
    aspect_ratio: str = "4:3"
    seed: int | None = None
    model_hint: str = "sdxl"
    generator: str = "template"


class PromptGenerator(ABC):
    name: str = "base"

    @abstractmethod
    async def generate(self, graph: SceneGraph) -> OptimizedPrompt: ...


def graph_to_description(graph: SceneGraph, min_confidence: float = 0.3) -> str:
    """Deterministic natural-language rendering of the graph — shared by all strategies."""
    parts: list[str] = []
    for obj in sorted(graph.objects.values(), key=lambda o: -o.salience):
        attrs = ", ".join(a.value for a in obj.attributes.values() if a.confidence >= min_confidence)
        parts.append(f"a {obj.category}" + (f" ({attrs})" if attrs else ""))
    for key, a in graph.globals.items():
        if a.confidence >= min_confidence:
            parts.append(f"{key.replace('_', ' ')}: {a.value}")
    return "; ".join(parts) if parts else "an abstract scene taking shape"
