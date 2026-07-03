"""ComfyUI adapter placeholder (Phase 4): local SDXL/FLUX with img2img refinement.

Kept as a first-class adapter so enabling a local GPU later is a config change
(`imagegen.backend: comfyui`), not an architecture change.
"""
from __future__ import annotations

from pathlib import Path

from backend.core.config import ComfyUIConfig
from backend.imagegen.base import ImageGenerator
from backend.prompting.base import OptimizedPrompt


class ComfyUIGenerator(ImageGenerator):
    name = "comfyui"

    def __init__(self, images_dir: Path, cfg: ComfyUIConfig) -> None:
        super().__init__(images_dir)
        self._cfg = cfg

    async def _fetch(self, prompt: OptimizedPrompt, width: int, height: int) -> bytes:
        raise NotImplementedError(
            "ComfyUI adapter is scheduled for Phase 4 (see docs/ROADMAP.md). "
            "Use backend 'pollinations' or 'huggingface'."
        )
