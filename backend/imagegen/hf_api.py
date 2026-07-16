"""Hugging Face Inference API adapter (SDXL etc.). Requires HF_TOKEN env var."""

from __future__ import annotations

import os
from pathlib import Path

import httpx

from backend.core.config import HFConfig
from backend.imagegen.base import ImageGenerator
from backend.prompting.base import OptimizedPrompt


class HuggingFaceGenerator(ImageGenerator):
    name = "huggingface"

    def __init__(self, images_dir: Path, cfg: HFConfig) -> None:
        super().__init__(images_dir)
        self._cfg = cfg
        token = os.environ.get(cfg.token_env)
        if not token:
            raise RuntimeError(f"env var {cfg.token_env} not set")
        self._headers = {"Authorization": f"Bearer {token}"}

    async def _fetch(self, prompt: OptimizedPrompt, width: int, height: int) -> bytes:
        async with httpx.AsyncClient(timeout=180.0) as client:
            r = await client.post(
                f"https://api-inference.huggingface.co/models/{self._cfg.model}",
                headers=self._headers,
                json={
                    "inputs": prompt.positive,
                    "parameters": {
                        "negative_prompt": prompt.negative,
                        "guidance_scale": prompt.guidance,
                        "num_inference_steps": prompt.steps,
                        "width": width,
                        "height": height,
                    },
                },
            )
            r.raise_for_status()
            return r.content
