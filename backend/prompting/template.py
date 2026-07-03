"""Deterministic template strategy — zero dependencies, always available.

Orders content by diffusion-model prompt conventions: subject → environment →
lighting/mood → camera → style → quality tags. Confidence gates inclusion.
"""
from __future__ import annotations

from backend.prompting.base import OptimizedPrompt, PromptGenerator
from backend.scene.schema import SceneGraph

_ORDER = ("environment", "weather", "time_of_day", "lighting", "mood", "motion",
          "scale", "color_palette", "visual_effects", "camera_angle", "camera_distance")
_QUALITY = "highly detailed, sharp focus, professional composition, 8k"


class TemplatePromptGenerator(PromptGenerator):
    name = "template"

    async def generate(self, graph: SceneGraph) -> OptimizedPrompt:
        parts: list[str] = []
        for obj in sorted(graph.objects.values(), key=lambda o: -o.salience):
            desc = [a.value for a in obj.attributes.values() if a.confidence >= 0.3]
            noun = {"celestial": "a luminous celestial body", "airborne": "a flying subject",
                    "subject": "a striking central subject"}.get(obj.category, f"a {obj.category}")
            parts.append(f"{noun}, {', '.join(desc)}" if desc else noun)

        for key in _ORDER:
            attr = graph.globals.get(key)
            if attr and attr.confidence >= 0.3:
                parts.append(attr.value)

        style = graph.globals.get("artistic_style")
        parts.append(style.value if style and style.confidence >= 0.3
                     else "cinematic digital painting")
        parts.append(_QUALITY)
        return OptimizedPrompt(positive=", ".join(parts), generator=self.name)
