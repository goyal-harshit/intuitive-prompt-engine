"""Environment-variable overrides layered on top of config.yaml."""

import importlib

import backend.core.config as config


def _fresh(monkeypatch, **env) -> config.AppConfig:
    """Reload config with a patched environment and a cleared cache."""
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    config.get_config.cache_clear()
    try:
        return config.get_config()
    finally:
        config.get_config.cache_clear()


def test_defaults_without_env(monkeypatch) -> None:
    for key in config._ENV_OVERRIDES:
        monkeypatch.delenv(key, raising=False)
    cfg = _fresh(monkeypatch)
    assert cfg.server.host == "127.0.0.1"
    assert cfg.imagegen.backend == "pollinations"


def test_env_overrides_nested_fields(monkeypatch) -> None:
    cfg = _fresh(
        monkeypatch,
        SERVER_HOST="0.0.0.0",
        SERVER_PORT="9001",
        IMAGEGEN_BACKEND="huggingface",
        PROMPTING_STRATEGY="template",
        OLLAMA_URL="http://ollama:11434",
    )
    assert cfg.server.host == "0.0.0.0"
    assert cfg.server.port == 9001  # coerced from str to int
    assert cfg.imagegen.backend == "huggingface"
    assert cfg.prompting.strategy == "template"
    assert cfg.prompting.ollama_url == "http://ollama:11434"


def test_empty_env_value_is_ignored(monkeypatch) -> None:
    monkeypatch.setenv("IMAGEGEN_BACKEND", "")
    config.get_config.cache_clear()
    try:
        cfg = config.get_config()
    finally:
        config.get_config.cache_clear()
    assert cfg.imagegen.backend == "pollinations"


def test_data_dir_override(monkeypatch, tmp_path) -> None:
    target = tmp_path / "engine-data"
    cfg = _fresh(monkeypatch, DATA_DIR=str(target))
    assert cfg.data_dir == target
    assert target.exists()  # created on load
    assert (target / "images").exists()


def test_module_reimport_is_stable(monkeypatch) -> None:
    # Guard against import-time side effects breaking a reload.
    importlib.reload(config)
    assert hasattr(config, "get_config")


def test_cors_origins_default(monkeypatch) -> None:
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    cfg = _fresh(monkeypatch)
    assert "http://localhost:5173" in cfg.server.cors_origins


def test_cors_origins_env_override_splits_on_comma(monkeypatch) -> None:
    cfg = _fresh(monkeypatch, CORS_ORIGINS="https://a.example, https://b.example")
    assert cfg.server.cors_origins == ["https://a.example", "https://b.example"]


def test_session_ttl_env_override(monkeypatch) -> None:
    cfg = _fresh(monkeypatch, SESSION_TTL_S="60")
    assert cfg.server.session_ttl_s == 60
