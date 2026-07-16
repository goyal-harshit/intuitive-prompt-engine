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
    """Drop-in for httpx.AsyncClient that records calls instead of hitting the network.

    ``routes`` maps a URL substring to a response (first match wins) so
    multi-endpoint flows like ComfyUI's queue→poll→download can be scripted;
    unmatched URLs get the catch-all ``response``.
    """

    calls: list[tuple[str, str, dict]] = []
    response: _FakeResponse = _FakeResponse()
    routes: list[tuple[str, _FakeResponse]] = []

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        pass

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, *exc) -> bool:  # noqa: ANN002
        return False

    def _respond(self, method: str, url: str, kwargs: dict) -> _FakeResponse:
        _FakeAsyncClient.calls.append((method, url, kwargs))
        for pattern, response in _FakeAsyncClient.routes:
            if pattern in url:
                return response
        return _FakeAsyncClient.response

    async def get(self, url: str, **kwargs) -> _FakeResponse:  # noqa: ANN003
        return self._respond("GET", url, kwargs)

    async def post(self, url: str, **kwargs) -> _FakeResponse:  # noqa: ANN003
        return self._respond("POST", url, kwargs)


class _FakeSyncClient:
    """Fake for httpx.Client — only used by ComfyUI's reachability probe.

    Defaults to "server not running" so factory tests never depend on (or
    touch) a real local ComfyUI.
    """

    reachable: bool = False

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        pass

    def get(self, url: str, **kwargs) -> _FakeResponse:  # noqa: ANN003
        if not _FakeSyncClient.reachable:
            raise httpx.ConnectError("connection refused")
        return _FakeResponse()


@pytest.fixture(autouse=True)
def _fake_httpx(monkeypatch):
    _FakeAsyncClient.calls = []
    _FakeAsyncClient.response = _FakeResponse()
    _FakeAsyncClient.routes = []
    _FakeSyncClient.reachable = False
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(httpx, "Client", _FakeSyncClient)
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


# ---------- ComfyUI ----------


def _comfy_history(prompt_id: str = "p1") -> dict:
    return {
        prompt_id: {
            "status": {"status_str": "success"},
            "outputs": {
                "9": {"images": [{"filename": "gg_1.png", "subfolder": "", "type": "output"}]}
            },
        }
    }


def test_comfyui_unreachable_server_fails_fast(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="not reachable"):
        ComfyUIGenerator(tmp_path, ComfyUIConfig())


def test_comfyui_unknown_workflow_fails_fast(tmp_path) -> None:
    _FakeSyncClient.reachable = True
    with pytest.raises(RuntimeError, match="workflow"):
        ComfyUIGenerator(tmp_path, ComfyUIConfig(workflow="does-not-exist"))


async def test_comfyui_queue_poll_download_flow(tmp_path) -> None:
    _FakeSyncClient.reachable = True
    _FakeAsyncClient.routes = [
        ("/prompt", _FakeResponse(json_data={"prompt_id": "p1"})),
        ("/history/p1", _FakeResponse(json_data=_comfy_history())),
        ("/view", _FakeResponse(content=b"comfy-png")),
    ]
    gen = ComfyUIGenerator(tmp_path, ComfyUIConfig())
    img = await gen.generate(_prompt(seed=7), 640, 480)

    assert img.backend == "comfyui"
    assert Path(img.path).read_bytes() == b"comfy-png"

    queue_call = next(c for c in _FakeAsyncClient.calls if c[0] == "POST" and "/prompt" in c[1])
    workflow = queue_call[2]["json"]["prompt"]
    assert workflow["6"]["inputs"]["text"] == "a red fox in a forest"  # positive
    assert "blurry" in workflow["7"]["inputs"]["text"]  # negative default
    assert workflow["5"]["inputs"] == {"batch_size": 1, "width": 640, "height": 480}
    assert workflow["3"]["inputs"]["seed"] == 7

    view_call = next(c for c in _FakeAsyncClient.calls if "/view" in c[1])
    assert view_call[2]["params"]["filename"] == "gg_1.png"


async def test_comfyui_workflow_error_raises(tmp_path) -> None:
    _FakeSyncClient.reachable = True
    _FakeAsyncClient.routes = [
        ("/prompt", _FakeResponse(json_data={"prompt_id": "p1"})),
        (
            "/history/p1",
            _FakeResponse(json_data={"p1": {"status": {"status_str": "error"}, "outputs": {}}}),
        ),
    ]
    gen = ComfyUIGenerator(tmp_path, ComfyUIConfig())
    with pytest.raises(RuntimeError, match="workflow failed"):
        await gen.generate(_prompt(), 512, 512)


async def test_comfyui_polling_times_out(tmp_path) -> None:
    _FakeSyncClient.reachable = True
    _FakeAsyncClient.routes = [
        ("/prompt", _FakeResponse(json_data={"prompt_id": "p1"})),
        ("/history/p1", _FakeResponse(json_data={})),  # never produces outputs
    ]
    gen = ComfyUIGenerator(tmp_path, ComfyUIConfig(timeout_s=0.2))
    with pytest.raises(RuntimeError, match="timed out"):
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
