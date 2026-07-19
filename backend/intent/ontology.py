"""Declarative evidence ontology: motion primitive → scene-attribute hypotheses.

Pure data. The engine applies context modifiers on top. The tables below are
the built-in defaults; ``load_ontology_pack`` loads the same structure from a
YAML pack under ``plugins/`` so domain-specific ontologies (architecture,
character design, ...) can be swapped in without touching code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from backend.gestures.schema import MotionPrimitive as P

PLUGINS_DIR = Path(__file__).resolve().parents[2] / "plugins"


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
        Hypothesis(
            "global",
            "environment",
            "vast panoramic landscape",
            0.4,
            conditions={"tempo": (0.0, 0.45)},
        ),
        Hypothesis(
            "global",
            "visual_effects",
            "bursting energy, particles",
            0.3,
            conditions={"tempo": (0.65, 1.0)},
        ),
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

# Air-drawn stroke shape → scene-attribute hypotheses. Position/size are folded
# into the emitted value text at emission time (RuleBasedIntentModel.on_drawn_shape)
# since they're per-instance, not static like the rest of this table.
SHAPE_ONTOLOGY: dict[str, list[Hypothesis]] = {
    "circle": [
        Hypothesis("new_object", "shape", "round, orb-like form", 0.55, category="drawn_object"),
        Hypothesis("global", "composition", "centered circular motif", 0.3),
    ],
    "line": [
        Hypothesis("global", "composition", "strong directional line, horizon or edge", 0.45),
    ],
    "zigzag": [
        Hypothesis("global", "motion", "jagged, energetic linework", 0.4),
        Hypothesis("global", "visual_effects", "lightning-like or angular energy", 0.3),
    ],
    "freeform": [
        Hypothesis("new_object", "shape", "abstract sketched form", 0.3, category="drawn_object"),
    ],
}

# Sustained affect/tempo → ambient hypotheses (checked against smoothed features)
AMBIENT_RULES: list[tuple[str, tuple[float, float], Hypothesis]] = [
    ("tempo", (0.6, 1.0), Hypothesis("global", "mood", "energetic, dramatic", 0.4)),
    ("tempo", (0.0, 0.2), Hypothesis("global", "mood", "calm, serene", 0.35)),
    ("smoothness", (0.75, 1.0), Hypothesis("global", "lighting", "soft diffuse light", 0.25)),
    ("valence", (0.4, 1.0), Hypothesis("global", "color_palette", "warm vibrant palette", 0.35)),
    ("valence", (-1.0, -0.4), Hypothesis("global", "lighting", "moody chiaroscuro", 0.4)),
    (
        "valence",
        (-1.0, -0.4),
        Hypothesis("global", "color_palette", "desaturated cold palette", 0.3),
    ),
    ("head_pitch", (12.0, 90.0), Hypothesis("global", "environment", "expansive sky above", 0.25)),
    ("arousal", (0.6, 1.0), Hypothesis("global", "visual_effects", "dramatic atmosphere", 0.25)),
]


# ---------- YAML ontology packs ----------


@dataclass(frozen=True)
class OntologyPack:
    """One swappable rule set: everything RuleBasedIntentModel consults."""

    ontology: dict[P, list[Hypothesis]]
    shape_ontology: dict[str, list[Hypothesis]]
    ambient_rules: list[tuple[str, tuple[float, float], Hypothesis]]


BUILTIN_PACK = OntologyPack(ONTOLOGY, SHAPE_ONTOLOGY, AMBIENT_RULES)


def _parse_hypothesis(raw: dict, where: str) -> Hypothesis:
    try:
        conditions = {
            feature: (float(bounds[0]), float(bounds[1]))
            for feature, bounds in (raw.get("conditions") or {}).items()
        }
        return Hypothesis(
            target=raw["target"],
            attribute=raw["attribute"],
            value=raw["value"],
            weight=float(raw["weight"]),
            category=raw.get("category"),
            conditions=conditions,
        )
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise ValueError(f"ontology pack: malformed hypothesis in {where}: {exc!r}") from exc


def load_ontology_pack(pack: str | Path = "default") -> OntologyPack:
    """Load an ontology pack from ``plugins/<name>/ontology.yaml`` (or a path).

    The shipped ``default`` pack mirrors the built-in tables; if its file is
    missing (trimmed deployment artifact), the built-ins are used so the app
    always boots. A *custom* pack that can't be found is an explicit
    configuration error and raises.
    """
    path = Path(pack) if isinstance(pack, Path) else PLUGINS_DIR / pack / "ontology.yaml"
    if not path.exists():
        if pack == "default":
            return BUILTIN_PACK
        raise FileNotFoundError(f"ontology pack {pack!r} not found at {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    valid_primitives = {p.value: p for p in P}

    ontology: dict[P, list[Hypothesis]] = {}
    for name, entries in (raw.get("primitives") or {}).items():
        if name not in valid_primitives:
            raise ValueError(
                f"ontology pack {path}: unknown primitive {name!r} "
                f"(valid: {', '.join(sorted(valid_primitives))})"
            )
        ontology[valid_primitives[name]] = [
            _parse_hypothesis(e, f"primitives.{name}") for e in entries
        ]

    shape_ontology = {
        shape: [_parse_hypothesis(e, f"shapes.{shape}") for e in entries]
        for shape, entries in (raw.get("shapes") or {}).items()
    }

    ambient_rules: list[tuple[str, tuple[float, float], Hypothesis]] = []
    for entry in raw.get("ambient") or []:
        try:
            feature = entry["feature"]
            lo, hi = float(entry["range"][0]), float(entry["range"][1])
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise ValueError(f"ontology pack {path}: malformed ambient rule: {exc!r}") from exc
        ambient_rules.append((feature, (lo, hi), _parse_hypothesis(entry, "ambient")))

    if not ontology:
        raise ValueError(f"ontology pack {path}: no 'primitives' section — nothing to match")
    return OntologyPack(ontology, shape_ontology, ambient_rules)
