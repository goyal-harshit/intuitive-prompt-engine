"""EventBus subscribe/unsubscribe behavior (the WS handler leak fix relies on this)."""

import asyncio

from backend.core.bus import EventBus


def test_unsubscribed_handler_is_not_called() -> None:
    bus = EventBus()
    calls = []

    async def handler(payload) -> None:
        calls.append(payload)

    async def scenario() -> None:
        bus.subscribe("topic", handler)
        await bus.publish("topic", "first")
        bus.unsubscribe("topic", handler)
        await bus.publish("topic", "second")

    asyncio.run(scenario())
    assert calls == ["first"]


def test_unsubscribe_unknown_handler_is_a_noop() -> None:
    bus = EventBus()

    async def handler(payload) -> None:  # noqa: ARG001
        pass

    bus.unsubscribe("topic", handler)  # never subscribed — must not raise


def test_multiple_subscribers_independent_unsubscribe() -> None:
    bus = EventBus()
    a_calls, b_calls = [], []

    async def a(payload) -> None:
        a_calls.append(payload)

    async def b(payload) -> None:
        b_calls.append(payload)

    async def scenario() -> None:
        bus.subscribe("topic", a)
        bus.subscribe("topic", b)
        bus.unsubscribe("topic", a)
        await bus.publish("topic", "x")

    asyncio.run(scenario())
    assert a_calls == [] and b_calls == ["x"]
