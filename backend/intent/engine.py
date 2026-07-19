"""Intent Engine: fuses motion primitives + ambient affect into IntentFrames.

Context-aware: repetition emphasis, post-render refinement weighting, and
recency gating. Behind `IntentModel` so a learned/LLM model can replace it.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections import deque

from backend.core.config import IntentConfig
from backend.gestures.schema import (
    DrawnShape,
    GestureFeatureVector,
    MotionPrimitive,
    SequenceSegment,
)
from backend.intent.ontology import Hypothesis, OntologyPack, load_ontology_pack
from backend.intent.schema import IntentFrame


class IntentModel(ABC):
    @abstractmethod
    def on_segment(
        self, seg: SequenceSegment, features: GestureFeatureVector
    ) -> list[IntentFrame]: ...

    @abstractmethod
    def on_features(self, features: GestureFeatureVector) -> list[IntentFrame]: ...

    @abstractmethod
    def notify_render(self, ts: float) -> None: ...

    def on_drawn_shape(self, shape: DrawnShape) -> list[IntentFrame]:
        """Optional: air-drawn shape evidence. Default no-op so existing/future
        IntentModel implementations aren't forced to support drawing."""
        return []


class RuleBasedIntentModel(IntentModel):
    def __init__(self, cfg: IntentConfig, pack: OntologyPack | None = None) -> None:
        self._cfg = cfg
        self._pack = pack or load_ontology_pack(cfg.ontology_pack)
        self._recent: deque[tuple[float, MotionPrimitive]] = deque(maxlen=20)
        self._last_render_ts: float | None = None
        self._ambient_state: dict[str, float] = {}
        self._ambient_emitted: dict[str, float] = {}

    def notify_render(self, ts: float) -> None:
        self._last_render_ts = ts

    def on_segment(self, seg: SequenceSegment, features: GestureFeatureVector) -> list[IntentFrame]:
        frames: list[IntentFrame] = []
        repeats = sum(1 for ts, p in self._recent if p == seg.primitive and seg.t_start - ts < 5.0)
        self._recent.append((seg.t_end, seg.primitive))

        for hyp in self._pack.ontology.get(seg.primitive, []):
            if not self._conditions_met(hyp, features):
                continue
            conf, modifiers = seg.confidence * hyp.weight, []
            if repeats:
                conf *= min(2.0, 1.3**repeats)
                modifiers.append(f"repetition x{repeats + 1}")
            if self._last_render_ts is not None and seg.t_start - self._last_render_ts < 8.0:
                conf *= 1.5
                modifiers.append("post_render_refinement")
            conf = min(1.0, conf)
            if conf < self._cfg.min_confidence:
                continue
            frames.append(
                IntentFrame(
                    id=f"int_{uuid.uuid4().hex[:8]}",
                    ts=seg.t_end,
                    target=hyp.target,
                    category=hyp.category,
                    attribute=hyp.attribute,
                    value=hyp.value,
                    confidence=round(conf, 3),
                    evidence=[seg.id],
                    modifiers=modifiers,
                )
            )
        return frames

    def on_features(self, features: GestureFeatureVector) -> list[IntentFrame]:
        """Ambient hypotheses from smoothed affect/tempo; rate-limited per attribute."""
        frames: list[IntentFrame] = []
        alpha = 0.05
        for key, (lo, hi), hyp in self._pack.ambient_rules:
            raw = getattr(features, key, 0.0)
            s = self._ambient_state.get(key, raw)
            s += alpha * (raw - s)
            self._ambient_state[key] = s
            if not lo <= s <= hi:
                continue
            gate = f"{key}:{hyp.attribute}:{hyp.value}"
            if features.ts - self._ambient_emitted.get(gate, -1e9) < 10.0:
                continue
            self._ambient_emitted[gate] = features.ts
            conf = hyp.weight
            if conf >= self._cfg.min_confidence:
                frames.append(
                    IntentFrame(
                        id=f"int_{uuid.uuid4().hex[:8]}",
                        ts=features.ts,
                        target=hyp.target,
                        attribute=hyp.attribute,
                        value=hyp.value,
                        confidence=conf,
                        modifiers=["ambient"],
                    )
                )
        return frames

    def on_drawn_shape(self, shape: DrawnShape) -> list[IntentFrame]:
        frames: list[IntentFrame] = []
        ts = shape.points[-1].ts if shape.points else 0.0
        for hyp in self._pack.shape_ontology.get(shape.shape, []):
            conf = min(1.0, shape.confidence * hyp.weight)
            if conf < self._cfg.min_confidence:
                continue
            value = f"{hyp.value}, positioned in the {shape.position_label}"
            frames.append(
                IntentFrame(
                    id=f"int_{uuid.uuid4().hex[:8]}",
                    ts=ts,
                    target=hyp.target,
                    category=hyp.category,
                    attribute=hyp.attribute,
                    value=value,
                    confidence=round(conf, 3),
                    evidence=[shape.id],
                    modifiers=["drawn_shape"],
                )
            )
        return frames

    def explain(
        self, fv: GestureFeatureVector, candidates: list[tuple[MotionPrimitive, float]]
    ) -> list[dict]:
        """Non-mutating: what the top-matching primitives would mean if sustained."""
        out: list[dict] = []
        for prim, score in candidates[:3]:
            for hyp in self._pack.ontology.get(prim, []):
                if not self._conditions_met(hyp, fv):
                    continue
                out.append(
                    {
                        "primitive": prim.value,
                        "match_score": round(score, 3),
                        "would_mean": f"{hyp.attribute} → {hyp.value}",
                        "base_weight": hyp.weight,
                    }
                )
        return out

    def ambient_snapshot(self) -> dict[str, float]:
        """Smoothed ambient state actually driving mood/lighting hypotheses —
        separate from the raw per-frame values shown live in the features bar."""
        return dict(self._ambient_state)

    @staticmethod
    def _conditions_met(hyp: Hypothesis, features: GestureFeatureVector) -> bool:
        return all(lo <= getattr(features, k, 0.0) <= hi for k, (lo, hi) in hyp.conditions.items())
