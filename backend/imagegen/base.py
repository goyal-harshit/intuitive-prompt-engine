"""Image generation adapter interface."""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel

from backend.prompting.base import OptimizedPrompt


class GeneratedImage(BaseModel):
    id: str
    path: str
    backend: str
    prompt_positive: str
    latency_ms: int
    created_at: float


class ImageGenerator(ABC):
    name: str = "base"

    def __init__(self, images_dir: Path) -> None:
        self._dir = images_dir

    @abstractmethod
    async def _fetch(self, prompt: OptimizedPrompt, width: int, height: int) -> bytes: ...

    async def generate(self, prompt: OptimizedPrompt, width: int, height: int) -> GeneratedImage:
        start = time.monotonic()
        data = await self._fetch(prompt, width, height)
        image_id = f"img_{uuid.uuid4().hex[:10]}"
        path = self._dir / f"{image_id}.png"
        path.write_bytes(data)
        return GeneratedImage(
            id=image_id,
            path=str(path),
            backend=self.name,
            prompt_positive=prompt.positive,
            latency_ms=int((time.monotonic() - start) * 1000),
            created_at=time.time(),
        )
