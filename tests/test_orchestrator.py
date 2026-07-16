"""PipelineSession generation gating and error handling.

The vision thread (real camera + MediaPipe) is never started here — these
tests drive the async half of PipelineSession directly with fake prompter/
imagegen backends, exercising _maybe_generate's gating and the
success/failure paths of _generate.
"""

from __future__ import annotations

import asyncio
import math
import time

import pytest

from backend.core.bus import EventBus, Topics
from backend.core.config import AppConfig
from backend.imagegen.base import GeneratedImage
from backend.pipeline.orchestrator import PipelineSession
from backend.prompting.base import OptimizedPrompt
from backend.storage.repo import Repository
from backend.vision.schema import HandLandmarks, LandmarkFrame


class _FakePrompter:
    name = "fake-prompter"

    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, graph) -> OptimizedPrompt:  # noqa: ANN001
        self.calls += 1
        return OptimizedPrompt(positive="a fake scene", generator=self.name)


class _FakeImageGen:
    name = "fake-imagegen"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    async def generate(self, prompt: OptimizedPrompt, width: int, height: int) -> GeneratedImage:
        self.calls += 1
        if self.fail:
            raise RuntimeError("backend exploded")
        return GeneratedImage(
            id="img_test",
            path="unused.png",
            backend=self.name,
            prompt_positive=prompt.positive,
            latency_ms=5,
            created_at=time.time(),
        )


class _Recorder:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def __call__(self, payload) -> None:  # noqa: ANN001
        pass

    def handler_for(self, topic: str):
        async def _handle(payload) -> None:  # noqa: ANN001
            self.events.append((topic, payload))

        return _handle


@pytest.fixture
async def session(tmp_path):
    cfg = AppConfig(data_dir=tmp_path)
    bus = EventBus()
    repo = Repository(tmp_path)
    sess = PipelineSession(cfg, bus, repo)
    repo.create_session(sess.id)
    sess._loop = asyncio.get_running_loop()
    yield sess


def _subscribe_all(bus: EventBus, recorder: _Recorder) -> None:
    for topic in (
        Topics.GENERATION_STARTED,
        Topics.GENERATION_DONE,
        Topics.ERROR,
        Topics.SCENE_UPDATE,
    ):
        bus.subscribe(topic, recorder.handler_for(topic))


# ---------- _maybe_generate gating ----------


async def test_maybe_generate_skips_when_scene_not_ready(session) -> None:
    session._prompter = _FakePrompter()
    session._imagegen = _FakeImageGen()
    await session._maybe_generate()
    await asyncio.sleep(0)
    assert session._prompter.calls == 0
    assert session._generating is False


async def test_maybe_generate_skips_when_already_generating(session) -> None:
    session._prompter = _FakePrompter()
    session._imagegen = _FakeImageGen()
    session.force_generate()
    session._generating = True
    await session._maybe_generate()
    assert session._prompter.calls == 0


async def test_maybe_generate_skips_when_diff_below_threshold(session) -> None:
    session._prompter = _FakePrompter()
    session._imagegen = _FakeImageGen()
    session.force_generate()
    session._last_snapshot = session.scene.graph.model_copy(deep=True)
    await session._maybe_generate()
    await asyncio.sleep(0)
    assert session._prompter.calls == 0


async def test_maybe_generate_proceeds_when_forced_and_diff_present(session) -> None:
    prompter = _FakePrompter()
    imagegen = _FakeImageGen()
    session._prompter = prompter
    session._imagegen = imagegen
    session.force_generate()
    await session._maybe_generate()
    assert session._generating is True
    task = next(t for t in asyncio.all_tasks() if t is not asyncio.current_task())
    await task
    assert prompter.calls == 1
    assert imagegen.calls == 1
    assert session._generating is False


# ---------- _generate success / failure ----------


async def test_generate_publishes_started_then_done_on_success(session) -> None:
    recorder = _Recorder()
    _subscribe_all(session._bus, recorder)
    session._prompter = _FakePrompter()
    session._imagegen = _FakeImageGen()
    await session._generate(session.scene.graph)
    topics = [t for t, _ in recorder.events]
    assert topics == [Topics.GENERATION_STARTED, Topics.GENERATION_DONE]
    done_payload = recorder.events[-1][1]
    assert done_payload["backend"] == "fake-imagegen"
    assert done_payload["url"] == "/api/images/img_test"
    assert session._generating is False


async def test_generate_publishes_error_when_imagegen_fails(session) -> None:
    recorder = _Recorder()
    _subscribe_all(session._bus, recorder)
    session._prompter = _FakePrompter()
    session._imagegen = _FakeImageGen(fail=True)
    await session._generate(session.scene.graph)
    topics = [t for t, _ in recorder.events]
    assert topics == [Topics.GENERATION_STARTED, Topics.ERROR]
    error_payload = recorder.events[-1][1]
    assert error_payload["code"] == "BACKEND_DOWN"
    assert "backend exploded" in error_payload["message"]
    # _generating must be reset even on failure, or the pipeline would wedge
    assert session._generating is False


async def test_generate_resets_generating_flag_even_on_prompter_failure(session) -> None:
    class _BoomPrompter:
        name = "boom"

        async def generate(self, graph):  # noqa: ANN001
            raise RuntimeError("prompter broke")

    session._prompter = _BoomPrompter()
    session._imagegen = _FakeImageGen()
    session._generating = True
    await session._generate(session.scene.graph)
    assert session._generating is False


# ---------- reset_scene / pause ----------


async def test_reset_scene_publishes_scene_update_and_clears_graph(session) -> None:
    recorder = _Recorder()
    _subscribe_all(session._bus, recorder)
    session.scene.graph.meta.revision = 5
    session.reset_scene()
    await asyncio.sleep(0.01)
    assert session.scene.graph.meta.revision == 0
    assert any(t == Topics.SCENE_UPDATE for t, _ in recorder.events)


def test_pause_toggles_paused_flag(session) -> None:
    assert session._paused is False
    session.pause(True)
    assert session._paused is True
    session.pause(False)
    assert session._paused is False


# ---------- air-draw wiring ----------


def _hand(index_x: float, index_y: float = 0.75, pinch_open: bool = False) -> HandLandmarks:
    points = [(0.0, 0.0, 0.0)] * 21
    points[0] = (0.5, 0.9, 0.0)  # wrist
    points[12] = (0.5, 0.7, 0.0)  # middle tip -> size 0.2
    points[8] = (index_x, index_y, 0.0)  # index tip
    offset = 0.3 if pinch_open else 0.005
    points[4] = (index_x + offset, index_y, 0.0)  # thumb tip
    return HandLandmarks(handedness="Right", points=points, score=0.9)


async def test_process_enters_draw_mode_and_skips_segmenter(session) -> None:
    recorder = _Recorder()
    session._bus.subscribe(Topics.DRAW_STROKE, recorder.handler_for(Topics.DRAW_STROKE))
    session._bus.subscribe(Topics.PRIMITIVE, recorder.handler_for(Topics.PRIMITIVE))
    for i in range(6):
        ts = i * 0.05
        session._process(LandmarkFrame(ts=ts, hands=[_hand(index_x=0.3 + i * 0.02)]))
    await asyncio.sleep(0.01)
    topics = [t for t, _ in recorder.events]
    assert Topics.DRAW_STROKE in topics
    assert Topics.PRIMITIVE not in topics


async def test_process_finalizes_shape_on_pinch_release(session) -> None:
    recorder = _Recorder()
    session._bus.subscribe(Topics.DRAW_SHAPE, recorder.handler_for(Topics.DRAW_SHAPE))
    n, ts = 10, 0.0
    for i in range(n):
        ts = i * 0.05
        t = 2 * math.pi * i / n
        hand = _hand(index_x=0.5 + 0.15 * math.cos(t), index_y=0.75 + 0.15 * math.sin(t))
        session._process(LandmarkFrame(ts=ts, hands=[hand]))
    session._process(LandmarkFrame(ts=ts + 0.05, hands=[_hand(index_x=0.5, pinch_open=True)]))
    await asyncio.sleep(0.01)
    topics = [t for t, _ in recorder.events]
    assert Topics.DRAW_SHAPE in topics


def test_clear_draw_resets_stroke_buffer(session) -> None:
    session._stroke.add_from_frame(LandmarkFrame(ts=0.0, hands=[_hand(index_x=0.5)]))
    assert len(session._stroke.points) == 1
    session.clear_draw()
    assert session._stroke.points == []
