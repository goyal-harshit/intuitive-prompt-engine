"""Structured logging: readable text for local dev, JSON-lines for anything
that ships logs to an aggregator (Loki/CloudWatch/etc — all free-tier capable
since this only ever emits plain JSON to stdout, no vendor SDK involved).

Toggle with LOG_FORMAT=json|text (default: text). Call sites attach structured
context via the stdlib `extra={...}` kwarg; recognized keys are pulled onto
the JSON record, everything else behaves like normal logging.
"""

from __future__ import annotations

import json
import logging
import os
import time

_STRUCTURED_FIELDS = (
    "session_id",
    "backend",
    "latency_ms",
    "code",
    "idle_s",
    "prompter",
    "imagegen",
)


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in _STRUCTURED_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    use_json = os.environ.get("LOG_FORMAT", "text").lower() == "json"
    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonLogFormatter()
        if use_json
        else logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
