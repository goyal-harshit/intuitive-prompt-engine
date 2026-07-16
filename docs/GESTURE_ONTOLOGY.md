# Gesture Ontology

The ontology defines the semantic vocabulary between body language and scene meaning. It has four layers (draw mode, features, primitives, evidence mapping). Nothing here is a command; every mapping is a *weighted evidence source* consumed by the Intent Engine. Live matching state (which primitives are close to firing right now, and what they'd mean) is surfaced at runtime via the `gesture_debug` WS message (see `docs/API.md`) rather than only documented here statically.

## Layer 1 — Continuous semantic features (per frame / 100 ms window)

| Feature | Definition | Range |
|---|---|---|
| `hand_openness` | mean fingertip–palm distance / hand size | 0–1 |
| `hands_separation` | wrist-to-wrist distance / shoulder width | 0–3 |
| `expansion_rate` | d(hands_separation)/dt | −∞..∞ (units/s) |
| `verticality` | mean hand height relative to shoulders | −1..1 |
| `vertical_velocity` | d(verticality)/dt | units/s |
| `pointing_vector` | index-finger direction when extended, else null | unit vec |
| `circularity` | fit error of wrist trajectory to circle (2 s window) | 0–1 |
| `tempo` | mean wrist speed, normalized | 0–1 |
| `smoothness` | inverse jerk (spectral arc length) | 0–1 |
| `symmetry` | mirror correlation of left/right wrist paths | 0–1 |
| `posture_lean` | torso pitch from pose landmarks | −1..1 |
| `head_yaw/pitch` | head orientation | degrees |
| `face_valence` | smile − frown blendshape score | −1..1 |
| `face_arousal` | brow raise + eye widening | 0–1 |
| `stillness` | 1 − tempo over 1 s | 0–1 |
| `pinch` | thumb–index tip distance / hand size | 0–1 |

## Layer 0 — Draw mode (pinch trigger)

A sustained thumb–index pinch (`pinch` below `pinch_enter_threshold` for `pinch_enter_hold_s`) toggles **draw mode** (`DrawModeGate`, `gestures/draw.py`). Exit uses a higher, separate threshold (hysteresis) so the boundary doesn't flicker. While drawing, Layer 2 primitive detection is paused — the index fingertip path is buffered instead (EMA-smoothed, distance-downsampled). Releasing the pinch classifies the finished stroke into a shape (below) and resumes normal primitive detection.

`DrawnShape` classes: `circle`, `line`, `zigzag`, `freeform` (fallback — always resolves to something). Each carries a bounding box, a coarse position label (`upper-left` … `center` … `lower-right`), duration, and a confidence score.

## Layer 2 — Motion primitives (SequenceSegmenter output)

Segments of coherent motion labeled by feature signatures, each with confidence:

`expand`, `contract`, `raise`, `lower`, `point(direction)`, `circle(plane, radius)`, `wave`, `push_away`, `pull_in`, `frame_rect` (two L-shaped hands), `hold_still`, `sweep_horizontal`, `spiral`.

Primitives are detected by soft signature matching (cosine similarity against prototype feature vectors), not thresholds on single features — so novel executions still score.

## Layer 2b — Drawn-shape evidence mapping (shape → scene-attribute hypotheses)

Parallel to Layer 3 below, but keyed by drawn shape instead of motion primitive (full table in `intent/ontology.py::SHAPE_ONTOLOGY`). Position/size are folded into the emitted value text per-instance rather than being static table entries:

| Shape | Hypotheses (weight) |
|---|---|
| `circle` | shape:round/orb-like form (0.55), composition:centered circular motif (0.3) |
| `line` | composition:strong directional line, horizon or edge (0.45) |
| `zigzag` | motion:jagged, energetic linework (0.4), visual_effects:lightning-like/angular energy (0.3) |
| `freeform` | shape:abstract sketched form (0.3) |

## Layer 3 — Semantic evidence mapping (primitive → scene-attribute hypotheses)

Each entry contributes evidence `(attribute, direction/value, weight)`; the Intent Engine fuses them with context. Examples (full table in `intent/ontology.py`):

| Evidence source | Hypotheses (weight) |
|---|---|
| `expand` slow + smooth | scale:+ (0.6), camera_distance:wider (0.5), environment:panoramic (0.4) |
| `expand` fast | scale:+ (0.5), visual_effects:explosion/energy (0.3) |
| `contract` | camera_distance:closer (0.6), scale:− (0.4) |
| `raise` + point up | new_object:airborne (0.5), motion:flying (0.5), camera_angle:low (0.3) |
| `circle` overhead | new_object:celestial (0.5), time_of_day:night (0.3) |
| `circle` frontal small | object_shape:round (0.4), motion:orbit (0.3) |
| `sweep_horizontal` wide | environment:landscape (0.6), camera_distance:panoramic (0.5) |
| `frame_rect` | camera_angle:framed shot (0.7) |
| `push_away` | depth:far placement (0.5) |
| `pull_in` | focus object emphasis (0.5) |
| `hold_still` ≥2 s | commit signal: scene stability +, triggers completeness check (0.8) |
| high `tempo` sustained | mood:energetic (0.5), motion:dynamic (0.5) |
| low `tempo` + high smoothness | mood:calm (0.6), lighting:soft (0.3) |
| `face_valence` > 0.4 | mood:joyful (0.4), color_palette:warm (0.3) |
| `face_valence` < −0.4 | mood:dark (0.4), lighting:moody (0.4), color_palette:desaturated (0.3) |
| `posture_lean` forward | engagement + → raises update learning rate (meta) |
| `head_pitch` up sustained | scene vertical emphasis: sky/ceiling (0.3) |

## Context modulation

The same primitive means different things given history:
- `raise` **after** a `new_object:airborne` hypothesis strengthens *altitude/motion* of that object rather than creating another.
- `expand` **immediately after** an image render is interpreted as *refinement*: camera_distance:wider on the existing scene, weight ×1.5.
- Repetition of a primitive within 5 s multiplies its weight (×1.3 per repeat, cap ×2) — natural human emphasis.

This context logic lives in `intent/engine.py` as reusable modifiers, keeping the ontology table declarative and data-driven (extensible via YAML without code changes in Phase 5).
