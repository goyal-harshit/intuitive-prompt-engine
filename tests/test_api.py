"""API surface tests that do not require a webcam or network.

Uses FastAPI's TestClient against a fresh app instance whose data directory is
redirected to a temp path, so tests never touch the real ``data/`` folder.
"""
import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PROMPTING_STRATEGY", "template")  # never probe the network
    import backend.core.config as config

    config.get_config.cache_clear()
    # Re-import the app module so its module-level config/repo pick up DATA_DIR.
    main = importlib.import_module("backend.app.main")
    main = importlib.reload(main)
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


def test_config_endpoint(client) -> None:
    resp = client.get("/api/config")
    assert resp.status_code == 200
    cfg = resp.json()
    assert cfg["imagegen"]["backend"] in {"pollinations", "huggingface", "comfyui"}
    assert "server" in cfg


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
