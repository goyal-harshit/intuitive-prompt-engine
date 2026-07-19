"""Session replay: repository read-side queries and the tools/replay.py CLI."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import replay  # noqa: E402  (tools/replay.py)

from backend.gestures.schema import MotionPrimitive, SequenceSegment
from backend.imagegen.base import GeneratedImage
from backend.intent.schema import IntentFrame
from backend.prompting.base import OptimizedPrompt
from backend.scene.schema import SceneGraph
from backend.storage.repo import Repository


@pytest.fixture()
def seeded_repo(tmp_path) -> tuple[Repository, str]:
    # Gesture/intent timestamps arrive in the pipeline's monotonic domain
    # (as in the live app) and the repo converts them to wall-clock on write;
    # add_snapshot stamps wall-clock itself. Seeded offsets give the order:
    # gesture < intent < scene(≈now) < generation.
    now = time.time()
    mono = time.monotonic()
    repo = Repository(tmp_path)
    sid = "ses_test01"
    repo.create_session(sid)
    repo.add_gesture(
        sid,
        SequenceSegment(
            id="seg_1",
            primitive=MotionPrimitive.EXPAND,
            t_start=mono - 31.0,
            t_end=mono - 30.0,
            confidence=0.8,
        ),
    )
    repo.add_intents(
        sid,
        [
            IntentFrame(
                id="int_1",
                ts=mono - 20.0,
                target="global",
                attribute="scale",
                value="grand, monumental scale",
                confidence=0.7,
            )
        ],
    )
    graph = SceneGraph()
    graph.meta.revision = 3
    graph.meta.completeness = 0.5
    repo.add_snapshot(sid, graph)
    repo.add_generation(
        sid,
        GeneratedImage(
            id="img_abc",
            path="/tmp/img_abc.png",
            backend="pollinations",
            prompt_positive="a vast landscape",
            latency_ms=1234,
            created_at=now + 10.0,
        ),
        OptimizedPrompt(positive="a vast landscape", generator="template"),
    )
    repo.end_session(sid)
    return repo, sid


def test_list_sessions_counts(seeded_repo) -> None:
    repo, sid = seeded_repo
    sessions = repo.list_sessions()
    assert len(sessions) == 1
    s = sessions[0]
    assert s["id"] == sid
    assert s["ended_at"] is not None
    assert (s["gestures"], s["intents"], s["snapshots"], s["generations"]) == (1, 1, 1, 1)


def test_timeline_is_chronological_and_tagged(seeded_repo) -> None:
    repo, sid = seeded_repo
    timeline = repo.session_timeline(sid)
    assert [e["kind"] for e in timeline] == ["gesture", "intent", "scene", "generation"]
    assert timeline == sorted(timeline, key=lambda e: e["ts"])
    gesture, intent, scene, generation = timeline
    assert gesture["primitive"] == "expand"
    assert intent["attribute"] == "scale"
    assert scene["revision"] == 3
    assert generation["image_id"] == "img_abc"
    assert generation["latency_ms"] == 1234


def test_pipeline_timestamps_stored_as_wall_clock(seeded_repo) -> None:
    # Monotonic pipeline ts must be converted at the storage boundary so all
    # event kinds share one time axis (regression: replay offsets jumped by
    # ~1.8e9s when gesture/intent rows kept raw monotonic values).
    repo, sid = seeded_repo
    now = time.time()
    for event in repo.session_timeline(sid):
        assert abs(event["ts"] - now) < 300, f"{event['kind']} ts not wall-clock: {event['ts']}"


def test_timeline_empty_for_unknown_session(seeded_repo) -> None:
    repo, _ = seeded_repo
    assert repo.session_timeline("ses_nope") == []


def test_cli_list_and_show(tmp_path, seeded_repo, capsys) -> None:
    _, sid = seeded_repo
    data_dir = str(tmp_path)  # the seeded repo's dir

    assert replay.main(["--data-dir", data_dir, "list"]) == 0
    out = capsys.readouterr().out
    assert sid in out

    assert replay.main(["--data-dir", data_dir, "show", sid]) == 0
    out = capsys.readouterr().out
    assert "EXPAND" in out.upper()
    assert "img_abc" in out


def test_cli_show_json_roundtrips(tmp_path, seeded_repo, capsys) -> None:
    _, sid = seeded_repo
    assert replay.main(["--data-dir", str(tmp_path), "show", sid, "--json"]) == 0
    events = json.loads(capsys.readouterr().out)
    assert len(events) == 4
    assert {e["kind"] for e in events} == {"gesture", "intent", "scene", "generation"}


def test_cli_show_unknown_session_exits_nonzero(tmp_path, seeded_repo, capsys) -> None:
    assert replay.main(["--data-dir", str(tmp_path), "show", "ses_nope"]) == 1
