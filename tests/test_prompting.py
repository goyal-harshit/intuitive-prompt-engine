"""Prompt generation strategies: deterministic template output, Ollama with
template fallback on failure, and auto-strategy selection.

Network calls are faked at the httpx.AsyncClient level so these tests run
offline and deterministically.
"""

from __future__ import annotations

import httpx
import pytest

from backend.core.config import PromptingConfig
from backend.prompting.factory import create_prompt_generator
from backend.prompting.ollama_gen import OllamaPromptGenerator, ollama_available
from backend.prompting.template import TemplatePromptGenerator
from backend.scene.schema import AttributeValue, SceneGraph, SceneObject


def _graph() -> SceneGraph:
    return SceneGraph(
        objects={
            "o1": SceneObject(
                id="o1",
                category="celestial",
                salience=0.9,
                attributes={"color": AttributeValue(value="pale blue", confidence=0.8)},
            ),
            "o2": SceneObject(id="o2", category="tree", salience=0.2),
        },
        globals={
            "lighting": AttributeValue(value="golden hour", confidence=0.9),
            "mood": AttributeValue(value="serene", confidence=0.1),  # below threshold
            "artistic_style": AttributeValue(value="watercolor", confidence=0.7),
        },
    )


class _FakeResponse:
    def __init__(self, status_code: int = 200, json_data: dict | None = None) -> None:
        self.status_code = status_code
        self._json = json_data or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "boom",
                request=httpx.Request("GET", "http://x"),
                response=httpx.Response(self.status_code),
            )

    def json(self) -> dict:
        return self._json


class _FakeAsyncClient:
    response: _FakeResponse = _FakeResponse()
    raises: Exception | None = None

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        pass

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, *exc) -> bool:  # noqa: ANN002
        return False

    async def get(self, url: str, **kwargs) -> _FakeResponse:  # noqa: ANN003
        if _FakeAsyncClient.raises:
            raise _FakeAsyncClient.raises
        return _FakeAsyncClient.response

    async def post(self, url: str, **kwargs) -> _FakeResponse:  # noqa: ANN003
        if _FakeAsyncClient.raises:
            raise _FakeAsyncClient.raises
        return _FakeAsyncClient.response


@pytest.fixture(autouse=True)
def _fake_httpx(monkeypatch):
    _FakeAsyncClient.response = _FakeResponse()
    _FakeAsyncClient.raises = None
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    yield


# ---------- Template strategy ----------


async def test_template_orders_subjects_by_salience_then_globals_then_style_and_quality() -> None:
    gen = TemplatePromptGenerator()
    prompt = gen.generate  # keep reference; call below to exercise real coroutine
    result = await prompt(_graph())
    assert result.generator == "template"
    parts = result.positive.split(", ")
    # celestial (salience .9) before tree (salience .2)
    assert parts.index("a luminous celestial body") < parts.index("a tree")
    # confident global (lighting) present, low-confidence global (mood) filtered out
    assert "golden hour" in result.positive
    assert "serene" not in result.positive
    # style then quality tag trail the prompt
    assert result.positive.endswith(
        "watercolor, highly detailed, sharp focus, professional composition, 8k"
    )


async def test_template_defaults_style_when_none_confident() -> None:
    graph = _graph()
    graph.globals["artistic_style"].confidence = 0.1
    result = await TemplatePromptGenerator().generate(graph)
    assert "cinematic digital painting" in result.positive


# ---------- Ollama strategy ----------


async def test_ollama_uses_llm_response_when_available() -> None:
    _FakeAsyncClient.response = _FakeResponse(
        json_data={"message": {"content": '"a serene watercolor scene, golden hour"'}}
    )
    gen = OllamaPromptGenerator(PromptingConfig())
    result = await gen.generate(_graph())
    assert result.generator == "ollama"
    assert result.positive == "a serene watercolor scene, golden hour"


async def test_ollama_falls_back_to_template_on_request_failure() -> None:
    _FakeAsyncClient.raises = httpx.ConnectError("connection refused")
    gen = OllamaPromptGenerator(PromptingConfig())
    result = await gen.generate(_graph())
    assert result.generator == "template"


async def test_ollama_falls_back_to_template_on_empty_response() -> None:
    _FakeAsyncClient.response = _FakeResponse(json_data={"message": {"content": "   "}})
    gen = OllamaPromptGenerator(PromptingConfig())
    result = await gen.generate(_graph())
    assert result.generator == "template"


async def test_ollama_available_true_on_200() -> None:
    _FakeAsyncClient.response = _FakeResponse(status_code=200)
    assert await ollama_available(PromptingConfig()) is True


async def test_ollama_available_false_on_connection_error() -> None:
    _FakeAsyncClient.raises = httpx.ConnectError("nope")
    assert await ollama_available(PromptingConfig()) is False


# ---------- Factory / auto strategy ----------


async def test_factory_returns_template_when_configured() -> None:
    gen = await create_prompt_generator(PromptingConfig(strategy="template"))
    assert isinstance(gen, TemplatePromptGenerator)


async def test_factory_returns_ollama_when_configured() -> None:
    gen = await create_prompt_generator(PromptingConfig(strategy="ollama"))
    assert isinstance(gen, OllamaPromptGenerator)


async def test_factory_auto_picks_ollama_when_reachable() -> None:
    _FakeAsyncClient.response = _FakeResponse(status_code=200)
    gen = await create_prompt_generator(PromptingConfig(strategy="auto"))
    assert isinstance(gen, OllamaPromptGenerator)


async def test_factory_auto_falls_back_to_template_when_ollama_unreachable() -> None:
    _FakeAsyncClient.raises = httpx.ConnectError("nope")
    gen = await create_prompt_generator(PromptingConfig(strategy="auto"))
    assert isinstance(gen, TemplatePromptGenerator)
