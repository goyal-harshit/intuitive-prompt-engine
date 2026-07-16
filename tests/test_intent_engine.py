"""Intent engine fusion behavior with synthetic segments."""

from backend.core.config import IntentConfig
from backend.gestures.schema import (
    DrawnShape,
    GestureFeatureVector,
    MotionPrimitive,
    SequenceSegment,
    StrokePoint,
)
from backend.gestures.sequence import PrototypeSegmenter
from backend.intent.engine import RuleBasedIntentModel


def _seg(prim: MotionPrimitive, t: float = 1.0, conf: float = 0.9) -> SequenceSegment:
    return SequenceSegment(id=f"s_{t}", primitive=prim, t_start=t - 0.5, t_end=t, confidence=conf)


def _fv(**kw) -> GestureFeatureVector:
    return GestureFeatureVector(ts=kw.pop("ts", 1.0), **kw)


def _shape(
    shape: str = "circle", confidence: float = 0.8, position_label: str = "center"
) -> DrawnShape:
    points = [StrokePoint(ts=0.0, x=0.5, y=0.5), StrokePoint(ts=0.5, x=0.5, y=0.5)]
    return DrawnShape(
        id="shp_1",
        shape=shape,
        points=points,
        bbox_center=(0.5, 0.5),
        bbox_size=1.0,
        position_label=position_label,
        duration_s=0.5,
        confidence=confidence,
    )


def test_expand_yields_scale_and_camera_hypotheses() -> None:
    model = RuleBasedIntentModel(IntentConfig())
    frames = model.on_segment(_seg(MotionPrimitive.EXPAND), _fv(tempo=0.3))
    attrs = {f.attribute for f in frames}
    assert "scale" in attrs and "camera_distance" in attrs
    assert all(f.confidence >= 0.35 for f in frames)


def test_condition_gating_fast_vs_slow_expand() -> None:
    model = RuleBasedIntentModel(IntentConfig())
    slow = model.on_segment(_seg(MotionPrimitive.EXPAND), _fv(tempo=0.2))
    model2 = RuleBasedIntentModel(IntentConfig())
    fast = model2.on_segment(_seg(MotionPrimitive.EXPAND, t=2.0), _fv(tempo=0.9))
    assert any(f.attribute == "environment" for f in slow)
    assert not any(f.attribute == "environment" for f in fast)


def test_repetition_boosts_confidence() -> None:
    model = RuleBasedIntentModel(IntentConfig())
    first = model.on_segment(_seg(MotionPrimitive.CONTRACT, t=1.0), _fv())
    second = model.on_segment(_seg(MotionPrimitive.CONTRACT, t=3.0), _fv(ts=3.0))
    c1 = next(f.confidence for f in first if f.attribute == "camera_distance")
    c2 = next(f.confidence for f in second if f.attribute == "camera_distance")
    assert c2 > c1
    assert any("repetition" in m for f in second for m in f.modifiers)


def test_post_render_refinement_weighting() -> None:
    model = RuleBasedIntentModel(IntentConfig())
    model.notify_render(0.9)
    frames = model.on_segment(_seg(MotionPrimitive.EXPAND, t=2.0), _fv(tempo=0.3))
    assert any("post_render_refinement" in f.modifiers for f in frames)


# ---------- on_drawn_shape ----------


def test_drawn_circle_yields_shape_hypothesis_with_position_folded_in() -> None:
    model = RuleBasedIntentModel(IntentConfig())
    frames = model.on_drawn_shape(_shape(shape="circle", position_label="upper-left"))
    assert any(f.attribute == "shape" and "upper-left" in f.value for f in frames)
    assert all(f.evidence == ["shp_1"] and "drawn_shape" in f.modifiers for f in frames)


def test_drawn_shape_confidence_scales_with_shape_confidence() -> None:
    model = RuleBasedIntentModel(IntentConfig(min_confidence=0.1))
    strong = model.on_drawn_shape(_shape(shape="circle", confidence=0.9))
    weak = model.on_drawn_shape(_shape(shape="circle", confidence=0.5))
    c_strong = next(f.confidence for f in strong if f.attribute == "shape")
    c_weak = next(f.confidence for f in weak if f.attribute == "shape")
    assert c_strong > c_weak


def test_low_confidence_drawn_shape_is_filtered_below_min_confidence() -> None:
    model = RuleBasedIntentModel(IntentConfig(min_confidence=0.9))
    frames = model.on_drawn_shape(_shape(shape="freeform", confidence=0.3))
    assert frames == []


def test_unknown_shape_key_yields_no_frames() -> None:
    model = RuleBasedIntentModel(IntentConfig())
    frames = model.on_drawn_shape(_shape(shape="rectangle"))
    assert frames == []


# ---------- explain (gesture transparency) ----------


def test_explain_surfaces_would_mean_text_for_top_candidates() -> None:
    model = RuleBasedIntentModel(IntentConfig())
    segmenter = PrototypeSegmenter()
    fv = _fv(expansion_rate=0.5, tempo=0.3, separation=1.2)
    candidates = segmenter.peek(fv)
    explanation = model.explain(fv, candidates)
    assert any(e["primitive"] == MotionPrimitive.EXPAND.value for e in explanation)
    assert all("would_mean" in e and "match_score" in e for e in explanation)


def test_explain_respects_ontology_conditions() -> None:
    model = RuleBasedIntentModel(IntentConfig())
    segmenter = PrototypeSegmenter()
    fast = _fv(expansion_rate=0.5, tempo=0.9, separation=1.2)
    explanation = model.explain(fast, segmenter.peek(fast))
    assert not any(e["would_mean"].endswith("vast panoramic landscape") for e in explanation)


# ---------- ambient_snapshot ----------


def test_ambient_snapshot_lags_behind_a_sudden_swing_in_raw_value() -> None:
    model = RuleBasedIntentModel(IntentConfig())
    model.on_features(_fv(ts=1.0, valence=0.0))
    model.on_features(_fv(ts=1.1, valence=0.8))
    snapshot = model.ambient_snapshot()
    assert 0.0 < snapshot["valence"] < 0.8  # smoothed (alpha=0.05), not raw


def test_ambient_snapshot_is_empty_before_any_features_observed() -> None:
    model = RuleBasedIntentModel(IntentConfig())
    assert model.ambient_snapshot() == {}
