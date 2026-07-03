"""SceneGraphManager: additive world model with evidence fusion.

Merge semantics (noisy-OR reinforcement, confidence×recency conflict
resolution), temporal decay, object coreference, completeness and diff
scoring. This is the single source of truth for the user's imagined scene.
"""
from __future__ import annotations

import math
import time
import uuid

from backend.core.config import SceneConfig
from backend.intent.schema import IntentFrame
from backend.scene.schema import (
    AttributeValue,
    SceneEvent,
    SceneGraph,
    SceneObject,
)

_COMPLETENESS_WEIGHTS: list[tuple[tuple[str, ...], float]] = [
    (("_objects",), 0.30),
    (("environment",), 0.20),
    (("mood", "lighting"), 0.15),
    (("camera_angle", "camera_distance"), 0.15),
    (("artistic_style",), 0.10),
    (("color_palette", "time_of_day"), 0.10),
]


class SceneGraphManager:
    def __init__(self, cfg: SceneConfig, decay_half_life_s: float = 90.0) -> None:
        self._cfg = cfg
        self._lambda = math.log(2) / decay_half_life_s
        self.graph = SceneGraph()
        self.commit_requested = False

    # ---------- updates ----------

    def apply(self, frames: list[IntentFrame]) -> bool:
        """Merge intent frames. Returns True if the graph mutated."""
        mutated = False
        for f in frames:
            if f.attribute == "_commit":
                self.commit_requested = True
                self._log(f.ts, "commit", "hold_still commit signal")
                continue
            target = self._resolve_target(f)
            attrs = self.graph.globals if target == "global" else self.graph.objects[target].attributes
            key = f.attribute
            mutated |= self._merge(attrs, key, f)
            if target != "global":
                obj = self.graph.objects[target]
                obj.salience = min(1.0, obj.salience + 0.15)
        if mutated:
            self.graph.meta.revision += 1
            self.graph.meta.updated_at = time.time()
            self.graph.meta.completeness = self._completeness()
        return mutated

    def _resolve_target(self, f: IntentFrame) -> str:
        if f.target == "global":
            return "global"
        if f.target == "focus_object":
            focus = max(self.graph.objects.values(), key=lambda o: o.salience, default=None)
            if focus:
                return focus.id
            f = f.model_copy(update={"category": "subject"})
            return self._create_object(f)
        # new_object: coreference — bind to same-category object touched in last 10 s
        now = time.time()
        for obj in self.graph.objects.values():
            recent = any(now - a.updated_at < 10.0 for a in obj.attributes.values())
            if obj.category == (f.category or "object") and recent:
                return obj.id
        return self._create_object(f)

    def _create_object(self, f: IntentFrame) -> str:
        oid = f"obj_{uuid.uuid4().hex[:6]}"
        self.graph.objects[oid] = SceneObject(id=oid, category=f.category or "object")
        self._log(f.ts, "object_created", f"{oid} ({f.category})")
        return oid

    def _merge(self, attrs: dict[str, AttributeValue], key: str, f: IntentFrame) -> bool:
        existing = attrs.get(key)
        if existing is None:
            attrs[key] = AttributeValue(value=f.value, confidence=f.confidence,
                                        updated_at=time.time(), provenance=[f.id])
            self._log(f.ts, "merged", f"{key} = {f.value} ({f.confidence:.2f})")
            return True
        if existing.value == f.value:  # reinforcement: noisy-OR
            existing.confidence = 1 - (1 - existing.confidence) * (1 - f.confidence)
            existing.updated_at = time.time()
            existing.provenance.append(f.id)
            self._log(f.ts, "merged", f"{key} reinforced → {existing.confidence:.2f}")
            return True
        # conflict: winner by decayed confidence
        if f.confidence > self._decayed(existing):
            self._log(f.ts, "conflict_won", f"{key}: '{f.value}' over '{existing.value}'")
            attrs[key] = AttributeValue(value=f.value, confidence=f.confidence,
                                        updated_at=time.time(), provenance=[f.id])
            return True
        self._log(f.ts, "conflict_lost", f"{key}: kept '{existing.value}'")
        return False

    # ---------- maintenance ----------

    def decay(self) -> None:
        """Apply temporal decay; archive faded objects. Call ~1 Hz."""
        for obj in list(self.graph.objects.values()):
            obj.salience *= 0.995
            if obj.salience < 0.1:
                self.graph.objects.pop(obj.id)
                self._log(time.time(), "decayed", f"archived {obj.id}")

    def _decayed(self, a: AttributeValue) -> float:
        return a.confidence * math.exp(-self._lambda * (time.time() - a.updated_at))

    # ---------- scoring ----------

    def _completeness(self) -> float:
        score = 0.0
        for keys, w in _COMPLETENESS_WEIGHTS:
            if keys == ("_objects",):
                if self.graph.objects:
                    score += w
            elif any(k in self.graph.globals for k in keys):
                score += w
        return round(score, 3)

    def ready_to_generate(self) -> bool:
        if self.commit_requested:
            return True
        m = self.graph.meta
        stable = time.time() - m.updated_at >= self._cfg.stability_s
        return m.completeness >= self._cfg.completeness_threshold and stable and m.revision > 0

    def diff_score(self, previous: SceneGraph | None) -> float:
        """Magnitude of change vs a previous snapshot — drives debounced regen."""
        if previous is None:
            return 1.0
        score = 0.0
        for key in set(self.graph.globals) | set(previous.globals):
            a, b = self.graph.globals.get(key), previous.globals.get(key)
            if a is None or b is None:
                score += 0.15
            elif a.value != b.value:
                score += 0.15
            else:
                score += abs(a.confidence - b.confidence) * 0.05
        score += 0.2 * len(set(self.graph.objects) ^ set(previous.objects))
        return score

    def snapshot(self) -> SceneGraph:
        self.commit_requested = False
        return self.graph.model_copy(deep=True)

    def reset(self) -> None:
        self.graph = SceneGraph()
        self.commit_requested = False

    def _log(self, ts: float, kind: str, detail: str) -> None:
        self.graph.history.append(SceneEvent(ts=ts, kind=kind, detail=detail))
        if len(self.graph.history) > 500:
            self.graph.history = self.graph.history[-250:]
