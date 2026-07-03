# Scene Graph Specification

The Scene Graph is the persistent internal model of the user's imagination. It is **additive**: intent frames merge into it; nothing is replaced wholesale.

## Structure

```
SceneGraph
├── objects: dict[str, SceneObject]
│     SceneObject
│     ├── id, category (e.g. "celestial", "airborne", "figure", "structure")
│     ├── attributes: dict[str, AttributeValue]   # size, motion, position_hint, shape
│     └── salience: float                          # how much attention the user gave it
├── globals: dict[GlobalKey, AttributeValue]
│     GlobalKey ∈ { environment, mood, lighting, weather, camera_angle,
│                   camera_distance, artistic_style, motion, scale,
│                   time_of_day, color_palette, visual_effects }
├── history: list[SceneEvent]                      # append-only provenance log
└── meta: { created_at, updated_at, revision, completeness }
```

`AttributeValue`:

```python
value: str | float
confidence: float        # 0–1, fused evidence
updated_at: datetime
provenance: list[str]    # intent-frame ids
```

## Update semantics

1. **Merge, don't replace.** Incoming hypothesis for an existing attribute:
   - same value → confidence ← 1 − (1−c_old)(1−c_new) (noisy-OR), provenance appended
   - conflicting value → winner by `confidence × recency_decay`; loser retained in history
2. **Temporal decay.** Confidence decays exponentially (half-life 90 s) so stale intents fade unless reinforced. Objects with salience < 0.1 are archived, not deleted.
3. **Object identity.** A `new_object` hypothesis first attempts binding to an existing object of the same category updated in the last 10 s (coreference); only unbound hypotheses create objects.
4. **Completeness score.** Weighted coverage: has ≥1 object (0.3), environment (0.2), mood or lighting (0.15), camera (0.15), style (0.1), palette/time (0.1). Generation triggers at ≥0.6 **and** graph stable for 2 s, or on `hold_still` commit intent.
5. **Diff score.** Between snapshots, Σ |Δconfidence| + new/removed nodes → drives debounced regeneration (regenerate only if diff > 0.25).

## Serialization

Pydantic models → JSON for: WebSocket state events, SQLite snapshots, LLM prompt-generation input. The LLM never sees raw gestures — only this graph — which is what makes prompt generation model-agnostic.

## Example snapshot

```json
{
  "objects": {
    "obj_1": {"category": "celestial", "attributes": {"size": {"value": "large", "confidence": 0.78}},
              "salience": 0.9}
  },
  "globals": {
    "environment": {"value": "panoramic landscape", "confidence": 0.71},
    "time_of_day": {"value": "night", "confidence": 0.55},
    "mood": {"value": "calm", "confidence": 0.62},
    "camera_distance": {"value": "wide", "confidence": 0.66}
  },
  "meta": {"revision": 14, "completeness": 0.68}
}
```
