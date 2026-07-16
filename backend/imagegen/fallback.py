"""Automatic failover across image backends.

Tries each backend in the chain in order and returns the first success.
Only raises once every backend has failed — the pipeline keeps running
instead of surfacing a single backend's outage as a hard error.
"""

from __future__ import annotations

import logging

from backend.imagegen.base import GeneratedImage, ImageGenerator
from backend.prompting.base import OptimizedPrompt

log = logging.getLogger(__name__)


class FallbackImageGenerator(ImageGenerator):
    name = "fallback"

    def __init__(self, chain: list[ImageGenerator]) -> None:
        if not chain:
            raise ValueError("fallback chain must have at least one generator")
        super().__init__(chain[0]._dir)
        self._chain = chain

    async def generate(self, prompt: OptimizedPrompt, width: int, height: int) -> GeneratedImage:
        errors: list[str] = []
        for gen in self._chain:
            try:
                image = await gen.generate(prompt, width, height)
                if errors:
                    log.warning(
                        "imagegen: fell back to %s after failures: %s",
                        gen.name,
                        "; ".join(errors),
                        extra={"backend": gen.name},
                    )
                return image
            except Exception as exc:  # noqa: BLE001 — try the next backend in the chain
                log.warning(
                    "imagegen backend %s failed: %s", gen.name, exc, extra={"backend": gen.name}
                )
                errors.append(f"{gen.name}: {exc}")
        raise RuntimeError(f"all image backends failed ({'; '.join(errors)})")

    async def _fetch(self, prompt: OptimizedPrompt, width: int, height: int) -> bytes:
        raise NotImplementedError("FallbackImageGenerator overrides generate() directly")
