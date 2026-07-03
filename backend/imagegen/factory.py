"""Image backend selection from config."""
from __future__ import annotations

from pathlib import Path

from backend.core.config import ImageGenConfig
from backend.imagegen.base import ImageGenerator
from backend.imagegen.comfyui import ComfyUIGenerator
from backend.imagegen.hf_api import HuggingFaceGenerator
from backend.imagegen.pollinations import PollinationsGenerator


def create_image_generator(cfg: ImageGenConfig, images_dir: Path) -> ImageGenerator:
    if cfg.backend == "pollinations":
        return PollinationsGenerator(images_dir)
    if cfg.backend == "huggingface":
        return HuggingFaceGenerator(images_dir, cfg.huggingface)
    if cfg.backend == "comfyui":
        return ComfyUIGenerator(images_dir, cfg.comfyui)
    raise ValueError(f"unknown imagegen backend: {cfg.backend}")
