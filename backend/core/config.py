"""Typed application configuration loaded from config.yaml with env overrides."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]

# Populate os.environ from a .env file for native (non-Docker) runs. Docker
# already injects env vars via compose; existing os.environ values win either
# way since load_dotenv() does not override by default.
load_dotenv(ROOT / ".env")


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
    # Named rule set under plugins/<name>/ontology.yaml (see docs/GESTURE_ONTOLOGY.md).
    ontology_pack: str = "default"


class GestureConfig(BaseModel):
    smoothing_alpha_position: float = 0.35
    smoothing_alpha_velocity: float = 0.5
    pinch_enter_threshold: float = 0.35
    pinch_exit_threshold: float = 0.55
    pinch_enter_hold_s: float = 0.12
    stroke_max_points: int = 400
    stroke_min_point_dist: float = 0.004
    shape_min_confidence: float = 0.45
    debug_emit_hz: float = 5.0


class FaceCalibrationConfig(BaseModel):
    enabled: bool = True
    calibration_duration_s: float = 3.0


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
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    session_ttl_s: float = 1800.0
    # Requests per minute per client IP for expensive POST endpoints
    # (session creation, forced generation). 0 disables the limiter — the
    # local/dev default; set it when exposing the backend publicly.
    rate_limit_per_minute: int = 0


class AppConfig(BaseModel):
    camera: CameraConfig = Field(default_factory=CameraConfig)
    vision: VisionConfig = Field(default_factory=VisionConfig)
    intent: IntentConfig = Field(default_factory=IntentConfig)
    gesture: GestureConfig = Field(default_factory=GestureConfig)
    face_calibration: FaceCalibrationConfig = Field(default_factory=FaceCalibrationConfig)
    scene: SceneConfig = Field(default_factory=SceneConfig)
    prompting: PromptingConfig = Field(default_factory=PromptingConfig)
    imagegen: ImageGenConfig = Field(default_factory=ImageGenConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    data_dir: Path = ROOT / "data"


# Environment overrides — deployment knobs a container/CI needs without editing
# config.yaml. Each maps an env var to a nested field applied after the YAML load.
# Kept deliberately small: these are the only settings that differ across hosts.
_ENV_OVERRIDES: dict[str, tuple[str, ...]] = {
    "DATA_DIR": ("data_dir",),
    "SERVER_HOST": ("server", "host"),
    "SERVER_PORT": ("server", "port"),
    "CORS_ORIGINS": ("server", "cors_origins"),
    "SESSION_TTL_S": ("server", "session_ttl_s"),
    "RATE_LIMIT_PER_MINUTE": ("server", "rate_limit_per_minute"),
    "IMAGEGEN_BACKEND": ("imagegen", "backend"),
    "ONTOLOGY_PACK": ("intent", "ontology_pack"),
    "PROMPTING_STRATEGY": ("prompting", "strategy"),
    "OLLAMA_URL": ("prompting", "ollama_url"),
}

# A handful of overrides target non-string fields; convert the raw env string
# before it lands in the config mapping instead of leaning on pydantic coercion
# (which cannot turn a comma-separated string into a list).
_ENV_TRANSFORMS: dict[str, Any] = {
    "CORS_ORIGINS": lambda v: [origin.strip() for origin in v.split(",") if origin.strip()],
}


def _apply_env_overrides(raw: dict) -> dict:
    """Overlay ``_ENV_OVERRIDES`` onto the raw config mapping (env wins)."""
    for env_var, path in _ENV_OVERRIDES.items():
        value = os.environ.get(env_var)
        if value is None or value == "":
            continue
        transform = _ENV_TRANSFORMS.get(env_var)
        typed_value: Any = transform(value) if transform else value
        node = raw
        for key in path[:-1]:
            node = node.setdefault(key, {})
            if not isinstance(node, dict):  # a scalar in YAML shadowing a section
                raise ValueError(f"config key {'.'.join(path)} is not a mapping")
        node[path[-1]] = typed_value
    return raw


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    path = ROOT / "config.yaml"
    raw = yaml.safe_load(path.read_text()) if path.exists() else {}
    raw = _apply_env_overrides(raw or {})
    cfg = AppConfig.model_validate(raw)
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    (cfg.data_dir / "images").mkdir(exist_ok=True)
    return cfg
