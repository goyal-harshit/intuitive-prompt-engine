"""Typed application configuration loaded from config.yaml with env overrides."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]


class CameraConfig(BaseModel):
    index: int = 0
    width: int = 640
    height: int = 480
    fps: int = 30


class VisionConfig(BaseModel):
    hands: bool = True
    pose: bool = True
    face: bool = True


class IntentConfig(BaseModel):
    window_s: float = 1.5
    decay_half_life_s: float = 90.0
    min_confidence: float = 0.35


class SceneConfig(BaseModel):
    completeness_threshold: float = 0.6
    stability_s: float = 2.0
    regen_diff: float = 0.25


class PromptingConfig(BaseModel):
    strategy: str = "auto"  # auto | template | ollama
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b"


class HFConfig(BaseModel):
    model: str = "stabilityai/stable-diffusion-xl-base-1.0"
    token_env: str = "HF_TOKEN"


class ComfyUIConfig(BaseModel):
    url: str = "http://127.0.0.1:8188"
    workflow: str = "sdxl_default"


class ImageGenConfig(BaseModel):
    backend: str = "pollinations"  # pollinations | huggingface | comfyui
    width: int = 1024
    height: int = 768
    huggingface: HFConfig = Field(default_factory=HFConfig)
    comfyui: ComfyUIConfig = Field(default_factory=ComfyUIConfig)


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000


class AppConfig(BaseModel):
    camera: CameraConfig = Field(default_factory=CameraConfig)
    vision: VisionConfig = Field(default_factory=VisionConfig)
    intent: IntentConfig = Field(default_factory=IntentConfig)
    scene: SceneConfig = Field(default_factory=SceneConfig)
    prompting: PromptingConfig = Field(default_factory=PromptingConfig)
    imagegen: ImageGenConfig = Field(default_factory=ImageGenConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    data_dir: Path = ROOT / "data"


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    path = ROOT / "config.yaml"
    raw = yaml.safe_load(path.read_text()) if path.exists() else {}
    cfg = AppConfig.model_validate(raw or {})
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    (cfg.data_dir / "images").mkdir(exist_ok=True)
    return cfg
