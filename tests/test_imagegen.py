"""Image backend adapters: URL/payload construction and fallback chaining.

All network calls are faked at the httpx.AsyncClient level so these tests run
offline and deterministically.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from backend.core.config import ComfyUIConfig, HFConfig, ImageGenConfig
from backend.imagegen.base import ImageGenerator
from backend.imagegen.comfyui import ComfyUIGenerator
from backend.imagegen.factory import create_image_generator
from backend.imagegen.fallback import FallbackImageGenerator
from backend.imagegen.hf_api import HuggingFaceGenerator
from backend.imagegen.pollinations import PollinationsGenerator
from backend.prompting.base import OptimizedPrompt


class _FakeResponse:
    def __init__(
        self, content: bytes = b"fake-png", status_code: int = 200, json_data: dict | None = None
    ) -> None:
        self.content = content
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
    """Drop-in for httpx.AsyncClient that records calls instead of hitting the network."""

    calls: list[tuple[str, str, dict]] = []
    response: _FakeResponse = _FakeResponse()

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        pass

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, *exc) -> bool:  # noqa: ANN002
        return False

    async def get(self, url: str, **kwargs) -> _FakeResponse:  # noqa: ANN003
        _FakeAsyncClient.calls.append(("GET", url, kwargs))
        return _FakeAsyncClient.response

    async def post(self, url: str, **kwargs) -> _FakeResponse:  # noqa: ANN003
        _FakeAsyncClient.calls.append(("POST", url, kwargs))
        return _FakeAsyncClient.response


@pytest.fixture(autouse=True)
def _fake_httpx(monkeypatch):
    _FakeAsyncClient.calls = []
    _FakeAsyncClient.response = _FakeResponse()
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    yield


def _prompt(**kw) -> OptimizedPrompt:
    return OptimizedPrompt(positive="a red fox in a forest", **kw)


# ---------- Pollinations ----------


async def test_pollinations_url_building(tmp_path) -> None:
    gen = PollinationsGenerator(tmp_path)
    img = await gen.generate(_prompt(seed=42), 512, 384)
    assert img.backend == "pollinations"
    method, url, _ = _FakeAsyncClient.calls[-1]
    assert method == "GET"
    assert url.startswith("https://image.pollinations.ai/prompt/")
    assert "width=512" in url and "height=384" in url
    assert "model=flux" in url and "seed=42" in url


async def test_pollinations_omits_seed_when_unset(tmp_path) -> None:
    gen = PollinationsGenerator(tmp_path)
    await gen.generate(_prompt(), 512, 384)
    _, url, _ = _FakeAsyncClient.calls[-1]
    assert "seed=" not in url


async def test_pollinations_writes_image_file(tmp_path) -> None:
    _FakeAsyncClient.response = _FakeResponse(content=b"\x89PNG-bytes")
    gen = PollinationsGenerator(tmp_path)
    img = await gen.generate(_prompt(), 256, 256)
    assert Path(img.path).read_bytes() == b"\x89PNG-bytes"


# ---------- Hugging Face ----------


def test_huggingface_requires_token(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("HF_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        HuggingFaceGenerator(tmp_path, HFConfig())


async def test_huggingface_sends_bearer_token_and_params(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HF_TOKEN", "tok_123")
    gen = HuggingFaceGenerator(tmp_path, HFConfig())
    await gen.generate(_prompt(guidance=9.0, steps=25), 768, 512)
    method, url, kwargs = _FakeAsyncClient.calls[-1]
    assert method == "POST"
    assert "stabilityai/stable-diffusion-xl-base-1.0" in url
    assert kwargs["headers"]["Authorization"] == "Bearer tok_123"
    assert kwargs["json"]["parameters"]["guidance_scale"] == 9.0
    assert kwargs["json"]["parameters"]["num_inference_steps"] == 25
    assert kwargs["json"]["parameters"]["width"] == 768


# ---------- ComfyUI (Phase 4 placeholder) ----------


async def test_comfyui_adapter_is_not_yet_implemented(tmp_path) -> None:
    gen = ComfyUIGenerator(tmp_path, ComfyUIConfig())
    with pytest.raises(NotImplementedError):
        await gen.generate(_prompt(), 512, 512)


# ---------- Fallback chain ----------


async def test_fallback_generator_uses_first_success(tmp_path) -> None:
    class _Boom(ImageGenerator):
        name = "boom"

        async def _fetch(self, prompt, width, height):  # noqa: ANN001
            raise RuntimeError("backend down")

    class _Ok(ImageGenerator):
        name = "ok"

        async def _fetch(self, prompt, width, height):  # noqa: ANN001
            return b"ok-bytes"

    chain = FallbackImageGenerator([_Boom(tmp_path), _Ok(tmp_path)])
    img = await chain.generate(_prompt(), 100, 100)
    assert img.backend == "ok"


async def test_fallback_generator_raises_when_everything_fails(tmp_path) -> None:
    class _AlwaysBoom(ImageGenerator):
        name = "boom"

        async def _fetch(self, prompt, width, height):  # noqa: ANN001
            raise RuntimeError("nope")

    chain = FallbackImageGenerator([_AlwaysBoom(tmp_path)])
    with pytest.raises(RuntimeError):
        await chain.generate(_prompt(), 100, 100)


def test_fallback_generator_requires_nonempty_chain(tmp_path) -> None:
    with pytest.raises(ValueError):
        FallbackImageGenerator([])


# ---------- Factory ----------


def test_factory_builds_configured_backend_with_fallback(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("HF_TOKEN", raising=False)
    gen = create_image_generator(ImageGenConfig(backend="pollinations"), tmp_path)
    # only pollinations is usable (no HF_TOKEN) -> single generator, no wrapper needed
    assert gen.name == "pollinations"


def test_factory_wraps_in_fallback_when_multiple_backends_usable(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HF_TOKEN", "tok")
    gen = create_image_generator(ImageGenConfig(backend="huggingface"), tmp_path)
    assert isinstance(gen, FallbackImageGenerator)
    assert [g.name for g in gen._chain] == ["huggingface", "pollinations"]


def test_factory_falls_back_when_configured_backend_is_unknown(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("HF_TOKEN", raising=False)
    # an unknown primary backend is skipped (logged), not raised — the auto
    # fallback order still yields a usable generator (pollinations).
    gen = create_image_generator(ImageGenConfig(backend="not-a-backend"), tmp_path)
    assert gen.name == "pollinations"
