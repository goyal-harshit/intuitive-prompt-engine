"""Ontology plugin packs: YAML loading, validation, and default-pack fidelity."""

from __future__ import annotations

import pytest

from backend.core.config import IntentConfig
from backend.gestures.schema import MotionPrimitive
from backend.intent.engine import RuleBasedIntentModel
from backend.intent.ontology import (
    AMBIENT_RULES,
    BUILTIN_PACK,
    ONTOLOGY,
    SHAPE_ONTOLOGY,
    load_ontology_pack,
)


def test_default_pack_matches_builtins() -> None:
    """plugins/default/ontology.yaml must stay a faithful export of the
    built-in tables — regenerate it if this fails after editing ontology.py."""
    pack = load_ontology_pack("default")
    assert pack.ontology == ONTOLOGY
    assert pack.shape_ontology == SHAPE_ONTOLOGY
    assert pack.ambient_rules == AMBIENT_RULES


def test_missing_default_pack_falls_back_to_builtins(tmp_path, monkeypatch) -> None:
    import backend.intent.ontology as onto

    monkeypatch.setattr(onto, "PLUGINS_DIR", tmp_path / "no-plugins-here")
    assert onto.load_ontology_pack("default") is BUILTIN_PACK


def test_missing_custom_pack_raises() -> None:
    with pytest.raises(FileNotFoundError, match="my-pack"):
        load_ontology_pack("my-pack")


def test_custom_pack_loads_from_path(tmp_path) -> None:
    pack_file = tmp_path / "ontology.yaml"
    pack_file.write_text(
        """
primitives:
  expand:
    - target: global
      attribute: scale
      value: overwhelming architecture
      weight: 0.9
      conditions: {tempo: [0.0, 0.5]}
shapes:
  circle:
    - target: new_object
      attribute: shape
      value: rotunda
      weight: 0.7
      category: building
ambient:
  - feature: tempo
    range: [0.5, 1.0]
    target: global
    attribute: mood
    value: bustling
    weight: 0.4
"""
    )
    pack = load_ontology_pack(pack_file)
    hyps = pack.ontology[MotionPrimitive.EXPAND]
    assert hyps[0].value == "overwhelming architecture"
    assert hyps[0].conditions == {"tempo": (0.0, 0.5)}
    assert pack.shape_ontology["circle"][0].category == "building"
    assert pack.ambient_rules[0][:2] == ("tempo", (0.5, 1.0))


def test_unknown_primitive_rejected(tmp_path) -> None:
    pack_file = tmp_path / "ontology.yaml"
    pack_file.write_text(
        "primitives:\n  jazz_hands:\n    - {target: global, attribute: mood, value: x, weight: 0.5}\n"
    )
    with pytest.raises(ValueError, match="jazz_hands"):
        load_ontology_pack(pack_file)


def test_malformed_hypothesis_rejected(tmp_path) -> None:
    pack_file = tmp_path / "ontology.yaml"
    pack_file.write_text("primitives:\n  expand:\n    - {target: global, weight: 0.5}\n")
    with pytest.raises(ValueError, match="primitives.expand"):
        load_ontology_pack(pack_file)


def test_empty_pack_rejected(tmp_path) -> None:
    pack_file = tmp_path / "ontology.yaml"
    pack_file.write_text("shapes: {}\n")
    with pytest.raises(ValueError, match="primitives"):
        load_ontology_pack(pack_file)


def test_engine_uses_configured_pack(tmp_path) -> None:
    pack_file = tmp_path / "ontology.yaml"
    pack_file.write_text(
        """
primitives:
  expand:
    - target: global
      attribute: scale
      value: custom-pack-value
      weight: 0.9
"""
    )
    model = RuleBasedIntentModel(IntentConfig(), pack=load_ontology_pack(pack_file))
    from backend.gestures.schema import GestureFeatureVector, SequenceSegment

    frames = model.on_segment(
        SequenceSegment(
            id="seg", primitive=MotionPrimitive.EXPAND, t_start=0.0, t_end=1.0, confidence=0.9
        ),
        GestureFeatureVector(ts=1.0),
    )
    assert [f.value for f in frames] == ["custom-pack-value"]
