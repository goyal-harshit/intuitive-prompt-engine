"""API surface tests that do not require a webcam or network.

Uses FastAPI's TestClient against a fresh app instance whose data directory is
redirected to a temp path, so tests never touch the real ``data/`` folder.
"""

import importlib

import pytest
from fastapi.testclient import TestClient


def _load_app(tmp_path, monkeypatch, **env):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PROMPTING_STRATEGY", "template")  # never probe the network
    # Isolate from whatever a developer's real .env on disk might set.
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.delenv("RATE_LIMIT_PER_MINUTE", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    import backend.core.config as config

    config.get_config.cache_clear()
    # Re-import the app module so its module-level config/repo pick up DATA_DIR.
    main = importlib.import_module("backend.app.main")
    return importlib.reload(main), config


@pytest.fixture()
def client(tmp_path, monkeypatch):
    main, config = _load_app(tmp_path, monkeypatch)
    try:
        with TestClient(main.app) as c:
            yield c
    finally:
        config.get_config.cache_clear()


def test_health(client) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "imagegen" in body and "prompting" in body


def test_health_schema_is_formal(client) -> None:
    body = client.get("/api/health").json()
    assert set(body) == {
        "status",
        "version",
        "uptime_s",
        "active_sessions",
        "imagegen",
        "prompting",
    }
    assert body["version"]
    assert body["uptime_s"] >= 0
    assert body["active_sessions"] == 0


def test_rate_limit_off_by_default(client) -> None:
    # With no RATE_LIMIT_PER_MINUTE configured, POSTs are never throttled.
    for _ in range(10):
        assert client.post("/api/session/nope/generate").status_code == 404


def test_rate_limit_returns_429_when_exceeded(tmp_path, monkeypatch) -> None:
    main, config = _load_app(tmp_path, monkeypatch, RATE_LIMIT_PER_MINUTE="3")
    try:
        with TestClient(main.app) as c:
            # The limiter counts POSTs before routing, so a 404 endpoint is a
            # camera-free way to exercise it.
            for _ in range(3):
                assert c.post("/api/session/nope/generate").status_code == 404
            resp = c.post("/api/session/nope/generate")
            assert resp.status_code == 429
            assert resp.json()["error"]["code"] == "RATE_LIMITED"
            assert int(resp.headers["Retry-After"]) >= 1
            # GETs are never rate-limited.
            assert c.get("/api/health").status_code == 200
    finally:
        config.get_config.cache_clear()


def test_config_endpoint(client) -> None:
    resp = client.get("/api/config")
    assert resp.status_code == 200
    cfg = resp.json()
    assert cfg["imagegen"]["backend"] in {"pollinations", "huggingface", "comfyui"}
    assert "server" in cfg


def test_config_endpoint_redacts_data_dir(client) -> None:
    assert "data_dir" not in client.get("/api/config").json()


def test_cors_preflight_allows_configured_origin(client) -> None:
    resp = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_api_open_by_default(client) -> None:
    # No API_KEY configured (the local/dev default) -> no auth required.
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/config").status_code == 200


def test_api_key_required_when_configured(tmp_path, monkeypatch) -> None:
    main, config = _load_app(tmp_path, monkeypatch, API_KEY="secret")
    try:
        with TestClient(main.app) as c:
            assert c.get("/api/config").status_code == 401
            assert c.get("/api/config", headers={"X-API-Key": "wrong"}).status_code == 401
            assert c.get("/api/config", headers={"X-API-Key": "secret"}).status_code == 200
            # health stays open so uptime monitors don't need the key
            assert c.get("/api/health").status_code == 200
    finally:
        config.get_config.cache_clear()


def test_unknown_session_is_404(client) -> None:
    for path in (
        "/api/session/does-not-exist/scene",
        "/api/session/does-not-exist/generations",
    ):
        assert client.get(path).status_code == 404


def test_force_generate_unknown_session_is_404(client) -> None:
    assert client.post("/api/session/nope/generate").status_code == 404


def test_missing_image_is_404(client) -> None:
    assert client.get("/api/images/not-a-real-id").status_code == 404


def test_frontend_index_served(client) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_openapi_schema(client) -> None:
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    assert "/api/health" in resp.json()["paths"]
