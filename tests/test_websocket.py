"""WebSocket lifecycle: connect/disconnect, pause/resume/reset_scene commands,
auth gating, and EventBus subscriber cleanup on disconnect.

The camera is faked to fail instantly (no retries) so sessions start in
milliseconds without needing real webcam hardware — PipelineSession already
degrades gracefully when the vision thread can't open a camera. Each session
is explicitly ended (DELETE) before the TestClient (and its event loop) shuts
down, so the vision thread's error-path publish always has a live loop to
schedule onto.
"""

from __future__ import annotations

import importlib
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


class _NoCamera:
    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        raise RuntimeError("no camera in test environment")


def _load_app(tmp_path, monkeypatch, **env):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PROMPTING_STRATEGY", "template")
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.delenv("RATE_LIMIT_PER_MINUTE", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    import backend.core.config as config

    config.get_config.cache_clear()
    main = importlib.import_module("backend.app.main")
    main = importlib.reload(main)
    monkeypatch.setattr("backend.pipeline.orchestrator.OpenCVCamera", _NoCamera)
    return main, config


@pytest.fixture()
def app(tmp_path, monkeypatch):
    main, config = _load_app(tmp_path, monkeypatch)
    try:
        with TestClient(main.app) as c:
            yield main, c
    finally:
        config.get_config.cache_clear()


@contextmanager
def _session(client, **headers):
    resp = client.post("/api/session", headers=headers)
    assert resp.status_code == 200
    sid = resp.json()["session_id"]
    try:
        yield sid
    finally:
        client.delete(f"/api/session/{sid}", headers=headers)


def test_ws_unknown_session_closes_with_4004(app) -> None:
    _, client = app
    with client.websocket_connect("/ws/does-not-exist") as ws:
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()


def test_ws_connects_for_known_session(app) -> None:
    main, client = app
    with _session(client) as sid, client.websocket_connect(f"/ws/{sid}"):
        assert any(main.bus._subs[topic] for topic in main._WS_TOPICS)


def _next_status(ws) -> dict:
    for _ in range(20):
        msg = ws.receive_json()
        if msg["type"] == "status":
            return msg["data"]
    raise AssertionError("no status event received")


def test_ws_pause_and_resume_commands_update_session_state(app) -> None:
    main, client = app
    with _session(client) as sid, client.websocket_connect(f"/ws/{sid}") as ws:
        ws.send_json({"type": "pause"})
        assert _next_status(ws)["paused"] is True
        ws.send_json({"type": "resume"})
        assert _next_status(ws)["paused"] is False


def test_ws_reset_scene_command_clears_graph(app) -> None:
    main, client = app
    with _session(client) as sid:
        session = main.sessions[sid]
        session.scene.graph.meta.revision = 7
        with client.websocket_connect(f"/ws/{sid}") as ws:
            ws.send_json({"type": "reset_scene"})
            _next_status(ws)
            assert session.scene.graph.meta.revision == 0


def test_ws_disconnect_unsubscribes_all_handlers(app) -> None:
    main, client = app
    with _session(client) as sid:
        before = {topic: len(main.bus._subs[topic]) for topic in main._WS_TOPICS}
        with client.websocket_connect(f"/ws/{sid}"):
            during = {topic: len(main.bus._subs[topic]) for topic in main._WS_TOPICS}
            assert all(during[t] == before[t] + 1 for t in main._WS_TOPICS)
        after = {topic: len(main.bus._subs[topic]) for topic in main._WS_TOPICS}
        assert after == before


def test_ws_reconnect_after_disconnect_resubscribes_cleanly(app) -> None:
    main, client = app
    with _session(client) as sid:
        before = {topic: len(main.bus._subs[topic]) for topic in main._WS_TOPICS}
        with client.websocket_connect(f"/ws/{sid}"):
            pass
        with client.websocket_connect(f"/ws/{sid}"):
            during = {topic: len(main.bus._subs[topic]) for topic in main._WS_TOPICS}
            assert all(during[t] == before[t] + 1 for t in main._WS_TOPICS)
        after = {topic: len(main.bus._subs[topic]) for topic in main._WS_TOPICS}
        assert after == before


def test_ws_requires_api_key_when_configured(tmp_path, monkeypatch) -> None:
    main, config = _load_app(tmp_path, monkeypatch, API_KEY="secret")
    try:
        with TestClient(main.app) as client:
            with _session(client, **{"X-API-Key": "secret"}) as sid:
                with client.websocket_connect(f"/ws/{sid}?api_key=wrong") as ws:
                    with pytest.raises(WebSocketDisconnect):
                        ws.receive_json()
                with client.websocket_connect(f"/ws/{sid}?api_key=secret"):
                    pass
    finally:
        config.get_config.cache_clear()
