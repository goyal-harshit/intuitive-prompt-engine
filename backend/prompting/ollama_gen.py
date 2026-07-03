"""LLM prompt strategy via Ollama (Qwen/Mistral). Falls back to template on failure."""
from __future__ import annotations

import logging

import httpx

from backend.core.config import PromptingConfig
from backend.prompting.base import OptimizedPrompt, PromptGenerator, graph_to_description
from backend.prompting.template import TemplatePromptGenerator
from backend.scene.schema import SceneGraph

log = logging.getLogger(__name__)

_SYSTEM = (
    "You are a prompt engineer for diffusion image models (SDXL/FLUX). "
    "Given a structured scene description, write ONE optimized positive prompt: "
    "comma-separated visual phrases, subject first, then environment, lighting, mood, "
    "camera, style, quality tags. No sentences, no explanations, under 80 words. "
    "Respond with the prompt only."
)


class OllamaPromptGenerator(PromptGenerator):
    name = "ollama"

    def __init__(self, cfg: PromptingConfig) -> None:
        self._cfg = cfg
        self._fallback = TemplatePromptGenerator()

    async def generate(self, graph: SceneGraph) -> OptimizedPrompt:
        description = graph_to_description(graph)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(f"{self._cfg.ollama_url}/api/chat", json={
                    "model": self._cfg.ollama_model,
                    "messages": [{"role": "system", "content": _SYSTEM},
                                 {"role": "user", "content": f"Scene: {description}"}],
                    "stream": False,
                })
                r.raise_for_status()
                text = r.json()["message"]["content"].strip().strip('"')
            if not text:
                raise ValueError("empty LLM response")
            return OptimizedPrompt(positive=text, generator=self.name)
        except Exception as exc:  # noqa: BLE001 — degrade, never block the pipeline
            log.warning("Ollama unavailable (%s); using template strategy", exc)
            return await self._fallback.generate(graph)


async def ollama_available(cfg: PromptingConfig) -> bool:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{cfg.ollama_url}/api/tags")
            return r.status_code == 200
    except Exception:  # noqa: BLE001
        return False
