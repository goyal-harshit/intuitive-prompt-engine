"""Scene Graph merge semantics — pure logic, no camera or network."""
from backend.core.config import SceneConfig
from backend.intent.schema import IntentFrame
from backend.scene.graph import SceneGraphManager


def _frame(attribute: str, value: str, conf: float, target: str = "global",
           category: str | None = None) -> IntentFrame:
    return IntentFrame(id=f"i_{attribute}_{value[:4]}", ts=0.0, target=target,
                       category=category, attribute=attribute, value=value, confidence=conf)


def test_reinforcement_noisy_or() -> None:
    mgr = SceneGraphManager(SceneConfig())
    mgr.apply([_frame("mood", "calm", 0.5)])
    mgr.apply([_frame("mood", "calm", 0.5)])
    assert mgr.graph.globals["mood"].confidence == 0.75


def test_conflict_higher_confidence_wins() -> None:
    mgr = SceneGraphManager(SceneConfig())
    mgr.apply([_frame("lighting", "soft", 0.4)])
    mgr.apply([_frame("lighting", "harsh", 0.9)])
    assert mgr.graph.globals["lighting"].value == "harsh"


def test_object_coreference_binds_same_category() -> None:
    mgr = SceneGraphManager(SceneConfig())
    mgr.apply([_frame("motion", "flying", 0.6, target="new_object", category="airborne")])
    mgr.apply([_frame("position", "high in sky", 0.6, target="new_object", category="airborne")])
    assert len(mgr.graph.objects) == 1
    obj = next(iter(mgr.graph.objects.values()))
    assert set(obj.attributes) == {"motion", "position"}


def test_completeness_and_readiness() -> None:
    mgr = SceneGraphManager(SceneConfig(stability_s=0.0))
    assert not mgr.ready_to_generate()
    mgr.apply([
        _frame("shape", "orb", 0.6, target="new_object", category="celestial"),
        _frame("environment", "vast landscape", 0.6),
        _frame("mood", "calm", 0.6),
        _frame("camera_distance", "wide", 0.6),
    ])
    assert mgr.graph.meta.completeness >= 0.6
    assert mgr.ready_to_generate()


def test_commit_signal_forces_readiness() -> None:
    mgr = SceneGraphManager(SceneConfig())
    mgr.apply([_frame("_commit", "commit", 0.9)])
    assert mgr.ready_to_generate()
    mgr.snapshot()
    assert not mgr.commit_requested
