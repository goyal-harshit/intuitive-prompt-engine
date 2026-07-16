"""Pollinations.ai adapter — free, keyless, FLUX-based. Default for GPU-less setups."""

from __future__ import annotations

from urllib.parse import quote

import httpx

from backend.imagegen.base import ImageGenerator
from backend.prompting.base import OptimizedPrompt


class PollinationsGenerator(ImageGenerator):
    name = "pollinations"
    _BASE = "https://image.pollinations.ai/prompt/"

    async def _fetch(self, prompt: OptimizedPrompt, width: int, height: int) -> bytes:
        url = (
            f"{self._BASE}{quote(prompt.positive[:1500])}"
            f"?width={width}&height={height}&nologo=true&model=flux"
        )
        if prompt.seed is not None:
            url += f"&seed={prompt.seed}"
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.content
