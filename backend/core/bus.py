"""In-process async pub/sub event bus.

Mirrors a broker-style API so a Redis/NATS implementation can replace it
without changing publishers or subscribers.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Awaitable, Callable

Handler = Callable[[Any], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, topic: str, handler: Handler) -> None:
        self._subs[topic].append(handler)

    async def publish(self, topic: str, payload: Any) -> None:
        for handler in self._subs.get(topic, []):
            try:
                await handler(payload)
            except Exception:  # noqa: BLE001 — one bad subscriber must not kill the pipeline
                import logging

                logging.getLogger(__name__).exception("handler failed on %s", topic)

    def publish_threadsafe(self, loop: asyncio.AbstractEventLoop, topic: str, payload: Any) -> None:
        asyncio.run_coroutine_threadsafe(self.publish(topic, payload), loop)


class Topics:
    LANDMARKS = "landmarks"
    FEATURES = "features"
    PRIMITIVE = "primitive"
    INTENT = "intent"
    SCENE_UPDATE = "scene_update"
    GENERATION_STARTED = "generation_started"
    GENERATION_DONE = "generation_done"
    STATUS = "status"
    ERROR = "error"
