"""Structured logging: JSON formatter field extraction and text/json toggle."""

from __future__ import annotations

import json
import logging

from backend.core.logging import JsonLogFormatter, configure_logging


def _make_record(**extra) -> logging.LogRecord:
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="generation complete",
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_json_formatter_includes_recognized_structured_fields() -> None:
    record = _make_record(session_id="ses_abc", backend="pollinations", latency_ms=42)
    payload = json.loads(JsonLogFormatter().format(record))
    assert payload["message"] == "generation complete"
    assert payload["level"] == "INFO"
    assert payload["session_id"] == "ses_abc"
    assert payload["backend"] == "pollinations"
    assert payload["latency_ms"] == 42


def test_json_formatter_omits_unset_structured_fields() -> None:
    record = _make_record(backend="ollama")
    payload = json.loads(JsonLogFormatter().format(record))
    assert "session_id" not in payload
    assert "latency_ms" not in payload
    assert payload["backend"] == "ollama"


def test_json_formatter_includes_exception_traceback() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        record = _make_record()
        record.exc_info = sys.exc_info()
    payload = json.loads(JsonLogFormatter().format(record))
    assert "ValueError: boom" in payload["exc_info"]


def test_configure_logging_defaults_to_text_formatter(monkeypatch) -> None:
    monkeypatch.delenv("LOG_FORMAT", raising=False)
    configure_logging()
    handler = logging.getLogger().handlers[0]
    assert not isinstance(handler.formatter, JsonLogFormatter)


def test_configure_logging_uses_json_formatter_when_requested(monkeypatch) -> None:
    monkeypatch.setenv("LOG_FORMAT", "json")
    configure_logging()
    handler = logging.getLogger().handlers[0]
    assert isinstance(handler.formatter, JsonLogFormatter)
