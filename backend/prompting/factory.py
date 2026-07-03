"""Prompt strategy selection: explicit config or auto-detection."""
from __future__ import annotations

from backend.core.config import PromptingConfig
from backend.prompting.base import PromptGenerator
from backend.prompting.ollama_gen import OllamaPromptGenerator, ollama_available
from backend.prompting.template import TemplatePromptGenerator


async def create_prompt_generator(cfg: PromptingConfig) -> PromptGenerator:
    if cfg.strategy == "template":
        return TemplatePromptGenerator()
    if cfg.strategy == "ollama":
        return OllamaPromptGenerator(cfg)
    # auto
    if await ollama_available(cfg):
        return OllamaPromptGenerator(cfg)
    return TemplatePromptGenerator()
