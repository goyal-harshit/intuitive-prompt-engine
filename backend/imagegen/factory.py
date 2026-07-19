"""Image backend selection from config, with automatic failover.

The configured ``imagegen.backend`` is always tried first. Any other backend
that is actually usable on this host (e.g. huggingface when HF_TOKEN is set)
is appended as a fallback, so a single backend's outage — like Pollinations
returning 500s — doesn't stop image generation.
"""

from __future__ import annotations

import logging
from pathlib import Path

from backend.core.config import ImageGenConfig
from backend.imagegen.base import ImageGenerator
from backend.imagegen.comfyui import ComfyUIGenerator
from backend.imagegen.fallback import FallbackImageGenerator
from backend.imagegen.hf_api import HuggingFaceGenerator
from backend.imagegen.pollinations import PollinationsGenerator

log = logging.getLogger(__name__)

# Backends probed as fallbacks in addition to whichever one is configured.
# Each _build must fail fast when its backend is unusable on this host
# (HF: no token; ComfyUI: server unreachable) so unusable ones are skipped.
_AUTO_FALLBACK_ORDER = ("pollinations", "huggingface", "comfyui")


def _build(backend: str, cfg: ImageGenConfig, images_dir: Path) -> ImageGenerator:
    if backend == "pollinations":
        return PollinationsGenerator(images_dir)
    if backend == "huggingface":
        return HuggingFaceGenerator(images_dir, cfg.huggingface)
    if backend == "comfyui":
        return ComfyUIGenerator(images_dir, cfg.comfyui)
    raise ValueError(f"unknown imagegen backend: {backend}")


def create_image_generator(cfg: ImageGenConfig, images_dir: Path) -> ImageGenerator:
    chain: list[ImageGenerator] = []
    seen: set[str] = set()

    def add(backend: str) -> None:
        if backend in seen:
            return
        seen.add(backend)
        try:
            chain.append(_build(backend, cfg, images_dir))
        except Exception as exc:  # noqa: BLE001 — backend unusable here, skip it
            log.info(
                "imagegen backend %r unavailable, skipping: %s",
                backend,
                exc,
                extra={"backend": backend},
            )

    add(cfg.backend)
    for backend in _AUTO_FALLBACK_ORDER:
        add(backend)

    if not chain:
        raise RuntimeError(
            "no usable image generation backend (check IMAGEGEN_BACKEND / HF_TOKEN configuration)"
        )
    return chain[0] if len(chain) == 1 else FallbackImageGenerator(chain)
