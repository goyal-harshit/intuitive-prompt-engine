"""Intent engine fusion behavior with synthetic segments."""
from backend.core.config import IntentConfig
from backend.gestures.schema import GestureFeatureVector, MotionPrimitive, SequenceSegment
from backend.intent.engine import RuleBasedIntentModel


def _seg(prim: MotionPrimitive, t: float = 1.0, conf: float = 0.9) -> SequenceSegment:
    return SequenceSegment(id=f"s_{t}", primitive=prim, t_start=t - 0.5, t_end=t, confidence=conf)


def _fv(**kw) -> GestureFeatureVector:
    return GestureFeatureVector(ts=kw.pop("ts", 1.0), **kw)


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
