"""Declarative evidence ontology: motion primitive → scene-attribute hypotheses.

Pure data. The engine applies context modifiers on top. Phase 5 externalizes
this to YAML packs; keeping it declarative here makes that a file move.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from backend.gestures.schema import MotionPrimitive as P


@dataclass(frozen=True)
class Hypothesis:
    target: str  # "global" | "new_object" | "focus_object"
    attribute: str
    value: str
    weight: float
    category: str | None = None  # object category when target == new_object
    conditions: dict[str, tuple[float, float]] = field(default_factory=dict)  # feature: (lo, hi)


ONTOLOGY: dict[P, list[Hypothesis]] = {
    P.EXPAND: [
        Hypothesis("global", "scale", "grand, monumental scale", 0.6),
        Hypothesis("global", "camera_distance", "wide shot", 0.5),
        Hypothesis("global", "environment", "vast panoramic landscape", 0.4,
                   conditions={"tempo": (0.0, 0.45)}),
        Hypothesis("global", "visual_effects", "bursting energy, particles", 0.3,
                   conditions={"tempo": (0.65, 1.0)}),
    ],
    P.CONTRACT: [
        Hypothesis("global", "camera_distance", "intimate close-up", 0.6),
        Hypothesis("global", "scale", "small, detailed scale", 0.4),
    ],
    P.RAISE: [
        Hypothesis("new_object", "motion", "soaring upward", 0.5, category="airborne"),
        Hypothesis("global", "camera_angle", "low angle looking up", 0.3),
    ],
    P.LOWER: [
        Hypothesis("global", "camera_angle", "high angle, bird's eye", 0.4),
        Hypothesis("global", "mood", "grounded, heavy", 0.25),
    ],
    P.POINT_UP: [
        Hypothesis("new_object", "position", "high in the sky", 0.5, category="airborne"),
        Hypothesis("new_object", "motion", "flying", 0.5, category="airborne"),
    ],
    P.POINT_FORWARD: [
        Hypothesis("focus_object", "salience", "emphasized focal subject", 0.5),
        Hypothesis("global", "camera_distance", "medium shot on subject", 0.3),
    ],
    P.CIRCLE_OVERHEAD: [
        Hypothesis("new_object", "shape", "glowing orb", 0.5, category="celestial"),
        Hypothesis("global", "time_of_day", "night", 0.3),
        Hypothesis("global", "lighting", "moonlit, celestial glow", 0.3),
    ],
    P.CIRCLE_FRONTAL: [
        Hypothesis("new_object", "shape", "round, orbiting form", 0.4, category="object"),
        Hypothesis("global", "motion", "orbital, swirling motion", 0.3),
    ],
    P.SWEEP_HORIZONTAL: [
        Hypothesis("global", "environment", "sweeping open landscape", 0.6),
        Hypothesis("global", "camera_distance", "panoramic vista", 0.5),
    ],
    P.PUSH_AWAY: [
        Hypothesis("focus_object", "position", "receding into the distance", 0.5),
        Hypothesis("global", "camera_distance", "distant framing", 0.3),
    ],
    P.PULL_IN: [
        Hypothesis("focus_object", "salience", "drawn close, dominant in frame", 0.5),
        Hypothesis("global", "camera_distance", "close-up", 0.4),
    ],
    P.FRAME_RECT: [
        Hypothesis("global", "camera_angle", "deliberately framed, cinematic composition", 0.7),
    ],
    P.HOLD_STILL: [
        Hypothesis("global", "_commit", "commit", 0.8),
    ],
    P.WAVE: [
        Hypothesis("global", "motion", "windswept, dynamic movement", 0.4),
        Hypothesis("global", "weather", "breezy", 0.25),
    ],
}

# Sustained affect/tempo → ambient hypotheses (checked against smoothed features)
AMBIENT_RULES: list[tuple[str, tuple[float, float], Hypothesis]] = [
    ("tempo", (0.6, 1.0), Hypothesis("global", "mood", "energetic, dramatic", 0.4)),
    ("tempo", (0.0, 0.2), Hypothesis("global", "mood", "calm, serene", 0.35)),
    ("smoothness", (0.75, 1.0), Hypothesis("global", "lighting", "soft diffuse light", 0.25)),
    ("valence", (0.4, 1.0), Hypothesis("global", "color_palette", "warm vibrant palette", 0.35)),
    ("valence", (-1.0, -0.4), Hypothesis("global", "lighting", "moody chiaroscuro", 0.4)),
    ("valence", (-1.0, -0.4), Hypothesis("global", "color_palette", "desaturated cold palette", 0.3)),
    ("head_pitch", (12.0, 90.0), Hypothesis("global", "environment", "expansive sky above", 0.25)),
    ("arousal", (0.6, 1.0), Hypothesis("global", "visual_effects", "dramatic atmosphere", 0.25)),
]
